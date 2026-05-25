"""Countdown baseline: standard rules. Six numbers, single decimal target,
subset allowed, + − × ÷ with exact integer division at every step."""
import sys
import os
import json
import argparse
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.solver import (
    one_expression_any_subset, reachable_from_numbers, random_use_all_instance,
)
from utils.expr import perturbed_distractors, eval_strict
from utils.io_utils import write_csv
from utils.mcq import shuffle_options

RULE_NAME = 'countdown_baseline'
NUM_SAMPLES = 100

RULE_DESC = (
    "Solve the following Countdown-style puzzle.\n"
    "Rules:\n"
    "  - You are given six numbers and a single integer target.\n"
    "  - Use a subset of the numbers (each at most once).\n"
    "  - Combine them with +, −, ×, ÷ and parentheses.\n"
    "  - Every intermediate division must yield an exact integer (no fractions)."
)


def _make_question(nums, target):
    nums_s = ", ".join(str(n) for n in nums)
    return (
        f"{RULE_DESC}\n\n"
        f"Numbers: {nums_s}\n"
        f"Target: {target}\n\n"
        "Which of the following expressions correctly reaches the target?"
    )


def _normalize(expr):
    return expr.replace('*', '×').replace('/', '÷').replace('-', '−')


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    rows = []
    counter = 1
    seen = set()
    skips = 0

    while len(rows) < num_samples and skips < num_samples * 10:
        hit = random_use_all_instance(rng, tgt_lo=100, tgt_hi=999)
        if hit is None:
            skips += 1
            continue
        nums, target, _full_expr = hit

        key = (tuple(sorted(nums)), target)
        if key in seen:
            skips += 1
            continue

        correct_expr = one_expression_any_subset(nums, target, None)
        if correct_expr is None:
            skips += 1
            continue

        distractors = perturbed_distractors(correct_expr, target, rng, count=3)
        if len(distractors) < 3:
            skips += 1
            continue

        seen.add(key)

        correct_disp = _normalize(correct_expr)
        distractor_disp = [_normalize(d) for d in distractors]

        opts, correct = shuffle_options(correct_disp, distractor_disp, rng)
        rows.append({
            'id': f'{RULE_NAME}_{counter:04d}',
            'rule': RULE_NAME,
            'state': 'baseline',
            'puzzle': json.dumps({'numbers': nums, 'target': target}),
            'question': _make_question(nums, target),
            'option_A': opts['A'],
            'option_B': opts['B'],
            'option_C': opts['C'],
            'option_D': opts['D'],
            'correct_option': correct,
            'correct_answer': correct_disp,
            'params': json.dumps({'numbers': nums, 'target': target}),
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
