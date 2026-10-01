# Ask Sage 🌿

**A wellness food companion that recommends what to eat based on your mood, menstrual cycle phase, and health profile, grounded in real nearby restaurants, real nutrition data, and what's actually in your pantry.**

https://github.com/user-attachments/assets/426864fd-fa9a-49cd-a80f-bdbb5a2a6580

🚀 [Try it live](https://ask-sage.streamlit.app/)

---

## The problem

"What do you want to eat?" turns into twenty minutes of scrolling delivery apps for a lot of people, especially with a health condition where the wrong choice matters. Sage exists to end that spiral: one clear, trustworthy recommendation instead of an endless menu.

## What makes it different

Sage's design principle: **anything safety-critical is verified in code, alongside the prompt.**

- **Real restaurants only.** Every pick is checked against live Google Places results before it reaches you.
- **Allergy-aware.** Each dish's ingredients are checked against your allergy list with a keyword map that catches specific ingredients (e.g. a shellfish allergy also catches "shrimp," not just the literal word "shellfish").
- **Honest confidence.** The model's self-rated certainty about a restaurant's cuisine is independently verified rather than taken at face value.
- **Real nutrition data.** Numbers come from USDA / API Ninjas lookups on the dish's actual ingredients.
- **Cycle-phase math from real sources**, not an assumed 28-day cycle. See the citations in `app.py`'s `calculate_cycle_phase`.

## Architecture

Three agents per turn, each with one job:

```
1. Search Agent    Real, currently-open nearby restaurants (Google Places API, no LLM)
2. Filter Agent    Scores them against mood + cycle phase + health profile + pantry (LLM, JSON output)
3. Sage            Writes the warm, final reply using the real pick + real nutrition (LLM)
```

Between steps 2 and 3, the Filter Agent's output passes through code-level safety nets (`_enforce_restaurant_grounding`, `_enforce_allergy_safety`, `_enforce_cuisine_confidence` in `app.py`) before anything reaches the user.

## Getting started

```bash
git clone https://github.com/<your-username>/ask-sage.git
cd ask-sage
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env
# fill in your own API keys in .env (see .env.example for where to get each one)

streamlit run app.py
```

### Deploying your own instance

This repo is set up so a public deployment never costs the deployer anything or risks their API quota: if no `.env` is present, the app automatically switches to a "bring your own key" screen, and each visitor enters their own free-tier API keys, used only for their session and never stored. Your own local `.env` is unaffected and skips this entirely.

The simplest free option is [Streamlit Community Cloud](https://streamlit.io/cloud): connect this repo, deploy `app.py`, and leave its secrets empty. Visitors will be prompted for their own keys automatically.

## Testing

```bash
cd evals
python run_evals.py               # full suite
python run_evals.py --skip-llm    # deterministic checks only, no API calls, no cost, runs in under a second
```

The suite has two layers:
- **Deterministic evals**: pure logic tests on the safety-net functions themselves (allergy keyword matching, restaurant grounding, cuisine-confidence honesty, cycle-phase math). No network calls, free to run on every change.
- **LLM-backed evals**: run the real pipeline against the live Groq API with a synthetic restaurant list, checking the safety nets actually hold up under real model output, not just in isolation. Each case runs a few trials and reports a pass rate, since LLM output isn't perfectly deterministic.

## Project structure

```
app.py              Streamlit app: UI, the 3-agent pipeline, all prompts
db.py                SQLite data layer: accounts, profiles, pantry, chats, sessions
evals/                Automated test suite (see Testing above)
.streamlit/config.toml   Theme
```

## License

MIT. See [LICENSE](LICENSE).
