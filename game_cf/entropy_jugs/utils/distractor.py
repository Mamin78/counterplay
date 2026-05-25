"""Distractor path generation for Entropy Jugs MCQ items.

All distractors are paths that look plausible but are wrong in one of two ways:
  1. Wrong final state — path reaches a different target amount (same or opposite ruleset).
  2. Wrong rule application — path reaches the correct target but follows the
     opposite ruleset's pour logic (so individual transitions are inconsistent
     with the stated rules).

Strategy order:
  1. BFS to adjacent targets (T±1, T±2, ...) under the SAME ruleset.
  2. BFS to the correct target under the OPPOSITE ruleset.
  3. BFS to adjacent targets under the OPPOSITE ruleset (fill remaining slots).
"""
from .solver import bfs


def make_distractors(cap1, cap2, target, taxed=False, rng=None,
                     count=3, exclude_paths=None):
    """Return up to `count` distinct distractor paths.

    exclude_paths: list of already-used paths to skip.
    """
    if exclude_paths is None:
        exclude_paths = []

    exclude_set = {_key(p) for p in exclude_paths}
    distractors = []

    # Strategy 1: adjacent targets, same ruleset
    for delta in [1, -1, 2, -2, 3, -3, 4, -4]:
        if len(distractors) >= count:
            break
        t2 = target + delta
        if t2 <= 0 or t2 >= max(cap1, cap2) or t2 == target:
            continue
        path = bfs(cap1, cap2, [0, 0], t2, taxed=taxed)
        if path is None:
            continue
        # Skip if this path also solves the original target
        if target in path[-1]:
            continue
        if _key(path) not in exclude_set:
            distractors.append(path)
            exclude_set.add(_key(path))

    # Strategy 2: correct target, opposite ruleset
    if len(distractors) < count:
        opposite = bfs(cap1, cap2, [0, 0], target, taxed=not taxed)
        if opposite is not None and _key(opposite) not in exclude_set:
            distractors.append(opposite)
            exclude_set.add(_key(opposite))

    # Strategy 3: adjacent targets, opposite ruleset
    for delta in [1, -1, 2, -2, 3, -3, 4, -4]:
        if len(distractors) >= count:
            break
        t2 = target + delta
        if t2 <= 0 or t2 >= max(cap1, cap2) or t2 == target:
            continue
        path = bfs(cap1, cap2, [0, 0], t2, taxed=not taxed)
        if path is None:
            continue
        if target in path[-1]:
            continue
        if _key(path) not in exclude_set:
            distractors.append(path)
            exclude_set.add(_key(path))

    return distractors[:count]


def _key(path):
    return str(path)
