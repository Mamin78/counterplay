"""BFS solvers for classic and Entropy Jugs (taxed) water jug problems.

Classic pour: exact transfer, no loss.
Taxed pour (Entropy Jugs):
    Amount removed from source = min(Source, TargetSpace + 1)
    Amount added to target     = max(0, AmountRemoved - 1)
"""
from collections import deque


def _pour_classic(state, cap1, cap2, src, tgt):
    s = list(state)
    caps = [cap1, cap2]
    amount = min(s[src], caps[tgt] - s[tgt])
    if amount == 0:
        return None
    s[src] -= amount
    s[tgt] += amount
    return tuple(s)


def _pour_taxed(state, cap1, cap2, src, tgt):
    s = list(state)
    caps = [cap1, cap2]
    t_space = caps[tgt] - s[tgt]
    amount_removed = min(s[src], t_space + 1)
    if amount_removed == 0:
        return None
    amount_added = max(0, amount_removed - 1)
    s[src] -= amount_removed
    s[tgt] += amount_added
    return tuple(s)


def bfs(cap1, cap2, start, target, taxed=False, max_depth=60):
    """
    BFS shortest path from start to any state containing target.

    Returns list of [jug_a, jug_b] states (including start), or None.
    """
    start = tuple(start)
    pour_fn = _pour_taxed if taxed else _pour_classic

    if target in start:
        return [list(start)]

    visited = {start}
    queue = deque([(start, [start])])

    while queue:
        state, path = queue.popleft()

        if len(path) > max_depth:
            continue

        candidates = []

        # Fill jug A to capacity
        if state[0] < cap1:
            candidates.append((cap1, state[1]))
        # Fill jug B to capacity
        if state[1] < cap2:
            candidates.append((state[0], cap2))
        # Empty jug A
        if state[0] > 0:
            candidates.append((0, state[1]))
        # Empty jug B
        if state[1] > 0:
            candidates.append((state[0], 0))
        # Pour A -> B
        if state[0] > 0 and state[1] < cap2:
            ns = pour_fn(state, cap1, cap2, 0, 1)
            if ns is not None:
                candidates.append(ns)
        # Pour B -> A
        if state[1] > 0 and state[0] < cap1:
            ns = pour_fn(state, cap1, cap2, 1, 0)
            if ns is not None:
                candidates.append(ns)

        for ns in candidates:
            if ns in visited:
                continue
            new_path = path + [ns]
            if target in ns:
                return [list(s) for s in new_path]
            visited.add(ns)
            queue.append((ns, new_path))

    return None
