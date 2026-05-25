"""Game of 24 CF2 — Three pairwise-distinct operator symbols.

With four numbers there are three binary operations. The CF requires the
three operator symbols be pairwise different (so one of {+,−,×,÷} is
unused, but the three symbols you do use must all be different — no
re-using the same operation twice).

CF invariant: the chosen (numbers, target=24) instance is solvable WITH
three distinct operators (otherwise the CF has no answer). The wrong-rule
trap is a normal Game-of-24 solution that uses a repeated operator.
"""
import sys
import os
import json
import argparse
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.solver import (
    solvable_for_24, one_solution_expression,
    has_solution_with_three_distinct_ops, one_expression_three_distinct_ops,
)
from utils.expr import perturbed_distractors, operators_used
from utils.io_utils import write_csv
from utils.mcq import shuffle_options

RULE_NAME = 'game24_cf2_each_operator_once'
NUM_SAMPLES = 100
TARGET = 24

RULE_DESC = (
    "Solve the following Game-of-24 puzzle with a structural constraint.\n"
    "Rules:\n"
    "  - Four numbers; use each exactly once.\n"
    "  - Combine with + − × ÷ and parentheses; division must be exact at each step.\n"
    "  - The three operator slots must use **three pairwise-different** symbols "
    "(so one of +, −, ×, ÷ does not appear, but no operator is repeated).\n"
    "  - The expression must evaluate to 24."
)


def _normalize(expr):
    return expr.replace('*', '×').replace('/', '÷').replace('-', '−')


def _make_question(nums):
    return (
        f"{RULE_DESC}\n\n"
        f"Numbers: {', '.join(str(n) for n in nums)}\n"
        "Which expression — using **three different** operators — reaches 24?"
    )


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    rows = []
    counter = 1
    seen = set()
    skips = 0

    while len(rows) < num_samples and skips < num_samples * 60:
        nums = [rng.randint(1, 9) for _ in range(4)]
        if not has_solution_with_three_distinct_ops(nums, TARGET):
            skips += 1
            continue

        key = tuple(sorted(nums))
        if key in seen:
            skips += 1
            continue

        correct_expr = one_expression_three_distinct_ops(nums, TARGET)
        if correct_expr is None:
            skips += 1
            continue
        # Sanity: confirm 3 distinct operators.
        if len(operators_used(correct_expr)) < 3:
            skips += 1
            continue

        # Distractor 1 (wrong-rule trap): a normal solution with repeated operator.
        wrong_rule_distractor = None
        # Try several random standard solutions and pick one with a repeat.
        for _ in range(60):
            cand = one_solution_expression(nums, TARGET)
            if cand is None:
                break
            if cand == correct_expr:
                # Tiny perturbation: shuffle nums and retry.
                rng.shuffle(nums)
                continue
            if len(operators_used(cand)) < 3:
                wrong_rule_distractor = cand
                break
            rng.shuffle(nums)

        needed = 3 if wrong_rule_distractor is None else 2
        perturbed = perturbed_distractors(correct_expr, TARGET, rng, count=needed)
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
            'puzzle': json.dumps({'numbers': nums, 'target': TARGET}),
            'question': _make_question(nums),
            'option_A': opts['A'],
            'option_B': opts['B'],
            'option_C': opts['C'],
            'option_D': opts['D'],
            'correct_option': correct,
            'correct_answer': correct_disp,
            'params': json.dumps({
                'numbers': nums, 'target': TARGET,
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
