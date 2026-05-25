"""Run all Sudoku variant generators."""
import sys
import os
import argparse

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import baseline.generate      as gen_baseline
import cf1_double8.generate   as gen_cf1
import cf2_shifted_boxes.generate as gen_cf2
import cf3_11to19.generate    as gen_cf3
import cf4_hex.generate       as gen_cf4

GENERATORS = [
    (gen_baseline, os.path.join(BASE, 'baseline',          'data')),
    (gen_cf1,      os.path.join(BASE, 'cf1_double8',       'data')),
    (gen_cf2,      os.path.join(BASE, 'cf2_shifted_boxes', 'data')),
    (gen_cf3,      os.path.join(BASE, 'cf3_11to19',        'data')),
    (gen_cf4,      os.path.join(BASE, 'cf4_hex',           'data')),
]


def main():
    parser = argparse.ArgumentParser(description='Generate all Sudoku CF datasets')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--num-samples', type=int, default=100)
    args = parser.parse_args()

    for module, out_dir in GENERATORS:
        os.makedirs(out_dir, exist_ok=True)
        module.generate(args.seed, out_dir, args.num_samples)


if __name__ == '__main__':
    main()
