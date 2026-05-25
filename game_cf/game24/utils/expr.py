"""Strict expression evaluator + distractor generator.

Strict semantics: every intermediate division must produce an integer and
never divide by zero — matches the countdown/game24 solver semantics.
"""
from __future__ import annotations

import ast
import re
from fractions import Fraction
from typing import List, Optional


def eval_strict(expr: str) -> Optional[Fraction]:
    """Return Fraction value if expression is valid under strict integer-division semantics
    AND the final result is an integer. Otherwise None."""
    try:
        tree = ast.parse(expr, mode='eval')
    except SyntaxError:
        return None

    def visit(node):
        if isinstance(node, ast.Expression):
            return visit(node.body)
        if isinstance(node, ast.BinOp):
            l = visit(node.left)
            r = visit(node.right)
            if l is None or r is None:
                return None
            if isinstance(node.op, ast.Add):
                return l + r
            if isinstance(node.op, ast.Sub):
                return l - r
            if isinstance(node.op, ast.Mult):
                return l * r
            if isinstance(node.op, ast.Div):
                if r == 0:
                    return None
                q = l / r
                if q.denominator != 1:
                    return None
                return q
            return None
        if isinstance(node, ast.Constant) and isinstance(node.value, int):
            return Fraction(node.value, 1)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            v = visit(node.operand)
            return -v if v is not None else None
        return None

    v = visit(tree)
    if v is None or v.denominator != 1:
        return None
    return v


def operators_used(expr: str) -> set:
    """Return the set of binary operators ({'+','-','*','/'}) appearing in expr."""
    return {ch for ch in expr if ch in '+-*/'}


def numbers_used(expr: str) -> List[int]:
    """Return the list of integer literals appearing in the expression, in order."""
    return [int(s) for s in re.findall(r'\d+', expr)]


def perturbed_distractors(correct_expr: str, target: int, rng, count: int,
                          avoid_values=None, allowed_ops=None) -> List[str]:
    """Generate distractor expressions by swapping operators in correct_expr.

    Each distractor must:
    - parse and evaluate cleanly
    - evaluate to a value different from target
    - have a value not in avoid_values
    - if allowed_ops is provided, only use operators from that set
    """
    if avoid_values is None:
        avoid_values = set()
    avoid_values = set(avoid_values) | {target}

    pool = allowed_ops if allowed_ops is not None else {'+', '-', '*', '/'}
    op_positions = [i for i, c in enumerate(correct_expr) if c in '+-*/']
    out: List[str] = []
    seen_exprs = {correct_expr}
    seen_values = set()

    # Try every single-position swap.
    attempts = []
    for pos in op_positions:
        for new_op in pool:
            if new_op == correct_expr[pos]:
                continue
            attempts.append((pos, new_op))
    rng.shuffle(attempts)

    for pos, new_op in attempts:
        if len(out) >= count:
            break
        cand = correct_expr[:pos] + new_op + correct_expr[pos + 1:]
        if cand in seen_exprs:
            continue
        v = eval_strict(cand)
        if v is None:
            continue
        iv = int(v)
        if iv in avoid_values or iv in seen_values:
            continue
        seen_exprs.add(cand)
        seen_values.add(iv)
        out.append(cand)

    # Fall back to two-position swaps if needed.
    if len(out) < count:
        pairs = []
        for p1 in op_positions:
            for p2 in op_positions:
                if p2 <= p1:
                    continue
                for o1 in pool:
                    for o2 in pool:
                        if o1 == correct_expr[p1] and o2 == correct_expr[p2]:
                            continue
                        pairs.append((p1, o1, p2, o2))
        rng.shuffle(pairs)
        for p1, o1, p2, o2 in pairs:
            if len(out) >= count:
                break
            cand_list = list(correct_expr)
            cand_list[p1] = o1
            cand_list[p2] = o2
            cand = ''.join(cand_list)
            if cand in seen_exprs:
                continue
            v = eval_strict(cand)
            if v is None:
                continue
            iv = int(v)
            if iv in avoid_values or iv in seen_values:
                continue
            seen_exprs.add(cand)
            seen_values.add(iv)
            out.append(cand)

    return out
