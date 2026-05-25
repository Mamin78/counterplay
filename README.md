# Counterplay  

Counterplay is a benchmark for evaluating how language models reason about
familiar games under *counterfactual* (CF) rule changes. Each game has a
baseline (standard rules) plus one or more CF variants where the rules are
altered (e.g. Sudoku on a hex grid, Hanoi with 4 pegs, Game of 24 in base 9).
Strong models that have memorized standard-rule solutions are forced to
*re-reason* under the perturbed rules.

Every task is **open-ended**: the model reads the puzzle and produces the
answer directly, which is verified by a programmatic checker. 
The repo ships both the **generators** (so anyone can reproduce or extend the
benchmark) and a **frozen snapshot** of the generated dataset (for citing an
exact version).

## Games

Eight games, two answer formats:

### Puzzle games (`game_cf/`) — 2,100 items

Model outputs a structured answer (filled grid, letter-to-digit map, jug
states, arithmetic expression …) wrapped in `<answer>...</answer>` tags. A
per-game checker validates the answer against `correct_answer`.

| Game             | Variants                                                                       | Items |
|------------------|--------------------------------------------------------------------------------|------:|
| Sudoku           | baseline, cf1_double8, cf2_shifted_boxes, cf3_11to19, cf4_hex                  | 500 |
| Cryptarithmetic  | baseline, cf1_base9_add, cf2_base9_sub, cf3_base9_mixed                        | 400 |
| Entropy jugs     | baseline, cf1_gcd_breaker, cf2_entropy_trap                                    | 300 |
| Game of 24       | baseline, cf1_base9, cf2_each_operator_once, cf3_prime_target                  | 400 |
| Countdown        | baseline, cf1_base9, cf2_no_subtraction, cf3_use_all_numbers, cf4_multi_target | 500 |

Schema: `row_id, game, variant, rule, state, puzzle, question, correct_answer, params`.

Expected answer format by game:

| Game             | Answer format                                                            |
|------------------|--------------------------------------------------------------------------|
| Sudoku           | 2D JSON array (9×9, or 16×16 for `cf4_hex`)                              |
| Cryptarithmetic  | JSON object mapping letter → digit, e.g. `{"A": 1, "B": 5, …}`           |
| Entropy jugs     | JSON list of `[jug_A, jug_B]` states from start to goal                  |
| Game of 24       | Arithmetic expression evaluating to 24                                   |
| Countdown        | Arithmetic expression evaluating to the target (two for `cf4_multi_target`) |

### Path games (`non_math_games/`) — 53 items

Model outputs a sequence of moves leading from `initial_state` to
`goal_state`. A per-game grader validates each move and confirms goal
reachability.

| Game             | Variants                                                | Items |
|------------------|---------------------------------------------------------|------:|
| Tower of Hanoi   | baseline (3-peg), cf1_four_pegs, cf2_adjacent           |  18 |
| Checker jumping  | baseline, cf1_asymmetric, cf2_jump_two, cf3_two_empty   |  27 |
| River crossing   | baseline, cf1_neutral                                   |   8 |

Schema: `row_id, game, variant, n, params, initial_state, goal_state, solution, num_moves`.
The `solution` column is the ground-truth move sequence; never show it to
the model.

## Repo layout

```
counterplay/
├── game_cf/                        # 5 puzzle games — generators + frozen CSVs
│   ├── <game>/
│   │   ├── baseline/  cfN_*/       # one folder per variant
│   │   │   ├── generate.py
│   │   │   └── data/<variant>.csv  # open-ended schema (MCQ columns stripped)
│   │   ├── utils/                  # per-game solver and helpers
│   │   └── run_all.py
│   ├── build_game_dataset.py       # merge per-variant CSVs -> game_cf/dataset.csv
│   └── dataset.csv                 # frozen snapshot, 2,100 rows
│
├── non_math_games/                 # 3 path games — generators + frozen CSVs
│   ├── <game>/
│   │   ├── baseline/  cfN_*/
│   │   │   ├── generate.py
│   │   │   └── data/<game>_<variant>.csv
│   │   ├── utils/                  # per-game state machine + solver
│   │   └── run_all.py
│   ├── run_all.py
│   ├── validate_all.py             # ground-truth correctness checks
│   └── dataset.csv                 # frozen snapshot, 53 rows
│
├── llm_eval/
│   └── evaluate_games_open.py      # open-ended evaluator for game_cf (OpenRouter)
│
├── non_math_games_eval/            # open-ended evaluator for non_math_games (Vertex)
│   ├── prompts/  parsers/  graders/
│   ├── build_prompts.py
│   ├── run_vertex.py
│   ├── evaluate.py
│   └── aggregate.py
│
└── scripts/
    ├── regen_all.sh                # regenerate every game and rebuild unified CSVs
    ├── build_non_math_games_dataset.py
    └── strip_mcq_from_game_cf.py   # post-process generator output to open-ended schema
```

## Quick start

### Install

```bash
pip install -r requirements.txt
```

If you only want to read the dataset, just `pandas` is enough.

### Read the benchmark

```python
import pandas as pd

puzzles = pd.read_csv("game_cf/dataset.csv")          # 2,100 puzzle rows
paths   = pd.read_csv("non_math_games/dataset.csv")   #   53 path rows
```

### Regenerate from scratch

```bash
./scripts/regen_all.sh
```

This calls every game's `run_all.py`, runs `strip_mcq_from_game_cf.py` to
remove the generators' MCQ-shaped columns and prompt residue, then rebuilds
the two unified dataset CSVs. Generators are seeded; re-running with the same
seed produces byte-identical CSVs.

> The generators still emit MCQ-shaped CSVs internally (`option_A..D`,
> `correct_option`) because the original design used multiple choice. The
> strip step is what converts them to the open-ended schema shipped here.
> If you bypass `regen_all.sh` and call the per-game `run_all.py` directly,
> run `python scripts/strip_mcq_from_game_cf.py` afterwards.

### Run the open-ended evaluation

**Puzzle games (`game_cf/`) — OpenRouter:**

```bash
export OPENROUTER_API_KEY=<your-key>

python llm_eval/evaluate_games_open.py \
    --csv "game_cf/*/*/data/*.csv" \
    --model anthropic/claude-sonnet-4.6 openai/gpt-5 \
    --api_key "$OPENROUTER_API_KEY" \
    --out results/game_cf_open.csv
```

The evaluator builds the prompt from the `puzzle` and `question` columns,
asks the model to wrap its final answer in `<answer>…</answer>`, parses it,
and validates against `correct_answer` using game-specific checkers.

**Path games (`non_math_games/`) — Google Vertex AI:**

```bash
export GOOGLE_CLOUD_PROJECT=<your-gcp-project>
gcloud auth application-default login

python non_math_games_eval/run_vertex.py \
    --model gemini-2.5-flash \
    --all --runs 5 \
    --out results/non_math_games/

python non_math_games_eval/evaluate.py \
    --responses results/non_math_games/_all_results.csv \
    --data <data_csv> \
    --output results/non_math_games/_all_scored.csv
```

A self-test that runs every ground-truth solution through the grader (no
model calls):

```bash
python non_math_games_eval/evaluate.py --self-test --all
```

## License

This repository is dual-licensed:

- **Code** (Python source, scripts) — [MIT License](LICENSE-CODE)
- **Dataset** (all `*.csv` files under `game_cf/` and `non_math_games/`) — [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE-DATA)

If you use this benchmark, please cite the thesis (citation TBD).
