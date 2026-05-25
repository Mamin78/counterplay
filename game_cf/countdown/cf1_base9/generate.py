"""Countdown CF1 — Native base-9 (open-eval).

Every numeral the model sees and produces — operands, target, and the
literals inside its answer expression — is a base-9 string. The problem is
no longer "decode then solve in decimal"; the model must perform the
arithmetic in base 9 (or decode/encode at every step itself).

CF invariant:
  - At least one operand or the target has a multi-digit base-9 form
    (otherwise the base-9 surface coincides with base-10 and the rule is
    inert).

Open-eval contract (consumed by llm_eval/evaluate_games_open.py):
  - Model output: a parenthesized expression whose integer literals are
    base-9 strings.
  - The expression is verified by decoding every literal as base 9,
    evaluating with exact integer arithmetic, and checking it reaches the
    target (decoded). Numbers used must be a sub-multiset of the operands.
"""
import sys
import os
import json
import argparse
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.solver import one_expression_any_subset, random_use_all_instance
from utils.io_utils import write_csv
from utils.base_utils import int_to_base

RULE_NAME = 'countdown_cf1_base9'
NUM_SAMPLES = 100
BASE = 9

RULE_DESC = (
    "Solve the following Countdown-style puzzle.\n"
    "Rule change: every numeral in this problem — operands, the target, and "
    "every literal in your answer — is written in **base 9** (digits 0-8 only).\n"
    "  - Read each given numeral as a base-9 integer (e.g. the string '10' "
    "means decimal 9, '12' means decimal 11, '100' means decimal 81).\n"
    "  - Combine a subset of the given operands (each used at most once) with "
    "+, −, ×, ÷ and parentheses to reach the target.\n"
    "  - Your answer expression must use base-9 literals; the expression will "
    "be evaluated as base-9 arithmetic.\n"
    "  - Every intermediate division must yield an exact integer in base 9 "
    "(equivalently, in base 10 after decoding).\n"
    "  - Do not include any base-10 reasoning in your final answer expression."
)


def _to_base9(expr_b10: str) -> str:
    """Replace every integer literal in a base-10 expression string with its
    base-9 numeral. The expression should contain only non-negative ints."""
    out, i = [], 0
    while i < len(expr_b10):
        c = expr_b10[i]
        if c.isdigit():
            j = i
            while j < len(expr_b10) and expr_b10[j].isdigit():
                j += 1
            out.append(int_to_base(int(expr_b10[i:j]), BASE))
            i = j
        else:
            out.append(c)
            i += 1
    return ''.join(out)


def _normalize(expr: str) -> str:
    return expr.replace('*', '×').replace('/', '÷').replace('-', '−')


def _make_question(strs_b9, target_b9):
    return (
        f"{RULE_DESC}\n\n"
        f"Numbers (base 9): {', '.join(strs_b9)}\n"
        f"Target (base 9): {target_b9}\n\n"
        "Produce a single parenthesized arithmetic expression in base-9 "
        "numerals that reaches the target."
    )


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    rows = []
    counter = 1
    seen = set()
    skips = 0

    while len(rows) < num_samples and skips < num_samples * 30:
        hit = random_use_all_instance(rng, tgt_lo=50, tgt_hi=400)
        if hit is None:
            skips += 1
            continue
        dec_nums, dec_target, _full = hit

        strs_b9 = [int_to_base(n, BASE) for n in dec_nums]
        target_b9 = int_to_base(dec_target, BASE)

        # CF invariant: the base-9 surface must actually differ from base-10.
        # That holds iff some numeral (operand or target) is multi-digit in base 9.
        if all(len(s) == 1 for s in strs_b9) and len(target_b9) == 1:
            skips += 1
            continue

        key = (tuple(dec_nums), dec_target)
        if key in seen:
            skips += 1
            continue

        correct_expr_b10 = one_expression_any_subset(dec_nums, dec_target, None)
        if correct_expr_b10 is None:
            skips += 1
            continue

        seen.add(key)
        correct_expr_b9 = _to_base9(correct_expr_b10)
        correct_disp = _normalize(correct_expr_b9)

        rows.append({
            'id': f'{RULE_NAME}_{counter:04d}',
            'rule': RULE_NAME,
            'state': 'counterfactual',
            'puzzle': json.dumps({
                'numbers_base9': strs_b9,
                'target_base9': target_b9,
                'numbers_decimal': dec_nums,
                'target_decimal': dec_target,
            }),
            'question': _make_question(strs_b9, target_b9),
            # MCQ columns intentionally blank — open-eval format
            'option_A': '',
            'option_B': '',
            'option_C': '',
            'option_D': '',
            'correct_option': '',
            # Reference solution in base-9 literals (used by humans / for debug;
            # the evaluator parses model output and verifies independently).
            'correct_answer': correct_disp,
            'params': json.dumps({
                'numbers_decimal': dec_nums,
                'target_decimal': dec_target,
                'numbers_base9': strs_b9,
                'target_base9': target_b9,
                'eval_mode': 'open_native_base9',
            }),
        })
        counter += 1

    output_path = os.path.join(output_dir, f'{RULE_NAME}.csv')
    write_csv(rows, output_path)
    print(f"Written {len(rows)} rows to {output_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--output-dir',
                        default=os.path.join(os.path.dirname(__file__), 'data'))
    parser.add_argument('--num-samples', type=int, default=NUM_SAMPLES)
    args = parser.parse_args()
    generate(args.seed, args.output_dir, args.num_samples)
