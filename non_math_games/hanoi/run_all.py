"""Run all Tower of Hanoi generators."""
import subprocess, sys, os

generators = [
    "baseline/generate.py",
    "cf1_four_pegs/generate.py",
    "cf2_adjacent/generate.py",
]

for g in generators:
    path = os.path.join(os.path.dirname(__file__), g)
    print(f"\n=== {g} ===")
    subprocess.run([sys.executable, path], check=True)
