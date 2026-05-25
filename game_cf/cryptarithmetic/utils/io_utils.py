"""CSV output for cryptarithmetic counterfactual items."""
import csv
import os

COLUMNS = [
    'id', 'rule', 'state', 'puzzle', 'question',
    'option_A', 'option_B', 'option_C', 'option_D',
    'correct_option', 'correct_answer', 'params',
]


def write_csv(rows, output_path):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
