"""Game of 24 CF3 — Prime target (not 24).

The four numbers must reach a prime target instead of 24.

CF invariant: the (numbers, prime) instance is solvable AND the same
multiset is NOT solvable for 24. So a solver applying the standard Game-of-24
rule would fail (or land on a different number); the CF correct answer
deviates from the standard answer in value.
"""
import sys
import os
import json
import argparse
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.solver import solvable_for_target, solvable_for_24, one_solution_expression
from utils.expr import perturbed_distractors
from utils.io_utils import write_csv
from utils.mcq import shuffle_options

RULE_NAME = 'game24_cf3_prime_target'
NUM_SAMPLES = 100
PRIMES = [17, 19, 23, 29, 31, 37, 41, 43, 47, 53, 59, 61, 67, 71, 73, 79, 83, 89, 97]

RULE_DESC = (
    "Solve the following Game-of-24 variant.\n"
    "Rule change: the target is a **prime** integer (not 24).\n"
    "  - Four numbers, used each exactly once.\n"
    "  - Combine with +, −, ×, ÷ and parentheses; every intermediate division must be exact.\n"
    "  - The expression must evaluate to the stated prime target."
)


def _normalize(expr):
    return expr.replace('*', '×').replace('/', '÷').replace('-', '−')


def _make_question(nums, prime):
    return (
        f"{RULE_DESC}\n\n"
        f"Numbers: {', '.join(str(n) for n in nums)}\n"
        f"Prime target: {prime}\n\n"
        f"Which expression — using each number exactly once — reaches {prime}?"
    )


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    rows = []
    counter = 1
    seen = set()
    skips = 0

    while len(rows) < num_samples and skips < num_samples * 60:
        nums = [rng.randint(1, 12) for _ in range(4)]
        prime = rng.choice(PRIMES)
        if not solvable_for_target(nums, prime):
            skips += 1
            continue
        # CF invariant: same multiset must NOT also solve 24 — otherwise the
        # standard Game-of-24 rule would give a valid (alternative) answer.
        if solvable_for_24(nums):
            skips += 1
            continue

        key = (tuple(sorted(nums)), prime)
        if key in seen:
            skips += 1
            continue

        correct_expr = one_solution_expression(nums, prime)
        if correct_expr is None:
            skips += 1
            continue

        distractors = perturbed_distractors(correct_expr, prime, rng, count=3)
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
            'state': 'counterfactual',
            'puzzle': json.dumps({'numbers': nums, 'target': prime}),
            'question': _make_question(nums, prime),
            'option_A': opts['A'],
            'option_B': opts['B'],
            'option_C': opts['C'],
            'option_D': opts['D'],
            'correct_option': correct,
            'correct_answer': correct_disp,
            'params': json.dumps({'numbers': nums, 'target': prime}),
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
