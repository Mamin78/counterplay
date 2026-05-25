"""
BFS solver for River Crossing variants.

State: (left_bank: frozenset, right_bank: frozenset, boat_side: int)
  boat_side 0 = left, 1 = right

A move is a sorted list of person IDs travelling in the boat.
"""
from collections import deque
from itertools import combinations
from .state import is_safe, make_people, make_initial_state, make_goal_state


def _boat_capacity(n):
    """Match Illusion paper: capacity 2 for n≤3, capacity 3 for n>3."""
    return 2 if n <= 3 else 3


def _bfs_river(n, people, goal_left, goal_right, capacity, safe_fn):
    initial_left = frozenset(people)
    initial_right = frozenset()
    start = (initial_left, initial_right, 0)  # boat on left
    goal = (goal_left, goal_right, 1)         # boat on right

    queue = deque([(start, [])])
    visited = {start}

    while queue:
        (left, right, boat_side), path = queue.popleft()
        current_bank = left if boat_side == 0 else right
        other_bank = right if boat_side == 0 else left

        for size in range(1, capacity + 1):
            for group in combinations(sorted(current_bank), size):
                group_set = frozenset(group)
                new_current = current_bank - group_set
                new_other = other_bank | group_set

                if boat_side == 0:
                    new_left, new_right = new_current, new_other
                else:
                    new_left, new_right = new_other, new_current

                if not safe_fn(new_left) or not safe_fn(new_right):
                    continue

                new_boat = 1 - boat_side
                new_state = (new_left, new_right, new_boat)

                move = sorted(group)
                if new_state == goal:
                    return path + [move]
                if new_state not in visited:
                    visited.add(new_state)
                    queue.append((new_state, path + [move]))
    return None


def solve_river(n):
    """Standard missionaries-and-cannibals BFS."""
    people = make_people(n, include_neutral=False)
    capacity = _boat_capacity(n)

    def safe(bank):
        return is_safe(bank, n)

    return _bfs_river(
        n, people,
        goal_left=frozenset(),
        goal_right=frozenset(people),
        capacity=capacity,
        safe_fn=safe,
    )


def solve_river_neutral(n):
    """
    River crossing with 1 extra neutral person.
    The neutral person can travel with anyone without violating safety rules.
    Safety check ignores the neutral person entirely.
    """
    people = make_people(n, include_neutral=True)
    capacity = _boat_capacity(n)

    def safe(bank):
        # neutral person never affects safety
        bank_without_neutral = bank - {"neutral"}
        return is_safe(bank_without_neutral, n)

    return _bfs_river(
        n, people,
        goal_left=frozenset(),
        goal_right=frozenset(people),
        capacity=capacity,
        safe_fn=safe,
    )
