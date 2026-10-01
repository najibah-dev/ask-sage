"""
Tiny eval harness — no pytest dependency, just enough structure to register
cases, run them, and print a report. Two kinds of cases:

- `@case(...)`      a plain pass/fail check (deterministic logic, no LLM).
- `@llm_case(...)`  runs N trials against the real Groq API and reports a
                     pass rate, since LLM output is non-deterministic and a
                     single failed trial isn't necessarily a real regression.

Import `app` once here (silencing Streamlit's bare-mode warnings) so every
eval module shares the same loaded module instead of re-importing it.
"""
import logging
import queue
import sys
import threading
import time
import traceback
from pathlib import Path

TRIAL_TIMEOUT_SECONDS = 60
LLM_CALL_PACING_SECONDS = 3


class TrialTimeout(Exception):
    pass


def _run_with_timeout(fn, timeout_seconds):
    """Runs fn() in a fresh daemon thread and waits up to timeout_seconds.
    Needed because some observed Groq call stalls outlast the SDK's own
    configured request timeout and never raise, and app.py's
    _call_filter_llm also catches bare Exception internally and retries —
    which would swallow a signal-based (in-process) timeout raised inside
    it. Running the trial in its own thread lets the harness simply stop
    *waiting* on a hung trial instead of needing to interrupt it. Python has
    no safe way to kill a thread from outside; an abandoned thread is
    daemonized so it dies when the whole process exits, and — critically —
    each trial gets its OWN thread (never reused), so one permanently-hung
    trial can never block a later trial from running."""
    result_q = queue.Queue(maxsize=1)

    def target():
        try:
            fn()
            result_q.put(("ok", None))
        except Exception as e:
            result_q.put(("error", e))

    t = threading.Thread(target=target, daemon=True)
    t.start()
    t.join(timeout=timeout_seconds)
    if t.is_alive():
        raise TrialTimeout(f"trial exceeded {timeout_seconds}s wall-clock limit (thread abandoned)")
    status, err = result_q.get()
    if status == "error":
        raise err


ASK_SAGE_DIR = Path(__file__).resolve().parent.parent
if str(ASK_SAGE_DIR) not in sys.path:
    sys.path.insert(0, str(ASK_SAGE_DIR))

logging.getLogger("streamlit.runtime.scriptrunner_utils.script_run_context").setLevel(logging.ERROR)
logging.getLogger("streamlit.runtime.state.session_state_proxy").setLevel(logging.ERROR)

import app  # noqa: E402  (must come after sys.path setup)
import db  # noqa: E402  (same module app.py imports; reused so DB_PATH patches affect both)

# app.py's _call_filter_llm deliberately swallows every exception from the
# Groq call (falls back to a JSON-mode-then-plain retry, then gives up
# silently) — reasonable for the live app, which always needs *some* answer,
# but it means eval failures show only the downstream symptom (a fallback
# dish) with no way to see why the real call failed. This wrapper logs the
# exception to stderr before letting app.py's own handling proceed exactly
# as it would in production.
_real_create = app.client.chat.completions.create


def _logged_create(**kwargs):
    try:
        return _real_create(**kwargs)
    except Exception as e:
        print(f"    [groq call failed: {type(e).__name__}: {e}]", file=sys.stderr, flush=True)
        raise


app.client.chat.completions.create = _logged_create

_DETERMINISTIC_CASES = []
_LLM_CASES = []


def case(name: str):
    """Registers a zero-arg function as a deterministic eval case. The
    function should raise (typically via `assert`) on failure and return
    normally on success."""
    def decorator(fn):
        _DETERMINISTIC_CASES.append((name, fn))
        return fn
    return decorator


def llm_case(name: str, trials: int = 3, pass_threshold: float = 0.66):
    """Registers a zero-arg function as an LLM-backed eval case, run
    `trials` times. `fn` should raise on a failed trial. The case as a whole
    passes if the observed pass rate meets `pass_threshold` — LLM sampling
    noise means demanding 100% of trials would make the suite flaky for
    reasons unrelated to real regressions. Defaults kept low (3 trials, 2/3
    threshold) because each trial's prompt cost is dominated by the full
    production system prompt (~3000+ tokens) regardless of trial count —
    more trials mainly buys quota exhaustion, not much extra confidence
    beyond what the deterministic, free-to-run enforcement-function tests
    already cover exhaustively."""
    def decorator(fn):
        _LLM_CASES.append((name, fn, trials, pass_threshold))
        return fn
    return decorator


def _run_deterministic():
    results = []
    for name, fn in _DETERMINISTIC_CASES:
        try:
            fn()
            results.append((name, True, ""))
        except Exception as e:
            results.append((name, False, f"{type(e).__name__}: {e}\n{traceback.format_exc(limit=3)}"))
    return results


def _run_llm(only_filter=None):
    results = []
    cases = _LLM_CASES
    if only_filter:
        cases = [c for c in _LLM_CASES if only_filter.lower() in c[0].lower()]
    for name, fn, trials, threshold in cases:
        print(f"  running: {name} ({trials} trials)...", flush=True)
        failures = []
        for i in range(trials):
            print(f"    trial {i + 1}/{trials}...", end=" ", flush=True)
            # Firing ~36 Groq calls back-to-back with zero gap trips a
            # requests-per-minute limit that doesn't raise a visible
            # exception (the SDK silently retries internally, so calls just
            # get progressively slower — up to 30s+ per call — instead of
            # erroring). A fixed pacing delay between trials keeps the whole
            # suite comfortably under that limit instead of degrading.
            time.sleep(LLM_CALL_PACING_SECONDS)
            try:
                _run_with_timeout(fn, TRIAL_TIMEOUT_SECONDS)
                print("ok", flush=True)
            except Exception as e:
                print(f"FAILED ({type(e).__name__})", flush=True)
                failures.append(f"  trial {i + 1}: {type(e).__name__}: {e}")
        pass_rate = (trials - len(failures)) / trials
        ok = pass_rate >= threshold
        detail = f"{trials - len(failures)}/{trials} passed ({pass_rate:.0%}, threshold {threshold:.0%})"
        if failures:
            detail += "\n" + "\n".join(failures[:3])
            if len(failures) > 3:
                detail += f"\n  ... and {len(failures) - 3} more"
        results.append((name, ok, detail))
    return results


def run_all(skip_llm: bool = False, only_filter: str = None):
    det_results = []
    if not only_filter:
        print("=" * 70)
        print("DETERMINISTIC EVALS (architecture / safety-net logic, no network)")
        print("=" * 70)
        det_results = _run_deterministic()
        for name, ok, detail in det_results:
            status = "PASS" if ok else "FAIL"
            print(f"[{status}] {name}")
            if not ok:
                print(detail)

    llm_results = []
    if skip_llm:
        print("\n(skipping LLM-backed evals — --skip-llm)")
    else:
        print()
        print("=" * 70)
        header = "LLM-BACKED EVALS (hallucination / grounding checks, hits Groq API)"
        if only_filter:
            header += f" — filtered to cases matching {only_filter!r}"
        print(header)
        print("=" * 70)
        llm_results = _run_llm(only_filter=only_filter)
        for name, ok, detail in llm_results:
            status = "PASS" if ok else "FAIL"
            print(f"[{status}] {name} — {detail}")

    all_results = det_results + llm_results
    total = len(all_results)
    passed = sum(1 for _, ok, _ in all_results if ok)
    print()
    print("=" * 70)
    print(f"RESULT: {passed}/{total} eval cases passed")
    print("=" * 70)
    return passed == total
