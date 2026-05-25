#!/usr/bin/env bash
# Regenerate every game's CSV from scratch, then rebuild the two unified dataset files.
#
# Usage:  ./scripts/regen_all.sh           # uses default seeds inside each generator
#         SEED=42 ./scripts/regen_all.sh   # exported var available to per-game runners
#
# Run from the project root.
set -euo pipefail

cd "$(dirname "$0")/.."

echo "=== game_cf ==="
for game_runner in \
    game_cf/sudoku/run_all.py \
    game_cf/cryptarithmetic/run_all.py \
    game_cf/entropy_jugs/run_all.py \
    game_cf/game24/run_all.py \
    game_cf/countdown/run_all.py; do
    echo ""
    echo "--- $game_runner ---"
    python3 "$game_runner"
done

echo ""
echo "=== non_math_games ==="
python3 non_math_games/run_all.py

echo ""
echo "=== Unified datasets ==="
python3 game_cf/build_game_dataset.py --out game_cf/dataset.csv
python3 scripts/build_non_math_games_dataset.py --out non_math_games/dataset.csv

echo ""
echo "Done. Frozen snapshots:"
echo "  game_cf/dataset.csv          (5 games: sudoku, cryptarithmetic, entropy_jugs, game24, countdown)"
echo "  non_math_games/dataset.csv   (3 games: hanoi, checker_jumping, river_crossing)"
