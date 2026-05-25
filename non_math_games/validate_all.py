#!/usr/bin/env python3
"""
Comprehensive correctness validation for non_math_games/.

Checks:
  1. Hanoi 3-peg baseline: every move valid, final state matches goal.
  2. Hanoi CF1 4-peg: every move valid (disk ID bug check), final state matches goal.
  3. Hanoi CF2 adjacent: every move valid and adjacent, final state matches goal.
  4. Checker jumping (all variants): every move valid, final state matches goal.
  5. River crossing (baseline + neutral): every transition safe, final state correct.
"""

import sys, os, copy, math

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE)

ERRORS = []
PASSES = []

def fail(msg):
    ERRORS.append(msg)
    print(f"  FAIL: {msg}")

def ok(msg):
    PASSES.append(msg)
    print(f"  OK:   {msg}")

# ─────────────────────────────────────────────────────────────────────────────
# 1.  HANOI SOLVERS
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== HANOI SOLVERS ===")

from hanoi.utils.solver import solve_hanoi, solve_hanoi_four_pegs, solve_hanoi_adjacent, _hanoi3, _hanoi4
from hanoi.utils.state import make_initial_state, make_goal_state, validate_move, apply_move

def run_hanoi(n, solver_fn, num_pegs, adjacent_only=False, label=""):
    initial = make_initial_state(n, num_pegs=num_pegs)
    goal    = make_goal_state(n,   num_pegs=num_pegs)
    moves   = solver_fn(n)
    state   = copy.deepcopy(initial)
    for step, move in enumerate(moves):
        disk, fp, tp = move
        ok_flag, reason = validate_move(state, disk, fp, tp, adjacent_only=adjacent_only)
        if not ok_flag:
            fail(f"[{label} n={n}] step {step}: move {move} invalid — {reason}  state={state}")
            return False
        state = apply_move(state, disk, fp, tp)
    if state != goal:
        fail(f"[{label} n={n}] final state {state} != goal {goal}")
        return False
    return True

# 1a. Baseline (3-peg)
all_ok = True
for n in range(2, 8):
    result = run_hanoi(n, solve_hanoi, 3, label="hanoi_baseline")
    all_ok = all_ok and result
if all_ok:
    ok("hanoi_baseline n=2..7: all moves valid, correct final state")

# 1b. CF1 (4-peg) — the suspected disk-ID bug
print("\n--- CF1 4-peg (suspected disk-ID bug) ---")
all_ok = True
for n in range(2, 8):
    result = run_hanoi(n, solve_hanoi_four_pegs, 4, label="hanoi_cf1_4peg")
    all_ok = all_ok and result
if all_ok:
    ok("hanoi_cf1_4peg n=2..7: all moves valid, correct final state")

# Detailed trace for n=4 to show the disk IDs returned by _hanoi3 inside _hanoi4
print("\n--- Detailed trace: _hanoi4(n=4, ...) disk IDs ---")
detail_moves = []
_hanoi4(4, 0, 3, 1, 2, detail_moves)
disk_ids_seen = sorted(set(m[0] for m in detail_moves))
print(f"  Disk IDs in 4-peg solution for n=4: {disk_ids_seen}")
if set(disk_ids_seen) == set(range(1, 5)):
    ok("hanoi_cf1_4peg n=4: disk IDs are 1..4 (absolute), no relative-ID bug")
else:
    fail(f"hanoi_cf1_4peg n=4: disk IDs found = {disk_ids_seen}, expected {{1,2,3,4}}")

# Verify specifically: when _hanoi4 calls _hanoi3, does _hanoi3 use the right IDs?
# For n=4, t=_optimal_t(4). _hanoi3(n-t, src, dst, aux2, moves) should move disks t+1..n
from hanoi.utils.solver import _optimal_t
for n in [4, 5, 6, 7]:
    t = _optimal_t(n)
    sub_moves = []
    _hanoi3(n - t, 0, 3, 2, sub_moves)   # same call as inside _hanoi4
    sub_disk_ids = set(m[0] for m in sub_moves)
    expected_ids = set(range(1, n - t + 1))  # _hanoi3 always numbers 1..(n-t)
    abs_expected = set(range(t + 1, n + 1))  # what we WANT: absolute disk IDs
    if sub_disk_ids == expected_ids and sub_disk_ids != abs_expected:
        fail(
            f"hanoi_cf1 n={n}: _hanoi3({n-t},...) uses relative IDs {sorted(sub_disk_ids)} "
            f"but absolute IDs {sorted(abs_expected)} are needed for the bottom {n-t} disks"
        )
    elif sub_disk_ids == abs_expected:
        ok(f"hanoi_cf1 n={n}: _hanoi3 sub-call disk IDs {sorted(sub_disk_ids)} == absolute {sorted(abs_expected)}")
    else:
        print(f"  NOTE n={n}: t={t}, sub IDs={sorted(sub_disk_ids)}, expected relative {sorted(expected_ids)}, expected absolute {sorted(abs_expected)}")

# 1c. CF2 adjacent
print("\n--- CF2 adjacent ---")
all_ok = True
for n in range(2, 6):
    result = run_hanoi(n, solve_hanoi_adjacent, 3, adjacent_only=True, label="hanoi_cf2_adj")
    all_ok = all_ok and result
if all_ok:
    ok("hanoi_cf2_adjacent n=2..5: all moves valid and adjacent, correct final state")

# ─────────────────────────────────────────────────────────────────────────────
# 2.  CHECKER JUMPING SOLVERS
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== CHECKER JUMPING SOLVERS ===")

from checker_jumping.utils.state import (
    make_initial_state as ck_initial,
    make_goal_state    as ck_goal,
    get_valid_moves, apply_move as ck_apply,
)
from checker_jumping.utils.solver import solve_checker, solve_checker_jump_two, solve_checker_two_empty

def run_checker(n_red, n_blue, max_jump, n_empty, label=""):
    initial = ck_initial(n_red, n_blue, n_empty)
    goal    = ck_goal(n_red, n_blue, n_empty)
    moves   = solve_checker(n_red, n_blue, max_jump_distance=max_jump, n_empty=n_empty)
    if moves is None:
        fail(f"[{label}] no solution found")
        return False
    board = list(initial)
    for step, move in enumerate(moves):
        color, fp, tp = move
        # Validate the move is in valid moves for this board
        valid = get_valid_moves(board, max_jump_distance=max_jump)
        valid_keys = [(m[1], m[2]) for m in valid]
        if (fp, tp) not in valid_keys:
            fail(f"[{label}] step {step}: move {move} not in valid moves {valid}")
            return False
        if board[fp] != color:
            fail(f"[{label}] step {step}: move {move} claims color={color} but board[{fp}]={board[fp]}")
            return False
        board = ck_apply(board, color, fp, tp)
    if board != goal:
        fail(f"[{label}] final board {board} != goal {goal}")
        return False
    return True

# 2a. Baseline symmetric
all_ok = True
for n in range(2, 7):
    all_ok = run_checker(n, n, 1, 1, label=f"checker_baseline_n{n}") and all_ok
if all_ok:
    ok("checker_baseline n=2..6: all moves valid, correct final state")

# 2b. CF1 asymmetric
print()
all_ok = True
for n in [2, 3, 4, 5]:
    for k in [1, 3, 5]:
        m = n + k
        r = run_checker(n, m, 1, 1, label=f"checker_cf1_n{n}_k{k}")
        if not r:
            all_ok = False
if all_ok:
    ok("checker_cf1_asymmetric: all moves valid, correct final state")

# 2c. CF2 jump-two
print()
all_ok = True
for n in range(2, 6):
    all_ok = run_checker(n, n, 2, 1, label=f"checker_cf2_n{n}") and all_ok
if all_ok:
    ok("checker_cf2_jump_two n=2..5: all moves valid, correct final state")

# 2d. CF3 two-empty
print()
all_ok = True
for n in range(2, 6):
    all_ok = run_checker(n, n, 1, 2, label=f"checker_cf3_n{n}") and all_ok
if all_ok:
    ok("checker_cf3_two_empty n=2..5: all moves valid, correct final state")

# ─────────────────────────────────────────────────────────────────────────────
# 3.  RIVER CROSSING SOLVER
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== RIVER CROSSING SOLVERS ===")

from river_crossing.utils.state import make_people, is_safe
from river_crossing.utils.solver import solve_river, solve_river_neutral, _boat_capacity

def run_river(n, solver_fn, include_neutral, label=""):
    people = make_people(n, include_neutral=include_neutral)
    moves  = solver_fn(n)
    if moves is None:
        fail(f"[{label} n={n}] no solution found")
        return False
    capacity = _boat_capacity(n)
    left  = frozenset(people)
    right = frozenset()
    boat  = 0  # 0=left, 1=right

    def safe_fn(bank):
        if include_neutral:
            return is_safe(bank - {"neutral"}, n)
        return is_safe(bank, n)

    for step, group in enumerate(moves):
        group_set = frozenset(group)
        # Check boat capacity
        if len(group_set) > capacity:
            fail(f"[{label} n={n}] step {step}: group {group} exceeds capacity {capacity}")
            return False
        # Check all in group are on the current bank
        current = left if boat == 0 else right
        if not group_set <= current:
            fail(f"[{label} n={n}] step {step}: group {group} not all on current bank {current}")
            return False
        # Apply move
        other = right if boat == 0 else left
        new_current = current - group_set
        new_other   = other   | group_set
        if boat == 0:
            left, right = new_current, new_other
        else:
            left, right = new_other, new_current
        boat = 1 - boat
        # Check safety
        if not safe_fn(left):
            fail(f"[{label} n={n}] step {step}: left bank {left} is unsafe after move {group}")
            return False
        if not safe_fn(right):
            fail(f"[{label} n={n}] step {step}: right bank {right} is unsafe after move {group}")
            return False
    # Check final state: everyone on right, boat on right
    if left != frozenset() or right != frozenset(people) or boat != 1:
        fail(f"[{label} n={n}] final state wrong: left={left} right={right} boat={boat}")
        return False
    return True

# 3a. Baseline
all_ok = True
for n in [2, 3, 4, 5]:
    all_ok = run_river(n, solve_river, False, label="river_baseline") and all_ok
if all_ok:
    ok("river_baseline n=2..5: all transitions safe, correct final state")

# 3b. Neutral
print()
all_ok = True
for n in [2, 3, 4, 5]:
    all_ok = run_river(n, solve_river_neutral, True, label="river_cf1_neutral") and all_ok
if all_ok:
    ok("river_cf1_neutral n=2..5: all transitions safe, correct final state")

# ─────────────────────────────────────────────────────────────────────────────
# 5.  ADDITIONAL STRUCTURAL CHECKS
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== ADDITIONAL STRUCTURAL CHECKS ===")

# 5a. Check _optimal_t never returns 0 or >= n (which would cause infinite recursion or wrong split)
print("\n--- _optimal_t validity ---")
from hanoi.utils.solver import _optimal_t
for n in range(2, 12):
    t = _optimal_t(n)
    if t <= 0 or t >= n:
        fail(f"_optimal_t({n}) = {t}, must be in 1..{n-1}")
    else:
        print(f"  _optimal_t({n}) = {t} [ok: 1 <= {t} <= {n-1}]")
ok("_optimal_t: all values in valid range 1..n-1 for n=2..11")

# 5b. Hanoi CF1: do the bottom n-t disks actually have IDs 1..(n-t) (relative)?
# The full simulation already checks this passes (the state checker validates disk IDs).
# Let's also verify the number of moves is strictly fewer than 2^n - 1
print("\n--- Hanoi CF1 vs baseline move counts ---")
from hanoi.utils.solver import solve_hanoi, solve_hanoi_four_pegs
for n in range(2, 8):
    baseline_count = len(solve_hanoi(n))
    fourpeg_count  = len(solve_hanoi_four_pegs(n))
    if fourpeg_count < baseline_count:
        print(f"  n={n}: 4-peg={fourpeg_count} < 3-peg={baseline_count} [ok]")
    elif fourpeg_count == baseline_count:
        print(f"  n={n}: 4-peg={fourpeg_count} == 3-peg={baseline_count} [ok for small n]")
    else:
        fail(f"n={n}: 4-peg={fourpeg_count} > 3-peg={baseline_count} — 4-peg should never be worse")

# 5c. Verify the disk-ID issue more explicitly:
# When _hanoi4(n, src, dst, ...) calls _hanoi3(n-t, src, dst, aux2, moves),
# _hanoi3 produces moves with disk IDs 1..(n-t).
# BUT in the physical state, the disks that remain on src peg at that point
# are the BOTTOM n-t disks, which have absolute IDs t+1..n.
# The validate_move() in state.py checks: state[from_peg][-1] == disk
# So if the physical top of src is disk (t+1) but _hanoi3 says to move disk 1,
# the validation would fail — and we already see that it PASSES above.
# This means one of:
#   (a) The bug exists but the simulation doesn't catch it because the pegs line up
#   (b) The bug does NOT exist — _hanoi3 relative IDs work because the smaller disks
#       happen to be at the same position in the state list.
# Let's trace carefully for n=3, t=1: _hanoi3(2, src, dst, aux2)
# Initial: src=[3,2,1], dst=[], aux1=[], aux2=[]
# Step 1: _hanoi4(1, src, aux1, aux2, dst) moves disk 1 from src to aux1
#   state: src=[3,2], dst=[], aux1=[1], aux2=[]
# Step 2: _hanoi3(2, src, dst, aux2) should move disks 2 and 3 (abs) from src to dst
#   _hanoi3 uses ids 1..2. Internally:
#     _hanoi3(1, src, aux2, dst): moves "disk 1" from src→aux2
#       But src top is disk 2 (absolute)! Will validate_move accept this?
print("\n--- Explicit trace n=3 4-peg to check disk-ID mismatch ---")
from hanoi.utils import make_initial_state, make_goal_state
from hanoi.utils.state import validate_move, apply_move

n = 3
state = make_initial_state(n, num_pegs=4)
print(f"  Initial state: {state}")

# Replicate _hanoi4(3, 0, 3, 1, 2, moves)
t = _optimal_t(3)
print(f"  _optimal_t(3) = {t}")

trace_moves = []
_hanoi4(3, 0, 3, 1, 2, trace_moves)
print(f"  All moves from _hanoi4(3,...): {trace_moves}")
print(f"  Disk IDs used: {sorted(set(m[0] for m in trace_moves))}")

# Now simulate step by step
state = make_initial_state(3, num_pegs=4)
for step, (disk, fp, tp) in enumerate(trace_moves):
    ok_flag, reason = validate_move(state, disk, fp, tp)
    top_fp = state[fp][-1] if state[fp] else None
    if not ok_flag:
        fail(f"  [n=3 4-peg trace] step {step} move [disk={disk},{fp}->{tp}]: {reason}  (peg top={top_fp})")
    state = apply_move(state, disk, fp, tp)
print(f"  Final state: {state}")
print(f"  Goal state:  {make_goal_state(3, num_pegs=4)}")

# ─────────────────────────────────────────────────────────────────────────────
# 6.  CHECKER JUMPING: Direction enforcement check
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== CHECKER DIRECTION ENFORCEMENT ===")
# R must move RIGHT (increasing index), B must move LEFT (decreasing index)
# Check the solver never produces a backward slide or jump
from checker_jumping.utils.state import get_valid_moves, apply_move as ck_apply

def check_checker_directions(n_red, n_blue, max_jump, n_empty, label):
    initial = ck_initial(n_red, n_blue, n_empty)
    goal    = ck_goal(n_red, n_blue, n_empty)
    moves   = solve_checker(n_red, n_blue, max_jump_distance=max_jump, n_empty=n_empty)
    if moves is None:
        fail(f"[{label}] no solution")
        return
    for step, (color, fp, tp) in enumerate(moves):
        if color == 'R' and tp <= fp:
            fail(f"[{label}] step {step}: R moves left (from {fp} to {tp})")
        if color == 'B' and tp >= fp:
            fail(f"[{label}] step {step}: B moves right (from {fp} to {tp})")

all_dir_ok = True
for n in range(2, 6):
    check_checker_directions(n, n, 1, 1, f"checker_baseline_n{n}")
    check_checker_directions(n, n, 2, 1, f"checker_cf2_n{n}")
    check_checker_directions(n, n, 1, 2, f"checker_cf3_n{n}")
ok("checker: all moves respect R→right, B→left direction rule")

# ─────────────────────────────────────────────────────────────────────────────
# 7.  RIVER CROSSING: Boat never travels empty
# ─────────────────────────────────────────────────────────────────────────────
print("\n=== RIVER CROSSING: NO EMPTY BOAT MOVES ===")
for n in [2, 3, 4, 5]:
    for fn, label, neutral in [(solve_river, "baseline", False), (solve_river_neutral, "neutral", True)]:
        sol = fn(n)
        if sol is None:
            fail(f"[river_{label} n={n}] no solution")
            continue
        for step, group in enumerate(sol):
            if len(group) == 0:
                fail(f"[river_{label} n={n}] step {step}: empty boat move!")
ok("river: no empty boat moves found")

# ─────────────────────────────────────────────────────────────────────────────
# SUMMARY
# ─────────────────────────────────────────────────────────────────────────────
print("\n" + "="*60)
print(f"SUMMARY: {len(PASSES)} checks passed, {len(ERRORS)} FAILURES")
print("="*60)
if ERRORS:
    print("\nFAILURES:")
    for e in ERRORS:
        print(f"  • {e}")
else:
    print("All checks passed!")
sys.exit(len(ERRORS))
