import copy


def make_initial_state(n, num_pegs=3):
    pegs = [[] for _ in range(num_pegs)]
    pegs[0] = list(range(n, 0, -1))  # largest disk at bottom
    return pegs


def make_goal_state(n, num_pegs=3):
    pegs = [[] for _ in range(num_pegs)]
    pegs[-1] = list(range(n, 0, -1))
    return pegs


def validate_move(state, disk, from_peg, to_peg, adjacent_only=False):
    num_pegs = len(state)
    if not (0 <= from_peg < num_pegs and 0 <= to_peg < num_pegs):
        return False, "invalid peg index"
    if from_peg == to_peg:
        return False, "same peg"
    if adjacent_only and abs(from_peg - to_peg) != 1:
        return False, "non-adjacent pegs"
    if not state[from_peg] or state[from_peg][-1] != disk:
        return False, "disk not on top of source peg"
    if state[to_peg] and state[to_peg][-1] < disk:
        return False, "larger disk on top of destination"
    return True, "ok"


def apply_move(state, disk, from_peg, to_peg):
    state = copy.deepcopy(state)
    state[from_peg].pop()
    state[to_peg].append(disk)
    return state
