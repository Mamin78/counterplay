"""Run all Entropy Jugs variant generators."""
import sys
import os
import argparse

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

import baseline.generate      as gen_baseline
import cf1_gcd_breaker.generate as gen_cf1
import cf2_entropy_trap.generate as gen_cf2

GENERATORS = [
    (gen_baseline, os.path.join(BASE, 'baseline',        'data')),
    (gen_cf1,      os.path.join(BASE, 'cf1_gcd_breaker', 'data')),
    (gen_cf2,      os.path.join(BASE, 'cf2_entropy_trap', 'data')),
]


def main():
    parser = argparse.ArgumentParser(description='Generate all Entropy Jugs CF datasets')
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--num-samples', type=int, default=100)
    args = parser.parse_args()

    for module, out_dir in GENERATORS:
        os.makedirs(out_dir, exist_ok=True)
        module.generate(args.seed, out_dir, args.num_samples)


if __name__ == '__main__':
    main()
