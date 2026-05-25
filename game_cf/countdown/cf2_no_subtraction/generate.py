"""Countdown CF2 — Subtraction is forbidden.

Allowed operators: +, ×, ÷ (no − anywhere in the expression).

CF invariant: a subset of these same numbers can hit the target via the
**standard** rule (using subtraction) but cannot hit it without subtraction.
So subtraction genuinely changes the reachable set for this instance, and a
solver applying the standard rule would arrive at an expression containing
'-' — which is invalid under the CF.
"""
import sys
import os
import json
import argparse
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.solver import (
    one_expression_any_subset, no_subtraction_slice_diverges,
)
from utils.expr import perturbed_distractors, eval_strict
from utils.io_utils import write_csv
from utils.mcq import shuffle_options

RULE_NAME = 'countdown_cf2_no_subtraction'
NUM_SAMPLES = 100
NO_SUB = {'+', '*', '/'}

RULE_DESC = (
    "Solve the following Countdown-style puzzle.\n"
    "Rule change: subtraction is **forbidden**.\n"
    "  - Allowed operators: +, ×, ÷ only (the − symbol may not appear anywhere).\n"
    "  - Six numbers, subset allowed (each at most once).\n"
    "  - Every intermediate division must yield an exact integer."
)


def _normalize(expr):
    return expr.replace('*', '×').replace('/', '÷').replace('-', '−')


def _make_question(nums, target):
    nums_s = ", ".join(str(n) for n in nums)
    return (
        f"{RULE_DESC}\n\n"
        f"Numbers: {nums_s}\n"
        f"Target: {target}\n\n"
        "Which expression — using +, ×, ÷ only — reaches the target?"
    )


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    rows = []
    counter = 1
    seen = set()
    skips = 0

    while len(rows) < num_samples and skips < num_samples * 40:
        nums = [rng.randint(2, 9) for _ in range(6)]
        tgt = rng.randint(120, 999)

        if not no_subtraction_slice_diverges(nums, tgt):
            skips += 1
            continue

        key = (tuple(sorted(nums)), tgt)
        if key in seen:
            skips += 1
            continue

        correct_expr = one_expression_any_subset(nums, tgt, NO_SUB)
        if correct_expr is None or '-' in correct_expr:
            skips += 1
            continue

        # Distractor 1 (preferred): a standard-rule solution that DOES use '-'.
        # Such a solution exists on some subset by the divergence check.
        wrong_rule_distractor = None
        wr = one_expression_any_subset(nums, tgt, None)
        if wr is not None and '-' in wr:
            wrong_rule_distractor = wr

        # Other distractors: perturb the correct expression (any operator).
        needed = 3 if wrong_rule_distractor is None else 2
        perturbed = perturbed_distractors(correct_expr, tgt, rng, count=needed)

        distractors = []
        if wrong_rule_distractor is not None:
            distractors.append(wrong_rule_distractor)
        distractors += perturbed
        if len(distractors) < 3:
            skips += 1
            continue
        distractors = distractors[:3]

        all_exprs = [correct_expr] + distractors
        if len(set(all_exprs)) != 4:
            skips += 1
            continue

        seen.add(key)

        correct_disp = _normalize(correct_expr)
        distractor_disp = [_normalize(d) for d in distractors]
        opts, correct = shuffle_options(correct_disp, distractor_disp, rng)

        rows.append({
            'id': f'{RULE_NAME}_{counter:04d}',
            'rule': RULE_NAME,
            'state': 'counterfactual',
            'puzzle': json.dumps({'numbers': nums, 'target': tgt}),
            'question': _make_question(nums, tgt),
            'option_A': opts['A'],
            'option_B': opts['B'],
            'option_C': opts['C'],
            'option_D': opts['D'],
            'correct_option': correct,
            'correct_answer': correct_disp,
            'params': json.dumps({
                'numbers': nums, 'target': tgt,
                'has_wrong_rule_distractor': wrong_rule_distractor is not None,
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
