"""Multiple-choice question shuffling utilities."""


def shuffle_options(correct_answer, distractors, rng):
    """
    Shuffle correct_answer + 3 distractors into slots A–D.
    Returns ({"A": ..., "B": ..., "C": ..., "D": ...}, correct_letter).
    """
    all_options = [correct_answer] + list(distractors)
    rng.shuffle(all_options)
    letters = ['A', 'B', 'C', 'D']
    opts = {letters[i]: all_options[i] for i in range(4)}
    for letter, val in opts.items():
        if val == correct_answer:
            return opts, letter
    return opts, 'A'
