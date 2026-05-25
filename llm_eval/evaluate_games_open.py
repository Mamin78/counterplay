"""
Open-ended (no-choice) evaluation of game counterfactual CSVs via OpenRouter.

The model sees the puzzle description only — no A/B/C/D options.  It must
produce the answer directly in a structured format, which is then parsed and
verified by a game-specific checker.

Usage
─────
Single CSV:
    python llm_eval/evaluate_games_open.py \\
        --csv game_cf/sudoku/cf2_shifted_boxes/data/sudoku_cf2_shifted_boxes.csv \\
        --model anthropic/claude-3-5-haiku \\
        --api_key $OPENROUTER_API_KEY \\
        --out llm_eval/results_games_open.csv

All game CSVs at once (glob pattern — quote to prevent shell expansion):
    --csv "game_cf/*/*/data/*.csv"

Multiple models:
    --model openai/gpt-4o anthropic/claude-3-5-haiku

Resume a partial run:
    --resume
"""
from __future__ import annotations

import argparse
import ast
import glob
import json
import os
import re
import tempfile
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from fractions import Fraction
from typing import Any

import pandas as pd
import requests
from tqdm import tqdm

# ── Constants ─────────────────────────────────────────────────────────────────

CHECKPOINT_EVERY = 50
_OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

SYSTEM_PROMPT = (
    "You are solving a logic or math puzzle with modified rules.\n"
    "Read the rules carefully and reason step by step.\n"
    "CRITICAL OUTPUT RULE: you MUST end your response with your final answer "
    "wrapped in <answer>...</answer> tags — both the opening AND closing tag are required. "
    "Put only the answer inside the tags, in the exact format the question specifies. "
    "Any response that does not contain a closing </answer> tag will be marked wrong."
)

# ── Prompt building ────────────────────────────────────────────────────────────

# Patterns that reference MCQ options and should be stripped for open-ended eval.
_MCQ_STRIP_RE = re.compile(
    r'\n(?:'
    r'Which of the following[^\n]*'
    r'|Which option[^\n]*'
    r'|Which expression[^\n]*'
    r'|Note: one option[^\n]*'
    r')',
    re.MULTILINE,
)


def _strip_mcq(q: str) -> str:
    return _MCQ_STRIP_RE.sub('', q).rstrip()


def _format_instruction(rule: str) -> str:
    if 'cf4_hex' in rule:
        return (
            "Provide the completed 16×16 grid as a 2D JSON array "
            "(16 lists of 16 integers; for hex values A=10, B=11, …, F=15)."
        )
    if rule.startswith('sudoku_'):
        return (
            "Provide the completed 9×9 grid as a 2D JSON array "
            "(9 lists of 9 integers)."
        )
    if rule.startswith('cryptarithmetic_'):
        return (
            'Provide the letter-to-digit assignment as a JSON object, '
            'e.g. {"A": 1, "B": 5, "C": 3}.'
        )
    if rule.startswith('entropy_jugs_'):
        return (
            "Provide the solution path as a JSON list of [Jug_A, Jug_B] states "
            "from start to goal, e.g. [[0,0],[5,0],[5,3]]."
        )
    if 'cf4_multi_target' in rule:
        return "Provide both expressions in exactly this format: A: <expr_A> ; B: <expr_B>"
    if 'cf1_base9' in rule and (rule.startswith('countdown_') or rule.startswith('game24_')):
        return (
            "Provide only the arithmetic expression in base-9 numerals "
            "(use ×, ÷, − or *, /, -; no equals sign). "
            "Your expression will be evaluated as base-9 arithmetic: every "
            "integer literal is read in base 9 (digits 0-8 only)."
        )
    if rule.startswith('countdown_') or rule.startswith('game24_'):
        return (
            "Provide only the arithmetic expression "
            "(you may use ×, ÷, − or equivalently *, /, -; no equals sign)."
        )
    return "Provide your answer."


def build_prompt(row) -> str:
    q = _strip_mcq(str(row['question']))
    inst = _format_instruction(str(row['rule']))
    return (
        f"{q}\n\n"
        f"{inst}\n"
        "You MUST wrap your final answer in <answer>...</answer> tags "
        "(both opening and closing tag required). "
        "Do not include any text after the closing </answer> tag."
    )


# ── Answer extraction ─────────────────────────────────────────────────────────

_TAG_RE = re.compile(r'<answer>\s*(.*?)\s*</answer>', re.DOTALL | re.IGNORECASE)
# Closing tag only — Gemini often omits the opening tag and outputs "content</answer>"
_CLOSE_TAG_RE = re.compile(r'^([\s\S]*?)\s*</answer>', re.IGNORECASE)
_HEX_MAP = {'A': 10, 'B': 11, 'C': 12, 'D': 13, 'E': 14, 'F': 15}


def _extract_tag(raw: str | None) -> str | None:
    """Extract answer from model response.

    Handles three observed patterns:
      1. <answer>content</answer>   — intended format
      2. content</answer>           — Gemini omits opening tag
      3. no tags at all             — return full response for downstream parsing
    """
    if not raw:
        return None
    raw = raw.strip()
    # 1. Both tags present
    m = _TAG_RE.search(raw)
    if m:
        return m.group(1).strip()
    # 2. Only closing tag (model treats <answer> as a cue and omits it from output)
    m = _CLOSE_TAG_RE.match(raw)
    if m:
        content = m.group(1).strip()
        if content:
            return content
    # 3. No tags — pass the full response to the game-specific parser
    return raw


def _try_json(text: str) -> Any:
    text = text.strip()
    # Strip markdown code fences (```json ... ``` or ``` ... ```)
    fence_m = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if fence_m:
        inner = fence_m.group(1).strip()
        try:
            return json.loads(inner)
        except Exception:
            pass
    try:
        return json.loads(text)
    except Exception:
        pass
    # Try every opening bracket position paired with the last matching closer.
    # This handles JSON embedded inside prose (e.g. "The path is [[0,0],[3,0]].")
    for open_c, close_c in (('[', ']'), ('{', '}')):
        rb = text.rfind(close_c)
        if rb == -1:
            continue
        for lb, ch in enumerate(text):
            if lb >= rb:
                break
            if ch != open_c:
                continue
            try:
                return json.loads(text[lb:rb + 1])
            except Exception:
                pass
    return None


def _normalize_cell(v) -> int | None:
    if isinstance(v, int):
        return v
    if isinstance(v, str):
        up = v.strip().upper()
        if up in _HEX_MAP:
            return _HEX_MAP[up]
        try:
            return int(v)
        except Exception:
            pass
    return None


def _parse_grid(text: str) -> list | None:
    obj = _try_json(text)
    if not isinstance(obj, list):
        return None
    grid = []
    for row in obj:
        if not isinstance(row, list):
            return None
        norm = [_normalize_cell(v) for v in row]
        if any(v is None for v in norm):
            return None
        grid.append(norm)
    return grid


def parse_answer(raw: str | None, rule: str) -> Any:
    text = _extract_tag(raw)
    if text is None:
        return None

    if rule.startswith('sudoku_'):
        return _parse_grid(text)

    if rule.startswith('cryptarithmetic_'):
        obj = _try_json(text)
        if isinstance(obj, dict):
            try:
                return {str(k): int(v) for k, v in obj.items()}
            except Exception:
                pass
        # Fallback: parse "LETTER=digit" or "LETTER: digit" patterns from prose
        matches = re.findall(r'\b([A-Z])\s*(?:=|:|→|->)\s*(\d)\b', text)
        if matches:
            return {k: int(v) for k, v in matches}
        return None

    if rule.startswith('entropy_jugs_'):
        obj = _try_json(text)
        if isinstance(obj, list):
            try:
                return [[int(a), int(b)] for a, b in obj]
            except Exception:
                pass
        # Fallback: scan for "(a, b)" or "(a,b)" state pairs in prose
        pairs = re.findall(r'\((\d+)\s*,\s*(\d+)\)', text)
        if pairs:
            try:
                return [[int(a), int(b)] for a, b in pairs]
            except Exception:
                pass
        return None

    # countdown / game24: extract arithmetic expression
    return _extract_expression(text)


def _extract_expression(text: str) -> str | None:
    """Find an arithmetic expression in model text (handles full reasoning dumps)."""
    text = text.strip()
    if not text:
        return None
    # Try the whole text first (works when model gives a clean one-liner)
    if _eval_strict(text) is not None:
        return text
    # Scan lines from the bottom up — the answer is usually last
    for line in reversed(text.splitlines()):
        line = line.strip()
        if not line:
            continue
        # Strip common prose prefixes: "Answer: expr", "= expr", "**expr**", etc.
        for prefix_re in (
            r'^(?:answer|expression|result|final answer)\s*[:\-=]\s*',
            r'^\*{1,2}',
            r'^=\s*',
        ):
            line = re.sub(prefix_re, '', line, flags=re.IGNORECASE).strip()
        # Strip trailing markdown bold markers
        line = re.sub(r'\*{1,2}$', '', line).strip()
        if _eval_strict(line) is not None:
            return line
    # Last resort: return the last non-empty line (let checker decide)
    for line in reversed(text.splitlines()):
        if line.strip():
            return line.strip()
    return None


# ── Inline strict expression evaluator ───────────────────────────────────────

def _eval_strict(expr: str) -> int | None:
    expr = expr.replace('×', '*').replace('÷', '/').replace('−', '-')
    try:
        tree = ast.parse(expr, mode='eval')
    except SyntaxError:
        return None

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.BinOp):
            l, r = visit(node.left), visit(node.right)
            if l is None or r is None:
                return None
            op = node.op
            if isinstance(op, ast.Add):
                return l + r
            if isinstance(op, ast.Sub):
                return l - r
            if isinstance(op, ast.Mult):
                return l * r
            if isinstance(op, ast.Div):
                if r == 0:
                    return None
                q = l / r
                return q if q.denominator == 1 else None
            return None
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return Fraction(node.value)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            v = visit(node.operand)
            return -v if v is not None else None
        return None

    v = visit(tree)
    return int(v) if (v is not None and v.denominator == 1) else None


def _nums_in_expr(expr: str) -> list[int]:
    expr = expr.replace('×', '*').replace('÷', '/').replace('−', '-')
    return [int(s) for s in re.findall(r'\d+', expr)]


def _decode_expr_base(expr: str, base: int) -> str | None:
    """Re-encode every integer literal in `expr` from `base` to base 10.

    Returns None if any literal contains a digit ≥ `base` (which would make
    the literal invalid as a base-`base` numeral). Operator/punctuation
    characters pass through unchanged.
    """
    out, i, n = [], 0, len(expr)
    while i < n:
        c = expr[i]
        if c.isdigit():
            j = i
            while j < n and expr[j].isdigit():
                j += 1
            s = expr[i:j]
            for ch in s:
                if int(ch) >= base:
                    return None
            out.append(str(int(s, base)))
            i = j
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def _nums_in_expr_base(expr: str, base: int) -> list[int] | None:
    """Extract integer literals from `expr`, interpreted in `base`.

    Returns None if any literal has a digit ≥ `base`.
    """
    expr = expr.replace('×', '*').replace('÷', '/').replace('−', '-')
    out = []
    for s in re.findall(r'\d+', expr):
        for ch in s:
            if int(ch) >= base:
                return None
        out.append(int(s, base))
    return out


def _ops_in_expr(expr: str) -> set[str]:
    expr = expr.replace('×', '*').replace('÷', '/').replace('−', '-')
    return {c for c in expr if c in '+-*/'}


# ── Game-specific correctness checkers ────────────────────────────────────────

def _is_valid_hex_sudoku(grid: list, puzzle: list | None = None) -> bool:
    """Semantic validity check for a 16×16 hex sudoku grid.

    puzzle, if provided, is the original puzzle grid where None marks empty
    cells and integers are givens.  Any given cell must match in grid.
    """
    N, BOX = 16, 4
    target = sorted(range(N))
    if len(grid) != N:
        return False
    for r in range(N):
        if len(grid[r]) != N or sorted(grid[r]) != target:
            return False
    for c in range(N):
        if sorted(grid[r][c] for r in range(N)) != target:
            return False
    for br in range(N // BOX):
        for bc in range(N // BOX):
            box = [grid[br * BOX + i][bc * BOX + j]
                   for i in range(BOX) for j in range(BOX)]
            if sorted(box) != target:
                return False
    if puzzle is not None:
        for r in range(N):
            for c in range(N):
                if puzzle[r][c] is not None and grid[r][c] != puzzle[r][c]:
                    return False
    return True


def _check_sudoku(parsed: Any, row) -> bool:
    if not isinstance(parsed, list):
        return False
    rule = row['rule']
    if 'cf4_hex' in rule:
        # cf4_hex does not enforce uniqueness, so exact match would wrongly
        # reject alternative valid solutions.  Validate semantically instead.
        # The puzzle now uses None (not 0) as the empty sentinel, so given-cell
        # consistency can be checked unambiguously.
        puzzle = json.loads(row['puzzle'])
        return _is_valid_hex_sudoku(parsed, puzzle=puzzle)
    # All other sudoku variants enforce unique solutions → exact match is correct.
    correct = json.loads(row['correct_answer'])
    return parsed == correct


def _check_crypto(parsed: Any, row) -> bool:
    if not isinstance(parsed, dict):
        return False
    correct = json.loads(row['correct_answer'])
    try:
        return {k: int(v) for k, v in parsed.items()} == correct
    except Exception:
        return False


def _is_valid_pour(s: tuple, ns: tuple, cap1: int, cap2: int, taxed: bool) -> bool:
    a, b = s
    na, nb = ns
    # Fill A or B
    if (na, nb) == (cap1, b) and a < cap1:
        return True
    if (na, nb) == (a, cap2) and b < cap2:
        return True
    # Empty A or B
    if (na, nb) == (0, b) and a > 0:
        return True
    if (na, nb) == (a, 0) and b > 0:
        return True
    # Pour A → B
    if a > 0 and b < cap2:
        if taxed:
            amt_r = min(a, (cap2 - b) + 1)
            if amt_r > 0 and (na, nb) == (a - amt_r, b + max(0, amt_r - 1)):
                return True
        else:
            amt = min(a, cap2 - b)
            if amt > 0 and (na, nb) == (a - amt, b + amt):
                return True
    # Pour B → A
    if b > 0 and a < cap1:
        if taxed:
            amt_r = min(b, (cap1 - a) + 1)
            if amt_r > 0 and (na, nb) == (a + max(0, amt_r - 1), b - amt_r):
                return True
        else:
            amt = min(b, cap1 - a)
            if amt > 0 and (na, nb) == (a + amt, b - amt):
                return True
    return False


def _check_entropy(parsed: Any, row) -> bool:
    if not isinstance(parsed, list) or len(parsed) < 1:
        return False
    puzzle = json.loads(row['puzzle'])
    cap1, cap2 = puzzle['capacities']
    target = puzzle['target']
    taxed = row['rule'] != 'entropy_jugs_baseline'
    correct = json.loads(row['correct_answer'])

    # Final state must reach target
    final = parsed[-1]
    if not (isinstance(final, list) and len(final) == 2 and target in final):
        return False

    # Path length must match optimal (BFS shortest)
    if len(parsed) != len(correct):
        return False

    # Each transition must be a valid pour under the appropriate rules
    for i in range(len(parsed) - 1):
        s = tuple(parsed[i])
        ns = tuple(parsed[i + 1])
        if not _is_valid_pour(s, ns, cap1, cap2, taxed):
            return False

    return True


def _check_countdown(parsed: Any, row) -> bool:
    if not isinstance(parsed, str) or not parsed.strip():
        return False
    rule = row['rule']
    puzzle = json.loads(row['puzzle'])

    if 'cf4_multi_target' in rule:
        m = re.match(r'A:\s*(.+?)\s*;\s*B:\s*(.+)', parsed, re.IGNORECASE)
        if not m:
            return False
        expr_a, expr_b = m.group(1).strip(), m.group(2).strip()
        t1, t2 = puzzle['target1'], puzzle['target2']
        va, vb = _eval_strict(expr_a), _eval_strict(expr_b)
        if va != t1 or vb != t2:
            return False
        grp_a = puzzle['group_a']
        nums = puzzle['numbers']
        ga = sorted(nums[i] for i in grp_a)
        gb = sorted(nums[j] for j in range(6) if j not in grp_a)
        return (sorted(_nums_in_expr(expr_a)) == ga and
                sorted(_nums_in_expr(expr_b)) == gb)

    # cf1_base9 is now native open-eval: literals in `parsed` are base-9 numerals.
    # Decode them to base 10 before evaluating.
    if 'cf1_base9' in rule:
        target = puzzle.get('target_decimal', puzzle.get('target'))
        dec_nums = puzzle.get('numbers_decimal', puzzle.get('numbers', []))
        decoded = _decode_expr_base(parsed, 9)
        if decoded is None:
            return False
        val = _eval_strict(decoded)
        if val is None or val != target:
            return False
        used = _nums_in_expr_base(parsed, 9)
        if used is None:
            return False
        available = list(dec_nums)
        for n in used:
            if n in available:
                available.remove(n)
            else:
                return False
        return True

    target = puzzle.get('target', puzzle.get('target_decimal'))
    dec_nums = puzzle.get('numbers_decimal', puzzle.get('numbers', []))

    val = _eval_strict(parsed)
    if val is None or val != target:
        return False

    # Numbers used must be a sub-multiset of the available pool
    used = _nums_in_expr(parsed)
    available = list(dec_nums)
    for n in used:
        if n in available:
            available.remove(n)
        else:
            return False

    if 'cf2_no_subtraction' in rule:
        if '-' in parsed.replace('−', '-'):
            return False

    if 'cf3_use_all_numbers' in rule:
        if sorted(used) != sorted(dec_nums):
            return False

    return True


def _check_game24(parsed: Any, row) -> bool:
    if not isinstance(parsed, str) or not parsed.strip():
        return False
    rule = row['rule']
    puzzle = json.loads(row['puzzle'])

    # cf1_base9 is now native open-eval in base 9.
    if 'cf1_base9' in rule:
        target = puzzle.get('target_decimal', 24)
        dec_nums = puzzle.get('numbers_decimal', puzzle.get('numbers', []))
        decoded = _decode_expr_base(parsed, 9)
        if decoded is None:
            return False
        val = _eval_strict(decoded)
        if val is None or val != target:
            return False
        used = _nums_in_expr_base(parsed, 9)
        if used is None:
            return False
        return sorted(used) == sorted(dec_nums)

    target = puzzle.get('target', 24)
    dec_nums = puzzle.get('numbers_decimal', puzzle.get('numbers', []))

    val = _eval_strict(parsed)
    if val is None or val != target:
        return False

    if sorted(_nums_in_expr(parsed)) != sorted(dec_nums):
        return False

    if 'cf2_each_operator_once' in rule:
        if len(_ops_in_expr(parsed)) < 3:
            return False

    return True


def check_correct(parsed: Any, row) -> bool:
    rule = str(row['rule'])
    if rule.startswith('sudoku_'):
        return _check_sudoku(parsed, row)
    if rule.startswith('cryptarithmetic_'):
        return _check_crypto(parsed, row)
    if rule.startswith('entropy_jugs_'):
        return _check_entropy(parsed, row)
    if 'countdown' in rule:
        return _check_countdown(parsed, row)
    if 'game24' in rule:
        return _check_game24(parsed, row)
    return False


# ── Rate limiter ──────────────────────────────────────────────────────────────

class RateLimiter:
    def __init__(self, max_per_minute: int):
        self._interval = 60.0 / max_per_minute
        self._lock = threading.Lock()
        self._last = 0.0

    def wait(self):
        with self._lock:
            now = time.monotonic()
            gap = self._last + self._interval - now
            if gap > 0:
                time.sleep(gap)
            self._last = time.monotonic()


# ── Checkpointing ─────────────────────────────────────────────────────────────

def _save(results: list[dict], path: str) -> None:
    tmp = path + ".tmp"
    pd.DataFrame(results).to_csv(tmp, index=False)
    os.replace(tmp, path)


# ── API call ──────────────────────────────────────────────────────────────────

def call_model(row, model: str, api_key: str, timeout: int,
               rate_limiter: RateLimiter, max_tokens: int) -> dict:
    rate_limiter.wait()
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://github.com/thesis-symbolic",
        "X-Title": "GameCF-OpenEval",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": build_prompt(row)},
        ],
        "max_tokens": max_tokens,
        "temperature": 0,
    }
    t0 = time.monotonic()
    raw, error = None, None
    try:
        resp = requests.post(_OPENROUTER_URL, json=payload, headers=headers, timeout=timeout)
        resp.raise_for_status()
        raw = resp.json()["choices"][0]["message"]["content"]
    except Exception as exc:
        error = str(exc)

    latency_ms = round((time.monotonic() - t0) * 1000)
    rule = str(row['rule'])
    extracted = _extract_tag(raw) if raw else None
    parsed = parse_answer(raw, rule) if not error else None
    is_correct = bool(check_correct(parsed, row)) if parsed is not None else False

    return {
        "row_id": row["row_id"],
        "model": model,
        "rule": rule,
        "state": row.get("state", ""),
        "raw_response": raw,
        "extracted_answer": extracted,
        "is_correct": is_correct,
        "error_msg": error,
        "latency_ms": latency_ms,
    }


# ── Evaluation loop ───────────────────────────────────────────────────────────

def evaluate(models: list[str], api_key: str, dataset_path: str, out_path: str,
             max_workers: int, rpm: int, timeout: int, sample: int | None,
             resume: bool, max_tokens: int) -> pd.DataFrame:

    df = pd.read_csv(dataset_path)
    if "id" in df.columns and "row_id" not in df.columns:
        df = df.rename(columns={"id": "row_id"})
    if sample:
        df = df.sample(n=min(sample, len(df)), random_state=42).reset_index(drop=True)

    print(f"Dataset: {len(df)} rows  |  rules: {sorted(df['rule'].unique())}")

    done: set[tuple] = set()
    if resume and os.path.exists(out_path):
        existing = pd.read_csv(out_path)
        done = set(zip(existing["row_id"], existing["model"]))
        print(f"Resuming: {len(done)} already evaluated.")

    all_results: list[dict] = (
        list(pd.read_csv(out_path).to_dict("records")) if done else []
    )
    rate_limiter = RateLimiter(rpm)

    for model in models:
        to_eval = [r for _, r in df.iterrows() if (r["row_id"], model) not in done]
        print(f"\nModel: {model}  |  rows: {len(to_eval)}")
        saved_since = 0
        try:
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(
                        call_model, row, model, api_key, timeout,
                        rate_limiter, max_tokens
                    ): row["row_id"]
                    for row in to_eval
                }
                for fut in tqdm(as_completed(futures), total=len(futures),
                                desc=model.split("/")[-1]):
                    try:
                        all_results.append(fut.result())
                    except Exception as exc:
                        all_results.append({
                            "row_id": futures[fut], "model": model,
                            "raw_response": None, "extracted_answer": None,
                            "is_correct": False, "error_msg": str(exc),
                            "latency_ms": None,
                        })
                    saved_since += 1
                    if saved_since >= CHECKPOINT_EVERY:
                        _save(all_results, out_path)
                        saved_since = 0
        except KeyboardInterrupt:
            print("\nInterrupted — saving …")
        finally:
            _save(all_results, out_path)
            print(f"  checkpoint → {out_path}  ({len(all_results)} rows)")

    df_out = pd.DataFrame(all_results)
    df_out.to_csv(out_path, index=False)
    print(f"\nFinal → {out_path}  ({len(df_out)} rows)\n")
    for mid in models:
        m = df_out[df_out["model"] == mid]
        if m.empty:
            continue
        n = len(m)
        nc = int(m["is_correct"].sum())
        print(f"  {mid}: acc={nc/n:.3f} ({nc}/{n})")
    return df_out


# ── CLI ───────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Open-ended evaluation of game CF CSVs via OpenRouter"
    )
    parser.add_argument(
        "--csv", required=True,
        help="Path to a game CF CSV, or a glob pattern (shell-quoted, e.g. 'game_cf/*/*/data/*.csv')"
    )
    parser.add_argument("--model", nargs="+", required=True,
                        help="OpenRouter model id(s)")
    parser.add_argument("--api_key",
                        default=os.environ.get("OPENROUTER_API_KEY"),
                        help="OpenRouter API key (or set OPENROUTER_API_KEY)")
    parser.add_argument("--out", default="llm_eval/results_games_open.csv")
    parser.add_argument("--max_workers", type=int, default=8)
    parser.add_argument("--rpm", type=int, default=60,
                        help="Max requests per minute (client-side)")
    parser.add_argument("--timeout", type=int, default=90)
    parser.add_argument("--sample", type=int, default=None,
                        help="Evaluate only N randomly sampled rows")
    parser.add_argument("--resume", action="store_true",
                        help="Skip row_id × model pairs already in --out")
    parser.add_argument("--max_tokens", type=int, default=8192,
                        help="Max tokens for model response (default 8192; reasoning models need headroom)")
    args = parser.parse_args()

    if not args.api_key:
        parser.error("Provide --api_key or set OPENROUTER_API_KEY")

    paths = sorted(glob.glob(args.csv)) or ([args.csv] if os.path.exists(args.csv) else [])
    if not paths:
        parser.error(f"No files matched: {args.csv}")

    frames = []
    for p in paths:
        df = pd.read_csv(p)
        if "id" in df.columns and "row_id" not in df.columns:
            df = df.rename(columns={"id": "row_id"})
        frames.append(df)
    df_all = pd.concat(frames, ignore_index=True)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False, mode='w') as f:
        tmp_path = f.name
        df_all.to_csv(f, index=False)

    try:
        evaluate(
            models=args.model,
            api_key=args.api_key,
            dataset_path=tmp_path,
            out_path=args.out,
            max_workers=args.max_workers,
            rpm=args.rpm,
            timeout=args.timeout,
            sample=args.sample,
            resume=args.resume,
            max_tokens=args.max_tokens,
        )
    finally:
        os.unlink(tmp_path)


if __name__ == "__main__":
    main()
