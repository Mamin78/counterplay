"""
BFS solvers for Checker Jumping variants.
All return a list of moves [color, from_pos, to_pos].
"""
from collections import deque
from .state import (
    make_initial_state, make_goal_state,
    get_valid_moves, apply_move,
)


def _bfs(initial, goal, move_fn):
    """Generic BFS. move_fn(board) → list of (move, next_board)."""
    initial = tuple(initial)
    goal = tuple(goal)
    if initial == goal:
        return []
    queue = deque([(initial, [])])
    visited = {initial}
    while queue:
        state, path = queue.popleft()
        for move, next_state in move_fn(list(state)):
            ns = tuple(next_state)
            if ns == goal:
                return path + [move]
            if ns not in visited:
                visited.add(ns)
                queue.append((ns, path + [move]))
    return None  # no solution


def solve_checker(n_red, n_blue=None, max_jump_distance=1, n_empty=1):
    """Standard (or asymmetric) checker jumping with configurable max jump distance."""
    if n_blue is None:
        n_blue = n_red
    initial = make_initial_state(n_red, n_blue, n_empty)
    goal = make_goal_state(n_red, n_blue, n_empty)

    def moves_fn(board):
        return [
            (m, apply_move(board, *m))
            for m in get_valid_moves(board, max_jump_distance=max_jump_distance)
        ]

    return _bfs(initial, goal, moves_fn)


def solve_checker_jump_two(n):
    """Checker jumping where a frog can jump over 1 OR 2 opposite-color checkers."""
    return solve_checker(n, n, max_jump_distance=2, n_empty=1)


def solve_checker_two_empty(n):
    """Checker jumping with two empty spaces in the middle."""
    return solve_checker(n, n, max_jump_distance=1, n_empty=2)
