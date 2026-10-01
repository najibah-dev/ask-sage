"""
Eval suite entry point for Sage.

    ./.venv/bin/python ask-sage/evals/run_evals.py               # full suite
    ./.venv/bin/python ask-sage/evals/run_evals.py --skip-llm     # deterministic only, no API calls

Two layers:
- deterministic_evals.py — pure logic checks on the code-level safety nets
  (cycle-phase math, allergy keyword matching, cuisine-confidence honesty,
  restaurant grounding, non-food filtering). No network, no API cost, safe
  to run constantly.
- llm_evals.py — runs the real Filter Agent / Sage pipeline against the
  live Groq API with a synthetic restaurant list and a throwaway eval user,
  to check the safety nets are actually wired into the real pipeline (not
  just correct in isolation). Each case runs 3 trials at a 2/3 pass
  threshold, since LLM sampling is non-deterministic. 7 cases x 3 trials =
  21 real Groq calls total (down from 36) — each call's prompt is still the
  full production FILTER_SYSTEM_PROMPT (~3000+ tokens), so a full run costs
  roughly 60-80k tokens; watch Groq's daily quota if re-running often. Use
  `--only <substring>` to cheaply re-check a single case instead of the
  whole suite.

Exits non-zero if any case fails, so this can be wired into a pre-commit
check or CI later if useful.
"""
import argparse
import sys

import deterministic_evals  # noqa: F401  (registers its cases on import)
from harness import run_all


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-llm", action="store_true",
        help="Only run deterministic evals — no Groq API calls, no network required.",
    )
    parser.add_argument(
        "--only", default=None,
        help="Only run LLM-backed cases whose name contains this substring "
             "(skips deterministic evals too) — for cheaply re-checking a "
             "single case without burning quota re-running everything that "
             "already passed.",
    )
    args = parser.parse_args()

    if not args.skip_llm:
        import llm_evals  # noqa: F401  (registers its cases on import)

    ok = run_all(skip_llm=args.skip_llm, only_filter=args.only)
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
