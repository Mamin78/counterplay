"""Run all countdown generators (baseline + 4 CFs)."""
import argparse
import importlib.util
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))

GENERATORS = [
    ('baseline', 'baseline/generate.py'),
    ('cf1_base9', 'cf1_base9/generate.py'),
    ('cf2_no_subtraction', 'cf2_no_subtraction/generate.py'),
    ('cf3_use_all_numbers', 'cf3_use_all_numbers/generate.py'),
    ('cf4_multi_target', 'cf4_multi_target/generate.py'),
]


def _run(path, seed, num_samples):
    spec = importlib.util.spec_from_file_location('gen_mod', os.path.join(HERE, path))
    mod = importlib.util.module_from_spec(spec)
    sys.path.insert(0, os.path.dirname(os.path.join(HERE, path)))
    try:
        spec.loader.exec_module(mod)
        out_dir = os.path.join(os.path.dirname(os.path.join(HERE, path)), 'data')
        mod.generate(seed, out_dir, num_samples)
    finally:
        sys.path.pop(0)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--num-samples', type=int, default=100)
    args = parser.parse_args()
    for name, path in GENERATORS:
        print(f"--- countdown/{name} ---")
        _run(path, args.seed, args.num_samples)


if __name__ == '__main__':
    main()
