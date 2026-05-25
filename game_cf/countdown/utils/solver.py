"""Countdown-style combinatorial search (subset of numbers, + − × ÷, exact integer division)."""
from __future__ import annotations

import random
from fractions import Fraction
from functools import lru_cache
from itertools import combinations
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


@lru_cache(maxsize=524288)
def _all_results_mem(state, ops_frozen):
    allowed_ops = set(ops_frozen)
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
                if op not in allowed_ops:
                    continue
                for z in (_apply(op, a, b), _apply(op, b, a)):
                    if z is None:
                        continue
                    nxt = _frac_state(rest + [z])
                    out |= _all_results_mem(nxt, ops_frozen)
    return frozenset(out)


def _all_results(nums, allowed_ops=None):
    if allowed_ops is None:
        allowed_ops = set(OPS)
    return {Fraction(p, q) for p, q in _all_results_mem(_frac_state(nums), frozenset(allowed_ops))}


def reachable_from_numbers(numbers, allowed_ops=None):
    return _all_results([Fraction(n, 1) for n in numbers], allowed_ops)


def can_hit_target(numbers, target, allowed_ops=None):
    t = Fraction(target, 1)
    n = len(numbers)
    for r in range(1, n + 1):
        for subset in combinations(range(n), r):
            vals = [numbers[i] for i in subset]
            if t in reachable_from_numbers(vals, allowed_ops):
                return True
    return False


def subtraction_matters_for_some_subset(numbers, target):
    """Some subset hits target with full ops but not without subtraction."""
    no_sub = {"+", "*", "/"}
    n = len(numbers)
    t = Fraction(target, 1)
    for r in range(1, n + 1):
        for subset in combinations(range(n), r):
            vals = [numbers[i] for i in subset]
            if t in reachable_from_numbers(vals) and t not in reachable_from_numbers(vals, no_sub):
                return True
    return False


def no_subtraction_slice_diverges(numbers, target):
    """CF (no subtraction globally) solvable AND subtraction genuinely matters on some subset."""
    return can_hit_target(numbers, target, {"+", "*", "/"}) and subtraction_matters_for_some_subset(numbers, target)


def strict_subset_solution_exists(numbers, target):
    """Exact hit using a proper subset (not all numbers)."""
    t = Fraction(target, 1)
    n = len(numbers)
    for r in range(1, n):
        for subset in combinations(range(n), r):
            vals = [numbers[i] for i in subset]
            if t in reachable_from_numbers(vals):
                return True
    return False


def use_all_numbers_matters(numbers, target):
    """Exact hit with all numbers exists AND some hit with a strict subset exists."""
    if len(numbers) != 6:
        return False
    t = Fraction(target, 1)
    if not strict_subset_solution_exists(numbers, target):
        return False
    return t in reachable_from_numbers(numbers)


def one_expression(numbers, target, allowed_ops=None):
    """One parenthesized expression using all given numbers exactly once."""
    if allowed_ops is None:
        allowed_ops = set(OPS)

    def search(vals):
        if len(vals) == 1:
            return vals[0][1] if vals[0][0] == Fraction(target, 1) else None
        n = len(vals)
        for i in range(n):
            for j in range(i + 1, n):
                (a, sa), (b, sb) = vals[i], vals[j]
                rest = [vals[k] for k in range(n) if k not in (i, j)]
                for op in OPS:
                    if op not in allowed_ops:
                        continue
                    for z, order in (
                        (_apply(op, a, b), f"({sa} {op} {sb})"),
                        (_apply(op, b, a), f"({sb} {op} {sa})"),
                    ):
                        if z is None:
                            continue
                        r = search(rest + [(z, order)])
                        if r:
                            return r
        return None

    return search([(Fraction(n, 1), str(n)) for n in numbers])


def one_expression_any_subset(numbers, target, allowed_ops=None):
    """One expression hitting target using a non-empty subset."""
    n = len(numbers)
    for r in range(1, n + 1):
        for subset in combinations(range(n), r):
            vals = [numbers[i] for i in subset]
            e = one_expression(vals, target, allowed_ops)
            if e:
                return e
    return None


def random_use_all_instance(rng, tgt_lo=50, tgt_hi=999, max_attempts=400):
    """Build a random binary expression on six integers; return (nums, target, expr)
    iff a strict-subset solution also exists."""
    for _ in range(max_attempts):
        nums = [rng.randint(1, 9) for _ in range(6)]
        vals = [(Fraction(n, 1), str(n)) for n in nums]
        ok = True
        while len(vals) > 1:
            m = len(vals)
            i, j = rng.sample(range(m), 2)
            if i > j:
                i, j = j, i
            a, sa = vals[i]
            b, sb = vals[j]
            rest = [vals[k] for k in range(m) if k not in (i, j)]
            op = rng.choice(OPS)
            z = _apply(op, a, b)
            order = (sa, sb)
            if z is None:
                z = _apply(op, b, a)
                order = (sb, sa)
            if z is None:
                ok = False
                break
            vals = rest + [(z, f"({order[0]} {op} {order[1]})")]
        if not ok or len(vals) != 1:
            continue
        t = vals[0][0]
        if t.denominator != 1:
            continue
        ti = int(t)
        if not (tgt_lo <= ti <= tgt_hi):
            continue
        if not strict_subset_solution_exists(nums, ti):
            continue
        return nums, ti, vals[0][1]
    return None
