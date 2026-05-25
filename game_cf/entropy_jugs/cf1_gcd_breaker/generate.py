"""CF1 — GCD Breaker: target impossible under classic rules, solvable with tax.

Because gcd(cap_A, cap_B) > 1 and target is not a multiple of that gcd,
Bézout's theorem guarantees no sequence of lossless pours can ever measure
the target.  The 1-unit evaporation tax breaks the GCD constraint and makes
previously unreachable volumes accessible.

Correct answer : BFS-optimal path under Entropy Jugs taxed rules.
Distractor 1   : BFS-optimal classic path to the nearest achievable amount
                 (the closest multiple of gcd), showing what classic rules
                 would produce instead.
Distractors 2–3: BFS paths to adjacent targets under taxed rules.

Each option is a JSON list of [Jug_A, Jug_B] states from start to goal.
"""
import sys
import os
import json
import argparse
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.solver import bfs
from utils.generator import generate_gcd_breaker
from utils.distractor import make_distractors
from utils.display import TAXED_RULES, puzzle_to_text
from utils.io_utils import write_csv
from utils.mcq import shuffle_options

RULE_NAME = 'entropy_jugs_cf1_gcd_breaker'
NUM_SAMPLES = 100

RULE_DESC = (
    "You are playing Entropy Jugs — a variant of the classic Water Jug puzzle.\n"
    "Rules — allowed moves:\n"
    f"{TAXED_RULES}\n"
    "Goal: reach the exact target volume in either jug using the fewest moves."
)


def _make_question(cap1, cap2, target, start, gcd_val):
    setup = puzzle_to_text(cap1, cap2, target, start, taxed=True)
    return (
        f"{RULE_DESC}\n\n"
        f"Puzzle: {setup}\n"
        f"(Note: gcd({cap1}, {cap2}) = {gcd_val}, so {target} is unreachable "
        f"under standard rules — the tax changes what is possible.)\n\n"
        "Each answer option is a JSON list of [Jug_A, Jug_B] states "
        "representing the sequence of jug states from start to the goal state.\n"
        "Which option shows the correct (shortest) solution sequence under Entropy Jugs rules?\n"
        "Note: one option shows the path obtained by applying standard Water Jug rules "
        "(which cannot reach this target and instead reaches the nearest achievable amount)."
    )


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    seen = set()
    rows = []
    counter = 1

    while len(rows) < num_samples:
        result = generate_gcd_breaker(rng, seen)
        if result is None:
            print("WARNING: exhausted puzzle space before reaching target count.")
            break
        cap1, cap2, target, start, taxed_path, near_target, gcd_val = result

        # Classic near-target path as the "normal solution" distractor
        classic_near_path = None
        if near_target is not None:
            classic_near_path = bfs(cap1, cap2, start, near_target, taxed=False)

        exclude = [taxed_path]
        if classic_near_path is not None:
            exclude.append(classic_near_path)

        other_distractors = make_distractors(
            cap1, cap2, target, taxed=True, rng=rng,
            count=3, exclude_paths=exclude,
        )

        distractors = []
        if classic_near_path is not None:
            distractors.append(json.dumps(classic_near_path))
        needed = 3 - len(distractors)
        distractors += [json.dumps(d) for d in other_distractors[:needed]]

        if len(distractors) < 3:
            continue

        sol_json = json.dumps(taxed_path)
        opts, correct = shuffle_options(sol_json, distractors[:3], rng)

        rows.append({
            'id': f'{RULE_NAME}_{counter:04d}',
            'rule': RULE_NAME,
            'state': 'counterfactual',
            'puzzle': json.dumps({
                'capacities': [cap1, cap2], 'target': target, 'start': start,
            }),
            'question': _make_question(cap1, cap2, target, start, gcd_val),
            'option_A': opts['A'],
            'option_B': opts['B'],
            'option_C': opts['C'],
            'option_D': opts['D'],
            'correct_option': correct,
            'correct_answer': sol_json,
            'params': json.dumps({
                'cap1': cap1, 'cap2': cap2, 'target': target,
                'gcd': gcd_val,
                'taxed': True,
                'category': 'gcd_breaker',
                'taxed_path_length': len(taxed_path),
                'near_target': near_target,
                'has_classic_near_distractor': classic_near_path is not None,
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
