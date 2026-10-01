"""
Ask Sage — Streamlit UI
Palette: sage green, lavender, cream, deep plum
Fonts: DM Serif Display + Plus Jakarta Sans
Geolocation: streamlit-js-eval (fully styleable, no black box)
"""

import streamlit as st
import os
import re
import json
import html
import requests
from pathlib import Path
from datetime import date, datetime
from groq import Groq
from dotenv import load_dotenv
from deep_translator import GoogleTranslator
from streamlit_js_eval import get_geolocation
import db

# -----------------------------------------------------------------------------
# PAGE CONFIG
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Ask Sage",
    page_icon="🌿",
    layout="centered",
    initial_sidebar_state="expanded"
)

# -----------------------------------------------------------------------------
# CUSTOM CSS
# -----------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');

html, body, [class*="css"] {
    font-family: 'Plus Jakarta Sans', sans-serif;
}

.stApp {
    background-color: #F5F0E8;
    min-height: 100vh;
}

/* ── Spinner ── */
.stSpinner > div > div {
    border-top-color: #7B9E6B !important;
}
.stSpinner p {
    color: #6B5F5A !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.9rem !important;
}

/* ── Header ── */
.sage-header {
    text-align: center;
    padding: 2.5rem 0 1.5rem 0;
}

.sage-title {
    font-family: 'DM Serif Display', serif;
    font-size: 3.2rem;
    font-weight: 400;
    color: #3D2B37;
    margin: 0;
    line-height: 1.1;
    letter-spacing: -0.5px;
}

.sage-title span { color: #7B9E6B; }

.sage-subtitle {
    font-family: 'Plus Jakarta Sans', sans-serif;
    font-size: 1rem;
    color: #8A7F7A;
    font-weight: 500;
    margin-top: 0.4rem;
}

.sage-divider {
    height: 1px;
    background: linear-gradient(to right, transparent, #A8BF99, transparent);
    margin: 1rem 0 1.5rem 0;
    border: none;
}

/* ── Chat messages ── */
.sage-message {
    background: #FFFFFF;
    border-radius: 16px;
    padding: 1.1rem 1.4rem;
    margin: 0.7rem 0;
    box-shadow: 0 2px 12px rgba(107,63,94,0.06);
    border-left: 4px solid #7B9E6B;
    font-size: 0.95rem;
    line-height: 1.7;
    color: #3D2B37;
}

.user-message {
    background: #EEE8F5;
    border-left: 4px solid #B8ADCC;
    color: #3D2B37;
}

/* ── Params card ── */
.params-card {
    background: #FAFAF7;
    border-radius: 12px;
    padding: 0.8rem 1.2rem;
    margin: 0.3rem 0 0.7rem 0;
    border: 1px solid #E8E3D8;
    display: flex;
    gap: 1.5rem;
    flex-wrap: wrap;
    font-size: 0.8rem;
}

.param-item { display: flex; align-items: center; gap: 0.4rem; }

.param-label {
    font-weight: 700;
    color: #8A7F7A;
    text-transform: uppercase;
    font-size: 0.68rem;
    letter-spacing: 0.06em;
}

.param-value { color: #3D2B37; font-weight: 500; }

/* ── Nutrition card ── */
.nutrition-card {
    background: #FFFFFF;
    border-radius: 16px;
    padding: 1.4rem;
    margin: 0.7rem 0;
    border: 1.5px solid #A8BF99;
    box-shadow: 0 2px 12px rgba(123,158,107,0.08);
}

.nutrition-title {
    font-family: 'DM Serif Display', serif;
    font-size: 1.05rem;
    color: #3D2B37;
    margin-bottom: 0.3rem;
}

.nutrition-subtitle {
    font-size: 0.75rem;
    color: #8A7F7A;
    font-weight: 500;
    margin-bottom: 1rem;
}

.nutrition-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 0.5rem;
}

.nutrition-item {
    background: #F5F0E8;
    border-radius: 10px;
    padding: 0.55rem 0.9rem;
    display: flex;
    justify-content: space-between;
    align-items: center;
    font-size: 0.85rem;
}

.nutrition-label { color: #6B5F5A; font-weight: 500; }

.nutrition-value {
    font-family: 'DM Serif Display', serif;
    font-size: 1rem;
    color: #3D2B37;
}

/* ── Restaurant cards ── */
.restaurant-card {
    background: #FFFFFF;
    border-radius: 16px;
    padding: 1.1rem 1.4rem;
    margin: 0.5rem 0;
    box-shadow: 0 2px 12px rgba(107,63,94,0.06);
    border-top: 3px solid #7B9E6B;
    transition: box-shadow 0.2s, transform 0.2s;
}

.restaurant-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 6px 20px rgba(107,63,94,0.1);
}

.restaurant-card:nth-child(2) { border-color: #B8ADCC; }
.restaurant-card:nth-child(3) { border-color: #6B3F5E; }
.restaurant-card:nth-child(4) { border-color: #A8BF99; }
.restaurant-card:nth-child(5) { border-color: #8A7F7A; }

.restaurant-name {
    font-family: 'DM Serif Display', serif;
    font-size: 1.1rem;
    color: #3D2B37;
    margin-bottom: 0.35rem;
}

.restaurant-meta {
    display: flex;
    gap: 0.8rem;
    align-items: center;
    flex-wrap: wrap;
    font-size: 0.82rem;
    color: #6B5F5A;
    margin-bottom: 0.35rem;
    font-weight: 500;
}

.restaurant-address { font-size: 0.82rem; color: #8A7F7A; }

.badge {
    display: inline-block;
    padding: 0.2rem 0.7rem;
    border-radius: 20px;
    font-size: 0.72rem;
    font-weight: 600;
}

.badge-open   { background: #E4EFE0; color: #3D6B2F; }
.badge-closed { background: #F5E4EF; color: #6B1F3F; }

/* ── Phase badge ── */
.phase-badge {
    display: inline-block;
    padding: 0.35rem 1.1rem;
    border-radius: 30px;
    font-weight: 600;
    font-size: 0.82rem;
    margin: 0.5rem 0;
}

.phase-menstrual  { background: #F5E4EF; color: #6B1F3F; }
.phase-follicular { background: #E4EFE0; color: #3D6B2F; }
.phase-ovulatory  { background: #FFF3E0; color: #7A4F10; }
.phase-luteal     { background: #EEE8F5; color: #4A2D6B; }

/* ── Location badge ── */
.location-badge {
    display: inline-block;
    background: #E4EFE0;
    color: #3D6B2F;
    padding: 0.35rem 1.1rem;
    border-radius: 30px;
    font-weight: 600;
    font-size: 0.85rem;
}

/* ── Sage avatar ── */
.sage-avatar-wrap {
    display: flex;
    justify-content: center;
    margin: 0.2rem 0 1.2rem 0;
}
.sage-avatar {
    width: 92px;
    height: 92px;
    border-radius: 50%;
    background: linear-gradient(135deg, #EEE8F5, #E4EFE0);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2.6rem;
    box-shadow: 0 4px 16px rgba(107,63,94,0.15);
    border: 3px solid #7B9E6B;
    animation: sage-bob 3.2s ease-in-out infinite;
}
@keyframes sage-bob {
    0%, 100% { transform: translateY(0px) rotate(-2deg); }
    50%      { transform: translateY(-8px) rotate(2deg); }
}

/* ── Section header ── */
.section-header {
    font-family: 'DM Serif Display', serif;
    font-size: 1.1rem;
    color: #3D2B37;
    margin: 1.5rem 0 0.5rem 0;
}

/* ── Input ── */
.stTextInput > div > div > input {
    border-radius: 12px !important;
    border: 1.5px solid #C8C0D4 !important;
    padding: 0.75rem 1.2rem !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-size: 0.95rem !important;
    background: #FFFFFF !important;
    color: #3D2B37 !important;
}

.stTextInput > div > div > input:focus {
    border-color: #7B9E6B !important;
    box-shadow: 0 0 0 3px rgba(123,158,107,0.15) !important;
}

.stTextInput > div > div > input::placeholder {
    color: #B0A8A4 !important;
}

/* ── All buttons (including form submit buttons, e.g. the chat Send button) ── */
.stButton > button, .stFormSubmitButton > button {
    border-radius: 12px !important;
    background: #7B9E6B !important;
    color: #FFFFFF !important;
    font-family: 'Plus Jakarta Sans', sans-serif !important;
    font-weight: 600 !important;
    font-size: 0.9rem !important;
    padding: 0.65rem 1rem !important;
    border: none !important;
    transition: background 0.2s, transform 0.15s !important;
    width: 100% !important;
    white-space: nowrap !important;
    overflow: hidden !important;
    text-overflow: ellipsis !important;
}

.stButton > button:hover, .stFormSubmitButton > button:hover {
    background: #6B8E5B !important;
    transform: translateY(-1px) !important;
}

/* ── Hide Streamlit chrome ──
   [data-testid="stExpandSidebarButton"] (the arrow that reopens a
   collapsed sidebar) is a CHILD of [data-testid="stToolbar"] — verified by
   reading Streamlit's actual frontend bundle, not assumed. Hiding the
   whole toolbar hides that button too, which is exactly the bug this
   caused twice. Fix: hide the toolbar, then explicitly force just that one
   button back to visible (a visibility:visible child overrides an
   inherited visibility:hidden from its parent; layout space is still
   reserved either way since visibility, unlike display:none, never
   removes the box from flow). */
#MainMenu { visibility: hidden; }
footer    { visibility: hidden; }
[data-testid="stToolbar"] { visibility: hidden; }
[data-testid="stHeader"] { background: transparent; }
/* Sidebar: light buttons for the chat list, green for New chat, and the
   logout button pinned to the bottom-left of the sidebar. */
[data-testid="stSidebar"] .stButton > button {
    background: #FFFFFF !important;
    color: #3D2B37 !important;
    border: 1px solid #E2DBD0 !important;
    justify-content: flex-start !important;
    text-align: left !important;
    padding: 0.5rem 0.7rem !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background: #F5F0E8 !important;
    transform: none !important;
}
[data-testid="stSidebar"] .st-key-new_chat_btn .stButton > button {
    background: #7B9E6B !important;
    color: #FFFFFF !important;
    border: none !important;
    justify-content: center !important;
    font-weight: 600 !important;
}
[data-testid="stSidebar"] [class*="st-key-chat_del_"] .stButton > button {
    justify-content: center !important;
    padding: 0.5rem 0 !important;
}
[data-testid="stSidebarUserContent"] { padding-bottom: 5rem; }
.st-key-logout_container {
    position: fixed;
    bottom: 1rem;
    left: 1rem;
    width: 268px;
    z-index: 1000;
}
[data-testid="stExpandSidebarButton"] {
    visibility: visible !important;
    z-index: 999999 !important;
}

/* ── Tabs (Log In / Sign Up, Settings sections) ──
   Streamlit's default inactive-tab color is a very light gray that nearly
   disappears against this app's cream background — easy to miss entirely,
   which is exactly what happened with the Sign Up tab. Darken it and make
   it obviously clickable. */
.stTabs [data-baseweb="tab-list"] button [data-testid="stMarkdownContainer"] p {
    color: #6B5D57 !important;
    font-weight: 600 !important;
    font-size: 0.95rem !important;
}
.stTabs [data-baseweb="tab-list"] button[aria-selected="true"] [data-testid="stMarkdownContainer"] p {
    color: #3D2B37 !important;
}
.stTabs [data-baseweb="tab-list"] button:hover [data-testid="stMarkdownContainer"] p {
    color: #6B8E5B !important;
}
</style>
""", unsafe_allow_html=True)

# -----------------------------------------------------------------------------
# LOAD ENV + CLIENTS
# -----------------------------------------------------------------------------
DOTENV_PATH = Path(__file__).with_name(".env")
load_dotenv(dotenv_path=DOTENV_PATH)

groq_key       = os.getenv("GROQ_API_KEY")
places_key     = os.getenv("GOOGLE_PLACES_API_KEY")
USDA_API_KEY   = os.getenv("USDA_API_KEY")
API_NINJAS_KEY = os.getenv("API_NINJAS_KEY")

# Bring-your-own-key mode: if this deployment has no server-side secrets
# configured (e.g. a public demo with nothing in .env), each visitor supplies
# their own keys instead of sharing the maintainer's — so a public demo can
# never run up costs or get rate-limited by other people's traffic. Keys are
# kept in st.session_state only, never written to disk or the database, and
# used solely for that visitor's own session. A real .env (local/personal
# use) skips this gate entirely — behavior is unchanged from before.
BYOK_MODE = not (groq_key and places_key)
if BYOK_MODE:
    for _k in ("byok_groq_key", "byok_places_key", "byok_usda_key", "byok_ninjas_key"):
        if _k not in st.session_state:
            st.session_state[_k] = ""

    if not (st.session_state.byok_groq_key and st.session_state.byok_places_key):
        st.markdown("""
        <div class="sage-header">
            <div class="sage-title">Ask <span>Sage</span></div>
            <div class="sage-subtitle">Your Personal Wellness Food Companion</div>
        </div>
        <hr class="sage-divider">
        """, unsafe_allow_html=True)
        st.markdown(
            "<div style='max-width:480px; margin:0 auto; text-align:center; "
            "color:#8A7F7A; font-size:0.9rem; line-height:1.6;'>"
            "This is a public demo with no shared API keys, so it never runs "
            "up usage costs on the maintainer's account. Bring your own "
            "free-tier keys below &mdash; they're used only for your session "
            "and are never stored or sent anywhere else.</div>",
            unsafe_allow_html=True,
        )
        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        key_col, _ = st.columns([2, 1])
        with key_col:
            groq_input = st.text_input(
                "Groq API key (required)", type="password",
                help="Free at console.groq.com/keys",
            )
            places_input = st.text_input(
                "Google Places API key (required)", type="password",
                help="Needs Places API + Geocoding API enabled, with billing set up on the Google Cloud project",
            )
            usda_input = st.text_input(
                "USDA API key (optional, improves nutrition lookups)", type="password",
                help="Free at fdc.nal.usda.gov/api-key-signup",
            )
            ninjas_input = st.text_input(
                "API Ninjas key (optional, nutrition fallback)", type="password",
                help="Free at api-ninjas.com",
            )
            if st.button("Start using Sage", use_container_width=True):
                if not groq_input.strip() or not places_input.strip():
                    st.error("A Groq key and a Google Places key are both required.")
                else:
                    st.session_state.byok_groq_key = groq_input.strip()
                    st.session_state.byok_places_key = places_input.strip()
                    st.session_state.byok_usda_key = usda_input.strip()
                    st.session_state.byok_ninjas_key = ninjas_input.strip()
                    st.rerun()
        st.stop()

    groq_key       = st.session_state.byok_groq_key
    places_key     = st.session_state.byok_places_key
    USDA_API_KEY   = st.session_state.byok_usda_key
    API_NINJAS_KEY = st.session_state.byok_ninjas_key

MODEL_NAME = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")
ENRICH_WITH_REVIEWS = os.getenv("ENRICH_WITH_REVIEWS", "false").lower() == "true"

client = Groq(api_key=groq_key)
db.init_db()

# -----------------------------------------------------------------------------
# FILTER AGENT'S BRAIN — reasons silently, outputs JSON only
# -----------------------------------------------------------------------------
FILTER_SYSTEM_PROMPT = """
You are the Filter Agent inside Sage, an AI wellness food companion. You never talk
to the user directly — you reason silently and return structured JSON that another
agent (Sage) will use to write the warm reply.

## YOUR JOB
Given a list of real, currently-open nearby restaurants, the user's mood/craving
message, and her menstrual cycle phase, you must:
1. Infer the likely cuisine/dishes each restaurant serves from its name (and from
   review notes if provided).
2. Score every restaurant against her current mood, craving, cycle phase, and
   health profile (medical conditions, allergies, preferences — given to you
   each turn). The restaurant list is ordered CLOSEST FIRST (real distance
   from her location) — proximity is a real convenience factor, so when two
   or more restaurants are a similarly good fit, prefer the closer one rather
   than picking a farther option for a marginal difference in fit.
3. Pick the TOP 3 restaurants, ranked best first. For your #1 pick especially,
   find the "middle ground" — a dish that honors what she's craving AND
   supports her cycle phase and health profile. If craving and phase
   conflict, bridge both worlds — never just override the craving.
4. Give each pick ONE smart, specific health tip tied to that dish.
5. If there's a genuinely simple dish she could just make at home (2-4 common
   ingredients, no real cooking skill — a yogurt parfait, boiled eggs, dal, toast,
   a smoothie, tea) that fits her mood/phase/health profile, include it as a bonus
   "home_option". Only include it when it's truly trivial to make. If nothing
   that simple fits, leave it out (set it to null).
6. You may be given a [PAST FEEDBACK] block listing dishes she's liked or
   disliked before. Use it as a real signal, not a strict rule — lean toward
   liked picks when they genuinely fit her current mood/phase, and avoid
   repeating disliked ones unless nothing else fits.
7. You may be given a [RECENTLY SUGGESTED: DO NOT REPEAT] block listing dishes
   she was just shown. Don't suggest the same dish (at the same restaurant)
   again unless nothing else genuinely fits.

You are ONLY allowed to suggest a dish plausible for a restaurant that is actually
in the provided list. Never invent a restaurant, and never suggest a dish type
that restaurant couldn't plausibly serve.

## DISH SPECIFICITY — IMPORTANT
You cannot see the real menu, so never invent an elaborate, hyper-specific dish
description (e.g. "Greek yogurt parfait with mixed berries, honey drizzle, and
toasted walnuts"). That level of detail reads as fake and breaks trust the moment
it's wrong. Instead, name dishes the way a person would actually say them when
ordering: a short, ordinary dish or cuisine category, 2-4 words — "chicken
biryani", "dal with rice", "beef noodle soup", "yogurt parfait". Only go more
specific than that if review/editorial notes were provided AND actually mention
a real dish by name.

When you can only name a cuisine/dish category (not an exact known dish), make
the health tip about HOW TO ORDER OR PORTION IT — e.g. "order the biryani but ask
for extra veggies and less rice" — rather than inventing precise nutrition
numbers you don't actually have.

## NEVER NAME A SPECIFIC INGREDIENT FOR A RESTAURANT ORDER
When a restaurant pick's reasoning, health_tip, or avoid field suggests adding or
asking for something, use a GENERAL term — "extra vegetables", "a side salad",
"some greens" — never a specific vegetable/ingredient like "spinach" or
"cucumber". You don't know their actual ingredients on hand, and naming one
specific thing that turns out not to be available is worse for her than a
general term she can ask about flexibly. (This rule is only for restaurant
picks — the home_option is fine to be ingredient-specific, since she's shopping
and cooking it herself.)

## EXCEPTION — WELL-KNOWN CHAINS YOU GENUINELY RECOGNIZE
If a restaurant's name is a globally or nationally famous chain you have real,
confident knowledge of from your training — not a guess, but something you
actually know (e.g. McDonald's, KFC, Domino's, Pizza Hut, Burger King, Subway,
Starbucks, Chick-fil-A) — the dish specificity and no-specific-ingredient rules
above do NOT apply. For a genuinely recognized chain, you may:
- Name an ACTUAL specific menu item that chain really sells (e.g. "Big Mac",
  "Zinger Burger", "Pepperoni Pizza"), not just a generic category.
- Name real, specific ingredients in your ordering/health tip if you genuinely
  know their standard recipe, since chain menus are standardized worldwide and
  you are not guessing.
- Mark "cuisine_confidence" as "high" for this reason even if the name itself
  contains no cuisine word.
Only use this exception when you are GENUINELY confident it's a real famous
chain — most restaurant names that merely sound generic ("Kabab King", "Star
Restaurant", "Food Corner") are independent local businesses, not chains. If
you're not sure, assume it is NOT a recognized chain and follow the normal
generic-naming rules instead.

## CUISINE CONFIDENCE — BE HONEST ABOUT HOW SURE YOU ARE
For each pick, rate your "cuisine_confidence" as "high" or "low":
- "high": the name contains an actual cuisine or dish word — a nationality/
  region ("Bangla", "Indian", "Thai", "Turkish"...), or a specific dish/food
  type ("biryani", "kabab", "pizza", "sushi", "BBQ", "tehari", "dal"...). OR
  review/editorial notes were provided and actually mention real dishes.
- "low": everything else — including names that only contain generic
  food-establishment words like "restaurant", "cafe", "café", "kitchen",
  "dine", "hotel", "food corner", or just a person's/place's name, WITH NO
  cuisine or dish word attached. Generic words like "cafe" do NOT count as a
  cuisine signal by themselves — a place literally named "X Café" could serve
  anything from pastries to full local meals, and guessing "cafés serve
  parfaits" is exactly the kind of confident-sounding but unverified guess
  that must be rated "low", not "high".
When in doubt between high and low, pick "low" — an honest hedge is better
than a confident-sounding wrong guess. This rating is used downstream to
decide whether to hedge or offer a safer alternative instead.

## CYCLE PHASE KNOWLEDGE
Cycle day/phase boundaries are calculated elsewhere from her actual cycle
length (not assumed to be 28 days) — you are only ever given the resulting
phase NAME. Use this knowledge of what each phase means nutritionally:

### Menstrual
- Estrogen and progesterone at their lowest. Body is shedding uterine lining.
- Priority nutrients: Iron, Vitamin C (aids iron absorption), Magnesium (eases cramps), Omega-3 (anti-inflammatory)
- Best foods: lean red meat, lentils, tofu, beans, seafood, spinach, kale,
  beets, red bell peppers, salmon, walnuts, chia seeds, flaxseeds

### Follicular
- Estrogen rising. Energy improving. Body preparing for ovulation.
- Priority nutrients: B-vitamins, Probiotics, Phytoestrogens, Cruciferous vegetables
- Best foods: fermented foods (kimchi, yogurt), quinoa, oats, broccoli,
  cauliflower, flaxseeds, fresh lightly cooked vegetables

### Ovulatory
- Estrogen peaks. Testosterone rises. Peak energy and confidence.
- Priority nutrients: Fiber (clears excess estrogen), Zinc, Antioxidants
- Best foods: berries, citrus, asparagus, brussels sprouts, chicken,
  fish, eggs, chickpeas

### Luteal
- Progesterone dominates. Metabolism increases. PMS may appear.
- Priority nutrients: Complex carbs (boost serotonin), Magnesium, B6, Calcium
- Body needs ~200-300 extra calories. Honor that.
- Best foods: sweet potatoes, dark chocolate (70%+), pumpkin seeds,
  bananas, brown rice, root vegetables

### If phase is "unknown" or not applicable
Weight mood, craving, and health context only — do not invent a phase.

## USER PROFILE & SAFETY — PROVIDED EACH TURN, NOT HARDCODED HERE
You will be given a [USER PROFILE] block each turn containing her medical
conditions, allergies, and food preferences (dietary style, sweet/savory
lean, spice tolerance). Treat it exactly like the phase knowledge above —
real context that should shape every pick.

ALLERGIES ARE A HARD SAFETY CONSTRAINT, NOT A PREFERENCE: never suggest a
dish whose plausible ingredients include something she's allergic to. If
you're unsure whether a dish contains an allergen, avoid it — a safer, less
exciting pick beats a dangerous one.

## MOOD & CRAVING
You'll be given her current mood and craving each turn — sometimes including
a craving she's saved before for that mood, which she's either confirmed or
overridden with something else this time. If craving and cycle phase align,
celebrate it. If they conflict, bridge both worlds instead of picking one
over the other.

## PANTRY-CONSTRAINED HOME OPTIONS
If an [AVAILABLE PANTRY ITEMS] block is provided, the home_option's dish MUST
be makeable from ONLY those items (plus reasonable staples like salt, oil,
water) — never invent a dish that needs something not listed there.

## RESTAURANT NAME → CUISINE INFERENCE (examples)
"Bangla Kitchen" → dal, rice, curry, chicken, fish dishes
"Asian Bar-Be-Cue" → BBQ, grilled meats, Asian dishes
"Nabihah Café" → café food, sandwiches, local snacks
"Tehari Khan" → tehari, biryani, rice dishes
"Magpie Restaurant" → café-style, continental, local fusion

## INDULGENCE CLASSIFICATION
Mark indulgent "yes" for burgers, fries, fried chicken, pizza, cheesecake, boba,
desserts, ice cream, anything heavy/fried/high sugar. Mark "no" for everything else.

## OUTPUT — RESPOND WITH JSON ONLY. NO PROSE. NO MARKDOWN FENCES.
{
  "phase_used": "<menstrual|follicular|ovulatory|luteal|unknown>",
  "picks": [
    {
      "restaurant": "<exact name copied from the provided list>",
      "cuisine": "<inferred cuisine>",
      "dish_name": "<short, ordinary dish or cuisine category, 2-4 words>",
      "key_ingredients": [
        {"name": "<main ingredient>", "grams": <realistic portion in grams>},
        {"name": "<other ingredient>", "grams": <realistic portion in grams>}
      ],
      "reasoning": "<1 line: why this dish/restaurant fits her mood+phase+health>",
      "health_tip": "<1 specific, actionable health tip — ordering/portioning advice if the dish is only a category, not an exact known item>",
      "vibe": "<cozy|fresh|light|hearty>",
      "avoid": "<anything to avoid ordering here, or empty string>",
      "price_level": "<1-4>",
      "indulgent": "<yes|no>",
      "cuisine_confidence": "<high|low>"
    }
  ],
  "home_option": {
    "dish_name": "<simple homemade dish>",
    "key_ingredients": [
      {"name": "<ingredient 1>", "grams": <realistic portion in grams>},
      {"name": "<ingredient 2>", "grams": <realistic portion in grams>}
    ],
    "reasoning": "<why it's easy and fits her mood+phase+health>",
    "health_tip": "<1 short tip>",
    "vibe": "<cozy|fresh|light|hearty>",
    "avoid": "<anything to go easy on, or empty string>"
  }
}
"key_ingredients" (both in each restaurant pick AND in home_option) must list
each of the 2-4 core ingredients that make up the dish SEPARATELY (e.g.
"beef", "egg noodles", "beef broth" — not "beef noodle soup" as one string),
each with a REALISTIC gram estimate for the portion actually used in ONE
serving — not a generic 100g default. Think about real portions: a slice of
cheese is ~20-30g, a slice of bread ~30g, a cup of yogurt ~150g, an egg ~50g,
a bowl of soup broth ~250g. These are looked up individually and scaled by
your gram estimate for real nutrition data. This matters even for restaurant
dishes: food databases have almost no entries for prepared/composed dishes
like "beef noodle soup" as a whole (searching that directly tends to match a
canned/instant packaged product, which is NOT what a restaurant serves) — but
they DO have clean entries for the plain ingredients themselves, so breaking
the dish into its components gives a far more realistic result.
Return exactly 3 picks, ranked best first. Set "home_option" to null if nothing
genuinely simple fits.
"""

# -----------------------------------------------------------------------------
# SAGE'S BRAIN — communicates the Filter Agent's pick warmly
# -----------------------------------------------------------------------------
SAGE_SYSTEM_PROMPT = """
You are Sage — a warm, funny, and deeply knowledgeable AI wellness food companion.
You help women figure out exactly what to eat based on how they feel RIGHT NOW,
combined with where they are in their menstrual cycle.

You are not a generic chatbot. You are the friend who actually read the nutrition
research, remembers what worked for you last time, and will gently roast you if
you say you want a salad when your body is clearly screaming for iron.

## YOUR PERSONALITY
- Warm, sisterly, and encouraging — never preachy or clinical
- Funny and light — you make nutrition feel fun, not like homework
- Direct — you give a clear recommendation, you don't hedge endlessly
- Smart — you explain the WHY behind every recommendation in plain language
- Honest — if someone says they want junk food, acknowledge the craving,
  validate it, then redirect with something that satisfies AND supports them

## CONVERSATION RULES
- You are in an ongoing conversation. Never forget what was established earlier.
- If the cycle phase you're given is "unknown", gently ask what day of her cycle
  she's on as part of your reply — never say the words "phase unknown."

## YOUR JOB HERE
Another step in the pipeline has already reasoned through the real nearby
restaurants and picked the best dish + restaurant for her right now, along with
a health tip and (when available) real nutrition numbers for that dish. Your job
is ONLY to communicate that pick warmly — do NOT second-guess it, do NOT invent
a different restaurant or dish.

## NUTRITION NUMBERS — ONLY USE WHAT YOU'RE GIVEN
If real nutrition numbers are provided, weave 1-2 of them in naturally. If you
are told no reliable numbers are available (common for regional/local dishes not
in US food databases), do NOT invent any numbers. Instead reason qualitatively
from common food knowledge in your own words — e.g. chicken/dal/eggs/yogurt are
good protein, rice/bread/potatoes are the carbs, vegetables bring the fiber.

## HOME-COOK OPTION — WHEN TO LEAD WITH IT INSTEAD
You may also be given a simple home-cook option, and each restaurant pick comes
with a "cuisine_confidence" of "high" or "low".
- If the top pick's confidence is "high": the restaurant/dish is your primary
  recommendation. Only mention the home option as a brief, optional aside if it
  fits naturally (e.g. "or honestly, you could just whip up X at home in 5
  minutes") — never lead with it, never make it feel mandatory.
- If the top pick's confidence is "low" AND a home option was given: LEAD with
  the home option instead — it's the safer bet since the restaurant guess is
  shaky. Still mention the restaurant briefly as a "if you want to go out"
  option, but be upfront you're not fully sure of their menu.
- If the top pick's confidence is "low" and there's NO home option: give the
  restaurant recommendation anyway (she still wants an answer, not a shrug),
  but be honest about the uncertainty — e.g. "not 100% sure of their exact
  menu, but going by the name, ask for X" — and lean on the ordering/portioning
  tip rather than asserting a specific dish with false confidence.

## YOUR RESPONSE STRUCTURE
Keep SHORT and conversational. 4-5 lines max. Friend texting back.
No bullet points. No headers.

1. One warm/funny line acknowledging how she feels
2. Recommend the dish (restaurant or home, per the rule above)
3. If the pick is marked indulgent, be warm and guilt-free about it
4. (Optional) one line for whichever of restaurant/home you didn't lead with

Then, on its OWN separate line — a blank line before it, nothing else on that
line — share the health tip you were given, in your own voice, starting with
"Health tip:" (capital H) so it's easy to spot at a glance instead of buried
in a paragraph.

Note: You are not a doctor. Always recommend consulting a healthcare provider.
"""

# -----------------------------------------------------------------------------
# SESSION STATE
# -----------------------------------------------------------------------------
if "conversation_history" not in st.session_state:
    st.session_state.conversation_history = [
        {"role": "system", "content": SAGE_SYSTEM_PROMPT}
    ]
if "messages" not in st.session_state:
    st.session_state.messages = []
if "chat_id" not in st.session_state:
    st.session_state.chat_id = None          # None = a new chat not saved yet
if "chat_title" not in st.session_state:
    st.session_state.chat_title = ""
if "_last_chat_json" not in st.session_state:
    st.session_state._last_chat_json = None  # last state written, to skip no-op saves


def _blank_chat() -> None:
    """Resets everything belonging to the current chat (not the login or
    location)."""
    st.session_state.messages = []
    st.session_state.conversation_history = [{"role": "system", "content": SAGE_SYSTEM_PROMPT}]
    st.session_state.pending_mood = ""
    st.session_state.pop("resolved_craving", None)
    st.session_state.chat_id = None
    st.session_state.chat_title = ""
    st.session_state._last_chat_json = None


def _apply_chat_state(state: dict) -> None:
    """Loads a saved chat state dict into session_state. Voice audio isn't
    stored (it's regenerated), and auto_played is forced True so restored
    replies don't all start speaking again."""
    messages = state.get("messages", [])
    for m in messages:
        if m.get("type") == "sage":
            m["auto_played"] = True
    st.session_state.messages = messages
    # The system prompt is never stored, so a saved chat always picks up the
    # current one instead of a stale copy.
    history = [m for m in state.get("conversation_history", []) if m.get("role") != "system"]
    st.session_state.conversation_history = (
        [{"role": "system", "content": SAGE_SYSTEM_PROMPT}] + history
    )
    st.session_state.pending_mood = state.get("pending_mood", "")
    if state.get("resolved_craving") is not None:
        st.session_state.resolved_craving = state["resolved_craving"]
    else:
        st.session_state.pop("resolved_craving", None)
if "location_set" not in st.session_state:
    st.session_state.location_set = False
if "user_location" not in st.session_state:
    st.session_state.user_location = ""
if "user_city" not in st.session_state:
    st.session_state.user_city = ""
if "detecting" not in st.session_state:
    st.session_state.detecting = False

# ---- Accounts / onboarding ----
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "onboarding_step" not in st.session_state:
    st.session_state.onboarding_step = "login"
if "onboarding_errors" not in st.session_state:
    st.session_state.onboarding_errors = ""
if "session_token" not in st.session_state:
    st.session_state.session_token = None
if "pending_url_token" not in st.session_state:
    st.session_state.pending_url_token = None

# Applying a just-created session token to the URL happens here, on the
# script pass AFTER login (not in the same pass as the login button's
# st.rerun()) — verified with a real browser that setting st.query_params
# immediately before st.rerun() silently drops the URL update; Streamlit
# never syncs it to the browser because the rerun interrupts that pending
# message. Deferring the write to a plain (non-rerun-triggering) pass fixes
# it, confirmed with Playwright.
if st.session_state.pending_url_token:
    st.query_params["s"] = st.session_state.pending_url_token
    st.session_state.pending_url_token = None

# Restore login across a page reload from a token kept in the URL's query
# string (st.query_params — read synchronously, no round trip) instead of
# forcing a fresh login every time the tab refreshes. A plain reload (F5)
# preserves the URL including its query string, so this survives that.
# If already logged in this session, touch the token instead so the
# 10-minute inactivity clock resets on every real interaction rather than
# expiring on a timer from login time.
if st.session_state.user_id is None:
    _url_token = st.query_params.get("s")
    if _url_token:
        _restored_uid = db.get_session_user(_url_token)
        if _restored_uid:
            st.session_state.user_id = _restored_uid
            st.session_state.session_token = _url_token
            st.session_state.onboarding_step = (
                "done" if db.has_completed_onboarding(_restored_uid)
                else db.resume_onboarding_step(_restored_uid)
            )
            # Location lives on the session row, not the permanent profile —
            # restoring it here means a page reload doesn't re-ask for it,
            # while a genuinely new login still will (fresh session, no
            # saved location yet), matching the original spec.
            _saved_location = db.get_session_location(_url_token)
            if _saved_location:
                st.session_state.user_location = _saved_location["user_location"]
                st.session_state.user_city = _saved_location["user_city"]
                st.session_state.location_set = True
            # Chats are saved per user (chats table). The session remembers
            # which one you had open; a brand-new chat with no saved row yet
            # keeps its mood/craving progress as a draft on the session.
            _open_chat_id = db.get_session_chat_id(_url_token)
            _open_chat = db.get_chat(_restored_uid, _open_chat_id) if _open_chat_id else None
            if _open_chat:
                st.session_state.chat_id = _open_chat["id"]
                _apply_chat_state(_open_chat["state"])
            else:
                _draft = db.get_session_chat_state(_url_token)
                if _draft:
                    _apply_chat_state(_draft)
            db.touch_session(_url_token)
        else:
            del st.query_params["s"]
elif st.session_state.session_token:
    db.touch_session(st.session_state.session_token)
    # st.navigation()'s own page routing (Chat/Profile/Pantry) rewrites the
    # URL to a path-based scheme (e.g. /page_profile) and silently strips
    # any query string in the process — confirmed by watching the URL
    # change on every sidebar page click. Re-assert the token here (runs on
    # every rerun, including page switches) so it's restored right after
    # navigation wipes it, instead of only being set once at login.
    if st.query_params.get("s") != st.session_state.session_token:
        st.query_params["s"] = st.session_state.session_token

# ---- Per-turn food-selection flow ----
if "pending_mood" not in st.session_state:
    st.session_state.pending_mood = ""
if "food_mode" not in st.session_state:
    st.session_state.food_mode = ""  # "restaurant" | "home", chosen via buttons each turn

# -----------------------------------------------------------------------------
# ONBOARDING — buttons/dropdowns wherever possible, mobile-friendly.
# Login -> basics -> medical/allergies/preferences -> cycle info (Female
# only) -> craving map -> done. Mirrors the same session-state view-gating
# pattern already used for the location step further down.
# -----------------------------------------------------------------------------
GENDER_OPTIONS = ["Male", "Female", "Other", "Prefer not to say"]
MEDICAL_CONDITION_OPTIONS = ["PCOS", "PCOD", "Diabetes", "Thyroid/Hashimoto's", "IBS", "Celiac", "Other", "None"]
ALLERGY_OPTIONS = ["Nuts", "Shellfish", "Dairy", "Gluten", "Soy", "Eggs", "Other", "None"]
DIETARY_STYLE_OPTIONS = ["No restriction", "Vegetarian", "Vegan", "Eggetarian", "Pescatarian", "Non-vegetarian"]
SPICE_OPTIONS = ["Mild", "Medium", "Spicy"]
SWEET_SAVORY_OPTIONS = ["Sweet", "Savory", "Balanced / no strong preference"]
MOOD_LIST = ["Happy", "Sad", "Anxious/Stressed", "Tired/Exhausted", "Irritable", "Energetic", "Bloated", "Crampy", "Normal Day"]
CRAVING_CATEGORY_OPTIONS = ["Sweet", "Savory", "Spicy", "Cheesy", "Carbs/Comfort food", "Light/Fresh", "Fried/Indulgent", "Anything/Surprise me"]
PANTRY_STALE_DAYS = 12

# Tap-to-add choices for the pantry page, so stocking up is a few taps instead
# of typing every item. Lowercase because pantry items are stored lowercase.
PANTRY_CATEGORIES = {
    "Vegetables": [
        "spinach", "onion", "tomato", "potato", "carrot", "broccoli", "cauliflower",
        "bell pepper", "cucumber", "cabbage", "garlic", "ginger", "eggplant",
        "green beans", "mushrooms", "sweet potato", "kale", "lettuce", "peas",
        "corn", "zucchini", "pumpkin", "green chili", "cilantro",
    ],
    "Fruits": [
        "banana", "apple", "orange", "lemon", "lime", "berries", "mango", "avocado",
        "grapes", "pineapple", "watermelon", "papaya", "pear", "dates",
    ],
    "Protein": [
        "eggs", "chicken", "beef", "fish", "salmon", "shrimp", "tofu", "lentils",
        "chickpeas", "black beans", "kidney beans", "paneer", "turkey", "tuna",
    ],
    "Dairy": ["milk", "yogurt", "cheese", "butter", "ghee", "cream", "cottage cheese"],
    "Grains & bread": [
        "rice", "oats", "bread", "pasta", "noodles", "flour", "quinoa", "tortillas",
        "couscous", "cornflakes",
    ],
    "Staples & sauces": [
        "cooking oil", "olive oil", "salt", "sugar", "honey", "peanut butter",
        "soy sauce", "vinegar", "tomato sauce", "coconut milk", "nuts", "seeds",
    ],
    "Spices": [
        "black pepper", "turmeric", "cumin", "chili powder", "paprika", "coriander powder",
        "curry powder", "garam masala", "cinnamon", "oregano",
    ],
}
PANTRY_PICK_KEYS = [f"pantry_pick_{i}" for i in range(len(PANTRY_CATEGORIES))] + ["pantry_pick_again"]


def _onboarding_header(title: str, subtitle: str = "") -> None:
    subtitle_html = ""
    if subtitle:
        subtitle_html = (
            "<div style='text-align:center; color:#8A7F7A; font-size:0.85rem; "
            f"margin-top:-0.8rem;'>{md_safe(subtitle)}</div>"
        )
    st.markdown(
        "<div class='sage-header'><div class='sage-title'>Ask <span>Sage</span></div>"
        f"<div class='sage-subtitle'>{md_safe(title)}</div></div>"
        f"{subtitle_html}"
        "<hr class='sage-divider'>",
        unsafe_allow_html=True,
    )


def render_login_signup() -> None:
    _onboarding_header("Welcome", "Log in or create an account to get started")
    st.markdown(
        "<div style='text-align:center; font-size:0.8rem; color:#8A7F7A; "
        "margin:-0.6rem 0 1.2rem 0;'>"
        "🔒 Your health, cycle, and pantry data stays on this device in a local "
        "database. Nothing is uploaded or shared anywhere."
        "</div>",
        unsafe_allow_html=True,
    )
    tab_login, tab_signup = st.tabs(["Log In", "Sign Up"])

    with tab_login:
        login_col, _ = st.columns([2, 1])
        with login_col:
            username = st.text_input("Username", key="login_username")
            password = st.text_input("Password", type="password", key="login_password")
        if st.button("Log In", key="login_btn"):
            uid = db.verify_login(username.strip(), password)
            if uid is None:
                st.session_state.onboarding_errors = "Incorrect username or password."
            else:
                st.session_state.user_id = uid
                st.session_state.onboarding_step = "done" if db.has_completed_onboarding(uid) else db.resume_onboarding_step(uid)
                st.session_state.onboarding_errors = ""
                token = db.create_session(uid)
                st.session_state.session_token = token
                st.session_state.pending_url_token = token
                st.rerun()

    with tab_signup:
        signup_col, _ = st.columns([2, 1])
        with signup_col:
            new_username = st.text_input("Choose a username", key="signup_username")
            new_password = st.text_input("Choose a password", type="password", key="signup_password")
            confirm_password = st.text_input("Confirm password", type="password", key="signup_confirm")
        if st.button("Create Account", key="signup_btn"):
            if not new_username.strip() or not new_password:
                st.session_state.onboarding_errors = "Username and password can't be empty."
            elif new_password != confirm_password:
                st.session_state.onboarding_errors = "Passwords don't match."
            else:
                uid = db.create_user(new_username.strip(), new_password)
                if uid is None:
                    st.session_state.onboarding_errors = "That username is already taken."
                else:
                    st.session_state.user_id = uid
                    st.session_state.onboarding_step = "basics"
                    st.session_state.onboarding_errors = ""
                    token = db.create_session(uid)
                    st.session_state.session_token = token
                    st.session_state.pending_url_token = token
                    st.rerun()

    if st.session_state.onboarding_errors:
        st.error(st.session_state.onboarding_errors)


def render_basics() -> None:
    _onboarding_header("Tell us about you", "Asked once. You can update this later")
    name = st.text_input("Name")

    age_col, gender_col = st.columns([1, 2])
    with age_col:
        age = st.number_input("Age", min_value=10, max_value=100, value=None, step=1, placeholder="e.g. 25")
    with gender_col:
        gender = st.selectbox("Gender", GENDER_OPTIONS, index=None, placeholder="Select...")

    st.markdown("Height")
    height_unit = st.segmented_control("Height unit", ["cm", "ft & in"], default="cm", label_visibility="collapsed", key="height_unit")
    if height_unit == "ft & in":
        hcol1, hcol2, _ = st.columns([1, 1, 2])
        with hcol1:
            feet = st.number_input("Feet", min_value=3, max_value=8, value=None, step=1, placeholder="ft", key="height_feet")
        with hcol2:
            inches = st.number_input("Inches", min_value=0, max_value=11, value=None, step=1, placeholder="in", key="height_inches")
        height = f"{int(feet)}'{int(inches)}\"" if feet is not None and inches is not None else ""
    else:
        hcol, _ = st.columns([1, 2])
        with hcol:
            height_cm = st.number_input("Height (cm)", min_value=100, max_value=250, value=None, step=1, placeholder="e.g. 163", label_visibility="collapsed", key="height_cm")
        height = f"{int(height_cm)} cm" if height_cm is not None else ""

    st.markdown("Weight")
    weight_unit = st.segmented_control("Weight unit", ["kg", "lbs"], default="kg", label_visibility="collapsed", key="weight_unit")
    wcol, _ = st.columns([1, 2])
    with wcol:
        weight_value = st.number_input(
            f"Weight ({weight_unit})", min_value=20, max_value=400, value=None, step=1,
            placeholder=f"e.g. {'59' if weight_unit == 'kg' else '130'}", label_visibility="collapsed", key="weight_value",
        )
    weight = f"{int(weight_value)} {weight_unit}" if weight_value is not None else ""

    if st.button("Continue", key="basics_continue"):
        if not name.strip() or age is None or gender is None:
            st.session_state.onboarding_errors = "Please fill in your name, age, and gender."
        else:
            db.save_profile(st.session_state.user_id, name.strip(), int(age), gender, height, weight)
            st.session_state.onboarding_step = "medical"
            st.session_state.onboarding_errors = ""
            st.rerun()

    if st.session_state.onboarding_errors:
        st.error(st.session_state.onboarding_errors)


def _multiselect_with_other(label: str, options: list, key: str, default: list = None) -> list:
    """A multiselect where picking "Other" reveals a free-text field for
    anything not covered by the fixed option list (e.g. a condition or
    allergy that isn't PCOS/Nuts/etc.). Returns the selected standard
    options plus whatever custom entries were typed, "Other" itself never
    included in the result. `default` may contain values outside `options`
    (previously saved custom entries) — those get folded into the custom
    text field instead of being silently dropped from the multiselect."""
    default = default or []
    standard_default = [d for d in default if d in options]
    custom_values = [d for d in default if d not in options]
    if custom_values and "Other" not in standard_default:
        standard_default = standard_default + ["Other"]

    selected = st.multiselect(label, options, default=standard_default, key=key)
    result = [s for s in selected if s != "Other"]
    if "Other" in selected:
        custom_text = st.text_input(
            "Please specify (comma-separated if more than one)",
            value=", ".join(custom_values),
            key=f"{key}_other_text",
        )
        result += [c.strip() for c in custom_text.split(",") if c.strip()]
    return result


def render_medical_info() -> None:
    _onboarding_header("Health & preferences", "Asked once. Update anytime from Settings")
    conditions = _multiselect_with_other("Medical conditions (if any)", MEDICAL_CONDITION_OPTIONS, key="med_conditions")
    allergies = _multiselect_with_other("Allergies (if any)", ALLERGY_OPTIONS, key="med_allergies")
    dietary_style = st.selectbox("Dietary style", DIETARY_STYLE_OPTIONS, index=None, placeholder="Select...")
    sweet_savory = st.radio("Do you lean sweet or savory?", SWEET_SAVORY_OPTIONS, index=None)
    spice_tolerance = st.selectbox("Spice tolerance", SPICE_OPTIONS, index=None, placeholder="Select...")
    notes = st.text_area("Anything else? (optional)", placeholder="e.g. prefers sweet over savory, dislikes mushrooms")
    if st.button("Continue", key="medical_continue"):
        if dietary_style is None or sweet_savory is None or spice_tolerance is None:
            st.session_state.onboarding_errors = "Please fill in dietary style, sweet/savory lean, and spice tolerance."
        else:
            db.save_medical_info(
                st.session_state.user_id, conditions, allergies, dietary_style,
                sweet_savory, spice_tolerance, notes.strip(),
            )
            profile = db.get_profile(st.session_state.user_id)
            st.session_state.onboarding_step = "cycle" if profile.get("gender") == "Female" else "craving_map"
            st.session_state.onboarding_errors = ""
            st.rerun()

    if st.session_state.onboarding_errors:
        st.error(st.session_state.onboarding_errors)


def render_cycle_info() -> None:
    _onboarding_header("Cycle info", "Only asked because this helps personalize recommendations. Used to calculate your current phase")
    st.markdown(
        "<div style='font-size:0.78rem; color:#8A7F7A; margin:-0.6rem 0 1rem 0;'>"
        "Phase estimates use a standard calendar method and are not a diagnosis. "
        "If you have irregular cycles or a diagnosed condition, talk to your "
        "healthcare provider about what's typical for you.</div>",
        unsafe_allow_html=True,
    )
    cycle_length = st.number_input(
        "Average cycle length (days)", min_value=21, max_value=45, value=None, step=1,
        placeholder="e.g. 28",
        help="A typical cycle is 21-35 days (ACOG). Outside that range is still fine to enter.",
    )
    last_period_date = st.date_input("First day of your last period", value=None)
    if st.button("Continue", key="cycle_continue"):
        if cycle_length is None or last_period_date is None:
            st.session_state.onboarding_errors = "Please fill in your cycle length and last period date."
        else:
            db.save_cycle_info(st.session_state.user_id, int(cycle_length), last_period_date.isoformat())
            st.session_state.onboarding_step = "craving_map"
            st.session_state.onboarding_errors = ""
            st.rerun()

    if st.session_state.onboarding_errors:
        st.error(st.session_state.onboarding_errors)


def render_craving_map() -> None:
    _onboarding_header("Your craving map", "For each mood, what do you usually crave? You can update this anytime.")
    selections = {}
    for mood in MOOD_LIST:
        selections[mood] = st.multiselect(f"When you're feeling **{mood}**", CRAVING_CATEGORY_OPTIONS, key=f"craving_{mood}")
    if st.button("Finish Setup", key="craving_finish"):
        mood_to_craving = {m: ", ".join(v) for m, v in selections.items() if v}
        if mood_to_craving:
            db.save_craving_map(st.session_state.user_id, mood_to_craving)
        db.mark_onboarding_complete(st.session_state.user_id)
        st.session_state.onboarding_step = "done"
        st.rerun()


def render_onboarding() -> None:
    step = st.session_state.onboarding_step
    if step == "login":
        render_login_signup()
    elif step == "basics":
        render_basics()
    elif step == "medical":
        render_medical_info()
    elif step == "cycle":
        render_cycle_info()
    elif step == "craving_map":
        render_craving_map()

# -----------------------------------------------------------------------------
# HELPERS
# -----------------------------------------------------------------------------
NON_FOOD_WORDS = [
    "agency", "shop", "store", "workshop", "clinic", "hospital",
    "school", "office", "bank", "salon", "pharmacy", "hardware",
    "electric", "supply", "mart", "enterprise", "trading", "industries"
]



def md_safe(text) -> str:
    """Make LLM/API text safe to drop into raw HTML via st.markdown(unsafe_allow_html=True).
    A stray backtick in a restaurant name or LLM reply opens an unmatched Markdown
    code span and can swallow the rest of that block into a rendered code box —
    escaping HTML chars and neutralizing backticks prevents that."""
    return html.escape(str(text), quote=True).replace("`", "&#96;")


def cap_first(text) -> str:
    """Capitalize just the first letter, leaving the rest of the text untouched
    (unlike .capitalize(), which would lowercase the rest of the string)."""
    text = str(text)
    return text[:1].upper() + text[1:] if text else text


def calculate_cycle_phase(cycle_day: int, cycle_length: int) -> str:
    """Cycle phase from cycle day + her actual cycle length, instead of
    assuming a fixed 28 days. Uses the standard calendar/luteal-phase method:
    ovulation day ~= cycle_length - 14, because the luteal phase (ovulation to
    next period) is the relatively fixed part (~14 days) while the follicular
    phase (before ovulation) absorbs most of the cycle-length variability.
    Sources: ACOG-based calendar method (Cleveland Clinic summary); NCBI
    StatPearls "Physiology, Menstrual Cycle"; Mayo Clinic on normal cycle/
    period length ranges. This is an estimate, not a diagnosis — real luteal
    phase length varies more between individuals than the classic model
    assumes (Human Reproduction, 2024)."""
    ovulation_day = cycle_length - 14
    menstrual_end = min(5, max(1, ovulation_day - 3))
    ovulatory_start = max(menstrual_end + 1, ovulation_day - 1)
    ovulatory_end = ovulation_day + 1
    if cycle_day <= menstrual_end:
        return "menstrual"
    elif cycle_day <= ovulatory_start - 1:
        return "follicular"
    elif cycle_day <= ovulatory_end:
        return "ovulatory"
    return "luteal"


def get_current_cycle_phase(user_id: int) -> str:
    """Looks up this user's stored cycle length + last period date and
    calculates today's phase fresh — no need for her to ever say 'day N' in
    chat, and it stays accurate across app restarts and multiple days
    automatically. Returns '' if cycle info isn't set (e.g. not applicable)."""
    info = db.get_cycle_info(user_id)
    if not info or not info.get("cycle_length") or not info.get("last_period_date"):
        return ""
    try:
        cycle_length = int(info["cycle_length"])
        last_period = date.fromisoformat(info["last_period_date"])
        cycle_day = (date.today() - last_period).days % cycle_length + 1
        return calculate_cycle_phase(cycle_day, cycle_length)
    except Exception:
        return ""


def save_feedback(user_id: int, restaurant: str, dish_name: str, liked: bool,
                   cuisine: str = "", indulgent: str = "", vibe: str = "",
                   phase: str = "") -> None:
    """Record a thumbs up/down on a pick, plus the attributes it was tagged
    with (cuisine/indulgent/vibe/phase), so future recommendations can lean
    toward what's worked before — not just by exact dish name, but by the
    kind of thing she tends to like. Now per-user in the database."""
    db.save_feedback(user_id, restaurant, dish_name, liked, cuisine, indulgent, vibe, phase)


def _top_counts(entries: list, field: str, n: int = 3) -> list:
    counts = {}
    for h in entries:
        val = (h.get(field) or "").strip()
        if val:
            counts[val] = counts.get(val, 0) + 1
    return sorted(counts.items(), key=lambda kv: -kv[1])[:n]


def log_interaction(user_id: int, **fields) -> None:
    """Per-user log of each turn's key decisions (phase, restaurant vs home,
    cuisine confidence, nutrition source) — lets us see behavior and drift
    over time by reading the database, instead of only noticing a problem
    when a reply happens to look visibly wrong in the moment."""
    db.log_interaction(user_id, **fields)


def load_feedback_summary(user_id: int) -> str:
    """Build a short summary of past feedback for the Filter Agent — both the
    specific liked/disliked dishes (recency-based) AND an aggregate pattern
    (cuisines/vibe/indulgence she tends to like or dislike), so the signal is
    a real preference profile, not just a list of exact dish names to repeat
    or avoid. This is what makes Sage feel like she remembers you."""
    history = db.get_feedback_history(user_id)
    if not history:
        return ""
    liked = [h for h in history if h.get("liked") == 1]
    disliked = [h for h in history if h.get("liked") == 0]

    lines = []
    liked_dishes = [f"{h['dish_name']} ({h['restaurant']})" for h in liked if h.get("dish_name")]
    if liked_dishes:
        lines.append("Liked before: " + ", ".join(liked_dishes[-10:]))
    disliked_dishes = [f"{h['dish_name']} ({h['restaurant']})" for h in disliked if h.get("dish_name")]
    if disliked_dishes:
        lines.append("Disliked before: " + ", ".join(disliked_dishes[-10:]))

    liked_cuisines = _top_counts(liked, "cuisine")
    if liked_cuisines:
        lines.append("Cuisines/styles she's liked most: " +
                      ", ".join(f"{c} ({n}x)" for c, n in liked_cuisines))
    disliked_cuisines = _top_counts(disliked, "cuisine")
    if disliked_cuisines:
        lines.append("Cuisines/styles she's disliked: " +
                      ", ".join(f"{c} ({n}x)" for c, n in disliked_cuisines))

    indulgent_liked = sum(1 for h in liked if h.get("indulgent") == "yes")
    indulgent_disliked = sum(1 for h in disliked if h.get("indulgent") == "yes")
    if indulgent_liked + indulgent_disliked >= 2:
        if indulgent_liked > indulgent_disliked:
            lines.append("She tends to enjoy indulgent picks when offered one.")
        elif indulgent_disliked > indulgent_liked:
            lines.append("She tends to prefer non-indulgent picks even when offered something indulgent.")

    return "\n".join(lines)




# NOTE: the old wants_to_eat_out() LLM-based intent classifier is gone —
# the food-mode buttons in the UI (Restaurant / At Home) now make this an
# explicit choice instead of something to infer from text, which removes a
# whole LLM call and the residual risk of it guessing wrong.

# -----------------------------------------------------------------------------
# CORE FUNCTIONS
# -----------------------------------------------------------------------------
MAX_HISTORY_MESSAGES = 6  # last 3 exchanges; older turns are dropped


def _trim_history(history: list, max_messages: int = MAX_HISTORY_MESSAGES) -> list:
    """Keeps the system prompt plus the most recent max_messages messages,
    starting on a user message. Without a cap every turn re-sent (and re-paid
    for) the whole conversation, which slows replies and burns the daily token
    quota. Each turn's context is self-contained (mood, phase, pick, real
    nutrition), so older turns aren't needed for Sage to write a good reply."""
    system, rest = history[:1], history[1:]
    rest = rest[-max_messages:]
    while rest and rest[0].get("role") != "user":
        rest = rest[1:]
    return system + rest


def ask_sage(user_message: str) -> str:
    st.session_state.conversation_history.append({
        "role": "user", "content": user_message
    })
    st.session_state.conversation_history = _trim_history(st.session_state.conversation_history)
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=st.session_state.conversation_history,
            temperature=0.7,
            max_tokens=1024,
            reasoning_effort="low",
        )
        sage_reply = response.choices[0].message.content
        st.session_state.conversation_history.append({
            "role": "assistant", "content": sage_reply
        })
        st.session_state.conversation_history = _trim_history(st.session_state.conversation_history)
        return sage_reply
    except Exception as e:
        return f"Sage hit an error: {e}"


def translate_if_bangla(name: str) -> str:
    if any('\u0980' <= char <= '\u09FF' for char in name):
        try:
            return GoogleTranslator(source='bn', target='en').translate(name)
        except:
            return name
    return name


def get_nearby_restaurants(location: str, keyword: str = "restaurant",
                           limit: int = 10) -> list:
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": location,
        "type": "restaurant",
        "keyword": keyword,
        "key": places_key,
        "opennow": True,
        "language": "en",
        "rankby": "distance",
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        if data.get("status") != "OK":
            return []
        results = data.get("results", [])
        restaurants = []
        for place in results[:20]:
            place_types = set(place.get("types", []))
            food_types = {"restaurant", "food", "cafe", "bakery",
                          "bar", "meal_takeaway", "meal_delivery"}
            if not food_types.intersection(place_types):
                continue
            if not place.get("rating"):
                continue
            name = translate_if_bangla(place.get("name", ""))
            if any(w in name.lower() for w in NON_FOOD_WORDS):
                continue
            restaurants.append({
                "name":        name,
                "place_id":    place.get("place_id", ""),
                "rating":      place.get("rating", "N/A"),
                "address":     place.get("vicinity", "No address"),
                "price_level": place.get("price_level", 0),
                "open_now":    place.get("opening_hours", {}).get("open_now"),
            })
            if len(restaurants) == limit:
                break
        return restaurants
    except:
        return []


def get_place_details(place_id: str) -> dict:
    """Optional enrichment (ENRICH_WITH_REVIEWS): pull review/editorial snippets
    for a restaurant so the Filter Agent has more than just the name to reason from."""
    if not place_id:
        return {}
    url = "https://maps.googleapis.com/maps/api/place/details/json"
    params = {
        "place_id": place_id,
        "fields": "reviews,editorial_summary",
        "key": places_key,
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        result = response.json().get("result", {})
        summary = result.get("editorial_summary", {}).get("overview", "")
        review_snippets = [
            rv.get("text", "")[:120]
            for rv in result.get("reviews", [])[:3]
            if rv.get("text")
        ]
        combined = " ".join([summary] + review_snippets).strip()
        return {"summary": combined[:300]} if combined else {}
    except Exception:
        return {}


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _is_repeat(dish_name: str, restaurant: str, recent: list) -> bool:
    """True if this exact dish (at this exact restaurant, or homemade when
    restaurant is blank) is among the recently shown picks."""
    dish, rest = _norm(dish_name), _norm(restaurant)
    return bool(dish) and any(
        _norm(r.get("dish_name")) == dish and _norm(r.get("restaurant")) == rest
        for r in recent
    )


def _recent_block(user_id: int) -> str:
    recent = db.get_recent_recommendations(user_id, limit=8)
    if not recent:
        return ""
    lines = []
    for r in recent:
        where = f" at {r['restaurant']}" if r.get("restaurant") else " (homemade)"
        lines.append(f"- {r['dish_name']}{where}")
    return (
        "[RECENTLY SUGGESTED: DO NOT REPEAT]\n" + "\n".join(lines) +
        "\nSuggest something different from these unless nothing else genuinely fits.\n\n"
    )


def _feedback_block(user_id: int) -> str:
    feedback_summary = load_feedback_summary(user_id)
    if not feedback_summary:
        return ""
    return (
        f"[PAST FEEDBACK]\n{feedback_summary}\n"
        f"Lean toward liked picks when they genuinely fit her current mood/phase; "
        f"avoid repeating disliked ones unless nothing else fits.\n\n"
    )


def _profile_block(user_id: int) -> str:
    """Builds the [USER PROFILE] context the Filter Agent's prompt now expects,
    replacing what used to be hardcoded 'PCOS HEALTH CONTEXT'/'PERSONAL
    CRAVING MAP' text — pulled fresh from the database each turn, so this
    works for whoever is actually logged in, not one hardcoded person."""
    medical = db.get_medical_info(user_id)
    if not medical:
        return ""
    lines = []
    if medical.get("medical_conditions"):
        lines.append("Medical conditions: " + ", ".join(medical["medical_conditions"]))
    if medical.get("allergies"):
        lines.append("Allergies (HARD constraint — never suggest these): " + ", ".join(medical["allergies"]))
    if medical.get("dietary_style") and medical["dietary_style"] != "No restriction":
        lines.append("Dietary style: " + medical["dietary_style"])
    if medical.get("sweet_savory"):
        lines.append("Sweet/savory lean: " + medical["sweet_savory"])
    if medical.get("spice_tolerance"):
        lines.append("Spice tolerance: " + medical["spice_tolerance"])
    if medical.get("preference_notes"):
        lines.append("Other preferences: " + medical["preference_notes"])
    if not lines:
        return ""
    return "[USER PROFILE]\n" + "\n".join(lines) + "\n\n"


def _get_allergies(user_id: int) -> list:
    return [a.lower() for a in db.get_medical_info(user_id).get("allergies", [])]


def _pantry_block(user_id: int) -> str:
    """Builds the [AVAILABLE PANTRY ITEMS] context for the At-Home path — the
    home_option's dish must be makeable from only what's actually listed."""
    items = db.get_pantry_items(user_id, only_unused=True)
    if not items:
        return ""
    listing = ", ".join(f"{i['item_name']}" + (f" ({i['quantity']})" if i.get("quantity") else "") for i in items)
    return f"[AVAILABLE PANTRY ITEMS]\n{listing}\n\n"


def _call_filter_llm(user_prompt: str) -> dict:
    """Shared Groq call + JSON parsing used by both filter_agent's normal
    restaurant-scoring path and the no-restaurants-open fallback below."""
    def _call(use_json_mode: bool):
        kwargs = dict(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": FILTER_SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
            # gpt-oss-120b spends a chunk of the budget on hidden reasoning
            # tokens before writing the JSON — low effort + a bigger cap
            # keeps it from running out mid-thought on a 15-restaurant list.
            max_tokens=2048,
            reasoning_effort="low",
        )
        if use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        return client.chat.completions.create(**kwargs)

    raw = ""
    try:
        raw = _call(True).choices[0].message.content
    except Exception:
        try:
            raw = _call(False).choices[0].message.content
        except Exception:
            raw = ""

    if not raw:
        return {}
    try:
        return json.loads(raw)
    except Exception:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except Exception:
                return {}
    return {}


def _home_only_recommendation(user_id: int, user_text: str, phase: str, context_note: str) -> dict:
    """Produce a home-cook-only recommendation (no restaurant involved) — used
    when At Home was chosen, when nothing is open nearby, and as the default
    when she hasn't signaled wanting to eat out at all (restaurant-name/
    cuisine guessing is inherently unreliable, so it shouldn't be the default
    she gets). Pulls in real pantry items when there are any, so the dish is
    grounded in what she actually has instead of invented."""
    pantry_block = _pantry_block(user_id)
    user_prompt = (
        f"[USER MESSAGE]\n{user_text}\n\n"
        f"[CYCLE PHASE]\n{phase or 'unknown'}\n\n"
        f"{_profile_block(user_id)}"
        f"{_feedback_block(user_id)}"
        f"{_recent_block(user_id)}"
        f"{pantry_block}"
        f"{context_note} Recommend something she can make at home instead, "
        f"matching her mood/craving/phase/health needs"
        f"{' — using ONLY the pantry items listed above' if pantry_block else ''}. "
        f'Return the same JSON schema, but with "picks" as an empty list and '
        f'"home_option" filled in with a real suggestion — do NOT leave it '
        f"null this time, she needs an actual answer."
    )
    parsed = _call_filter_llm(user_prompt)
    home_option = parsed.get("home_option") if isinstance(parsed, dict) else None
    recent = db.get_recent_recommendations(user_id, limit=8)
    if home_option and _is_repeat(home_option.get("dish_name", ""), "", recent):
        # The prompt asks it not to repeat, but that's not something to trust
        # on instruction alone: retry once, then accept whatever comes back.
        retry = _call_filter_llm(
            user_prompt + f'\n\nYou just suggested "{home_option.get("dish_name")}", which she has '
            f"had recently. Suggest a clearly different dish."
        )
        retry_home = retry.get("home_option") if isinstance(retry, dict) else None
        if retry_home and not _is_repeat(retry_home.get("dish_name", ""), "", recent):
            parsed, home_option = retry, retry_home
    if not home_option:
        # Ultimate fail-safe if even this LLM call fails — never leave her
        # with literally nothing. Deliberately avoids all of the common
        # allergens we ask about (nuts/shellfish/dairy/gluten/soy/eggs), since
        # this bypasses the LLM entirely and so can't be personalized to know
        # what to avoid — the allergy check below still runs on it regardless.
        home_option = {
            "dish_name": "rice with steamed vegetables",
            "key_ingredients": [
                {"name": "rice", "grams": 150},
                {"name": "mixed vegetables", "grams": 150},
            ],
            "reasoning": "A simple, no-cook-skill option that's easy to put together right now.",
            "health_tip": "Add a squeeze of lemon and a pinch of salt for flavor without much added sugar or sodium.",
            "vibe": "fresh", "avoid": "added sugar",
        }
    phase_used = (parsed.get("phase_used") if isinstance(parsed, dict) else None) or phase or "unknown"
    shortlist = {"phase_used": phase_used, "picks": [], "home_option": home_option}
    return _enforce_allergy_safety(shortlist, _get_allergies(user_id))


CUISINE_SIGNAL_WORDS = [
    # nationalities / regional cuisines
    "bangla", "bangladeshi", "indian", "thai", "chinese", "italian", "mexican",
    "japanese", "korean", "turkish", "lebanese", "mediterranean", "vietnamese",
    "greek", "spanish", "french", "cajun", "creole", "ethiopian", "moroccan",
    "persian", "peruvian", "caribbean", "jamaican", "hawaiian", "german",
    # specific dish / food-type words — these genuinely tell you what's
    # served, unlike vague wellness branding like "bowl" or "superfoods"
    "biryani", "biriyani", "kabab", "kebab", "kabob", "sushi", "ramen", "pho",
    "taco", "burrito", "pizza", "bbq", "barbecue", "tehari", "dal", "curry",
    "noodle", "dumpling", "sandwich", "burger", "bakery", "grill", "shawarma",
    "falafel", "hummus", "teriyaki", "pasta", "steakhouse", "seafood",
    "wings", "donut", "bagel", "waffle", "pancake", "diner", "deli",
]

KNOWN_CHAIN_WORDS = [
    "mcdonald", "kfc", "domino", "pizza hut", "burger king", "subway",
    "starbucks", "chick-fil-a", "chickfila", "taco bell", "wendy", "popeyes",
    "panda express", "dunkin", "chipotle", "five guys", "shake shack",
    "in-n-out", "in n out", "sonic", "arby", "dairy queen", "little caesars",
    "papa john",
]


def _restaurant_name_has_real_signal(name: str) -> bool:
    """A code-level check on the restaurant's actual name — not just trusting
    the model's own 'high confidence' claim, which kept slipping through on
    vague wellness branding (e.g. 'Blue Bowl Superfoods' rated high confidence
    for an invented 'Quinoa Bean Bowl', even though the name has no real
    cuisine/dish signal, just marketing buzzwords like 'bowl'/'superfoods')."""
    n = name.lower()
    return any(w in n for w in CUISINE_SIGNAL_WORDS) or any(w in n for w in KNOWN_CHAIN_WORDS)


def _enforce_restaurant_grounding(picks: list, restaurants: list) -> list:
    """Discards any pick whose 'restaurant' field isn't an exact match for a
    name actually in the real nearby-restaurants list. The prompt already
    instructs the model to 'never invent a restaurant,' but that's exactly
    the kind of safety-critical claim this codebase has learned not to trust
    on instruction alone (same pattern as cuisine confidence and allergies
    below) — an invented restaurant name here would mean showing her a place
    that isn't actually open nearby, or isn't real at all."""
    real_names = {r.get("name", "") for r in restaurants}
    return [p for p in picks if p.get("restaurant", "") in real_names]


def _enforce_cuisine_confidence(picks: list, enrich: bool) -> list:
    """Overrides a pick's self-claimed 'high' confidence if its restaurant
    name doesn't actually contain a real cuisine/dish/chain signal — telling
    the model to be honest about confidence in the prompt wasn't enough on
    its own, so this verifies the claim in code instead of just trusting it."""
    if enrich:
        # Review-grounded picks may legitimately be high-confidence for
        # reasons the bare name doesn't show — only enforce this for the
        # name-only (default) path.
        return picks
    for p in picks:
        if p.get("cuisine_confidence") == "high" and not _restaurant_name_has_real_signal(p.get("restaurant", "")):
            p["cuisine_confidence"] = "low"
    return picks


# A plain substring match on the category word alone ("shellfish") misses
# dishes that name the specific ingredient instead ("shrimp", "crab") — this
# expands each of the fixed ALLERGY_OPTIONS categories into the specific
# words a dish/ingredient list would actually use, so the safety check still
# catches them. Allergy input is a closed multiselect from ALLERGY_OPTIONS,
# so this covers every possible value.
ALLERGEN_KEYWORDS = {
    "nuts": [
        "nut", "peanut", "almond", "cashew", "walnut", "pistachio",
        "hazelnut", "pecan", "macadamia", "praline",
    ],
    "shellfish": [
        "shellfish", "shrimp", "prawn", "crab", "lobster", "scallop",
        "clam", "mussel", "oyster", "crawfish", "crayfish",
    ],
    "dairy": [
        "dairy", "milk", "cheese", "yogurt", "yoghurt", "butter", "cream",
        "ghee", "paneer", "custard", "casein", "whey",
    ],
    "gluten": [
        "gluten", "wheat", "flour", "bread", "pasta", "noodle", "barley",
        "rye", "couscous", "semolina", "bulgur", "seitan", "roti", "naan",
        "paratha",
    ],
    "soy": ["soy", "soya", "tofu", "edamame", "tempeh", "miso"],
    "eggs": ["egg"],
}


def _dish_contains_allergen(pick: dict, allergies: list) -> bool:
    """Checks a pick's key_ingredients (and dish name, as a fallback) against
    the user's allergy list, expanded via ALLERGEN_KEYWORDS. This is a
    safety-critical check we verify in code rather than just trusting the
    prompt instruction to have been honored (the same pattern that's proven
    necessary for cuisine confidence and the eat-out gate earlier)."""
    if not allergies:
        return False
    ingredient_text = " ".join(
        ing.get("name", "") if isinstance(ing, dict) else str(ing)
        for ing in (pick.get("key_ingredients") or [])
    )
    text = f"{pick.get('dish_name', '')} {ingredient_text}".lower()
    keywords = set()
    for allergen in allergies:
        keywords.update(ALLERGEN_KEYWORDS.get(allergen, [allergen]))
    # Word-boundary match (with an optional trailing "s" for plurals), not
    # plain substring — plain substring would false-positive on "coconut"
    # (contains "nut") and "eggplant" (starts with "egg"), over-filtering
    # dishes that are actually safe for those allergies.
    return any(re.search(rf"\b{re.escape(keyword)}s?\b", text) for keyword in keywords)


def _enforce_allergy_safety(shortlist: dict, allergies: list) -> dict:
    """Discards any restaurant pick or home_option whose ingredients match a
    known allergy. Allergies are a hard safety constraint, not a preference —
    this runs regardless of confidence or how good the pick otherwise looks."""
    if not allergies:
        return shortlist
    shortlist["picks"] = [p for p in shortlist.get("picks", []) if not _dish_contains_allergen(p, allergies)]
    home = shortlist.get("home_option")
    if home and _dish_contains_allergen(home, allergies):
        shortlist["home_option"] = None
    return shortlist


def filter_agent(user_id: int, restaurants: list, user_text: str, phase: str, enrich: bool) -> dict:
    """Agent 2: reasons over the real nearby restaurants + mood/cravings/phase/health
    context and returns a ranked top-3 shortlist with dish + reasoning + health tip."""
    if not restaurants:
        return _home_only_recommendation(
            user_id, user_text, phase, "No restaurants are currently open nearby."
        )

    listing_lines = []
    for r in restaurants:
        line = f"- {r['name']} | rating {r['rating']} | price_level {r['price_level']} | {r['address']}"
        if enrich:
            details = get_place_details(r.get("place_id", ""))
            if details.get("summary"):
                line += f" | notes: {details['summary']}"
        listing_lines.append(line)

    user_prompt = (
        f"[NEARBY OPEN RESTAURANTS]\n{chr(10).join(listing_lines)}\n\n"
        f"[USER MESSAGE]\n{user_text}\n\n"
        f"[CYCLE PHASE]\n{phase or 'unknown'}\n\n"
        f"{_profile_block(user_id)}"
        f"{_feedback_block(user_id)}"
        f"{_recent_block(user_id)}"
        f"Score these restaurants and return the JSON described in your instructions."
    )

    parsed = _call_filter_llm(user_prompt)
    picks = parsed.get("picks") if isinstance(parsed, dict) else None
    allergies = _get_allergies(user_id)
    if not picks:
        # Fallback: highest-rated restaurants, no reasoned dish — keeps the
        # app usable even if the model returns something unparseable.
        ranked = sorted(restaurants, key=lambda r: r.get("rating") or 0, reverse=True)[:3]
        picks = [
            {
                "restaurant": r["name"], "cuisine": "", "dish_name": "",
                "reasoning": "Highest-rated option open near you right now.",
                "health_tip": "", "vibe": "", "avoid": "",
                "price_level": str(r.get("price_level", "")), "indulgent": "no",
                "cuisine_confidence": "low",
            }
            for r in ranked
        ]
        return {"phase_used": phase or "unknown", "picks": picks, "home_option": None}

    grounded_picks = _enforce_restaurant_grounding(picks[:3], restaurants)
    recent = db.get_recent_recommendations(user_id, limit=8)
    # Stable sort: picks she hasn't just had come first, repeats go last.
    grounded_picks.sort(key=lambda p: _is_repeat(p.get("dish_name", ""), p.get("restaurant", ""), recent))
    shortlist = {
        "phase_used": parsed.get("phase_used", phase or "unknown"),
        "picks": _enforce_cuisine_confidence(grounded_picks, enrich),
        "home_option": parsed.get("home_option"),
    }
    return _enforce_allergy_safety(shortlist, allergies)


def get_nutrition_usda(dish_name: str) -> dict:
    url = "https://api.nal.usda.gov/fdc/v1/foods/search"
    params = {
        "query": dish_name,
        "api_key": USDA_API_KEY,
        "pageSize": 5,
        "dataType": "SR Legacy,Foundation",
    }
    try:
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        foods = data.get("foods", [])
        if not foods:
            return {}
        for food in foods:
            nutrients = food.get("foodNutrients", [])
            if not nutrients:
                continue
            # USDA lists "Energy" TWICE per food — once in kcal, once in kJ.
            # A plain name->value dict lets whichever one appears last in the
            # list silently overwrite the other, sometimes leaving "calories"
            # holding the kJ figure (e.g. cheddar cheese showing 1710 instead
            # of its real 408 kcal) — so calories must be matched by unit,
            # not just by name.
            nm = {}
            calories = 0
            for n in nutrients:
                name = n.get("nutrientName", "")
                if name == "Energy":
                    if n.get("unitName", "").upper() == "KCAL":
                        calories = n.get("value", 0)
                    continue
                nm[name] = n.get("value", 0)
            nutrition = {
                "found": True, "source": "USDA",
                "dish": food.get("description", dish_name),
                "serving_size": "100g",
                "calories":  calories,
                "protein":   nm.get("Protein", 0),
                "carbs":     nm.get("Carbohydrate, by difference", 0),
                "fat":       nm.get("Total lipid (fat)", 0),
                "fiber":     nm.get("Fiber, total dietary", 0),
                "sugar":     nm.get("Sugars, total including NLEA", 0),
                "iron":      nm.get("Iron, Fe", 0),
                "magnesium": nm.get("Magnesium, Mg", 0),
                "calcium":   nm.get("Calcium, Ca", 0),
                "vitamin_c": nm.get("Vitamin C, total ascorbic acid", 0),
                "sodium":    nm.get("Sodium, Na", 0),
            }
            # Used to just take the first candidate with any calorie data,
            # regardless of whether it was actually a sensible match — USDA's
            # own search ranking isn't relevance-aware enough for that (e.g.
            # a plain "banana" search ranks "Bananas, dehydrated, or banana
            # powder" ABOVE "Bananas, raw"). Checking relevance per-candidate
            # and moving on to the next one if it fails means a bad first
            # result no longer silently wins just for having a number.
            if (nutrition["calories"] and nutrition["calories"] > 0
                    and _nutrition_matches_query(dish_name, nutrition["dish"])):
                return nutrition
        return {}
    except:
        return {}


def get_nutrition_ninjas(dish_name: str) -> dict:
    url = "https://api.api-ninjas.com/v1/nutrition"
    headers = {"X-Api-Key": API_NINJAS_KEY}
    params = {"query": dish_name}
    try:
        response = requests.get(url, headers=headers, params=params, timeout=5)
        data = response.json()
        if not data or not isinstance(data, list):
            return {}
        total = {
            "found": True, "source": "API Ninjas",
            "dish": dish_name, "serving_size": "1 serving",
            "calories": 0, "protein": 0, "carbs": 0,
            "fat": 0, "fiber": 0, "sugar": 0, "sodium": 0,
        }
        field_map = {
            "calories": "calories", "protein": "protein_g",
            "carbs": "carbohydrates_total_g", "fat": "fat_total_g",
            "fiber": "fiber_g", "sugar": "sugar_g", "sodium": "sodium_mg",
        }
        for item in data:
            for total_key, item_key in field_map.items():
                value = item.get(item_key, 0)
                # The free API Ninjas tier returns a placeholder string like
                # "Only available for premium subscribers." for some fields
                # (notably calories/protein) instead of a number — skip those
                # rather than let a str+int crash silently discard everything.
                if isinstance(value, (int, float)):
                    total[total_key] += value
        # Accept the result if we got any real numeric macro data, not just
        # calories specifically — the free tier sometimes paywalls calories/
        # protein but still gives fat/carbs/fiber/sodium for free.
        if any(total[k] > 0 for k in ("calories", "protein", "carbs", "fat", "fiber")):
            return total
        return {}
    except:
        return {}


NUTRITION_STOPWORDS = {
    "with", "and", "a", "an", "the", "of", "in", "on", "for", "to", "side",
    "style", "fresh", "mixed", "served",
}


def _singularize(word: str) -> str:
    """Crude plural stripping, not a real lemmatizer, just enough so "onion"
    matches a result keyword set containing "onions" instead of treating them
    as unrelated strings. Good enough for the simple English food words this
    is matched against; not meant to handle every irregular plural."""
    if word.endswith("ies") and len(word) > 4:
        return word[:-3] + "y"
    if word.endswith("oes") and len(word) > 4:
        return word[:-2]
    if word.endswith("s") and not word.endswith("ss") and len(word) > 3:
        return word[:-1]
    return word


def _keywords(text: str) -> set:
    return {
        _singularize(w) for w in re.findall(r"[a-z]+", text.lower())
        if w not in NUTRITION_STOPWORDS and len(w) > 2
    }


# Words signaling a search result is a processed/transformed product, not
# the raw ingredient a bare single-word query like "apple" or "spinach"
# almost always means in this app's context (a dish to actually cook).
# Found by testing real ingredient lookups and seeing USDA rank these above
# the plain raw form: "apple" matching "Croissants, apple" (254 kcal/100g,
# a pastry, vs ~50 for actual apple), "spinach" matching "Spinach souffle"
# (172 vs ~23), "tomato" matching "Tomato powder" (302 vs ~18), "carrot"
# matching "Carrot, dehydrated" (341 vs ~41), each wildly wrong in exactly
# the direction that would silently inflate a recipe's calorie total.
NUTRITION_PROCESSED_FORM_WORDS = {
    "dehydrated", "powder", "flour", "souffle", "soufflé", "oil", "dried",
    "flake", "pancake", "bread", "juice", "chip", "extract", "concentrate",
    "croissant", "pie", "cake", "muffin", "jam", "jelly", "sauce", "paste",
    "canned", "frozen", "smoked", "pickled", "powdered", "candied",
    "babyfood", "toddler", "infant", "breaded", "battered",
}


def _nutrition_matches_query(query: str, result_dish: str) -> bool:
    """Guard against USDA/API Ninjas fuzzy-matching to something unrelated
    (e.g. searching 'chicken biryani' and getting back 'Spinach Souffle', or
    'paneer butter masala' matching 'Indian Bean Masala' on the word 'masala'
    alone) — require at least 2 shared keywords for a multi-word query.

    A 1-word query (a bare ingredient like "apple") keeps the single-keyword
    bar, but also rejects a result that looks like a processed/transformed
    form of it (see NUTRITION_PROCESSED_FORM_WORDS) unless the query itself
    asked for that form — "apple" shouldn't match a croissant just because
    the word "apple" appears in its name as a qualifier."""
    q, r = _keywords(query), _keywords(result_dish)
    if (r & NUTRITION_PROCESSED_FORM_WORDS) and not (q & NUTRITION_PROCESSED_FORM_WORDS):
        return False
    if len(q) == 1:
        return bool(q & r)
    needed = min(2, len(q))
    return len(q & r) >= needed


def get_nutrition(dish_name: str) -> dict:
    if not dish_name:
        return {"found": False, "dish": ""}
    for lookup in (get_nutrition_usda, get_nutrition_ninjas):
        result = lookup(dish_name)
        if result and _nutrition_matches_query(dish_name, result.get("dish", dish_name)):
            return result
    return {"found": False, "dish": dish_name}


INGREDIENT_QUERY_OVERRIDES = {
    "egg": "egg, whole, raw", "eggs": "egg, whole, raw",
    "cheese": "cheddar cheese",
    "milk": "milk, whole, 3.25% milkfat",
    "yogurt": "yogurt, plain, whole milk",
    "rice": "rice, white, long-grain, regular, cooked",
    "bread": "bread, whole wheat", "toast": "bread, whole wheat",
    "butter": "butter, salted",
    "chicken": "chicken, breast, cooked, roasted",
    "apple": "apples, raw, with skin", "apples": "apples, raw, with skin",
    "flour": "wheat flour, white, all-purpose, enriched",
    "tomato": "tomatoes, red, ripe, raw, year round average",
    "tomatoes": "tomatoes, red, ripe, raw, year round average",
    "potato": "potatoes, flesh and skin, raw",
    "potatoes": "potatoes, flesh and skin, raw",
}


def _resolve_ingredient_query(name: str) -> str:
    """A bare ingredient name like 'egg' can match an ambiguous database entry
    (we found it resolving to egg WHITES, not a whole egg) — this nudges a
    handful of common, easily-mismatched ingredients toward a more sensible
    default match."""
    return INGREDIENT_QUERY_OVERRIDES.get(name.strip().lower(), name)


def get_nutrition_for_ingredients(dish_name: str, ingredients: list) -> dict:
    """Sum real nutrition data across a homemade dish's individual ingredients,
    scaled by a realistic gram portion per ingredient — instead of matching
    the whole compound name (e.g. 'cheese omelette with toast') to one
    database entry, or assuming a flat 100g of everything (a slice of cheese
    isn't the same portion as a slice of bread). Food databases return values
    per 100g, so we scale each ingredient's numbers by grams/100 before
    summing — far more accurate than a same-size-for-everything guess."""
    if not ingredients:
        return {"found": False, "dish": dish_name}
    total = {
        "found": False, "source": "USDA/API Ninjas (combined ingredients, estimated portions)",
        "dish": dish_name, "serving_size": "estimated realistic portions",
        "calories": 0, "protein": 0, "carbs": 0, "fat": 0, "fiber": 0, "sugar": 0,
    }
    matched_any = False
    for item in ingredients:
        if isinstance(item, dict):
            name = item.get("name", "")
            try:
                grams = float(item.get("grams") or 100)
            except (TypeError, ValueError):
                grams = 100.0
        else:
            # Fallback if the model didn't follow the {name, grams} schema —
            # treat it as a plain ingredient name at a default 100g portion.
            name = str(item)
            grams = 100.0
        if not name:
            continue
        n = get_nutrition(_resolve_ingredient_query(name))
        if n.get("found"):
            matched_any = True
            scale = grams / 100.0
            for key in ("calories", "protein", "carbs", "fat", "fiber", "sugar"):
                total[key] += (n.get(key, 0) or 0) * scale
    if not matched_any:
        return {"found": False, "dish": dish_name}
    total["found"] = True
    for key in ("calories", "protein", "carbs", "fat", "fiber", "sugar"):
        total[key] = round(total[key], 1)
    return total


def get_city_from_coordinates(location: str) -> str:
    try:
        lat, lng = location.split(",")
        url = "https://maps.googleapis.com/maps/api/geocode/json"
        params = {
            "latlng": f"{lat.strip()},{lng.strip()}",
            "key": places_key,
            "result_type": "locality"
        }
        response = requests.get(url, params=params, timeout=5)
        data = response.json()
        results = data.get("results", [])
        if not results:
            return "your city"
        components = results[0].get("address_components", [])
        city = country = ""
        for component in components:
            types = component.get("types", [])
            if "locality" in types:
                city = component.get("long_name", "")
            if "country" in types:
                country = component.get("long_name", "")
        if city and country:
            return f"{city}, {country}"
        return city or "your city"
    except:
        return "your city"


def _add_selected_pantry_items() -> None:
    """Button callback: adds every tapped chip in one go, then clears the
    selections. Runs before the next script pass, which is what lets it reset
    the pills' own widget state."""
    user_id = st.session_state.user_id
    have = {i["item_name"].lower() for i in db.get_pantry_items(user_id, only_unused=True)}
    for key in PANTRY_PICK_KEYS:
        for name in st.session_state.get(key) or []:
            if name.lower() not in have:
                db.add_pantry_item(user_id, name)
                have.add(name.lower())
        st.session_state[key] = []


def page_pantry() -> None:
    user_id = st.session_state.user_id

    st.markdown(
        "<div style='font-family:\"DM Serif Display\",serif; font-size:1.6rem; "
        "color:#3D2B37; margin-bottom:0.4rem;'>🥫 Pantry</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        "<div style='font-size:0.85rem; color:#8A7F7A; margin-bottom:1rem;'>"
        "Keep this updated so 'At Home' suggestions only use what you actually have. "
        f"Items unused past {PANTRY_STALE_DAYS} days get flagged.</div>",
        unsafe_allow_html=True,
    )

    current = db.get_pantry_items(user_id, only_unused=True)
    have = {i["item_name"].lower() for i in current}

    st.markdown("<div class='section-header'>Tap what you bought</div>", unsafe_allow_html=True)
    tabs = st.tabs(list(PANTRY_CATEGORIES))
    for i, (tab, (category, options)) in enumerate(zip(tabs, PANTRY_CATEGORIES.items())):
        with tab:
            # Items already in the pantry are left out, so every chip is something new.
            available = [o for o in options if o not in have]
            if available:
                st.pills(
                    category, available, selection_mode="multi", key=f"pantry_pick_{i}",
                    format_func=str.capitalize, label_visibility="collapsed",
                )
            else:
                st.caption("Everything here is already in your pantry.")

    # Things you've used up before: one tap to restock instead of retyping.
    seen, restock = set(), []
    for item in reversed(db.get_pantry_items(user_id, only_unused=False)):
        name = item["item_name"].lower()
        if name not in have and name not in seen:
            seen.add(name)
            restock.append(name)
    if restock:
        st.markdown("<div class='section-header'>Buy again</div>", unsafe_allow_html=True)
        st.pills(
            "Buy again", restock[:20], selection_mode="multi", key="pantry_pick_again",
            format_func=str.capitalize, label_visibility="collapsed",
        )

    picked = sum(len(st.session_state.get(k) or []) for k in PANTRY_PICK_KEYS)
    st.button(
        f"Add {picked} selected to pantry" if picked else "Select items to add",
        key="pantry_add_selected", disabled=picked == 0, on_click=_add_selected_pantry_items,
    )

    with st.expander("Something not on the list?"):
        new_item = st.text_input("Item", key="pantry_new_item", placeholder="e.g. dragon fruit")
        new_qty = st.text_input("Quantity (optional)", key="pantry_new_qty", placeholder="e.g. 2 lbs")
        if st.button("Add", key="pantry_add_btn") and new_item.strip():
            db.add_pantry_item(user_id, new_item.strip().lower(), new_qty.strip())
            st.rerun()

    st.markdown("<div class='section-header'>In your pantry</div>", unsafe_allow_html=True)
    _render_pantry_table(user_id)


def _render_pantry_table(user_id: int) -> None:
    """Item / Quantity / Added / Used table. Tick Used to mark an item used
    (it stays in the table, ticked, so a mistake can be undone by unticking);
    Quantity is editable in place."""
    import pandas as pd

    everything = db.get_pantry_items(user_id, only_unused=False)
    # Items still in the pantry first (oldest first, so the ones going stale are
    # on top), then the most recently used ones.
    in_pantry = [i for i in everything if not i["used"]]
    used = [i for i in everything if i["used"]][-10:]
    rows = in_pantry + used
    if not rows:
        st.markdown(
            "<div style='font-size:0.82rem; color:#B0A8A4; padding:0.5rem 0;'>Nothing in your pantry yet.</div>",
            unsafe_allow_html=True,
        )
        return

    def added_text(item: dict) -> str:
        if item["used"]:
            return "Used"
        age = item["age_days"]
        when = "Today" if age == 0 else f"{age}d ago"
        return when + (" ⚠️ use soon" if age > PANTRY_STALE_DAYS else "")

    original = pd.DataFrame(
        {
            "Item": [i["item_name"].capitalize() for i in rows],
            "Quantity": [i.get("quantity") or "" for i in rows],
            "Added": [added_text(i) for i in rows],
            "Used": [bool(i["used"]) for i in rows],
        },
        index=[i["id"] for i in rows],
    )
    # A new key after every change: data_editor remembers edits by row
    # position, so reusing one key against a changed table would replay old
    # edits onto the wrong rows.
    version = st.session_state.get("pantry_editor_version", 0)
    edited = st.data_editor(
        original,
        key=f"pantry_editor_{version}",
        hide_index=True,
        use_container_width=True,
        disabled=["Item", "Added"],
        column_config={
            "Item": st.column_config.TextColumn("Item", width="medium"),
            "Quantity": st.column_config.TextColumn("Quantity", width="small"),
            "Added": st.column_config.TextColumn("Added", width="small"),
            "Used": st.column_config.CheckboxColumn("Used", width="small"),
        },
    )

    changed = False
    for item_id in original.index:
        if bool(edited.at[item_id, "Used"]) != bool(original.at[item_id, "Used"]):
            if edited.at[item_id, "Used"]:
                db.mark_pantry_used(item_id)
            else:
                db.mark_pantry_unused(item_id, user_id)
            changed = True
        new_qty = (edited.at[item_id, "Quantity"] or "").strip()
        if new_qty != original.at[item_id, "Quantity"]:
            db.update_pantry_quantity(item_id, user_id, new_qty)
            changed = True
    if changed:
        st.session_state.pantry_editor_version = version + 1
        st.rerun()


def page_profile() -> None:
    """A dedicated page (not gated behind location setup) for everything
    onboarding only asked once for — profile, medical/allergies/preferences,
    cycle info, and the craving map. All the underlying db.save_* calls are
    upserts, so re-saving here just overwrites the existing row."""
    user_id = st.session_state.user_id

    st.markdown(
        "<div style='font-family:\"DM Serif Display\",serif; font-size:1.6rem; "
        "color:#3D2B37; margin-bottom:0.4rem;'>👤 Profile</div>",
        unsafe_allow_html=True,
    )

    st.markdown(
        "<div style='font-size:0.78rem; color:#8A7F7A; margin-bottom:0.8rem;'>"
        "🔒 Stored locally on this device only. Editing here updates your "
        "saved profile directly, and nothing is sent anywhere else."
        "</div>",
        unsafe_allow_html=True,
    )
    profile = db.get_profile(user_id)
    medical = db.get_medical_info(user_id)
    craving_map = db.get_craving_map(user_id)
    is_female = profile.get("gender") == "Female"

    tab_names = ["Basics", "Health & preferences"]
    if is_female:
        tab_names.append("Cycle info")
    tab_names.append("Craving map")
    tabs = st.tabs(tab_names)
    tab_iter = iter(tabs)

    with next(tab_iter):
        name = st.text_input("Name", value=profile.get("name", ""), key="settings_name")
        age = st.number_input("Age", min_value=10, max_value=100, value=int(profile.get("age") or 25), step=1, key="settings_age")
        gender = st.selectbox("Gender", GENDER_OPTIONS, index=GENDER_OPTIONS.index(profile.get("gender")) if profile.get("gender") in GENDER_OPTIONS else 0, key="settings_gender")
        height = st.text_input("Height", value=profile.get("height", ""), key="settings_height")
        weight = st.text_input("Weight", value=profile.get("weight", ""), key="settings_weight")
        if st.button("Save", key="settings_save_basics"):
            db.save_profile(user_id, name.strip(), int(age), gender, height.strip(), weight.strip())
            st.success("Saved.")
            st.rerun()

    with next(tab_iter):
        conditions = _multiselect_with_other("Medical conditions (if any)", MEDICAL_CONDITION_OPTIONS, key="settings_conditions", default=medical.get("medical_conditions", []))
        allergies = _multiselect_with_other("Allergies (if any)", ALLERGY_OPTIONS, key="settings_allergies", default=medical.get("allergies", []))
        dietary_style = st.selectbox("Dietary style", DIETARY_STYLE_OPTIONS, index=DIETARY_STYLE_OPTIONS.index(medical.get("dietary_style")) if medical.get("dietary_style") in DIETARY_STYLE_OPTIONS else 0, key="settings_diet")
        sweet_savory = st.radio("Do you lean sweet or savory?", SWEET_SAVORY_OPTIONS, index=SWEET_SAVORY_OPTIONS.index(medical.get("sweet_savory")) if medical.get("sweet_savory") in SWEET_SAVORY_OPTIONS else 0, key="settings_sweet_savory")
        spice_tolerance = st.selectbox("Spice tolerance", SPICE_OPTIONS, index=SPICE_OPTIONS.index(medical.get("spice_tolerance")) if medical.get("spice_tolerance") in SPICE_OPTIONS else 0, key="settings_spice")
        notes = st.text_area("Anything else? (optional)", value=medical.get("preference_notes", ""), key="settings_notes")
        if st.button("Save", key="settings_save_medical"):
            db.save_medical_info(user_id, conditions, allergies, dietary_style, sweet_savory, spice_tolerance, notes.strip())
            st.success("Saved.")
            st.rerun()

    if is_female:
        with next(tab_iter):
            cycle = db.get_cycle_info(user_id)
            cycle_length = st.number_input(
                "Average cycle length (days)", min_value=21, max_value=45,
                value=int(cycle.get("cycle_length") or 28), step=1, key="settings_cycle_length",
            )
            default_last_period = (
                date.fromisoformat(cycle["last_period_date"]) if cycle.get("last_period_date") else date.today()
            )
            last_period_date = st.date_input("First day of your last period", value=default_last_period, key="settings_last_period")
            if st.button("Save", key="settings_save_cycle"):
                db.save_cycle_info(user_id, int(cycle_length), last_period_date.isoformat())
                st.success("Saved.")
                st.rerun()

    with next(tab_iter):
        st.markdown(
            "<div style='font-size:0.82rem; color:#8A7F7A; margin-bottom:0.6rem;'>"
            "Update what you usually crave for each mood. Sage checks this every time you tell her how you're feeling.</div>",
            unsafe_allow_html=True,
        )
        selections = {}
        for mood in MOOD_LIST:
            current = [c.strip() for c in craving_map.get(mood, "").split(",") if c.strip()]
            selections[mood] = st.multiselect(
                f"When you're feeling **{mood}**", CRAVING_CATEGORY_OPTIONS,
                default=[c for c in current if c in CRAVING_CATEGORY_OPTIONS],
                key=f"settings_craving_{mood}",
            )
        if st.button("Save", key="settings_save_craving"):
            mood_to_craving = {m: ", ".join(v) for m, v in selections.items() if v}
            if mood_to_craving:
                db.save_craving_map(user_id, mood_to_craving)
            st.success("Saved.")
            st.rerun()


def render_restaurants(restaurant_list: list, phase: str, note: str = ""):
    phase_emoji = {"menstrual": "🩸", "follicular": "🌱",
                   "ovulatory": "✨", "luteal": "🌙"}.get(phase, "🌿")
    phase_class = f"phase-{phase}" if phase else ""

    st.markdown(
        "<div class='section-header'>🍽️ Sage's Picks Near You</div>",
        unsafe_allow_html=True
    )
    if phase:
        st.markdown(
            f"<span class='phase-badge {phase_class}'>"
            f"{phase_emoji} {phase.title()} Phase</span>",
            unsafe_allow_html=True
        )
    if note:
        st.markdown(
            f"<div style='font-size:0.82rem; color:#8A7F7A; "
            f"font-style:italic; margin:0.3rem 0 0.8rem 0;'>🌿 {note}</div>",
            unsafe_allow_html=True
        )
    if not restaurant_list:
        st.markdown(
            "<div style='font-size:0.85rem; color:#8A7F7A; font-style:italic;'>"
            "No restaurants found nearby right now.</div>",
            unsafe_allow_html=True
        )
        return
    for i, r in enumerate(restaurant_list):
        price_str = "💰" * r["price_level"] if r["price_level"] else "💰"
        open_badge = ""
        if r["open_now"] is True:
            open_badge = "<span class='badge badge-open'>Open Now</span>"
        elif r["open_now"] is False:
            open_badge = "<span class='badge badge-closed'>Closed</span>"
        rank_label = "🏆 Top Pick" if i == 0 else "Alternate"
        dish_line = ""
        if r.get("dish_name"):
            dish_line = (
                f"<div class='restaurant-address'>🍴 {md_safe(r['dish_name'].title())}</div>"
            )
        reasoning_line = ""
        if r.get("reasoning"):
            reasoning_line = (
                f"<div class='restaurant-address' style='font-style:italic;'>"
                f"🌿 {md_safe(r['reasoning'])}</div>"
            )
        confidence_line = ""
        if r.get("cuisine_confidence") == "low":
            confidence_line = (
                "<div class='restaurant-address' style='font-style:italic;'>"
                "🤔 Guessing the cuisine from the name, not fully sure of their menu</div>"
            )
        # Built as one single-line string (no embedded newlines/indentation) so
        # Streamlit's markdown pass can't mistake part of it for a code block.
        card_html = (
            f"<div class='restaurant-card'>"
            f"<div class='restaurant-meta'><span class='badge badge-open'>{rank_label}</span></div>"
            f"<div class='restaurant-name'>{md_safe(r['name'])}</div>"
            f"<div class='restaurant-meta'><span>⭐ {r['rating']}</span><span>{price_str}</span>{open_badge}</div>"
            f"<div class='restaurant-address'>📍 {md_safe(r['address'])}</div>"
            f"{dish_line}{reasoning_line}{confidence_line}"
            f"</div>"
        )
        st.markdown(card_html, unsafe_allow_html=True)


def setup_location(lat: float, lng: float):
    """Process coordinates and set up location context."""
    location = f"{lat},{lng}"
    with st.spinner("Detecting your city..."):
        city = get_city_from_coordinates(location)
    st.session_state.user_location = location
    st.session_state.user_city = city
    st.session_state.location_set = True
    st.session_state.detecting = False
    if st.session_state.session_token:
        db.save_session_location(st.session_state.session_token, location, city)
    ask_sage(
        f"[SYSTEM: User is in {city}. Think like a local food guide. "
        f"Only recommend cuisines actually available in {city}.]"
    )
    st.rerun()


def process_message(user_text: str, food_mode: str):
    """
    3-agent flow:
    1. Search Agent  — fetch real, open, nearby restaurants (no LLM)
    2. Filter Agent  — reason over mood/craving/phase/health, pick top 3 (LLM)
    3. Sage          — communicate the pick + real nutrition warmly (LLM)

    food_mode is "restaurant" or "home" — an explicit button choice from the
    UI now, not inferred from text (that used to be a whole extra LLM call,
    and inference could still guess wrong).
    """
    user_id = st.session_state.user_id
    if not st.session_state.messages:
        # First turn of a chat: name it from the mood + mode (no extra LLM call)
        mood_match = re.match(r"Feeling (.+?)\.", user_text)
        mood_label = mood_match.group(1) if mood_match else "New chat"
        st.session_state.chat_title = f"{mood_label}, {'at home' if food_mode == 'home' else 'restaurant'}"
    st.session_state.messages.append({
        "type": "user", "content": user_text
    })

    # Step 0 — cycle phase: calculated fresh from her stored cycle length +
    # last period date every turn, not parsed from "day N" in the message.
    phase = get_current_cycle_phase(user_id)

    # Step 1 — Search Agent (only when "Restaurant" was explicitly chosen —
    # otherwise skip straight to a home-cook suggestion, since guessing a
    # real restaurant's menu is inherently unreliable and shouldn't be the
    # default when she chose to cook)
    if food_mode == "restaurant":
        with st.spinner("Checking what's open near you..."):
            nearby = get_nearby_restaurants(
                st.session_state.user_location,
                keyword="restaurant",
                limit=15
            )
        # Step 2 — Filter Agent
        with st.spinner("Sage is weighing your options..."):
            shortlist = filter_agent(user_id, nearby, user_text, phase, ENRICH_WITH_REVIEWS)
        # Don't present a restaurant she can't actually trust the dish guess
        # for — if even the top pick is just a low-confidence cuisine guess,
        # drop it and fall back to the home-cook option instead of showing a
        # "guessing" restaurant recommendation.
        if shortlist.get("picks") and shortlist["picks"][0].get("cuisine_confidence") == "low":
            shortlist["picks"] = []
    else:
        nearby = []
        with st.spinner("Sage is thinking of something for you..."):
            shortlist = _home_only_recommendation(
                user_id, user_text, phase,
                "She chose to cook at home rather than eat out, so give a "
                "homemade suggestion."
            )

    picks = shortlist.get("picks", [])
    top = picks[0] if picks else {}
    home = shortlist.get("home_option") or {}
    # If there's no restaurant pick (nothing open nearby), fall back to
    # looking up nutrition for the home-cook suggestion instead.
    dish_name = top.get("dish_name") or home.get("dish_name", "")
    phase_used = shortlist.get("phase_used", phase)

    # Step 3 — Nutrition (silent, non-LLM). Sum nutrition across the dish's
    # individual ingredients (restaurant OR home-cook) — much more accurate
    # than matching a compound dish name like "beef noodle soup" or "cheese
    # omelette with toast" to a single database entry, which tends to match
    # a canned/instant packaged product rather than anything realistic —
    # falling back to a whole-dish lookup if the ingredient breakdown
    # doesn't turn up anything.
    ingredients = (top.get("key_ingredients") if top else None) or home.get("key_ingredients")
    if not dish_name:
        nutrition = {"found": False, "dish": ""}
    elif ingredients:
        nutrition = get_nutrition_for_ingredients(dish_name, ingredients)
        if not nutrition.get("found"):
            nutrition = get_nutrition(dish_name)
    else:
        nutrition = get_nutrition(dish_name)

    # Step 4 — Sage communicates the already-reasoned pick
    context_lines = [
        f"[USER MESSAGE]\n{user_text}",
        f"\n[CYCLE PHASE]\n{phase_used or 'unknown'}",
    ]
    if top:
        context_lines.append(
            f"\n[TOP PICK FROM FILTER AGENT]\n"
            f"Restaurant: {top.get('restaurant', '')}\n"
            f"Dish: {top.get('dish_name', '')}\n"
            f"Reasoning: {top.get('reasoning', '')}\n"
            f"Health tip: {top.get('health_tip', '')}\n"
            f"Indulgent: {top.get('indulgent', 'no')}\n"
            f"Cuisine confidence: {top.get('cuisine_confidence', 'low')}"
        )
    elif shortlist.get("home_option"):
        context_lines.append(
            "\n[TOP PICK FROM FILTER AGENT]\n"
            "No restaurants are open nearby right now. Lead confidently with "
            "the home-cook option below as the MAIN recommendation (not a "
            "side note) — don't apologize, just help her make something good "
            "at home."
        )
    else:
        context_lines.append(
            "\n[TOP PICK FROM FILTER AGENT]\n"
            "No confident pick was found — apologize briefly and suggest "
            "she try again in a moment."
        )
    if nutrition.get("found"):
        context_lines.append(
            f"\n[NUTRITION]\nFor '{nutrition.get('dish', dish_name)}' "
            f"(per {nutrition.get('serving_size', '100g')}): "
            f"Calories: {round(nutrition.get('calories', 0))} kcal, "
            f"Protein: {round(nutrition.get('protein', 0), 1)}g, "
            f"Carbs: {round(nutrition.get('carbs', 0), 1)}g, "
            f"Sugar: {round(nutrition.get('sugar', 0), 1)}g, "
            f"Fat: {round(nutrition.get('fat', 0), 1)}g, "
            f"Fiber: {round(nutrition.get('fiber', 0), 1)}g."
        )
    else:
        context_lines.append(
            "\n[NUTRITION]\nNo reliable nutrition numbers available for this "
            "dish (common for regional dishes not in US food databases). Do "
            "NOT invent numbers — reason qualitatively from the ingredients."
        )

    if home:
        if top:
            context_lines.append(
                f"\n[HOME-COOK OPTION — OPTIONAL ASIDE ONLY]\n"
                f"Dish: {home.get('dish_name', '')}\n"
                f"Reasoning: {home.get('reasoning', '')}\n"
                f"Health tip: {home.get('health_tip', '')}\n"
                f"Only mention this briefly if it fits naturally — the restaurant "
                f"pick above is still your primary recommendation."
            )
        else:
            context_lines.append(
                f"\n[HOME-COOK OPTION — THIS IS THE MAIN RECOMMENDATION]\n"
                f"Dish: {home.get('dish_name', '')}\n"
                f"Reasoning: {home.get('reasoning', '')}\n"
                f"Health tip: {home.get('health_tip', '')}"
            )

    context_lines.append(
        "\n[INSTRUCTION]\nWrite ONE warm conversational reply (4-5 lines max, "
        "no bullet points, no headers) using the pick and nutrition above. "
        "Include the health tip in your own voice. Do not invent a different "
        "restaurant or dish."
    )

    with st.spinner("Sage is thinking..."):
        reply = ask_sage("\n".join(context_lines))

    # Step 5 — Store for display (restaurant/dish/etc attached so we can record
    # feedback and build a shareable card for this specific pick later)
    st.session_state.messages.append({
        "type": "sage", "content": reply.strip(),
        # Falls back to the home-cook option's fields when there's no
        # restaurant pick, so feedback still works for that too. cuisine/
        # indulgent/vibe are carried along so feedback can build a structured
        # preference profile, not just a flat list of past dish names.
        "restaurant": top.get("restaurant") or ("Homemade" if home else ""),
        "dish_name": top.get("dish_name") or home.get("dish_name", ""),
        "cuisine": top.get("cuisine", ""),
        "indulgent": top.get("indulgent", "no"),
        "vibe": top.get("vibe") or home.get("vibe", ""),
        "phase": phase_used,
        "feedback": None,
        "auto_played": False,
    })

    if nutrition.get("found"):
        st.session_state.messages.append({
            "type": "nutrition", "content": nutrition
        })

    if top or home:
        st.session_state.messages.append({
            "type": "params",
            "content": {
                "avoid":       top.get("avoid") or home.get("avoid", ""),
                "vibe":        top.get("vibe") or home.get("vibe", ""),
                # Price level only applies to an actual restaurant purchase —
                # there isn't one to show for a home-cook suggestion.
                "price_level": top.get("price_level", ""),
                "phase":       phase_used,
            }
        })

    # Step 6 — Restaurant display: match the shortlist back to the real
    # nearby-restaurant data for rating/address/open-now — no second Places call.
    nearby_by_name = {r["name"]: r for r in nearby}
    matched = []
    for p in picks:
        base = nearby_by_name.get(p.get("restaurant", ""), {})
        matched.append({
            "name":        p.get("restaurant", base.get("name", "")),
            "rating":      base.get("rating", "N/A"),
            "address":     base.get("address", "No address"),
            "price_level": base.get("price_level", 0),
            "open_now":    base.get("open_now"),
            "dish_name":   p.get("dish_name", ""),
            "reasoning":   p.get("reasoning", ""),
            "cuisine_confidence": p.get("cuisine_confidence", "high"),
        })

    # Skip this card entirely when there are no restaurant matches but we do
    # have a home-cook suggestion — the chat reply + nutrition + share card
    # already cover that gracefully, so an empty "no restaurants" box here
    # would just look like a contradiction right under a confident answer.
    if matched or not home:
        st.session_state.messages.append({
            "type": "restaurants",
            "content": matched,
            "phase": (phase_used or "").lower(),
            "note": "" if matched else "No restaurants found nearby right now."
        })

    log_interaction(
        user_id,
        user_text=user_text,
        phase=phase_used,
        mode="restaurant" if top else ("home" if home else "none"),
        restaurant=top.get("restaurant", ""),
        dish_name=dish_name,
        cuisine_confidence=top.get("cuisine_confidence", ""),
        nutrition_found=nutrition.get("found", False),
        nutrition_source=nutrition.get("source", ""),
    )


# =============================================================================
# UI
# =============================================================================

def do_logout() -> None:
    db.delete_session(st.session_state.session_token)
    if "s" in st.query_params:
        del st.query_params["s"]
    # Clear everything tied to the previous user, not just the login. Their
    # saved chats stay in the database; only the in-memory copy is dropped so
    # it can't show up for whoever logs in next in this tab.
    st.session_state.user_id = None
    st.session_state.session_token = None
    st.session_state.onboarding_step = "login"
    st.session_state.location_set = False
    st.session_state.user_location = ""
    st.session_state.user_city = ""
    _blank_chat()
    st.rerun()


# Pinned to the bottom-left of the sidebar (see .st-key-logout_container in
# the CSS), including mid-onboarding so nobody gets stuck in a half-finished
# account.
if st.session_state.user_id is not None:
    with st.sidebar:
        with st.container(key="logout_container"):
            if st.button("Log Out", key="logout_btn"):
                do_logout()

if st.session_state.user_id is None or st.session_state.onboarding_step != "done":
    # Logged out, or still in the setup wizard. Registering a hidden
    # navigation (instead of skipping st.navigation altogether) is what
    # removes the Chat/Profile/Pantry menu after logging out: the browser
    # keeps the last nav it was sent until it's told otherwise, so just
    # stopping the script left the old menu sitting next to the login form.
    if st.session_state.user_id is None:
        # Logged out: nothing belongs in the sidebar, so hide the whole panel
        # (an already-open one would otherwise stay behind as an empty white
        # column). Mid-setup users keep it, since Log Out lives there.
        st.markdown(
            "<style>[data-testid='stSidebar'], [data-testid='stExpandSidebarButton'],"
            " [data-testid='stSidebarCollapseButton'] { display: none !important; }</style>",
            unsafe_allow_html=True,
        )
    st.navigation([st.Page(render_onboarding, title="Sign in", default=True)], position="hidden").run()
    st.stop()

st.markdown("""
<div class="sage-header">
    <div class="sage-title">Ask <span>Sage</span></div>
    <div class="sage-subtitle">Your Personal Wellness Food Companion</div>
    <div style="font-size:0.72rem; color:#B0A8A4; max-width:480px; margin:0.5rem auto 0 auto; line-height:1.5;">
        Sage offers general wellness information and is not a substitute for professional
        medical advice. Please consult your healthcare provider for guidance specific to you.
    </div>
</div>
<hr class="sage-divider">
""", unsafe_allow_html=True)

def page_chat() -> None:
    # -----------------------------------------------------------------------------
    # LOCATION SETUP
    # -----------------------------------------------------------------------------
    if not st.session_state.location_set:

        st.markdown("""
        <div style="text-align:center; padding:1rem 0 1.5rem 0;">
            <div style="font-family:'DM Serif Display',serif; font-size:1.4rem;
                 color:#3D2B37; margin-bottom:0.5rem;">
                Where Are You Right Now?
            </div>
            <div style="font-size:0.88rem; color:#8A7F7A; max-width:420px;
                 margin:0 auto; line-height:1.6;">
                Sage needs your location to find restaurants near you.
            </div>
        </div>
        """, unsafe_allow_html=True)

        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            # Clean Streamlit button — fully green, no black box
            # When clicked, triggers get_geolocation() which calls browser GPS
            detect_clicked = st.button("📍 Detect My Location", key="detect_btn")

        if detect_clicked:
            st.session_state.detecting = True

        # get_geolocation runs in background when detecting is True
        # It triggers the browser permission popup automatically
        if st.session_state.detecting:
            with st.spinner("Waiting for location permission..."):
                loc = get_geolocation()

            if loc and loc.get("coords"):
                lat = loc["coords"]["latitude"]
                lng = loc["coords"]["longitude"]
                setup_location(lat, lng)

        st.markdown("""
        <div style="text-align:center; font-size:0.8rem; color:#B0A8A4;
             margin:1.5rem 0 0.5rem 0;">
            Or enter coordinates manually
            (maps.google.com → right-click your location → copy coordinates)
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns([3, 1])
        with col1:
            coords_input = st.text_input(
                "coords",
                placeholder="Paste coordinates: 23.8103, 90.4125",
                label_visibility="collapsed"
            )
        with col2:
            locate_btn = st.button("Let's Go")

        if locate_btn and coords_input.strip():
            location = coords_input.strip()
            if "," not in location:
                location = "23.8103,90.4125"
            with st.spinner("Detecting your city..."):
                city = get_city_from_coordinates(location)
            st.session_state.user_location = location
            st.session_state.user_city = city
            st.session_state.location_set = True
            if st.session_state.session_token:
                db.save_session_location(st.session_state.session_token, location, city)
            ask_sage(
                f"[SYSTEM: User is in {city}. Think like a local food guide. "
                f"Only recommend cuisines actually available in {city}.]"
            )
            st.rerun()

    # -----------------------------------------------------------------------------
    # MAIN CHAT
    # -----------------------------------------------------------------------------
    else:

        st.markdown(
            "<div class='sage-avatar-wrap'><div class='sage-avatar'>🌿</div></div>",
            unsafe_allow_html=True
        )

        st.markdown(
            f"<div style='text-align:center; margin-bottom:1.2rem;'>"
            f"<span class='location-badge'>📍 {st.session_state.user_city}</span>"
            f"</div>",
            unsafe_allow_html=True
        )

        for i, msg in enumerate(st.session_state.messages):

            if msg["type"] == "user":
                st.markdown(
                    f"<div class='sage-message user-message'>{md_safe(msg['content'])}</div>",
                    unsafe_allow_html=True
                )

            elif msg["type"] == "sage":
                st.markdown(
                    f"<div class='sage-message'>🌿 {md_safe(msg['content'])}</div>",
                    unsafe_allow_html=True
                )
                if msg.get("dish_name"):
                    if msg.get("feedback") is None:
                        fb_col1, fb_col2, fb_col3 = st.columns([1, 1, 5])
                        with fb_col1:
                            if st.button("👍", key=f"fb_up_{i}"):
                                save_feedback(
                                    st.session_state.user_id,
                                    msg["restaurant"], msg["dish_name"], True,
                                    cuisine=msg.get("cuisine", ""),
                                    indulgent=msg.get("indulgent", ""),
                                    vibe=msg.get("vibe", ""),
                                    phase=msg.get("phase", ""),
                                )
                                msg["feedback"] = "liked"
                                st.rerun()
                        with fb_col2:
                            if st.button("👎", key=f"fb_down_{i}"):
                                save_feedback(
                                    st.session_state.user_id,
                                    msg["restaurant"], msg["dish_name"], False,
                                    cuisine=msg.get("cuisine", ""),
                                    indulgent=msg.get("indulgent", ""),
                                    vibe=msg.get("vibe", ""),
                                    phase=msg.get("phase", ""),
                                )
                                msg["feedback"] = "disliked"
                                st.rerun()
                    else:
                        note = ("Glad you liked it! 🌿" if msg["feedback"] == "liked"
                                else "Noted — I'll try something different next time.")
                        st.markdown(
                            f"<div style='font-size:0.78rem; color:#8A7F7A; "
                            f"font-style:italic; margin:-0.4rem 0 0.6rem 0;'>{note}</div>",
                            unsafe_allow_html=True
                        )

            elif msg["type"] == "nutrition":
                n = msg["content"]
                if n.get("found"):
                    items = []
                    if n.get("calories"):
                        items.append(("🔥 Calories", f"{round(n['calories'])} kcal"))
                    if n.get("protein"):
                        items.append(("💪 Protein", f"{round(n['protein'], 1)}g"))
                    if n.get("carbs"):
                        items.append(("🌾 Carbs", f"{round(n['carbs'], 1)}g"))
                    if n.get("sugar"):
                        items.append(("🍬 Sugar", f"{round(n['sugar'], 1)}g"))
                    if n.get("fat"):
                        items.append(("🥑 Fat", f"{round(n['fat'], 1)}g"))
                    if n.get("fiber"):
                        items.append(("🌿 Fiber", f"{round(n['fiber'], 1)}g"))
                    if n.get("iron"):
                        items.append(("🩸 Iron", f"{round(n['iron'], 1)}mg"))
                    if n.get("magnesium"):
                        items.append(("⚡ Magnesium", f"{round(n['magnesium'], 1)}mg"))
                    if n.get("calcium"):
                        items.append(("🦴 Calcium", f"{round(n['calcium'], 1)}mg"))
                    if n.get("sodium"):
                        items.append(("🧂 Sodium", f"{round(n['sodium'], 1)}mg"))

                    grid_html = "".join([
                        f"<div class='nutrition-item'>"
                        f"<span class='nutrition-label'>{label}</span>"
                        f"<span class='nutrition-value'>{value}</span>"
                        f"</div>"
                        for label, value in items
                    ])
                    nutrition_html = (
                        f"<div class='nutrition-card'>"
                        f"<div class='nutrition-title'>📊 {md_safe(n.get('dish','').title())}</div>"
                        f"<div class='nutrition-subtitle'>per {md_safe(n.get('serving_size','100g'))} · {md_safe(n.get('source',''))}</div>"
                        f"<div class='nutrition-grid'>{grid_html}</div>"
                        f"</div>"
                    )
                    st.markdown(nutrition_html, unsafe_allow_html=True)

            elif msg["type"] == "params":
                p = msg["content"]
                items_html = ""
                if p.get("phase"):
                    emoji = {"menstrual": "🩸", "follicular": "🌱",
                             "ovulatory": "✨", "luteal": "🌙"}.get(
                        p["phase"].lower(), "🌿")
                    items_html += (
                        f"<div class='param-item'><span class='param-label'>Phase</span>"
                        f"<span class='param-value'>{emoji} {md_safe(cap_first(p['phase']))}</span></div>"
                    )
                if p.get("vibe"):
                    items_html += (
                        f"<div class='param-item'><span class='param-label'>Vibe</span>"
                        f"<span class='param-value'>{md_safe(cap_first(p['vibe']))}</span></div>"
                    )
                if p.get("price_level"):
                    try:
                        price_str = "💰" * int(p["price_level"])
                    except:
                        price_str = md_safe(p["price_level"])
                    items_html += (
                        f"<div class='param-item'><span class='param-label'>Budget</span>"
                        f"<span class='param-value'>{price_str}</span></div>"
                    )
                if p.get("avoid"):
                    items_html += (
                        f"<div class='param-item'><span class='param-label'>Avoid</span>"
                        f"<span class='param-value'>{md_safe(cap_first(p['avoid']))}</span></div>"
                    )
                if items_html:
                    st.markdown(
                        f"<div class='params-card'>{items_html}</div>",
                        unsafe_allow_html=True
                    )

            elif msg["type"] == "restaurants":
                render_restaurants(
                    msg["content"],
                    msg.get("phase", ""),
                    msg.get("note", "")
                )

        # ── Input: mood button -> craving confirm/override -> Restaurant/At Home
        # buttons -> process_message. Buttons/dropdowns wherever possible instead
        # of a single free-text box, per the redesign.
        st.markdown("<hr class='sage-divider'>", unsafe_allow_html=True)

        if not st.session_state.pending_mood:
            st.markdown("<div class='section-header'>How are you feeling?</div>", unsafe_allow_html=True)
            mood_cols = st.columns(2)
            for i, mood in enumerate(MOOD_LIST):
                with mood_cols[i % 2]:
                    if st.button(mood, key=f"mood_{mood}", use_container_width=True):
                        st.session_state.pending_mood = mood
                        st.rerun()
        else:
            mood = st.session_state.pending_mood
            saved_craving = db.get_craving_map(st.session_state.user_id).get(mood, "")
            st.markdown(f"<div class='section-header'>Feeling {md_safe(mood)}</div>", unsafe_allow_html=True)

            if "resolved_craving" not in st.session_state:
                if saved_craving:
                    st.markdown(
                        f"I have **{md_safe(saved_craving)}** saved for when you're {mood.lower()}. "
                        f"Want me to go with that, or something else this time?"
                    )
                    if st.button("Yes, use that", key="craving_yes"):
                        st.session_state.resolved_craving = saved_craving
                        st.rerun()
                other_craving = st.text_input(
                    "Something else you're craving right now? (optional)", key="craving_other"
                )
                update_saved = False
                if other_craving.strip():
                    update_saved = st.checkbox(
                        f"Save this as my new go-to craving for feeling {mood.lower()}",
                        key="craving_update_saved",
                    )
                if st.button("Continue", key="craving_continue"):
                    st.session_state.resolved_craving = other_craving.strip()
                    if other_craving.strip() and update_saved:
                        db.save_craving_map(st.session_state.user_id, {mood: other_craving.strip()})
                    st.rerun()
            else:
                craving = st.session_state.resolved_craving
                summary = f"Feeling {mood}" + (f", craving {craving}" if craving else "") + "."
                st.markdown(f"Got it. {md_safe(summary)}")
                st.markdown("<div class='section-header'>Restaurant, or cook at home?</div>", unsafe_allow_html=True)
                c1, c2 = st.columns(2)
                with c1:
                    restaurant_clicked = st.button("🍽️ Restaurant", key="mode_restaurant", use_container_width=True)
                with c2:
                    home_clicked = st.button("🏠 At Home", key="mode_home", use_container_width=True)

                if restaurant_clicked or home_clicked:
                    food_mode = "restaurant" if restaurant_clicked else "home"
                    user_text = f"Feeling {mood}." + (f" Craving: {craving}." if craving else "")
                    process_message(user_text, food_mode)
                    st.session_state.pending_mood = ""
                    del st.session_state.resolved_craving
                    st.rerun()

                if st.button("Start over", key="mood_reset"):
                    st.session_state.pending_mood = ""
                    del st.session_state.resolved_craving
                    st.rerun()

# -----------------------------------------------------------------------------
# PAGE NAVIGATION — Profile and Pantry are always reachable regardless of
# whether the Chat page's own location-setup step has been completed yet,
# since they're now independent pages rather than sidebar widgets nested
# inside the chat flow.
# -----------------------------------------------------------------------------
def _current_chat_json() -> str:
    """The saveable state of the open chat. Transient UI flags (voice audio,
    auto_played) and the system prompt are left out, so re-opening a chat
    produces the identical JSON and doesn't count as a change."""
    state = {
        "messages": [
            {k: v for k, v in m.items() if k not in ("audio_bytes", "auto_played")}
            for m in st.session_state.messages
        ],
        "conversation_history": [
            m for m in st.session_state.conversation_history if m.get("role") != "system"
        ],
        "pending_mood": st.session_state.pending_mood,
        "resolved_craving": st.session_state.get("resolved_craving"),
    }
    return json.dumps(state, default=str)


def persist_chat_state() -> None:
    """Saves the open chat. Called from a finally around pg.run() so it also
    runs when a page ends via st.rerun() (how every button handler finishes).
    A chat is written to the chats table once it has a message; before that,
    mood/craving progress is kept as a draft on the session so a reload
    mid-flow isn't lost."""
    token = st.session_state.get("session_token")
    user_id = st.session_state.get("user_id")
    if not token or user_id is None:
        return
    blob = _current_chat_json()
    if blob == st.session_state._last_chat_json:
        return
    if st.session_state.chat_id is None:
        if st.session_state.messages:
            chat_id = db.create_chat(user_id, st.session_state.chat_title or "New chat", blob)
            st.session_state.chat_id = chat_id
            db.set_session_chat_id(token, chat_id)
            db.save_session_chat_state(token, None)
        else:
            db.save_session_chat_state(token, blob)
    else:
        db.update_chat(user_id, st.session_state.chat_id, blob)
    st.session_state._last_chat_json = blob


def _start_new_chat() -> None:
    token = st.session_state.session_token
    db.set_session_chat_id(token, None)
    db.save_session_chat_state(token, None)
    _blank_chat()


def _open_chat(chat_id: int) -> None:
    chat = db.get_chat(st.session_state.user_id, chat_id)
    if not chat:
        return
    token = st.session_state.session_token
    _blank_chat()
    st.session_state.chat_id = chat["id"]
    _apply_chat_state(chat["state"])
    db.set_session_chat_id(token, chat["id"])
    db.save_session_chat_state(token, None)
    st.session_state._last_chat_json = _current_chat_json()


def render_chat_sidebar(chat_page) -> None:
    """ChatGPT-style list of saved chats: New chat button, click one to reopen
    it, trash icon to delete it."""
    user_id = st.session_state.user_id
    st.markdown(
        "<div style='font-size:0.75rem; font-weight:600; letter-spacing:0.06em; "
        "color:#8A7F7A; margin:1rem 0 0.4rem 0;'>YOUR CHATS</div>",
        unsafe_allow_html=True,
    )
    if st.button("New chat", key="new_chat_btn", use_container_width=True):
        _start_new_chat()
        st.switch_page(chat_page)
    for chat in db.list_chats(user_id):
        is_open = chat["id"] == st.session_state.chat_id
        open_col, del_col = st.columns([5, 1])
        with open_col:
            label = ("🌿 " if is_open else "") + chat["title"]
            if st.button(label, key=f"chat_open_{chat['id']}", help=chat["updated_at"].replace("T", " "),
                         use_container_width=True):
                _open_chat(chat["id"])
                st.switch_page(chat_page)
        with del_col:
            if st.button("🗑", key=f"chat_del_{chat['id']}", help="Delete this chat"):
                db.delete_chat(user_id, chat["id"])
                if is_open:
                    _start_new_chat()
                st.rerun()


chat_page = st.Page(page_chat, title="Chat", icon="💬", default=True)
pg = st.navigation([
    chat_page,
    st.Page(page_profile, title="Profile", icon="👤"),
    st.Page(page_pantry, title="Pantry", icon="🥫"),
])
# After st.navigation() (switch_page needs the pages registered); the nav
# itself always renders at the top of the sidebar regardless of call order.
with st.sidebar:
    render_chat_sidebar(chat_page)
try:
    pg.run()
finally:
    persist_chat_state()
