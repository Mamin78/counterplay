#!/usr/bin/env python3
"""
Evaluate non-math game CFs via Google Cloud Vertex AI (Model Garden).

Supports all models available through Vertex AI:
  • Gemini SDK       — gemini-2.5-flash, gemini-2.5-pro, …
  • Vertex MaaS      — Grok, DeepSeek, Llama, Gemma, GPT-OSS, Qwen, GLM, Kimi, …

Games covered:
  Hanoi (baseline, cf1_four_pegs, cf2_adjacent)
  Checker Jumping (baseline, cf1_asymmetric, cf2_jump_two, cf3_two_empty)
  River Crossing (baseline, cf1_neutral)

Open-ended evaluation: model produces a full solution path.

Each problem is run --runs times (default 5).

Prerequisites:
  pip install openai google-auth google-cloud-aiplatform pandas tqdm
  gcloud auth application-default login        # once per machine
  export GOOGLE_CLOUD_PROJECT=<your-gcp-project-id>

Usage examples:
  # All datasets, Gemini 2.5 Flash, 5 runs:
  python non_math_games_eval/run_vertex.py \\
      --model gemini-2.5-flash --all --runs 5 \\
      --out results/non_math_games/

  # One dataset, multiple models:
  python non_math_games_eval/run_vertex.py \\
      --model deepseek-r1 grok llama-4-maverick \\
      --data non_math_games/hanoi/baseline/data/hanoi_baseline.csv \\
      --runs 5 --location global \\
      --out results/hanoi_multi.csv

  # Smoke test — 3 rows × 2 runs:
  python non_math_games_eval/run_vertex.py \\
      --model gemini-2.5-flash --all --runs 2 --sample 3 \\
      --out results/smoke/

  # Resume an interrupted run:
      --resume
"""
from __future__ import annotations

import argparse
import os
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pandas as pd
from tqdm import tqdm

# ── Path setup ────────────────────────────────────────────────────────────────
_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _ROOT)

from non_math_games_eval import graders, parsers
from non_math_games_eval.prompts import build_prompt

# ── Constants ─────────────────────────────────────────────────────────────────

DEFAULT_PROJECT  = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
CHECKPOINT_EVERY = 20  # save after every N completed requests
_SCOPES = ("https://www.googleapis.com/auth/cloud-platform",)
_creds_lock = threading.Lock()

SYSTEM_PROMPT = (
    "You are an expert puzzle solver. Read the rules and the initial state carefully. "
    "Reason through the problem step by step, then output your answer in the EXACT "
    "format specified in the problem — no deviations, no extra text on solution lines."
)

# All known data CSVs (relative to _ROOT/non_math_games/)
_NMG = os.path.join(_ROOT, "non_math_games")
ALL_DATA_CSVS: dict[str, str] = {
    "hanoi_baseline":          f"{_NMG}/hanoi/baseline/data/hanoi_baseline.csv",
    "hanoi_cf1_four_pegs":     f"{_NMG}/hanoi/cf1_four_pegs/data/hanoi_cf1_four_pegs.csv",
    "hanoi_cf2_adjacent":      f"{_NMG}/hanoi/cf2_adjacent/data/hanoi_cf2_adjacent.csv",
    "checker_baseline":        f"{_NMG}/checker_jumping/baseline/data/checker_baseline.csv",
    "checker_cf1_asymmetric":  f"{_NMG}/checker_jumping/cf1_asymmetric/data/checker_cf1_asymmetric.csv",
    "checker_cf2_jump_two":    f"{_NMG}/checker_jumping/cf2_jump_two/data/checker_cf2_jump_two.csv",
    "checker_cf3_two_empty":   f"{_NMG}/checker_jumping/cf3_two_empty/data/checker_cf3_two_empty.csv",
    "river_baseline":          f"{_NMG}/river_crossing/baseline/data/river_baseline.csv",
    "river_cf1_neutral":       f"{_NMG}/river_crossing/cf1_neutral/data/river_cf1_neutral.csv",
}

# ── Model aliases (mirrors llm_eval/evaluate_games_vertex.py) ─────────────────

MODEL_ALIASES: dict[str, str] = {
    # Grok
    "grok":               "xai/grok-4.1-fast-non-reasoning",
    "grok-4.1":           "xai/grok-4.1-fast-non-reasoning",
    "grok-3":             "xai/grok-3",
    # DeepSeek (MaaS — only r1-0528-maas is currently live in us-central1;
    #  v3.x requires manual enablement in Vertex AI Model Garden console)
    "deepseek-r1":        "deepseek-ai/deepseek-r1-0528-maas",
    "deepseek":           "deepseek-ai/deepseek-r1-0528-maas",
    "deepseek-v3":        "deepseek-ai/deepseek-v3.2-maas",   # enable in Model Garden first
    "deepseek-v3.1":      "deepseek-ai/deepseek-v3.1-maas",   # enable in Model Garden first
    "deepseek-v3.2":      "deepseek-ai/deepseek-v3.2-maas",   # enable in Model Garden first
    # GPT-OSS
    "gpt-oss-20b":        "openai/gpt-oss-20b-maas",
    "gpt-oss-120b":       "openai/gpt-oss-120b-maas",
    # Meta Llama
    "llama-3.3-70b":      "meta/llama-3.3-70b-instruct-maas",
    "llama-4-scout":      "meta/llama-4-scout-17b-16e-instruct-maas",
    "llama-4-maverick":   "meta/llama-4-maverick-17b-128e-instruct-maas",
    # Gemma
    "gemma-4":            "google/gemma-4-26b-a4b-it-maas",
    "gemma-4-27b":        "google/gemma-4-26b-a4b-it-maas",
    # Qwen3
    "qwen3-235b":         "qwen/qwen3-235b-a22b-instruct-2507-maas",
    "qwen3-coder":        "qwen/qwen3-coder-480b-a35b-instruct-maas",
    # GLM
    "glm-4.7":            "zai-org/glm-4.7-maas",
    "glm-5":              "zai-org/glm-5-maas",
    # Kimi
    "kimi-k2":            "moonshotai/kimi-k2-thinking-maas",
    # MiniMax
    "minimax-m2":         "minimaxai/minimax-m2-maas",
}

# Models that require global endpoint (publisher prefix → True)
# Exception: some deepseek-ai models run on regional endpoints (maas suffix + region-pinned)
_GLOBAL_MODELS = {"xai", "deepseek-ai", "moonshotai", "minimaxai", "zai-org", "google", "openai"}

# Models within global-publisher families that actually run on a specific region
_REGIONAL_OVERRIDES: dict[str, str] = {
    "deepseek-ai/deepseek-r1-0528-maas":          "us-central1",
    "qwen/qwen3-235b-a22b-instruct-2507-maas":    "us-south1",
    "qwen/qwen3-coder-480b-a35b-instruct-maas":   "us-south1",
}


def _model_location(model: str, requested_location: str) -> str:
    """Return the correct Vertex AI location for this model."""
    if model in _REGIONAL_OVERRIDES:
        return _REGIONAL_OVERRIDES[model]
    prefix = model.split("/")[0] if "/" in model else ""
    if prefix in _GLOBAL_MODELS and requested_location not in ("global",):
        return "global"
    return requested_location


# ── Rate limiter (token bucket, thread-safe) ───────────────────────────────────

class RateLimiter:
    def __init__(self, rpm: int):
        self._interval = 60.0 / max(rpm, 1)
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            wait_s = self._interval - (now - self._last)
            if wait_s > 0:
                time.sleep(wait_s)
            self._last = time.monotonic()


# ── Grading helper ─────────────────────────────────────────────────────────────

def _grade_response(data_row: dict, raw: str | None) -> dict:
    """Parse model text and grade it. Returns partial result dict."""
    if not raw:
        return {"valid": False, "goal_reached": False, "correct": False,
                "valid_but_wrong": False, "parsed_moves": None}

    game = data_row["game"]
    moves = parsers.parse(game, raw)
    result = graders.grade(data_row, moves)
    valid = result.get("valid", False)
    goal = result.get("goal_reached", False)
    return {
        "valid": valid,
        "goal_reached": goal,
        "correct": result.get("correct", False),
        "valid_but_wrong": valid and not goal,
        "parsed_moves": str(moves) if moves else None,
        "move_count": result.get("move_count"),
        "error_msg_grader": result.get("error"),
        "error_at_move": result.get("error_at_move"),
    }


def _make_result(data_row: dict, model_id: str, run: int,
                 raw: str | None, api_error: str | None, elapsed_s: float) -> dict:
    grade = _grade_response(data_row, raw) if not api_error else {
        "valid": False, "goal_reached": False, "correct": False,
        "valid_but_wrong": False, "parsed_moves": None,
    }
    return {
        "id":              data_row["id"],
        "run":             run,
        "game":            data_row["game"],
        "variant":         data_row["variant"],
        "n":               data_row.get("n", ""),
        "model":           model_id,
        "response":        raw,
        "parsed_moves":    grade.get("parsed_moves"),
        "valid":           grade.get("valid", False),
        "goal_reached":    grade.get("goal_reached", False),
        "correct":         grade.get("correct", False),
        "valid_but_wrong": grade.get("valid_but_wrong", False),
        "move_count":      grade.get("move_count"),
        "extracted_answer": grade.get("extracted_answer"),
        "correct_answer":  grade.get("correct_answer"),
        "error_msg":       api_error,
        "error_msg_grader": grade.get("error_msg_grader"),
        "error_at_move":   grade.get("error_at_move"),
        "latency_ms":      round(elapsed_s * 1000),
    }


# ── Backend: Gemini SDK ────────────────────────────────────────────────────────

_thread_local = threading.local()


def _get_gemini_model(model_id: str, project: str, location: str):
    from vertexai.generative_models import GenerativeModel
    cache = getattr(_thread_local, "gemini_cache", {})
    key = (model_id, project, location)
    if key not in cache:
        cache[key] = GenerativeModel(model_id, system_instruction=SYSTEM_PROMPT)
    _thread_local.gemini_cache = cache
    return cache[key]


def _gemini_text(response) -> str | None:
    try:
        t = response.text
        if t:
            return t
    except Exception:
        pass
    parts: list[str] = []
    try:
        for c in (response.candidates or []):
            for p in (getattr(getattr(c, "content", None), "parts", None) or []):
                txt = getattr(p, "text", None)
                if txt:
                    parts.append(txt)
    except Exception:
        return None
    return "".join(parts) or None


def call_gemini(data_row: dict, model_id: str, run: int,
                project: str, location: str,
                rate_limiter: RateLimiter, max_tokens: int,
                temperature: float = 0.0, timeout: float = 300.0) -> dict:
    from vertexai.generative_models import GenerationConfig, HarmCategory, HarmBlockThreshold

    _SAFETY = {
        HarmCategory.HARM_CATEGORY_HARASSMENT:        HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_HATE_SPEECH:       HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
    }
    rate_limiter.wait()
    model = _get_gemini_model(model_id, project, location)
    cfg = GenerationConfig(
        max_output_tokens=max_tokens,
        temperature=temperature,
        candidate_count=1,
    )
    t0 = time.monotonic()
    raw, error = None, None
    try:
        resp = model.generate_content(
            build_prompt(data_row), generation_config=cfg, safety_settings=_SAFETY,
        )
        raw = _gemini_text(resp)
        if not raw:
            finish = None
            try:
                if resp.candidates:
                    finish = getattr(resp.candidates[0], "finish_reason", None)
            except Exception:
                pass
            error = f"empty_or_blocked (finish_reason={finish!r})"
    except Exception as exc:
        error = str(exc)

    return _make_result(data_row, model_id, run, raw, error, time.monotonic() - t0)


# ── Backend: Vertex OpenAI-compatible endpoint ─────────────────────────────────

def _vertex_base_url(project: str, location: str) -> str:
    loc = (location or "global").strip()
    host = ("https://aiplatform.googleapis.com" if loc == "global"
            else f"https://{loc}-aiplatform.googleapis.com")
    return f"{host}/v1/projects/{project}/locations/{loc}/endpoints/openapi"


def _bearer(creds) -> str:
    import google.auth.transport.requests
    req = google.auth.transport.requests.Request()
    with _creds_lock:
        if not creds.valid:
            creds.refresh(req)
        return str(creds.token or "")


def call_vertex_openai(
    data_row: dict, model: str, run: int, creds,
    base_url: str, rate_limiter: RateLimiter,
    max_tokens: int, timeout: float,
    temperature: float = 0.0,
) -> dict:
    from openai import OpenAI
    rate_limiter.wait()
    client = OpenAI(base_url=base_url, api_key=_bearer(creds), timeout=timeout)

    t0 = time.monotonic()
    raw, error = None, None
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user",   "content": build_prompt(data_row)},
            ],
            max_tokens=max_tokens,
            temperature=temperature,
        )
        choice = resp.choices[0].message if resp.choices else None
        finish = resp.choices[0].finish_reason if resp.choices else None
        if choice:
            raw = choice.content or ""
            if not raw and getattr(choice, "refusal", None):
                error = f"refusal: {choice.refusal!r}"
            elif not raw:
                error = f"empty_response (finish_reason={finish!r})"
        else:
            error = "no choices in response"
    except Exception as exc:
        error = str(exc)

    return _make_result(data_row, model, run, raw, error, time.monotonic() - t0)


# ── Checkpoint ────────────────────────────────────────────────────────────────

def _save(results: list[dict], path: str) -> None:
    tmp = path + ".tmp"
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    pd.DataFrame(results).to_csv(tmp, index=False)
    os.replace(tmp, path)


# ── Accuracy reporting ─────────────────────────────────────────────────────────

def _print_live_stats(results: list[dict], model_id: str, dataset_name: str) -> None:
    rows = [r for r in results if r.get("model") == model_id
            and str(r.get("variant", "")).startswith(dataset_name.split("_")[0])]
    if not rows:
        rows = [r for r in results if r.get("model") == model_id]
    if not rows:
        return
    n = len(rows)
    nc = sum(1 for r in rows if r.get("correct"))
    ne = sum(1 for r in rows if r.get("error_msg"))
    vbw = sum(1 for r in rows if r.get("valid_but_wrong"))
    print(f"    [{model_id.split('/')[-1]}] {nc}/{n} correct  "
          f"errors={ne}  valid≠goal={vbw}")


def _print_summary(all_results: list[dict], models: list[str]) -> None:
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    df = pd.DataFrame(all_results)
    if df.empty:
        return
    for model in models:
        m = df[df["model"] == model]
        if m.empty:
            continue
        n, nc = len(m), int(m["correct"].sum())
        ne = int(m["error_msg"].notna().sum()) if "error_msg" in m else 0
        vbw = int(m["valid_but_wrong"].sum()) if "valid_but_wrong" in m else 0
        print(f"\n{model}")
        print(f"  Overall  : {nc}/{n} correct ({100*nc/n:.1f}%)  "
              f"errors={ne}  valid≠goal={vbw}")
        for (game, variant, n_val), grp in m.groupby(["game", "variant", "n"]):
            ng, ncg = len(grp), int(grp["correct"].sum())
            print(f"  {game}/{variant} n={n_val:<4} runs={ng:<4} "
                  f"pass@1={ncg/ng:.2f} ({ncg}/{ng})")


# ── Main evaluation loop ───────────────────────────────────────────────────────

def evaluate_dataset(
    dataset_name: str,
    data_csv: str,
    models: list[str],
    project: str,
    location: str,
    out_path: str,
    runs: int,
    max_workers: int,
    rate_limiter: RateLimiter,
    timeout: float,
    sample: int | None,
    resume: bool,
    max_tokens: int,
    creds,
    temperature: float = 0.0,
) -> list[dict]:
    """Evaluate one data CSV across all models and runs. Returns list of result dicts."""

    df = pd.read_csv(data_csv)
    # Normalise id column
    if "id" not in df.columns and "row_id" in df.columns:
        df = df.rename(columns={"row_id": "id"})

    if sample:
        df = df.sample(n=min(sample, len(df)), random_state=42).reset_index(drop=True)
        print(f"  Sample: {len(df)} rows")
    else:
        print(f"  Rows: {len(df)}")

    # Expand for multiple runs: each (row, run) is an independent task
    tasks = []
    for _, row in df.iterrows():
        for run_idx in range(1, runs + 1):
            tasks.append((dict(row), run_idx))

    # Load already-done (id, model, run) triples
    done: set[tuple] = set()
    all_results: list[dict] = []
    if resume and os.path.exists(out_path):
        existing = pd.read_csv(out_path)
        all_results = existing.to_dict("records")
        done = {(r["id"], r["model"], int(r.get("run", 1))) for r in all_results}
        print(f"  Resuming: {len(done)} already done")

    for model in models:
        use_gemini = model.startswith("gemini-")
        if use_gemini:
            import vertexai
            loc = location if location != "global" else "us-central1"
            vertexai.init(project=project, location=loc)

        # Auto-detect location for this model
        model_location = _model_location(model, location)
        if model_location != location:
            print(f"  Note: {model} routed to {model_location} endpoint")
        base_url = _vertex_base_url(project, model_location)

        pending = [
            (row, run)
            for row, run in tasks
            if (row["id"], model, run) not in done
        ]
        print(f"\n  Model: {model.split('/')[-1]}  "
              f"backend={'gemini' if use_gemini else 'vertex_openai'}  "
              f"tasks: {len(pending)}")

        def _submit(args):
            row, run = args
            if use_gemini:
                return call_gemini(row, model, run, project,
                                   location if location != "global" else "us-central1",
                                   rate_limiter, max_tokens, temperature, timeout)
            else:
                return call_vertex_openai(row, model, run, creds,
                                          base_url, rate_limiter, max_tokens, timeout,
                                          temperature)

        saved_since = 0
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {executor.submit(_submit, args): args for args in pending}
                for fut in tqdm(as_completed(futures), total=len(futures),
                                desc=f"{model.split('/')[-1]} [{dataset_name}]"):
                    try:
                        result = fut.result()
                    except Exception as exc:
                        row, run = futures[fut]
                        result = _make_result(row, model, run, None, str(exc), 0.0)
                    all_results.append(result)
                    saved_since += 1
                    if saved_since >= CHECKPOINT_EVERY:
                        _save(all_results, out_path)
                        _print_live_stats(all_results, model, dataset_name)
                        saved_since = 0
        except KeyboardInterrupt:
            print("\n  Interrupted — saving …")
        finally:
            _save(all_results, out_path)

    return all_results


def run_all(
    models: list[str],
    project: str,
    location: str,
    out_dir: str,
    runs: int,
    max_workers: int,
    rpm: int,
    timeout: float,
    sample: int | None,
    resume: bool,
    max_tokens: int,
    datasets: list[str] | None = None,
) -> None:
    import google.auth
    creds, _ = google.auth.default(scopes=list(_SCOPES))
    rate_limiter = RateLimiter(rpm)
    os.makedirs(out_dir, exist_ok=True)

    targets = datasets or list(ALL_DATA_CSVS.keys())
    all_global_results: list[dict] = []

    for name in targets:
        csv_path = ALL_DATA_CSVS.get(name)
        if not csv_path or not os.path.exists(csv_path):
            print(f"\nSKIP {name}: CSV not found")
            continue

        # Hanoi/Checker/River: --runs repeats, temp=0.7 for diversity
        effective_runs = runs
        effective_temp = 0.7

        out_path = os.path.join(out_dir, f"{name}.csv")
        print(f"\n{'─'*60}")
        print(f"Dataset: {name}  runs={effective_runs}  temp={effective_temp}")

        results = evaluate_dataset(
            dataset_name=name,
            data_csv=csv_path,
            models=models,
            project=project,
            location=location,
            out_path=out_path,
            runs=effective_runs,
            max_workers=max_workers,
            rate_limiter=rate_limiter,
            timeout=timeout,
            sample=sample,
            resume=resume,
            max_tokens=max_tokens,
            creds=creds,
            temperature=effective_temp,
        )
        all_global_results.extend(results)
        print(f"  → {out_path}")

    # Combined output
    if all_global_results:
        combined = os.path.join(out_dir, "_all_results.csv")
        pd.DataFrame(all_global_results).to_csv(combined, index=False)
        print(f"\nCombined → {combined}  ({len(all_global_results)} rows)")
        _print_summary(all_global_results, models)


# ── CLI ────────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Evaluate non-math game CFs via Vertex AI Model Garden",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # Models
    ap.add_argument(
        "--model", nargs="+", required=True,
        help=(
            "Model ID(s). Gemini: gemini-2.5-flash  gemini-2.5-pro\n"
            "Aliases: grok  deepseek-r1  deepseek-v3  llama-4-maverick  llama-4-scout\n"
            "         llama-3.3-70b  gemma-4  gpt-oss-20b  gpt-oss-120b\n"
            "         qwen3-235b  glm-5  kimi-k2  minimax-m2\n"
            "Or raw Vertex model IDs: xai/grok-4.1-fast-non-reasoning etc."
        ),
    )

    # Dataset selection
    ds_group = ap.add_mutually_exclusive_group(required=True)
    ds_group.add_argument("--all", action="store_true",
                          help="Evaluate all datasets")
    ds_group.add_argument("--data", nargs="+",
                          help="Path(s) to specific data CSV(s)")
    ds_group.add_argument("--dataset", nargs="+",
                          choices=list(ALL_DATA_CSVS.keys()),
                          help="Named dataset(s): hanoi_baseline, checker_cf1_asymmetric, …")

    # GCP
    ap.add_argument("--project",
                    default=os.environ.get("GOOGLE_CLOUD_PROJECT", DEFAULT_PROJECT),
                    help=f"GCP project ID (default: {DEFAULT_PROJECT})")
    ap.add_argument("--location",
                    default=os.environ.get("VERTEX_LOCATION", "us-central1"),
                    help="Vertex AI region. Use 'global' for Grok/DeepSeek/Gemma/Kimi/MiniMax. "
                         "(env: VERTEX_LOCATION)")

    # Evaluation settings
    ap.add_argument("--runs", type=int, default=5,
                    help="Runs per problem (default 5).")
    ap.add_argument("--sample", type=int, default=None,
                    help="Smoke-test: randomly sample N rows per dataset")
    ap.add_argument("--resume", action="store_true",
                    help="Skip (id, model, run) triples already in the output CSV")

    # Output
    ap.add_argument("--out", default="results/non_math_games/",
                    help="Output path. If --all or multiple datasets: treated as directory. "
                         "If single dataset: treated as CSV path.")

    # Performance
    ap.add_argument("--max_workers", type=int, default=8,
                    help="Parallel workers (default 8)")
    ap.add_argument("--rpm", type=int, default=120,
                    help="Max requests per minute, client-side (default 120)")
    ap.add_argument("--timeout", type=float, default=300.0,
                    help="Per-request timeout in seconds (default 300)")
    ap.add_argument("--max_tokens", type=int, default=16384,
                    help="Max output tokens (default 16384)")

    args = ap.parse_args()

    # Resolve model aliases
    models = [MODEL_ALIASES.get(m, m) for m in args.model]
    for raw, resolved in zip(args.model, models):
        if raw != resolved:
            print(f"Alias: {raw!r} → {resolved!r}")

    if not args.project:
        ap.error("Provide --project or set GOOGLE_CLOUD_PROJECT")

    # --- Route to run_all or single-dataset ---

    if args.all or args.dataset:
        dataset_keys = list(ALL_DATA_CSVS.keys()) if args.all else args.dataset
        out_dir = args.out if args.out.endswith("/") or not args.out.endswith(".csv") else os.path.dirname(args.out)
        run_all(
            models=models,
            project=args.project,
            location=args.location,
            out_dir=out_dir,
            runs=args.runs,
            max_workers=args.max_workers,
            rpm=args.rpm,
            timeout=args.timeout,
            sample=args.sample,
            resume=args.resume,
            max_tokens=args.max_tokens,
            datasets=dataset_keys if not args.all else None,
        )

    elif args.data:
        import google.auth
        creds, _ = google.auth.default(scopes=list(_SCOPES))
        rate_limiter = RateLimiter(args.rpm)

        for data_path in args.data:
            if not os.path.exists(data_path):
                print(f"SKIP {data_path}: not found")
                continue
            name = os.path.splitext(os.path.basename(data_path))[0]
            out_path = args.out if len(args.data) == 1 and args.out.endswith(".csv") \
                else os.path.join(args.out, f"{name}.csv")

            effective_runs = args.runs
            effective_temp = 0.7

            print(f"\n{'─'*60}")
            print(f"Dataset: {data_path}  runs={effective_runs}  temp={effective_temp}")
            results = evaluate_dataset(
                dataset_name=name,
                data_csv=data_path,
                models=models,
                project=args.project,
                location=args.location,
                out_path=out_path,
                runs=effective_runs,
                max_workers=args.max_workers,
                rate_limiter=rate_limiter,
                timeout=args.timeout,
                sample=args.sample,
                resume=args.resume,
                max_tokens=args.max_tokens,
                creds=creds,
                temperature=effective_temp,
            )
            print(f"  → {out_path}  ({len(results)} rows)")
            _print_summary(results, models)


if __name__ == "__main__":
    main()
