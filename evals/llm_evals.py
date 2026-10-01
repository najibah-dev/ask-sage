"""
LLM-backed evals — call the real Filter Agent / Sage pipeline through Groq to
check the architecture actually holds up under real model sampling, not just
in the isolated enforcement functions tested in deterministic_evals.py.
Every check here re-verifies something the code-level enforcement should
already guarantee — these exist to catch a regression in how that
enforcement is *wired in*, not just whether the function works in isolation.

Uses a throwaway SQLite database (not the real ask-sage/sage.db) so eval
runs never touch real user data.
"""
import tempfile
from pathlib import Path

from harness import app, db, llm_case

# Bounded timeout for eval runs specifically — a real network stall should
# fail a trial fast (and get counted against the pass rate) instead of
# hanging the whole suite indefinitely. The live app keeps the SDK default.
app.client.timeout = 45

EVAL_DB = Path(tempfile.gettempdir()) / "sage_eval.db"


def _fresh_eval_user(allergies=None, conditions=None, dietary_style="No restriction") -> int:
    """Creates (or reuses) a throwaway user in the eval DB with a given
    allergy/condition profile, returning the user_id."""
    db.DB_PATH = EVAL_DB
    if EVAL_DB.exists():
        EVAL_DB.unlink()
    db.init_db()
    uid = db.create_user("eval_user", "eval_password_123")
    db.save_profile(uid, "Eval User", 28, "Female", "165cm", "60kg")
    db.save_medical_info(
        uid, conditions or [], allergies or [], dietary_style,
        "Balanced / no strong preference", "Medium", "",
    )
    return uid


# A synthetic nearby-restaurants list with clear, distinct, fake-but-plausible
# names so any restaurant name in the model's output that ISN'T one of these
# is unambiguously a hallucination, not an ambiguous real-world match.
# Kept to 4 (not more) to hold prompt size down — enough to still meaningfully
# test "top 3 of N" capping and to include one name with no cuisine signal
# ("Green Table") for the confidence-honesty check.
FAKE_RESTAURANTS = [
    {"name": "Bangla Kitchen", "place_id": "p1", "rating": 4.5, "address": "12 Gulshan Ave", "price_level": 2, "open_now": True},
    {"name": "Tehari Khan", "place_id": "p2", "rating": 4.2, "address": "8 Banani Rd", "price_level": 2, "open_now": True},
    {"name": "Napoli Pizzeria", "place_id": "p4", "rating": 4.1, "address": "44 Uttara Blvd", "price_level": 2, "open_now": True},
    {"name": "Green Table", "place_id": "p5", "rating": 3.9, "address": "5 Mirpur Rd", "price_level": 1, "open_now": True},
]
REAL_NAMES = {r["name"] for r in FAKE_RESTAURANTS}

# Every LLM case below runs 3 trials at a 2/3 pass threshold (not 5-6 trials
# at 80%) — the full FILTER_SYSTEM_PROMPT alone costs ~3000+ tokens per call
# regardless of trial count (it's the real production prompt, not shrunk for
# evals, since testing a trimmed-down prompt wouldn't tell us anything about
# production behavior). Trial count was the only lever that didn't compromise
# fidelity, and running 36 total trials was consistently enough to exhaust a
# day's ~200k token quota before the suite finished. 3 trials is thinner
# statistical evidence than 5-6, but the code-level enforcement functions
# (tested exhaustively, for free, in deterministic_evals.py) are what
# actually guarantee safety — these LLM-backed cases exist to catch a wiring
# regression, not to be the primary statistical evidence of correctness.
LLM_TRIALS = 3
LLM_PASS_THRESHOLD = 0.66  # tolerates 1 failure out of 3


@llm_case("filter_agent: every returned pick names a restaurant from the real nearby list", trials=LLM_TRIALS, pass_threshold=LLM_PASS_THRESHOLD)
def _():
    uid = _fresh_eval_user()
    shortlist = app.filter_agent(uid, FAKE_RESTAURANTS, "I'm happy and craving something spicy", "follicular", False)
    for pick in shortlist.get("picks", []):
        assert pick.get("restaurant") in REAL_NAMES, (
            f"hallucinated restaurant not in provided list: {pick.get('restaurant')!r}"
        )


@llm_case("filter_agent: never returns more than 3 picks", trials=LLM_TRIALS, pass_threshold=LLM_PASS_THRESHOLD)
def _():
    uid = _fresh_eval_user()
    shortlist = app.filter_agent(uid, FAKE_RESTAURANTS, "tired and want comfort food", "luteal", False)
    assert len(shortlist.get("picks", [])) <= 3


@llm_case("filter_agent: a nut allergy never survives into a returned pick's ingredients", trials=LLM_TRIALS, pass_threshold=LLM_PASS_THRESHOLD)
def _():
    uid = _fresh_eval_user(allergies=["Nuts"])
    # Deliberately craving something that commonly contains nuts, to actually
    # stress the safety net rather than trivially passing because nothing
    # nut-related was ever considered.
    shortlist = app.filter_agent(uid, FAKE_RESTAURANTS, "craving pad thai or a nutty dessert", "ovulatory", False)
    allergies = app._get_allergies(uid)
    for pick in shortlist.get("picks", []):
        assert not app._dish_contains_allergen(pick, allergies), (
            f"allergen leaked through into a pick: {pick.get('dish_name')} / {pick.get('key_ingredients')}"
        )
    home = shortlist.get("home_option")
    if home:
        assert not app._dish_contains_allergen(home, allergies), (
            f"allergen leaked through into home_option: {home.get('dish_name')}"
        )


@llm_case("filter_agent: a shellfish allergy never survives into a returned pick's ingredients", trials=LLM_TRIALS, pass_threshold=LLM_PASS_THRESHOLD)
def _():
    uid = _fresh_eval_user(allergies=["Shellfish"])
    shortlist = app.filter_agent(uid, FAKE_RESTAURANTS, "craving shrimp or seafood tonight", "menstrual", False)
    allergies = app._get_allergies(uid)
    for pick in shortlist.get("picks", []):
        assert not app._dish_contains_allergen(pick, allergies), (
            f"allergen leaked through into a pick: {pick.get('dish_name')} / {pick.get('key_ingredients')}"
        )


@llm_case("home-only recommendation: home_option is buildable from the given pantry items", trials=LLM_TRIALS, pass_threshold=LLM_PASS_THRESHOLD)
def _():
    uid = _fresh_eval_user()
    db.add_pantry_item(uid, "eggs")
    db.add_pantry_item(uid, "spinach")
    db.add_pantry_item(uid, "rice")
    shortlist = app._home_only_recommendation(
        uid, "hungry and want something warm", "luteal",
        "She chose to cook at home rather than eat out, so give a homemade suggestion.",
    )
    home = shortlist.get("home_option")
    assert home, "expected a home_option to be filled in"
    pantry_names = {i["item_name"].lower() for i in db.get_pantry_items(uid)}
    staples = {"salt", "oil", "water", "pepper", "sugar", "butter", "spices", "seasoning"}
    ingredient_names = {
        (ing.get("name", "") if isinstance(ing, dict) else str(ing)).lower()
        for ing in (home.get("key_ingredients") or [])
    }
    # Every ingredient should either be a pantry item (allowing loose
    # substring match, since the model may say "rice" vs pantry's "white
    # rice") or a reasonable cooking staple — never something unrelated.
    for ing in ingredient_names:
        matches_pantry = any(p in ing or ing in p for p in pantry_names)
        matches_staple = any(s in ing for s in staples)
        assert matches_pantry or matches_staple, (
            f"home_option used an ingredient not in pantry or staples: {ing!r} "
            f"(pantry={pantry_names}, dish={home.get('dish_name')})"
        )


@llm_case("filter_agent: cuisine_confidence 'high' is never claimed for a restaurant with no name signal", trials=LLM_TRIALS, pass_threshold=LLM_PASS_THRESHOLD)
def _():
    uid = _fresh_eval_user()
    # "Green Table" has no cuisine/dish word in its name at all, so even if
    # the model claims high confidence, _enforce_cuisine_confidence inside
    # filter_agent should have already downgraded it before we see it here.
    shortlist = app.filter_agent(uid, FAKE_RESTAURANTS, "anything, surprise me", "follicular", False)
    for pick in shortlist.get("picks", []):
        if pick.get("restaurant") == "Green Table":
            assert pick.get("cuisine_confidence") == "low", (
                "Green Table has no real cuisine signal in its name — confidence should be enforced to 'low'"
            )


@llm_case("ask_sage: final reply never leaks raw JSON/structured fields to the user", trials=LLM_TRIALS, pass_threshold=LLM_PASS_THRESHOLD)
def _():
    uid = _fresh_eval_user()
    app.st.session_state.conversation_history = [{"role": "system", "content": app.SAGE_SYSTEM_PROMPT}]
    reply = app.ask_sage(
        "[USER MESSAGE]\nFeeling happy.\n\n[CYCLE PHASE]\nfollicular\n\n"
        "[TOP PICK FROM FILTER AGENT]\nRestaurant: Bangla Kitchen\nDish: dal with rice\n"
        "Reasoning: warm and fitting her mood\nhealth tip: pair with a source of vitamin C\n"
        "Indulgent: no\nCuisine confidence: high\n\n"
        "[NUTRITION]\nFor 'dal with rice' (per 250g): Calories: 350 kcal, Protein: 12.0g, "
        "Carbs: 55.0g, Sugar: 2.0g, Fat: 8.0g, Fiber: 6.0g.\n\n"
        "[INSTRUCTION]\nWrite ONE warm conversational reply (4-5 lines max, no bullet points, "
        "no headers) using the pick and nutrition above. Include the health tip in your own voice. "
        "Do not invent a different restaurant or dish."
    )
    lowered = reply.lower()
    for leak_marker in ('"restaurant":', "'restaurant':", "cuisine_confidence", "key_ingredients", "phase_used"):
        assert leak_marker not in lowered, f"raw structured field leaked into user-facing reply: {leak_marker!r}\nreply={reply!r}"


if __name__ == "__main__":
    from harness import run_all
    run_all(skip_llm=False)
