"""
SQLite-backed user data layer for Sage — accounts, profiles, medical info,
cycle info, craving map, pantry, feedback, and interaction log. Replaces the
old per-file JSON memory (cycle_memory.json, feedback_memory.json,
interaction_log.jsonl) with per-user rows in a single local database, since
the app now supports more than one profile.

Local, single-user, non-commercial tool — stdlib sqlite3 + hashlib password
hashing is adequate here; this is not hardened for public multi-tenant use.
"""
import sqlite3
import hashlib
import secrets
import json
from pathlib import Path
from datetime import date, datetime, timedelta

DB_PATH = Path(__file__).with_name("sage.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    salt TEXT NOT NULL,
    created_at TEXT NOT NULL,
    onboarding_completed INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS profiles (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    name TEXT, age INTEGER, gender TEXT, height TEXT, weight TEXT
);

CREATE TABLE IF NOT EXISTS medical_info (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    medical_conditions TEXT,
    allergies TEXT,
    dietary_style TEXT,
    sweet_savory TEXT,
    spice_tolerance TEXT,
    preference_notes TEXT
);

CREATE TABLE IF NOT EXISTS cycle_info (
    user_id INTEGER PRIMARY KEY REFERENCES users(id),
    cycle_length INTEGER,
    last_period_date TEXT
);

CREATE TABLE IF NOT EXISTS craving_map (
    user_id INTEGER REFERENCES users(id),
    mood TEXT,
    craving TEXT,
    PRIMARY KEY (user_id, mood)
);

CREATE TABLE IF NOT EXISTS pantry_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    item_name TEXT NOT NULL,
    quantity TEXT,
    added_date TEXT NOT NULL,
    used INTEGER DEFAULT 0,
    used_date TEXT
);

CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    date TEXT, restaurant TEXT, dish_name TEXT, liked INTEGER,
    cuisine TEXT, indulgent TEXT, vibe TEXT, phase TEXT
);

CREATE TABLE IF NOT EXISTS interaction_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER REFERENCES users(id),
    timestamp TEXT, user_text TEXT, phase TEXT, mode TEXT,
    restaurant TEXT, dish_name TEXT, cuisine_confidence TEXT,
    nutrition_found INTEGER, nutrition_source TEXT
);

CREATE TABLE IF NOT EXISTS sessions (
    token TEXT PRIMARY KEY,
    user_id INTEGER NOT NULL REFERENCES users(id),
    last_active_at TEXT NOT NULL,
    user_location TEXT,
    user_city TEXT,
    chat_state TEXT,
    current_chat_id INTEGER
);

CREATE TABLE IF NOT EXISTS chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    title TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    state TEXT NOT NULL
);
"""

SESSION_TIMEOUT_MINUTES = 10


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db() -> None:
    conn = get_connection()
    conn.executescript(SCHEMA)
    # Migration for databases created before onboarding_completed existed —
    # CREATE TABLE IF NOT EXISTS above only applies to brand-new tables, so
    # an existing users table needs the column added separately.
    try:
        conn.execute("ALTER TABLE users ADD COLUMN onboarding_completed INTEGER NOT NULL DEFAULT 0")
    except sqlite3.OperationalError:
        pass  # column already exists
    for column in ("user_location TEXT", "user_city TEXT", "chat_state TEXT", "current_chat_id INTEGER"):
        try:
            conn.execute(f"ALTER TABLE sessions ADD COLUMN {column}")
        except sqlite3.OperationalError:
            pass  # column already exists
    conn.commit()
    conn.close()


# -----------------------------------------------------------------------------
# AUTH
# -----------------------------------------------------------------------------
def _hash_password(password: str, salt: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 200_000).hex()


def create_user(username: str, password: str) -> int | None:
    """Returns the new user_id, or None if the username is already taken."""
    conn = get_connection()
    try:
        salt = secrets.token_hex(16)
        pw_hash = _hash_password(password, salt)
        cur = conn.execute(
            "INSERT INTO users (username, password_hash, salt, created_at) VALUES (?, ?, ?, ?)",
            (username, pw_hash, salt, datetime.now().isoformat()),
        )
        conn.commit()
        return cur.lastrowid
    except sqlite3.IntegrityError:
        return None
    finally:
        conn.close()


def verify_login(username: str, password: str) -> int | None:
    """Returns the user_id on success, or None if the username/password is wrong."""
    conn = get_connection()
    row = conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    conn.close()
    if not row:
        return None
    if _hash_password(password, row["salt"]) == row["password_hash"]:
        return row["id"]
    return None


def has_completed_onboarding(user_id: int) -> bool:
    """Explicit flag, set by mark_onboarding_complete() — NOT inferred from a
    profile row existing, since a profile is saved after just the first
    onboarding step. Using profile-existence as the signal meant closing the
    browser mid-onboarding (after Basics but before Medical/Cycle/Craving
    Map) would make the next login skip straight to the main chat with an
    incomplete profile."""
    conn = get_connection()
    row = conn.execute("SELECT onboarding_completed FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()
    return bool(row and row["onboarding_completed"])


def mark_onboarding_complete(user_id: int) -> None:
    conn = get_connection()
    conn.execute("UPDATE users SET onboarding_completed = 1 WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()


def resume_onboarding_step(user_id: int) -> str:
    """For a user who started but didn't finish onboarding, figures out
    which step to resume at instead of making them redo everything from
    Basics. Mirrors the step order in app.py's render_onboarding()."""
    if not get_profile(user_id):
        return "basics"
    if not get_medical_info(user_id):
        return "medical"
    profile = get_profile(user_id)
    if profile.get("gender") == "Female" and not get_cycle_info(user_id):
        return "cycle"
    return "craving_map"


# -----------------------------------------------------------------------------
# SESSIONS — lets login survive a page reload without logging out every time,
# while still expiring after real inactivity. The token itself is stored
# client-side in the browser's localStorage (see app.py); this table is the
# server-side source of truth for whether it's still valid.
# -----------------------------------------------------------------------------
def create_session(user_id: int) -> str:
    token = secrets.token_hex(32)
    conn = get_connection()
    conn.execute(
        "INSERT INTO sessions (token, user_id, last_active_at) VALUES (?, ?, ?)",
        (token, user_id, datetime.now().isoformat()),
    )
    conn.commit()
    conn.close()
    return token


def get_session_user(token: str) -> int | None:
    """Returns the user_id for a still-valid (not timed-out) token, or None
    if the token is missing/unknown/expired. An expired row is deleted here
    so stale sessions don't accumulate."""
    if not token:
        return None
    conn = get_connection()
    row = conn.execute("SELECT user_id, last_active_at FROM sessions WHERE token = ?", (token,)).fetchone()
    if not row:
        conn.close()
        return None
    last_active = datetime.fromisoformat(row["last_active_at"])
    if datetime.now() - last_active > timedelta(minutes=SESSION_TIMEOUT_MINUTES):
        conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None
    conn.close()
    return row["user_id"]


def touch_session(token: str) -> None:
    """Resets the inactivity clock — called on every active rerun so the
    10-minute timeout is measured from the last real interaction, not from
    login time."""
    if not token:
        return
    conn = get_connection()
    conn.execute("UPDATE sessions SET last_active_at = ? WHERE token = ?", (datetime.now().isoformat(), token))
    conn.commit()
    conn.close()


def delete_session(token: str) -> None:
    if not token:
        return
    conn = get_connection()
    conn.execute("DELETE FROM sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()


def save_session_location(token: str, user_location: str, user_city: str) -> None:
    if not token:
        return
    conn = get_connection()
    conn.execute(
        "UPDATE sessions SET user_location = ?, user_city = ? WHERE token = ?",
        (user_location, user_city, token),
    )
    conn.commit()
    conn.close()


def save_session_chat_state(token: str, chat_state_json: str) -> None:
    """Draft state (mood/craving progress) of a brand-new chat that has no
    saved chats row yet, so a reload mid-flow doesn't lose it. Pass None to
    clear it. Once the first message exists the chat moves to the chats
    table (see create_chat) and is kept until deleted."""
    if not token:
        return
    conn = get_connection()
    conn.execute("UPDATE sessions SET chat_state = ? WHERE token = ?", (chat_state_json or None, token))
    conn.commit()
    conn.close()


def get_session_chat_state(token: str) -> dict:
    if not token:
        return {}
    conn = get_connection()
    row = conn.execute("SELECT chat_state FROM sessions WHERE token = ?", (token,)).fetchone()
    conn.close()
    if not row or not row["chat_state"]:
        return {}
    try:
        return json.loads(row["chat_state"])
    except ValueError:
        return {}


def set_session_chat_id(token: str, chat_id) -> None:
    if not token:
        return
    conn = get_connection()
    conn.execute("UPDATE sessions SET current_chat_id = ? WHERE token = ?", (chat_id, token))
    conn.commit()
    conn.close()


def get_session_chat_id(token: str):
    if not token:
        return None
    conn = get_connection()
    row = conn.execute("SELECT current_chat_id FROM sessions WHERE token = ?", (token,)).fetchone()
    conn.close()
    return row["current_chat_id"] if row else None


# -----------------------------------------------------------------------------
# CHATS — saved permanently per user (ChatGPT-style), independent of the
# 10-minute login timeout. The state blob holds messages, the LLM history and
# mood/craving progress as JSON.
# -----------------------------------------------------------------------------
def create_chat(user_id: int, title: str, state_json: str) -> int:
    now = datetime.now().isoformat(timespec="seconds")
    conn = get_connection()
    cur = conn.execute(
        "INSERT INTO chats (user_id, title, created_at, updated_at, state) VALUES (?, ?, ?, ?, ?)",
        (user_id, title, now, now, state_json),
    )
    conn.commit()
    chat_id = cur.lastrowid
    conn.close()
    return chat_id


def update_chat(user_id: int, chat_id: int, state_json: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE chats SET state = ?, updated_at = ? WHERE id = ? AND user_id = ?",
        (state_json, datetime.now().isoformat(timespec="seconds"), chat_id, user_id),
    )
    conn.commit()
    conn.close()


def list_chats(user_id: int, limit: int = 30) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT id, title, updated_at FROM chats WHERE user_id = ? ORDER BY updated_at DESC, id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_chat(user_id: int, chat_id: int) -> dict | None:
    """Scoped to user_id so one account can never open another's chat."""
    conn = get_connection()
    row = conn.execute(
        "SELECT id, title, state FROM chats WHERE id = ? AND user_id = ?", (chat_id, user_id)
    ).fetchone()
    conn.close()
    if not row:
        return None
    try:
        state = json.loads(row["state"])
    except ValueError:
        state = {}
    return {"id": row["id"], "title": row["title"], "state": state}


def delete_chat(user_id: int, chat_id: int) -> None:
    conn = get_connection()
    conn.execute("DELETE FROM chats WHERE id = ? AND user_id = ?", (chat_id, user_id))
    conn.execute("UPDATE sessions SET current_chat_id = NULL WHERE current_chat_id = ? AND user_id = ?", (chat_id, user_id))
    conn.commit()
    conn.close()


def get_recent_recommendations(user_id: int, limit: int = 8) -> list:
    """Most recent picks Sage actually showed this user, newest first, from the
    interaction log (which already records every turn permanently). Used to
    stop Sage repeating itself."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT dish_name, restaurant, mode FROM interaction_log "
        "WHERE user_id = ? AND dish_name IS NOT NULL AND dish_name != '' "
        "ORDER BY id DESC LIMIT ?",
        (user_id, limit),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_session_location(token: str) -> dict:
    """Returns {'user_location', 'user_city'} if previously saved for this
    token, else {}. Location lives on the session row (not the permanent
    profile) so it survives a page reload within the same login session but
    still gets asked fresh on the next actual login, matching the original
    'ask location every time, after login' behavior."""
    if not token:
        return {}
    conn = get_connection()
    row = conn.execute("SELECT user_location, user_city FROM sessions WHERE token = ?", (token,)).fetchone()
    conn.close()
    if not row or not row["user_location"]:
        return {}
    return {"user_location": row["user_location"], "user_city": row["user_city"]}


# -----------------------------------------------------------------------------
# PROFILE
# -----------------------------------------------------------------------------
def save_profile(user_id: int, name: str, age: int, gender: str, height: str, weight: str) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO profiles (user_id, name, age, gender, height, weight)
           VALUES (?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             name=excluded.name, age=excluded.age, gender=excluded.gender,
             height=excluded.height, weight=excluded.weight""",
        (user_id, name, age, gender, height, weight),
    )
    conn.commit()
    conn.close()


def get_profile(user_id: int) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM profiles WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}


# -----------------------------------------------------------------------------
# MEDICAL / ALLERGIES / PREFERENCES
# -----------------------------------------------------------------------------
def save_medical_info(user_id: int, conditions: list, allergies: list, dietary_style: str,
                       sweet_savory: str, spice_tolerance: str, preference_notes: str) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO medical_info
             (user_id, medical_conditions, allergies, dietary_style, sweet_savory, spice_tolerance, preference_notes)
           VALUES (?, ?, ?, ?, ?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             medical_conditions=excluded.medical_conditions, allergies=excluded.allergies,
             dietary_style=excluded.dietary_style, sweet_savory=excluded.sweet_savory,
             spice_tolerance=excluded.spice_tolerance, preference_notes=excluded.preference_notes""",
        (user_id, ", ".join(conditions), ", ".join(allergies), dietary_style,
         sweet_savory, spice_tolerance, preference_notes),
    )
    conn.commit()
    conn.close()


def get_medical_info(user_id: int) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM medical_info WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    if not row:
        return {}
    d = dict(row)
    d["medical_conditions"] = [c.strip() for c in (d.get("medical_conditions") or "").split(",") if c.strip()]
    d["allergies"] = [a.strip() for a in (d.get("allergies") or "").split(",") if a.strip()]
    return d


# -----------------------------------------------------------------------------
# CYCLE INFO
# -----------------------------------------------------------------------------
def save_cycle_info(user_id: int, cycle_length: int, last_period_date: str) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO cycle_info (user_id, cycle_length, last_period_date)
           VALUES (?, ?, ?)
           ON CONFLICT(user_id) DO UPDATE SET
             cycle_length=excluded.cycle_length, last_period_date=excluded.last_period_date""",
        (user_id, cycle_length, last_period_date),
    )
    conn.commit()
    conn.close()


def get_cycle_info(user_id: int) -> dict:
    conn = get_connection()
    row = conn.execute("SELECT * FROM cycle_info WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return dict(row) if row else {}


# -----------------------------------------------------------------------------
# CRAVING MAP
# -----------------------------------------------------------------------------
def save_craving_map(user_id: int, mood_to_craving: dict) -> None:
    conn = get_connection()
    for mood, craving in mood_to_craving.items():
        conn.execute(
            """INSERT INTO craving_map (user_id, mood, craving) VALUES (?, ?, ?)
               ON CONFLICT(user_id, mood) DO UPDATE SET craving=excluded.craving""",
            (user_id, mood, craving),
        )
    conn.commit()
    conn.close()


def get_craving_map(user_id: int) -> dict:
    conn = get_connection()
    rows = conn.execute("SELECT mood, craving FROM craving_map WHERE user_id = ?", (user_id,)).fetchall()
    conn.close()
    return {r["mood"]: r["craving"] for r in rows}


# -----------------------------------------------------------------------------
# PANTRY
# -----------------------------------------------------------------------------
def add_pantry_item(user_id: int, item_name: str, quantity: str = "") -> None:
    conn = get_connection()
    conn.execute(
        "INSERT INTO pantry_items (user_id, item_name, quantity, added_date, used) VALUES (?, ?, ?, ?, 0)",
        (user_id, item_name, quantity, date.today().isoformat()),
    )
    conn.commit()
    conn.close()


def mark_pantry_used(item_id: int) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE pantry_items SET used = 1, used_date = ? WHERE id = ?",
        (date.today().isoformat(), item_id),
    )
    conn.commit()
    conn.close()


def mark_pantry_unused(item_id: int, user_id: int) -> None:
    """Undo a mistaken 'used' tick."""
    conn = get_connection()
    conn.execute(
        "UPDATE pantry_items SET used = 0, used_date = NULL WHERE id = ? AND user_id = ?",
        (item_id, user_id),
    )
    conn.commit()
    conn.close()


def update_pantry_quantity(item_id: int, user_id: int, quantity: str) -> None:
    conn = get_connection()
    conn.execute(
        "UPDATE pantry_items SET quantity = ? WHERE id = ? AND user_id = ?",
        (quantity, item_id, user_id),
    )
    conn.commit()
    conn.close()


def get_pantry_items(user_id: int, only_unused: bool = True) -> list:
    conn = get_connection()
    query = "SELECT * FROM pantry_items WHERE user_id = ?"
    if only_unused:
        query += " AND used = 0"
    query += " ORDER BY added_date ASC"
    rows = conn.execute(query, (user_id,)).fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        age_days = (date.today() - date.fromisoformat(d["added_date"])).days
        d["age_days"] = age_days
        result.append(d)
    return result


# -----------------------------------------------------------------------------
# FEEDBACK (per-user; replaces feedback_memory.json)
# -----------------------------------------------------------------------------
MAX_FEEDBACK_ENTRIES = 20


def save_feedback(user_id: int, restaurant: str, dish_name: str, liked: bool,
                   cuisine: str = "", indulgent: str = "", vibe: str = "", phase: str = "") -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO feedback (user_id, date, restaurant, dish_name, liked, cuisine, indulgent, vibe, phase)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (user_id, date.today().isoformat(), restaurant, dish_name, int(liked),
         cuisine, indulgent, vibe, phase),
    )
    # Trim to the most recent MAX_FEEDBACK_ENTRIES rows for this user
    conn.execute(
        """DELETE FROM feedback WHERE user_id = ? AND id NOT IN (
             SELECT id FROM feedback WHERE user_id = ? ORDER BY id DESC LIMIT ?
           )""",
        (user_id, user_id, MAX_FEEDBACK_ENTRIES),
    )
    conn.commit()
    conn.close()


def get_feedback_history(user_id: int) -> list:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM feedback WHERE user_id = ? ORDER BY id ASC", (user_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# -----------------------------------------------------------------------------
# INTERACTION LOG (per-user; replaces interaction_log.jsonl)
# -----------------------------------------------------------------------------
def log_interaction(user_id: int, **fields) -> None:
    conn = get_connection()
    conn.execute(
        """INSERT INTO interaction_log
             (user_id, timestamp, user_text, phase, mode, restaurant, dish_name,
              cuisine_confidence, nutrition_found, nutrition_source)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            user_id, datetime.now().isoformat(timespec="seconds"),
            fields.get("user_text", ""), fields.get("phase", ""), fields.get("mode", ""),
            fields.get("restaurant", ""), fields.get("dish_name", ""),
            fields.get("cuisine_confidence", ""), int(fields.get("nutrition_found", False)),
            fields.get("nutrition_source", ""),
        ),
    )
    conn.commit()
    conn.close()
