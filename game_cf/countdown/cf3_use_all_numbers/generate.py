"""Countdown CF3 — Must use all six numbers exactly once.

The standard rule allows any non-empty subset. Under the CF rule all six
operands must appear in the expression exactly once.

CF invariant: a strict-subset solution also exists for the same (numbers,
target), so a solver applying the standard rule would emit a five-or-fewer
number expression — which is invalid here.
"""
import sys
import os
import json
import argparse
import random
from itertools import combinations

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.solver import (
    one_expression, use_all_numbers_matters, random_use_all_instance,
)
from utils.expr import perturbed_distractors, numbers_used
from utils.io_utils import write_csv
from utils.mcq import shuffle_options

RULE_NAME = 'countdown_cf3_use_all_numbers'
NUM_SAMPLES = 100

RULE_DESC = (
    "Solve the following Countdown-style puzzle.\n"
    "Rule change: you must use **all six** numbers exactly once.\n"
    "  - Six numbers given; each must appear in your expression exactly once.\n"
    "  - Combine with +, −, ×, ÷ and parentheses.\n"
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
        "Which expression — using **all six** numbers exactly once — reaches the target?"
    )


def _uses_all(expr, nums):
    return sorted(numbers_used(expr)) == sorted(nums)


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    rows = []
    counter = 1
    seen = set()
    skips = 0

    while len(rows) < num_samples and skips < num_samples * 30:
        hit = random_use_all_instance(rng, tgt_lo=50, tgt_hi=999)
        if hit is None:
            skips += 1
            continue
        nums, target, full_expr = hit

        if not use_all_numbers_matters(nums, target):
            skips += 1
            continue

        key = (tuple(sorted(nums)), target)
        if key in seen:
            skips += 1
            continue

        # Correct expression uses all six. The seed expression from
        # random_use_all_instance already does (by construction).
        correct_expr = full_expr
        if not _uses_all(correct_expr, nums):
            # Try the full-six solver.
            cand = one_expression(nums, target, None)
            if cand is None or not _uses_all(cand, nums):
                skips += 1
                continue
            correct_expr = cand

        # Distractor 1: a strict-subset solution (uses fewer than six numbers).
        wrong_rule_distractor = None
        for r in range(5, 0, -1):
            for subset in combinations(range(6), r):
                vals = [nums[i] for i in subset]
                e = one_expression(vals, target, None)
                if e is not None and e != correct_expr:
                    wrong_rule_distractor = e
                    break
            if wrong_rule_distractor is not None:
                break

        needed = 3 if wrong_rule_distractor is None else 2
        perturbed = perturbed_distractors(correct_expr, target, rng, count=needed)

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
            'puzzle': json.dumps({'numbers': nums, 'target': target}),
            'question': _make_question(nums, target),
            'option_A': opts['A'],
            'option_B': opts['B'],
            'option_C': opts['C'],
            'option_D': opts['D'],
            'correct_option': correct,
            'correct_answer': correct_disp,
            'params': json.dumps({
                'numbers': nums, 'target': target,
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
