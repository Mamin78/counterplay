"""CSV writer matching the format used by sibling games."""
import csv
import os

COLUMNS = [
    'id', 'rule', 'state', 'puzzle', 'question',
    'option_A', 'option_B', 'option_C', 'option_D',
    'correct_option', 'correct_answer', 'params',
]


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'w', newline='', encoding='utf-8') as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, '') for k in COLUMNS})
