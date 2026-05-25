"""Game of 24 CF1 — Native base-9 (open-eval).

All four operands and the target are presented as base-9 strings, and the
model is asked to produce an expression whose literals are base-9 numerals.
The underlying problem (reach the *decimal value* 24, which is "26" in base
9) is identical to baseline Game-of-24 in solvability — only the surface
notation changes — so any accuracy drop relative to baseline isolates the
cost of reasoning in base 9.

CF invariant:
  - At least one operand has a multi-digit base-9 form (otherwise the
    base-9 surface coincides with base-10 and the rule is inert).

Open-eval contract:
  - Model output: one parenthesized expression in base-9 literals using
    each of the four operands exactly once.
  - Verification decodes every literal as base 9, checks the expression
    evaluates to the decimal target (24), and checks the decoded multiset
    matches the operands.
"""
import sys
import os
import json
import argparse
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.solver import solvable_for_24, one_solution_expression
from utils.io_utils import write_csv
from utils.base_utils import int_to_base

RULE_NAME = 'game24_cf1_base9'
NUM_SAMPLES = 100
TARGET_DECIMAL = 24
BASE = 9
TARGET_BASE9 = int_to_base(TARGET_DECIMAL, BASE)  # "26"

RULE_DESC = (
    "Solve the following Game-of-24 puzzle.\n"
    "Rule change: every numeral in this problem — the four given operands, "
    "the target, and every literal in your answer — is written in **base 9** "
    "(digits 0-8 only).\n"
    "  - Read each given numeral as a base-9 integer (e.g. '17' means "
    "1·9 + 7 = decimal 16; '26' means 2·9 + 6 = decimal 24).\n"
    "  - Combine the four operands with +, −, ×, ÷ and parentheses, using "
    "each operand exactly once, to reach the target.\n"
    "  - Your answer expression must use base-9 literals; it will be "
    "evaluated as base-9 arithmetic.\n"
    "  - Every intermediate division must yield an exact integer.\n"
    f"  - The target written in base 9 is '{TARGET_BASE9}' (= 24 in decimal)."
)


def _to_base9(expr_b10: str) -> str:
    """Replace every integer literal in a base-10 expression string with its
    base-9 numeral. Assumes non-negative literals (the solver only produces
    those for this game)."""
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


def _is_b9(s: str) -> bool:
    return all(c in '012345678' for c in s)


def _make_question(strs_b9):
    return (
        f"{RULE_DESC}\n\n"
        f"Numbers (base 9): {', '.join(strs_b9)}\n"
        f"Target (base 9): {TARGET_BASE9}\n\n"
        "Produce a single parenthesized arithmetic expression in base-9 "
        "numerals that uses each operand exactly once and reaches the target."
    )


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    rows = []
    counter = 1
    seen = set()
    skips = 0

    while len(rows) < num_samples and skips < num_samples * 50:
        dec = [rng.randint(5, 80) for _ in range(4)]
        strs_b9 = [int_to_base(x, BASE) for x in dec]
        if not all(_is_b9(s) for s in strs_b9):
            skips += 1
            continue

        # CF invariant: at least one operand must be multi-digit in base 9.
        if all(len(s) == 1 for s in strs_b9):
            skips += 1
            continue

        if not solvable_for_24(dec):
            skips += 1
            continue

        key = tuple(sorted(dec))
        if key in seen:
            skips += 1
            continue

        correct_expr_b10 = one_solution_expression(dec, TARGET_DECIMAL)
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
                'numbers_decimal': dec,
                'target_decimal': TARGET_DECIMAL,
                'target_base9': TARGET_BASE9,
            }),
            'question': _make_question(strs_b9),
            'option_A': '',
            'option_B': '',
            'option_C': '',
            'option_D': '',
            'correct_option': '',
            'correct_answer': correct_disp,
            'params': json.dumps({
                'numbers_decimal': dec,
                'numbers_base9': strs_b9,
                'target_decimal': TARGET_DECIMAL,
                'target_base9': TARGET_BASE9,
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
