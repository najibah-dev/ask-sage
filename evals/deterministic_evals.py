"""
Deterministic evals — no network, no LLM calls. These check the code-level
safety nets the architecture relies on instead of trusting prompt
instructions alone (cycle-phase math, allergy matching, cuisine-confidence
downgrading, restaurant grounding, non-food filtering). Fast enough to run
on every change.
"""
from harness import app, case


# -----------------------------------------------------------------------------
# Cycle-phase math (ACOG calendar method — see CLAUDE.md / plan for sources)
# -----------------------------------------------------------------------------

@case("cycle phase: every day of the cycle gets exactly one phase, in order")
def _():
    for length in (21, 24, 28, 30, 35, 45):
        phases = [app.calculate_cycle_phase(d, length) for d in range(1, length + 1)]
        assert phases[0] == "menstrual", f"cycle_length={length} day1={phases[0]}"
        # phases must appear in this order with no phase skipped or reappearing
        seen_order = []
        for p in phases:
            if not seen_order or seen_order[-1] != p:
                seen_order.append(p)
        assert seen_order == ["menstrual", "follicular", "ovulatory", "luteal"], (
            f"cycle_length={length} produced out-of-order phases: {seen_order}"
        )


@case("cycle phase: ovulatory window is centered near (cycle_length - 14)")
def _():
    for length in (24, 28, 30, 35):
        expected_ovulation = length - 14
        ovulatory_days = [d for d in range(1, length + 1) if app.calculate_cycle_phase(d, length) == "ovulatory"]
        assert ovulatory_days, f"no ovulatory phase found for cycle_length={length}"
        assert min(ovulatory_days) <= expected_ovulation <= max(ovulatory_days) + 1, (
            f"cycle_length={length}: expected ovulation ~day {expected_ovulation}, "
            f"got ovulatory window {ovulatory_days}"
        )


# -----------------------------------------------------------------------------
# Allergy safety — code-level enforcement, not prompt-only
# -----------------------------------------------------------------------------

ALLERGY_CASES = [
    # (allergy categories, dish_name, key_ingredient_names, should_flag, why)
    (["nuts"], "Pad Thai", ["peanuts", "rice noodles"], True, "peanuts under nuts category"),
    (["nuts"], "Walnut Salad", ["walnuts", "greens"], True, "walnuts plural under nuts category"),
    (["shellfish"], "Shrimp Pasta", ["shrimp", "pasta"], True, "shrimp is shellfish, not literally 'shellfish'"),
    (["shellfish"], "Crab Cakes", ["crab", "breadcrumbs"], True, "crab is shellfish"),
    (["eggs"], "Egg Fried Rice", ["eggs", "rice"], True, "literal eggs"),
    (["soy"], "Miso Soup", ["miso", "tofu"], True, "miso and tofu are soy products"),
    (["dairy"], "Cheese Pizza", ["cheese", "dough"], True, "cheese is dairy"),
    (["gluten"], "Garlic Bread", ["bread", "garlic"], True, "bread contains gluten"),
    # False-positive regressions — plain substring matching would wrongly flag these
    (["nuts"], "Chicken Curry", ["chicken", "coconut milk"], False, "coconut is not a tree-nut allergen"),
    (["eggs"], "Eggplant Curry", ["eggplant", "spices"], False, "eggplant contains no egg"),
    # No allergy on file -> never flag anything
    ([], "Peanut Butter Sandwich", ["peanut butter", "bread"], False, "no allergies recorded"),
]


@case("allergy check: catches allergens named by specific ingredient, not just category word")
def _():
    for allergies, dish_name, ingredients, should_flag, why in ALLERGY_CASES:
        pick = {"dish_name": dish_name, "key_ingredients": [{"name": i} for i in ingredients]}
        result = app._dish_contains_allergen(pick, allergies)
        assert result == should_flag, (
            f"{dish_name} with allergies={allergies}: expected flagged={should_flag} ({why}), got {result}"
        )


@case("allergy enforcement: strips unsafe picks and nulls an unsafe home_option")
def _():
    shortlist = {
        "picks": [
            {"dish_name": "Pad Thai", "key_ingredients": [{"name": "peanuts"}]},
            {"dish_name": "Chicken Curry", "key_ingredients": [{"name": "chicken"}, {"name": "coconut milk"}]},
            {"dish_name": "Shrimp Pasta", "key_ingredients": [{"name": "shrimp"}]},
        ],
        "home_option": {"dish_name": "yogurt with nuts", "key_ingredients": [{"name": "nuts"}]},
    }
    result = app._enforce_allergy_safety(shortlist, ["nuts", "shellfish"])
    assert [p["dish_name"] for p in result["picks"]] == ["Chicken Curry"], result["picks"]
    assert result["home_option"] is None


@case("allergy enforcement: the hardcoded home_option fail-safe is itself allergen-free")
def _():
    # This is the literal fallback dish used when the Filter Agent's own LLM
    # call fails entirely — it bypasses the LLM so it can't be personalized,
    # and must survive the allergy check for every one of the six categories
    # simultaneously (the worst case: someone allergic to all of them).
    fallback = {
        "dish_name": "rice with steamed vegetables",
        "key_ingredients": [{"name": "rice", "grams": 150}, {"name": "mixed vegetables", "grams": 150}],
    }
    all_allergies = ["nuts", "shellfish", "dairy", "gluten", "soy", "eggs"]
    assert not app._dish_contains_allergen(fallback, all_allergies), (
        "the ultimate fail-safe home_option must never contain a common allergen"
    )


# -----------------------------------------------------------------------------
# Cuisine confidence — honesty check on the Filter Agent's self-rating
# -----------------------------------------------------------------------------

@case("cuisine confidence: downgrades an unfounded 'high' claim on vague branding")
def _():
    picks = [
        {"restaurant": "Blue Bowl Superfoods", "cuisine_confidence": "high"},
        {"restaurant": "Bangla Kitchen", "cuisine_confidence": "high"},
        {"restaurant": "Magpie Restaurant", "cuisine_confidence": "low"},
    ]
    result = app._enforce_cuisine_confidence(picks, enrich=False)
    by_name = {p["restaurant"]: p["cuisine_confidence"] for p in result}
    assert by_name["Blue Bowl Superfoods"] == "low", "vague wellness branding has no real cuisine signal"
    assert by_name["Bangla Kitchen"] == "high", "'Bangla' is a genuine cuisine signal, should stay high"
    assert by_name["Magpie Restaurant"] == "low", "already low, should stay low"


@case("cuisine confidence: enrich=True (review-grounded) path is not overridden")
def _():
    picks = [{"restaurant": "Blue Bowl Superfoods", "cuisine_confidence": "high"}]
    result = app._enforce_cuisine_confidence(picks, enrich=True)
    assert result[0]["cuisine_confidence"] == "high", "enrich path may have real signal the name alone doesn't show"


# -----------------------------------------------------------------------------
# Restaurant grounding — the core hallucination guard
# -----------------------------------------------------------------------------

@case("restaurant grounding: drops a pick naming a restaurant not in the real nearby list")
def _():
    restaurants = [{"name": "Bangla Kitchen"}, {"name": "Tehari Khan"}]
    picks = [
        {"restaurant": "Bangla Kitchen", "dish_name": "dal"},
        {"restaurant": "Imaginary Bistro", "dish_name": "steak"},  # hallucinated — not in the list
        {"restaurant": "Tehari Khan", "dish_name": "biryani"},
    ]
    result = app._enforce_restaurant_grounding(picks, restaurants)
    names = [p["restaurant"] for p in result]
    assert names == ["Bangla Kitchen", "Tehari Khan"], names


@case("restaurant grounding: exact-name match only, not a fuzzy/substring match")
def _():
    restaurants = [{"name": "Bangla Kitchen"}]
    picks = [{"restaurant": "Bangla Kitchen Restaurant", "dish_name": "dal"}]  # close but not exact
    result = app._enforce_restaurant_grounding(picks, restaurants)
    assert result == [], "a near-miss name should not slip through as grounded"


# -----------------------------------------------------------------------------
# Search Agent — non-food filtering (no LLM; monkeypatch the Google Places call)
# -----------------------------------------------------------------------------

class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def json(self):
        return self._payload


def _fake_places_payload():
    def place(name, types, rating=4.2, open_now=True):
        return {
            "name": name, "types": types, "rating": rating, "place_id": name,
            "vicinity": "123 Fake St", "price_level": 2,
            "opening_hours": {"open_now": open_now},
        }
    return {
        "status": "OK",
        "results": [
            place("Bangla Kitchen", ["restaurant", "food", "point_of_interest"]),
            place("City Pharmacy", ["pharmacy", "health", "store"]),  # non-food word + non-food type
            place("Tehari Khan", ["restaurant", "food"]),
            place("Ace Hardware", ["hardware_store", "store"]),  # non-food type entirely
            place("No Rating Diner", ["restaurant", "food"], rating=None),  # missing rating -> excluded
            place("Downtown Trading Enterprises", ["restaurant", "food"]),  # food type but NON_FOOD_WORDS hit
        ],
    }


@case("search agent: filters out non-food place types, NON_FOOD_WORDS names, and unrated places")
def _():
    real_get = app.requests.get
    try:
        app.requests.get = lambda *a, **k: _FakeResponse(_fake_places_payload())
        results = app.get_nearby_restaurants("23.81,90.41", limit=10)
    finally:
        app.requests.get = real_get

    names = {r["name"] for r in results}
    assert names == {"Bangla Kitchen", "Tehari Khan"}, (
        f"expected only genuine food places to survive filtering, got {names}"
    )


@case("translate_if_bangla: passes through non-Bangla names unchanged (no network call)")
def _():
    assert app.translate_if_bangla("Bangla Kitchen") == "Bangla Kitchen"
    assert app.translate_if_bangla("Tehari Khan") == "Tehari Khan"


# -----------------------------------------------------------------------------
# Conversation memory: bounded history, repeat protection, saved chats
# -----------------------------------------------------------------------------

@case("history trim: keeps the system prompt, caps length, starts on a user message")
def _():
    history = [{"role": "system", "content": "sys"}]
    for i in range(20):
        history.append({"role": "user", "content": f"u{i}"})
        history.append({"role": "assistant", "content": f"a{i}"})
    trimmed = app._trim_history(history)
    assert trimmed[0]["role"] == "system"
    assert len(trimmed) - 1 <= app.MAX_HISTORY_MESSAGES, len(trimmed)
    assert trimmed[1]["role"] == "user", "must not start on a dangling assistant reply"
    assert trimmed[-1]["content"] == "a19", "must keep the most recent turn"
    # a short history is left alone
    short = history[:3]
    assert app._trim_history(short) == short


@case("repeat protection: same dish at the same place is a repeat, different is not")
def _():
    recent = [
        {"dish_name": "Chicken Biryani", "restaurant": "Tehari Khan", "mode": "restaurant"},
        {"dish_name": "Spinach egg fried rice", "restaurant": "", "mode": "home"},
    ]
    assert app._is_repeat("chicken biryani ", "tehari khan", recent), "case/space differences still match"
    assert not app._is_repeat("Chicken Biryani", "Bangla Kitchen", recent), "same dish, different restaurant is fine"
    assert app._is_repeat("Spinach Egg Fried Rice", "", recent), "homemade repeat"
    assert not app._is_repeat("Dal with rice", "", recent)
    assert not app._is_repeat("", "", recent), "blank dish is never a repeat"


@case("saved chats: per user, another account cannot open them, delete works")
def _():
    import tempfile
    from pathlib import Path
    original = app.db.DB_PATH
    try:
        app.db.DB_PATH = Path(tempfile.mkdtemp()) / "chats_eval.db"
        app.db.init_db()
        a = app.db.create_user("chat_a", "pw")
        b = app.db.create_user("chat_b", "pw")
        cid = app.db.create_chat(a, "Happy, at home", '{"messages": []}')
        assert [c["id"] for c in app.db.list_chats(a)] == [cid]
        assert app.db.list_chats(b) == []
        assert app.db.get_chat(b, cid) is None, "another account must not be able to open this chat"
        app.db.update_chat(a, cid, '{"messages": [1]}')
        assert app.db.get_chat(a, cid)["state"] == {"messages": [1]}
        app.db.delete_chat(b, cid)
        assert app.db.get_chat(a, cid) is not None, "another account must not be able to delete it"
        app.db.delete_chat(a, cid)
        assert app.db.get_chat(a, cid) is None
    finally:
        app.db.DB_PATH = original


@case("recent recommendations: newest first, per user, blanks excluded")
def _():
    import tempfile
    from pathlib import Path
    original = app.db.DB_PATH
    try:
        app.db.DB_PATH = Path(tempfile.mkdtemp()) / "recent_eval.db"
        app.db.init_db()
        a = app.db.create_user("rec_a", "pw")
        b = app.db.create_user("rec_b", "pw")
        app.db.log_interaction(a, dish_name="Dal", restaurant="", mode="home")
        app.db.log_interaction(a, dish_name="", restaurant="", mode="none")
        app.db.log_interaction(a, dish_name="Biryani", restaurant="Tehari Khan", mode="restaurant")
        app.db.log_interaction(b, dish_name="Pizza", restaurant="Napoli", mode="restaurant")
        recent = app.db.get_recent_recommendations(a)
        assert [r["dish_name"] for r in recent] == ["Biryani", "Dal"], recent
    finally:
        app.db.DB_PATH = original


if __name__ == "__main__":
    from harness import run_all
    run_all(skip_llm=True)
