"""Classic Water Jug baseline generator — 100 MCQ items.

Correct answer : BFS-optimal path under standard (lossless) pour rules.
Distractor 1   : BFS-optimal path under Entropy Jugs taxed rules (if different).
Distractors 2–3: BFS paths to adjacent targets under classic rules.

Each option is a JSON list of [Jug_A, Jug_B] states from start to goal.
"""
import sys
import os
import json
import argparse
import random

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.solver import bfs
from utils.generator import generate_classic
from utils.distractor import make_distractors
from utils.display import CLASSIC_RULES, puzzle_to_text
from utils.io_utils import write_csv
from utils.mcq import shuffle_options

RULE_NAME = 'entropy_jugs_baseline'
NUM_SAMPLES = 100

RULE_DESC = (
    "You are playing the classic Water Jug puzzle.\n"
    "Rules — allowed moves:\n"
    f"{CLASSIC_RULES}\n"
    "Goal: reach the exact target volume in either jug using the fewest moves."
)


def _make_question(cap1, cap2, target, start):
    setup = puzzle_to_text(cap1, cap2, target, start, taxed=False)
    return (
        f"{RULE_DESC}\n\n"
        f"Puzzle: {setup}\n\n"
        "Each answer option is a JSON list of [Jug_A, Jug_B] states "
        "representing the sequence of jug states from start to the goal state.\n"
        "Which option shows the correct (shortest) solution sequence?\n"
        "Note: one option shows the path obtained by applying "
        "Entropy Jugs rules (1-unit evaporation tax on pours)."
    )


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    seen = set()
    rows = []
    counter = 1

    while len(rows) < num_samples:
        result = generate_classic(rng, seen)
        if result is None:
            print("WARNING: exhausted puzzle space before reaching target count.")
            break
        cap1, cap2, target, start, classic_path = result

        # Taxed path as cross-rule distractor
        taxed_path = bfs(cap1, cap2, start, target, taxed=True)

        exclude = [classic_path]
        if taxed_path is not None and taxed_path != classic_path:
            exclude.append(taxed_path)

        other_distractors = make_distractors(
            cap1, cap2, target, taxed=False, rng=rng,
            count=3, exclude_paths=exclude,
        )

        distractors = []
        if taxed_path is not None and taxed_path != classic_path:
            distractors.append(json.dumps(taxed_path))
        needed = 3 - len(distractors)
        distractors += [json.dumps(d) for d in other_distractors[:needed]]

        if len(distractors) < 3:
            continue

        sol_json = json.dumps(classic_path)
        opts, correct = shuffle_options(sol_json, distractors[:3], rng)

        rows.append({
            'id': f'{RULE_NAME}_{counter:04d}',
            'rule': RULE_NAME,
            'state': 'baseline',
            'puzzle': json.dumps({
                'capacities': [cap1, cap2], 'target': target, 'start': start,
            }),
            'question': _make_question(cap1, cap2, target, start),
            'option_A': opts['A'],
            'option_B': opts['B'],
            'option_C': opts['C'],
            'option_D': opts['D'],
            'correct_option': correct,
            'correct_answer': sol_json,
            'params': json.dumps({
                'cap1': cap1, 'cap2': cap2, 'target': target,
                'taxed': False,
                'path_length': len(classic_path),
                'has_taxed_distractor': (
                    taxed_path is not None and taxed_path != classic_path
                ),
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
