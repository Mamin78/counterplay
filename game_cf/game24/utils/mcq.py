"""MCQ shuffling helper."""


def shuffle_options(correct_answer, distractors, rng):
    all_options = [correct_answer] + list(distractors)
    if len(set(str(o) for o in all_options)) != 4:
        raise ValueError(
            f"shuffle_options requires 4 distinct values, got {all_options!r}"
        )
    rng.shuffle(all_options)
    letters = ['A', 'B', 'C', 'D']
    options_dict = {letters[i]: all_options[i] for i in range(4)}
    correct_letter = None
    for letter, val in options_dict.items():
        if val == correct_answer:
            correct_letter = letter
            break
    return options_dict, correct_letter
