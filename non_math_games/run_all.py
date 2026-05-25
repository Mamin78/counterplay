"""Run all non-math game generators."""
import subprocess, sys, os

games = [
    "hanoi/run_all.py",
    "checker_jumping/run_all.py",
    "river_crossing/run_all.py",
]

for g in games:
    path = os.path.join(os.path.dirname(__file__), g)
    print(f"\n{'='*60}")
    print(f"  {g}")
    print(f"{'='*60}")
    subprocess.run([sys.executable, path], check=True)
