"""Countdown CF4 — Two targets with a fixed 3+3 partition.

Six numbers are partitioned into Group A (3 numbers) and Group B (3 numbers).
Group A must reach target1 using all three of its numbers; Group B must
reach target2 using all three of its numbers.

CF invariant: target1 is reachable from Group A but NOT from Group B, and
target2 is reachable from Group B but NOT from Group A. A solver applying
the standard rule (any subset of all six → single target) would not respect
the partition.
"""
import sys
import os
import json
import argparse
import random
from fractions import Fraction
from itertools import combinations

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from utils.solver import (
    one_expression, reachable_from_numbers, one_expression_any_subset,
)
from utils.io_utils import write_csv
from utils.mcq import shuffle_options

RULE_NAME = 'countdown_cf4_multi_target'
NUM_SAMPLES = 100


RULE_DESC = (
    "Solve the following two-target Countdown-style puzzle.\n"
    "Rule change: there are **two targets** and a **fixed partition** of the six numbers "
    "into Group A (three numbers) and Group B (three numbers).\n"
    "  - Group A must reach target1 using each of its three numbers exactly once.\n"
    "  - Group B must reach target2 using each of its three numbers exactly once.\n"
    "  - Combine with +, −, ×, ÷ and parentheses; every intermediate division must be exact.\n"
    "  - You must produce **both** expressions; they will be shown as 'A: <expr> ; B: <expr>'."
)


def _normalize(expr):
    return expr.replace('*', '×').replace('/', '÷').replace('-', '−')


def _make_question(nums, group_a, target1, target2):
    ga = [nums[i] for i in group_a]
    gb = [nums[j] for j in range(6) if j not in group_a]
    return (
        f"{RULE_DESC}\n\n"
        f"All numbers: {nums}\n"
        f"Group A = {ga} → target1 = {target1}\n"
        f"Group B = {gb} → target2 = {target2}\n\n"
        "Which option correctly solves BOTH partitions?"
    )


def _ops_in(expr):
    return {ch for ch in expr if ch in '+-*/'}


def _nontrivial(nums3, target, expr):
    if len(set(nums3)) < 2:
        return False
    if target in {sum(nums3), nums3[0] * nums3[1] * nums3[2]}:
        return False
    return len(_ops_in(expr)) >= 2


def _format_pair(expr_a, expr_b):
    return f"A: {_normalize(expr_a)} ; B: {_normalize(expr_b)}"


def generate(seed, output_dir, num_samples=NUM_SAMPLES):
    rng = random.Random(seed)
    rows = []
    counter = 1
    seen = set()
    skips = 0

    while len(rows) < num_samples and skips < num_samples * 60:
        nums = [rng.randint(2, 9) for _ in range(6)]
        found = None
        partitions = list(combinations(range(6), 3))
        rng.shuffle(partitions)
        for grp_a in partitions:
            A = [nums[i] for i in grp_a]
            B = [nums[j] for j in range(6) if j not in grp_a]
            ra = [int(z) for z in reachable_from_numbers(A)
                  if z.denominator == 1 and 50 <= int(z) <= 900]
            rb = [int(z) for z in reachable_from_numbers(B)
                  if z.denominator == 1 and 50 <= int(z) <= 900]
            if len(ra) < 2 or len(rb) < 2:
                continue
            rng.shuffle(ra)
            rng.shuffle(rb)
            ra = ra[:8]
            rb = rb[:8]
            picked = False
            for t1 in ra:
                if picked:
                    break
                if Fraction(t1, 1) in reachable_from_numbers(B):
                    continue
                for t2 in rb:
                    if t2 == t1:
                        continue
                    if Fraction(t2, 1) in reachable_from_numbers(A):
                        continue
                    ex1 = one_expression(A, t1)
                    ex2 = one_expression(B, t2)
                    if ex1 is None or ex2 is None:
                        continue
                    if not _nontrivial(A, t1, ex1) or not _nontrivial(B, t2, ex2):
                        continue
                    found = (grp_a, t1, t2, ex1, ex2, A, B)
                    picked = True
                    break
            if picked:
                break

        if found is None:
            skips += 1
            continue

        grp_a, t1, t2, ex1, ex2, A, B = found
        key = (tuple(sorted(nums)), tuple(sorted(grp_a)), t1, t2)
        if key in seen:
            skips += 1
            continue

        correct_pair = _format_pair(ex1, ex2)

        # Distractor 1 (preferred wrong-rule foil): single expression on all six
        # numbers reaching a single target — ignores the partition entirely.
        wrong_rule_distractor = None
        single_target = t1 + t2
        for tgt in (single_target, t1, t2):
            cand = one_expression_any_subset(nums, tgt, None)
            if cand is not None:
                disp = f"All six → {tgt}: {_normalize(cand)}"
                if disp != correct_pair:
                    wrong_rule_distractor = disp
                    break

        # Distractor 2: swap the targets (A solves t2, B solves t1) — only valid
        # if both inverse expressions exist. By the divergence filter t1 is NOT
        # reachable in B and t2 is NOT reachable in A, so this swap is unsolvable
        # and the displayed pair is invalid. Generate the *attempt* as a string.
        # If no inverse is reachable we synthesise a near-miss pair instead.
        ex1_swap = one_expression(B, t1)
        ex2_swap = one_expression(A, t2)
        swap_distractor = None
        if ex1_swap is not None or ex2_swap is not None:
            # At least one swap "works" but the pair is still invalid because the
            # other half can't be reached — we mark it explicitly.
            placeholder_a = _normalize(ex2_swap) if ex2_swap is not None else f"({A[0]} + {A[1]} + {A[2]})"
            placeholder_b = _normalize(ex1_swap) if ex1_swap is not None else f"({B[0]} + {B[1]} + {B[2]})"
            swap_distractor = f"A→{t2}: {placeholder_a} ; B→{t1}: {placeholder_b}"

        # Distractor 3: A reaches target1 correctly but B's expression does not hit target2.
        if (B[0] + B[1] + B[2]) != t2:
            fake_ex_b = f"({B[0]} + {B[1]} + {B[2]})"
        else:
            fake_ex_b = f"({B[0]} × {B[1]} − {B[2]})"
        partial_distractor = f"A: {_normalize(ex1)} ; B: {fake_ex_b}"

        # Final distractor: both wrong (sum-only)
        sum_a = f"({A[0]} + {A[1]} + {A[2]})"
        sum_b = f"({B[0]} + {B[1]} + {B[2]})"
        sum_distractor = f"A: {sum_a} ; B: {sum_b}"

        candidates = []
        if wrong_rule_distractor is not None:
            candidates.append(wrong_rule_distractor)
        if swap_distractor is not None:
            candidates.append(swap_distractor)
        candidates.append(partial_distractor)
        candidates.append(sum_distractor)

        # Pick 3 distinct distractors all different from correct.
        distractors = []
        for c in candidates:
            if c == correct_pair:
                continue
            if c in distractors:
                continue
            distractors.append(c)
            if len(distractors) == 3:
                break
        if len(distractors) < 3:
            skips += 1
            continue

        all_opts = [correct_pair] + distractors
        if len(set(all_opts)) != 4:
            skips += 1
            continue

        seen.add(key)
        opts, correct = shuffle_options(correct_pair, distractors, rng)

        rows.append({
            'id': f'{RULE_NAME}_{counter:04d}',
            'rule': RULE_NAME,
            'state': 'counterfactual',
            'puzzle': json.dumps({
                'numbers': nums, 'group_a': list(grp_a),
                'target1': t1, 'target2': t2,
            }),
            'question': _make_question(nums, grp_a, t1, t2),
            'option_A': opts['A'],
            'option_B': opts['B'],
            'option_C': opts['C'],
            'option_D': opts['D'],
            'correct_option': correct,
            'correct_answer': correct_pair,
            'params': json.dumps({
                'numbers': nums, 'group_a': list(grp_a),
                'target1': t1, 'target2': t2,
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
