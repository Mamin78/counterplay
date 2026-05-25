"""Game of 24: combine four integers with + − × ÷ (each number once, any parenthesization)."""
from __future__ import annotations

from fractions import Fraction
from functools import lru_cache
from itertools import permutations, product
from typing import FrozenSet, List, Optional, Set, Tuple

OPS = ("+", "-", "*", "/")


def _apply(op, x, y):
    if op == "+":
        return x + y
    if op == "-":
        return x - y
    if op == "*":
        return x * y
    if op == "/":
        if y == 0:
            return None
        q = x / y
        if q.denominator != 1:
            return None
        return q
    return None


def _frac_state(nums):
    return tuple(sorted((x.numerator, x.denominator) for x in nums))


@lru_cache(maxsize=262144)
def _all_results_mem(state):
    nums = [Fraction(p, q) for p, q in state]
    if len(nums) == 1:
        return frozenset([(nums[0].numerator, nums[0].denominator)])
    out = set()
    n = len(nums)
    for i in range(n):
        for j in range(i + 1, n):
            a, b = nums[i], nums[j]
            rest = [nums[k] for k in range(n) if k not in (i, j)]
            for op in OPS:
                for z in (_apply(op, a, b), _apply(op, b, a)):
                    if z is None:
                        continue
                    nxt = _frac_state(rest + [z])
                    out |= _all_results_mem(nxt)
    return frozenset(out)


@lru_cache(maxsize=8192)
def _reachable_targets_tuple(nums_t):
    targets = set()
    for perm in permutations(nums_t):
        fr = [Fraction(p, 1) for p in perm]
        for p, q in _all_results_mem(_frac_state(fr)):
            targets.add((p, q))
    return frozenset(targets)


def reachable_targets(nums):
    pairs = _reachable_targets_tuple(tuple(sorted(nums)))
    return {Fraction(p, q) for p, q in pairs}


def solvable_for_target(nums, target):
    return Fraction(target, 1) in reachable_targets(nums)


def solvable_for_24(nums):
    return solvable_for_target(nums, 24)


def one_solution_expression(nums, target):
    t = Fraction(target, 1)

    def search(vals):
        if len(vals) == 1:
            return vals[0][1] if vals[0][0] == t else None
        m = len(vals)
        for i in range(m):
            for j in range(i + 1, m):
                (a, sa), (b, sb) = vals[i], vals[j]
                rest = [vals[k] for k in range(m) if k not in (i, j)]
                for op in OPS:
                    for z, e0, e1 in (
                        (_apply(op, a, b), sa, sb),
                        (_apply(op, b, a), sb, sa),
                    ):
                        if z is None:
                            continue
                        r = search(rest + [(z, f"({e0} {op} {e1})")])
                        if r:
                            return r
        return None

    for perm in permutations(nums):
        start = [(Fraction(p, 1), str(p)) for p in perm]
        e = search(start)
        if e:
            return e
    return None


def _five_shapes(vals, ops):
    a, b, c, d = vals
    o0, o1, o2 = ops
    out = set()

    def add(z):
        if z is not None:
            out.add(z)

    z01 = _apply(o0, a, b)
    if z01 is not None:
        z012 = _apply(o1, z01, c)
        if z012 is not None:
            add(_apply(o2, z012, d))
    z12 = _apply(o1, b, c)
    if z12 is not None:
        z02 = _apply(o0, a, z12)
        if z02 is not None:
            add(_apply(o2, z02, d))
    z01b = _apply(o0, a, b)
    z23 = _apply(o2, c, d)
    if z01b is not None and z23 is not None:
        add(_apply(o1, z01b, z23))
    z12c = _apply(o1, b, c)
    if z12c is not None:
        z123 = _apply(o2, z12c, d)
        if z123 is not None:
            add(_apply(o0, a, z123))
    z23d = _apply(o2, c, d)
    if z23d is not None:
        z123b = _apply(o1, b, z23d)
        if z123b is not None:
            add(_apply(o0, a, z123b))
    return out


def has_solution_with_three_distinct_ops(nums, target=24):
    """Solvable using three pairwise-different operator symbols across the three steps."""
    t = Fraction(target, 1)
    for perm in permutations(nums):
        vals = tuple(Fraction(p, 1) for p in perm)
        for op_triple in product(OPS, repeat=3):
            if len(set(op_triple)) < 3:
                continue
            if t in _five_shapes(vals, op_triple):
                return True
    return False


def one_expression_three_distinct_ops(nums, target=24):
    """Return one solution where the three binary operators are pairwise different."""
    t = Fraction(target, 1)
    for perm in permutations(nums):
        a, b, c, d = (Fraction(p, 1) for p in perm)
        sa, sb, sc, sd = (str(p) for p in perm)
        for op_triple in product(OPS, repeat=3):
            if len(set(op_triple)) < 3:
                continue
            o0, o1, o2 = op_triple
            z01 = _apply(o0, a, b)
            if z01 is not None:
                z012 = _apply(o1, z01, c)
                if z012 is not None:
                    zf = _apply(o2, z012, d)
                    if zf == t:
                        return f"(({sa} {o0} {sb}) {o1} {sc}) {o2} {sd}"
            z12 = _apply(o1, b, c)
            if z12 is not None:
                z02 = _apply(o0, a, z12)
                if z02 is not None and _apply(o2, z02, d) == t:
                    return f"({sa} {o0} ({sb} {o1} {sc})) {o2} {sd}"
            z01b = _apply(o0, a, b)
            z23 = _apply(o2, c, d)
            if z01b is not None and z23 is not None and _apply(o1, z01b, z23) == t:
                return f"({sa} {o0} {sb}) {o1} ({sc} {o2} {sd})"
            z12c = _apply(o1, b, c)
            if z12c is not None:
                z123 = _apply(o2, z12c, d)
                if z123 is not None and _apply(o0, a, z123) == t:
                    return f"{sa} {o0} (({sb} {o1} {sc}) {o2} {sd})"
            z23d = _apply(o2, c, d)
            if z23d is not None:
                z123b = _apply(o1, b, z23d)
                if z123b is not None and _apply(o0, a, z123b) == t:
                    return f"{sa} {o0} ({sb} {o1} ({sc} {o2} {sd}))"
    return None
