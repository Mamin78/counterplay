"""Puzzle generation for Entropy Jugs variants."""
import math
from .solver import bfs


def generate_classic(rng, seen=None):
    """
    Generate a unique classic water jug puzzle solvable in >= 3 states.

    Returns (cap1, cap2, target, start, path) or None if exhausted.
    """
    if seen is None:
        seen = set()

    for _ in range(30000):
        cap1 = rng.randint(3, 9)
        cap2 = rng.randint(3, 12)
        if cap1 > cap2:
            cap1, cap2 = cap2, cap1
        target = rng.randint(1, max(cap1, cap2) - 1)

        key = (cap1, cap2, target)
        if key in seen:
            continue

        path = bfs(cap1, cap2, [0, 0], target, taxed=False)
        if path is None or len(path) < 3:
            continue

        seen.add(key)
        return cap1, cap2, target, [0, 0], path

    return None


def generate_gcd_breaker(rng, seen=None):
    """
    Generate a GCD-breaker puzzle:
      - gcd(cap1, cap2) = g > 1 and target % g != 0
      - Provably unsolvable under classic rules (Bezout's theorem)
      - Solvable under Entropy Jugs taxed rules

    Returns (cap1, cap2, target, start, taxed_path, near_target, gcd_val) or None.
    """
    if seen is None:
        seen = set()

    # All (cap1, cap2) pairs with gcd > 1, cap1 <= cap2
    gcd_pairs = []
    for c1 in range(3, 11):
        for c2 in range(c1, 13):
            g = math.gcd(c1, c2)
            if g > 1:
                gcd_pairs.append((c1, c2, g))

    for _ in range(30000):
        cap1, cap2, g = rng.choice(gcd_pairs)

        non_multiples = [t for t in range(1, max(cap1, cap2))
                         if t % g != 0]
        if not non_multiples:
            continue
        target = rng.choice(non_multiples)

        key = (cap1, cap2, target)
        if key in seen:
            continue

        taxed_path = bfs(cap1, cap2, [0, 0], target, taxed=True)
        if taxed_path is None or len(taxed_path) < 2:
            continue

        near_target = _nearest_classic_target(cap1, cap2, target, g)
        seen.add(key)
        return cap1, cap2, target, [0, 0], taxed_path, near_target, g

    return None


def generate_entropy_trap(rng, seen=None):
    """
    Generate an entropy trap puzzle:
      - Both classic and taxed rules can reach the target
      - The optimal first move differs between the two rulesets
        OR the taxed path is >= 2 moves longer than the classic path

    Returns (cap1, cap2, target, start, taxed_path, classic_path,
             first_move_differs, len_diff) or None.
    """
    if seen is None:
        seen = set()

    for _ in range(30000):
        cap1 = rng.randint(3, 9)
        cap2 = rng.randint(3, 12)
        if cap1 > cap2:
            cap1, cap2 = cap2, cap1
        target = rng.randint(1, max(cap1, cap2) - 1)

        key = (cap1, cap2, target)
        if key in seen:
            continue

        classic_path = bfs(cap1, cap2, [0, 0], target, taxed=False)
        if classic_path is None or len(classic_path) < 3:
            continue

        taxed_path = bfs(cap1, cap2, [0, 0], target, taxed=True)
        if taxed_path is None or len(taxed_path) < 3:
            continue

        if classic_path == taxed_path:
            continue

        classic_moves = len(classic_path) - 1
        taxed_moves = len(taxed_path) - 1
        len_diff = taxed_moves - classic_moves

        first_move_differs = (classic_path[1] != taxed_path[1])

        if not first_move_differs and abs(len_diff) < 2:
            continue

        seen.add(key)
        return (cap1, cap2, target, [0, 0],
                taxed_path, classic_path, first_move_differs, len_diff)

    return None


def _nearest_classic_target(cap1, cap2, target, g):
    """Nearest target achievable under classic rules (multiple of gcd, reachable by BFS)."""
    max_t = max(cap1, cap2)
    for delta in range(1, max_t + 1):
        for t in [target - delta, target + delta]:
            if 1 <= t < max_t and t % g == 0:
                path = bfs(cap1, cap2, [0, 0], t, taxed=False)
                if path is not None:
                    return t
    return None
