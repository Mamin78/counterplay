# Counterplay — A Counterfactual Game Benchmark for LLMs

Counterplay is a benchmark for evaluating how language models reason about
familiar games under *counterfactual* (CF) rule changes. Each game has a
baseline (standard rules) plus one or more CF variants where the rules are
altered (e.g. Sudoku on a hex grid, Hanoi with 4 pegs, Game of 24 in base 9).
Strong models that have memorized standard-rule solutions are forced to
*re-reason* under the perturbed rules.

The repo ships both the **generators** (so anyone can reproduce or extend the
benchmark) and a **frozen snapshot** of the generated dataset (for citing an
exact version).

## Games

Eight games, two task formats:

### MCQ games (`game_cf/`) — 2,100 items

| Game             | Variants                                                     | Items |
|------------------|--------------------------------------------------------------|------:|
| Sudoku           | baseline, cf1_double8, cf2_shifted_boxes, cf3_11to19, cf4_hex| 500 |
| Cryptarithmetic  | baseline, cf1_base9_add, cf2_base9_sub, cf3_base9_mixed      | 400 |
| Entropy jugs     | baseline, cf1_gcd_breaker, cf2_entropy_trap                  | 300 |
| Game of 24       | baseline, cf1_base9, cf2_each_operator_once, cf3_prime_target| 400 |
| Countdown        | baseline, cf1_base9, cf2_no_subtraction, cf3_use_all_numbers, cf4_multi_target | 500 |

Each row is a 4-option multiple-choice question with a single correct answer.
Schema: `id, rule, state, puzzle, question, option_A..D, correct_option,
correct_answer, params`.

### Open-ended games (`non_math_games/`) — 53 items

| Game             | Variants                                                     | Items |
|------------------|--------------------------------------------------------------|------:|
| Tower of Hanoi   | baseline (3-peg), cf1_four_pegs, cf2_adjacent                |  18 |
| Checker jumping  | baseline, cf1_asymmetric, cf2_jump_two, cf3_two_empty        |  27 |
| River crossing   | baseline, cf1_neutral                                        |   8 |

Each row asks the model to produce a full solution path (sequence of moves).
Schema: `id, game, variant, n, params, initial_state, goal_state, solution,
num_moves`. The `solution` column is the ground-truth path; never show it to
the model.

## Repo layout

```
counterplay/
├── game_cf/                        # 5 MCQ games — generators + frozen CSVs
│   ├── <game>/
│   │   ├── baseline/  cfN_*/       # one folder per variant
│   │   │   ├── generate.py
│   │   │   └── data/<variant>.csv
│   │   ├── utils/                  # per-game solver, distractors, MCQ shuffler
│   │   └── run_all.py
│   ├── build_game_dataset.py       # merges per-variant CSVs -> game_cf/dataset.csv
│   └── dataset.csv                 # frozen snapshot, 2,100 rows
│
├── non_math_games/                 # 3 open-ended games — generators + frozen CSVs
│   ├── <game>/
│   │   ├── baseline/  cfN_*/
│   │   │   ├── generate.py
│   │   │   └── data/<game>_<variant>.csv
│   │   ├── utils/                  # per-game state machine + solver
│   │   └── run_all.py
│   ├── run_all.py                  # runs every generator
│   └── validate_all.py             # ground-truth correctness checks
│
├── non_math_games_eval/            # eval pipeline for the open-ended games
│   ├── prompts/                    # per-game prompt builders
│   ├── parsers/                    # per-game response parsers (text -> moves)
│   ├── graders/                    # per-game graders (moves -> valid / goal_reached)
│   ├── build_prompts.py            # data CSV -> prompts CSV
│   ├── run_vertex.py               # run models via Vertex AI Model Garden
│   ├── evaluate.py                 # score responses
│   └── aggregate.py                # pass@k aggregation
│
└── scripts/
    ├── regen_all.sh                # regenerate every game and rebuild unified CSVs
    └── build_non_math_games_dataset.py
```

## Quick start

### Install

```bash
pip install -r requirements.txt
```

Eval-only dependencies (`openai`, `google-auth`, `google-cloud-aiplatform`,
`tqdm`) are listed in the same file; remove them if you only need to read
the dataset.

### Read the benchmark

```python
import pandas as pd

mcq  = pd.read_csv("game_cf/dataset.csv")          # 2,100 MCQ rows
open = pd.read_csv("non_math_games/dataset.csv")   # 53 open-ended rows (after regen, see below)
```

### Regenerate from scratch

```bash
./scripts/regen_all.sh
```

This calls every game's `run_all.py`, then rebuilds the two unified dataset
CSVs. Generators are seeded — re-running produces byte-identical CSVs.

### Run the LLM evaluation (open-ended games)

The `non_math_games_eval/` pipeline targets Google Vertex AI Model Garden
(Gemini and third-party MaaS endpoints).

```bash
export GOOGLE_CLOUD_PROJECT=<your-gcp-project>
gcloud auth application-default login

python non_math_games_eval/run_vertex.py \
    --model gemini-2.5-flash \
    --all --runs 5 \
    --out results/
python non_math_games_eval/evaluate.py --responses results/_all_results.csv \
    --data <data_csv> --output results/_all_scored.csv
```

A self-test that runs every ground-truth solution through the grader (no
model calls):

```bash
python non_math_games_eval/evaluate.py --self-test --all
```

For the MCQ games (`game_cf/`), the correct option is already in the CSV and
any standard MCQ-scoring harness works — there is no game-specific eval code.

## Design notes

- **MCQ vs open-ended.** MCQ games trap the model with a wrong-rule distractor:
  one option is correct under the CF rule, another is correct under the
  standard rule, and the remaining two are plausible-but-wrong. Open-ended
  games require the model to output an entire solution path that the grader
  validates move-by-move.

- **Structural CFs.** Some CFs constrain the *form* of the answer rather than
  the value (e.g. `countdown/cf2_no_subtraction`, `game24/cf2_each_operator_once`).
  The MCQ correct option satisfies both the value and the structural rule;
  the trap distractor satisfies only the value.

- **Reproducibility.** Generators use `--seed 42` by default. The CSVs in
  this repo are the canonical seeded snapshot.

- **No chess.** An earlier version of this work included chess opening
  legality. It was dropped: chess questions devolved into "is this opening
  legal?" which is largely a tokenization / memorization task rather than a
  reasoning task. The remaining 8 games all admit verifiable solutions.

## License

This repository is dual-licensed:

- **Code** (Python source, scripts) — [MIT License](LICENSE-CODE)
- **Dataset** (all `*.csv` files under `game_cf/` and `non_math_games/`) — [Creative Commons Attribution 4.0 International (CC BY 4.0)](LICENSE-DATA)

If you use this benchmark, please cite the thesis (citation TBD).
