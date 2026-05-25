"""Run all Checker Jumping generators."""
import subprocess, sys, os

generators = [
    "baseline/generate.py",
    "cf1_asymmetric/generate.py",
    "cf2_jump_two/generate.py",
    "cf3_two_empty/generate.py",
]

for g in generators:
    path = os.path.join(os.path.dirname(__file__), g)
    print(f"\n=== {g} ===")
    subprocess.run([sys.executable, path], check=True)
