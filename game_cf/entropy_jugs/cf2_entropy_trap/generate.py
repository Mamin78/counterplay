"""CF2 — Entropy Trap: both rulesets can reach the target, but optimal paths diverge.

Selected puzzles satisfy at least one of:
  - The first optimal move differs between classic and taxed rules.
  - The taxed optimal path is ≥2 moves longer/shorter than the classic path.

The trap: a solver relying on classic intuition (e.g., "always fill the bigger
jug first") will choose the wrong first move and follow the wrong route.

Correct answer : BFS-optimal path under Entropy Jugs taxed rules.
Distractor 1   : BFS-optimal path under standard (lossless) rules — same target,
                 different sequence; individual pour transitions violate the tax rule.
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
from utils.generator import generate_entropy_trap
from utils.distractor import make_distractors
from utils.display import TAXED_RULES, puzzle_to_text
from utils.io_utils import write_csv
from utils.mcq import shuffle_options

RULE_NAME = 'entropy_jugs_cf2_entropy_trap'
NUM_SAMPLES = 100

RULE_DESC = (
    "You are playing Entropy Jugs — a variant of the classic Water Jug puzzle.\n"
    "Rules — allowed moves:\n"
    f"{TAXED_RULES}\n"
    "Goal: reach the exact target volume in either jug using the fewest moves."
)


def _make_question(cap1, cap2, target, start):
    setup = puzzle_to_text(cap1, cap2, target, start, taxed=True)
    return (
        f"{RULE_DESC}\n\n"
        f"Puzzle: {setup}\n\n"
        "Each answer option is a JSON list of [Jug_A, Jug_B] states "
        "representing the sequence of jug states from start to the goal state.\n"
        "Which option shows the correct (shortest) solution sequence under Entropy Jugs rules?\n"
        "Note: one option shows the solution obtained by applying standard "
        "Water Jug rules (no evaporation tax) — it reaches the target via a "
        "different route whose pour steps are inconsistent with the tax rule."
    )


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    seen = set()
    rows = []
    counter = 1

    while len(rows) < num_samples:
        result = generate_entropy_trap(rng, seen)
        if result is None:
            print("WARNING: exhausted puzzle space before reaching target count.")
            break
        (cap1, cap2, target, start,
         taxed_path, classic_path, first_move_differs, len_diff) = result

        exclude = [taxed_path, classic_path]

        other_distractors = make_distractors(
            cap1, cap2, target, taxed=True, rng=rng,
            count=3, exclude_paths=exclude,
        )

        # Classic path is always distractor 1 (the "normal solution")
        distractors = [json.dumps(classic_path)]
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
            'question': _make_question(cap1, cap2, target, start),
            'option_A': opts['A'],
            'option_B': opts['B'],
            'option_C': opts['C'],
            'option_D': opts['D'],
            'correct_option': correct,
            'correct_answer': sol_json,
            'params': json.dumps({
                'cap1': cap1, 'cap2': cap2, 'target': target,
                'taxed': True,
                'category': 'entropy_trap',
                'taxed_path_length': len(taxed_path),
                'classic_path_length': len(classic_path),
                'path_length_diff': len_diff,
                'first_move_differs': first_move_differs,
                'has_classic_distractor': True,
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
