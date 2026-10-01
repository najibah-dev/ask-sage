# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

"Ask Sage" — a wellness food companion that recommends what to eat based on the user's mood, menstrual cycle phase, and personal health profile (medical conditions, allergies, dietary preferences), grounded in real, currently-open nearby restaurants (Google Places) and real nutrition data (USDA / API Ninjas). Also tracks a home pantry so "cook at home" suggestions are grounded in ingredients actually on hand.

Multi-user: accounts, onboarding, and all personal data live in a local SQLite database (`sage.db`), not hardcoded into the prompt.

## Running

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # fill in your keys, or leave it absent for bring-your-own-key mode
streamlit run app.py
```

There's no build step. Tests are the `evals/` suite (see below), not a conventional test framework.

## Files

- `app.py` — the entire Streamlit app: UI, session-state view gating (onboarding wizard, login, `st.navigation` for Chat/Profile/Pantry pages), the 3-agent pipeline, and both system prompts (`FILTER_SYSTEM_PROMPT`, `SAGE_SYSTEM_PROMPT`).
- `db.py` — SQLite data layer: accounts, profiles, medical info, cycle info, craving map, pantry, feedback, interaction log, sessions, and saved chats. All `save_*`/`create_*` functions are upserts where relevant.
- `evals/` — automated test suite: `deterministic_evals.py` (pure logic, no network), `llm_evals.py` (runs the real pipeline against the live Groq API), `harness.py` (the runner), `run_evals.py` (CLI entry point).

## Architecture: the 3-agent pipeline

Per turn (`process_message()` in `app.py`):

1. **Search Agent** (`get_nearby_restaurants`) — Google Places Nearby Search, `opennow=True`, filtered to food-related place types and against `NON_FOOD_WORDS`. No LLM involved.
2. **Filter Agent** (`filter_agent` / `_home_only_recommendation`) — one Groq call, given the real restaurant list (or pantry items, for at-home), the user's mood/craving, cycle phase, and profile. Returns structured JSON: up to 3 restaurant picks plus an optional `home_option`, each with `key_ingredients` (used for nutrition lookup).
3. **Sage** (`ask_sage`) — a second Groq call that writes the final warm reply from the already-decided pick and real nutrition numbers. Never re-decides the pick, never invents nutrition data.

**Code-level safety nets, applied after step 2, before anything reaches the user:**
- `_enforce_restaurant_grounding` — drops any pick naming a restaurant not in the real search results.
- `_enforce_allergy_safety` / `_dish_contains_allergen` — checks `key_ingredients` against the user's allergy list via `ALLERGEN_KEYWORDS` (category → specific-ingredient words, e.g. "shellfish" → shrimp/crab/prawn/...), with word-boundary matching to avoid false positives (coconut ≠ nut, eggplant ≠ egg).
- `_enforce_cuisine_confidence` — downgrades a self-claimed "high" cuisine confidence if the restaurant's name has no real cuisine/dish signal.

This pattern — verify in code, don't just trust the prompt — is the main architectural lesson baked into this codebase. When adding a new safety-critical behavior, follow it: don't rely on a prompt instruction alone if code can check the actual output.

## Bring-your-own-key mode

If `GROQ_API_KEY` or `GOOGLE_PLACES_API_KEY` is missing from the environment, `app.py` shows a key-entry screen instead of crashing — each visitor supplies their own keys, kept in `st.session_state` only, never persisted. This is what makes a public deployment safe to leave open with no server-side secrets. See the `BYOK_MODE` block near the top of `app.py`.

## Evals

```bash
cd evals
python run_evals.py               # full suite (~21 live Groq calls)
python run_evals.py --skip-llm    # deterministic only, free, instant
python run_evals.py --only pantry # re-check one LLM-backed case by name substring, without re-running everything else
```

The live-LLM cases hit a real daily token quota — `--only` exists specifically to avoid re-running the whole suite (and re-spending quota) when only one case needs re-checking.

## Testing UI changes

This app has no unit-testable UI layer — verify changes with `streamlit.testing.v1.AppTest` for logic/session-state, or an actual browser (Playwright is a reasonable choice) for anything involving real interaction, multi-page navigation, or visual layout. Reading the code and assuming it works has been wrong often enough in this project's history to be worth stating explicitly.
