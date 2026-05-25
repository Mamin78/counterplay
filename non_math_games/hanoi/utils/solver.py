"""
Solvers for Tower of Hanoi variants.

All solvers return a list of moves, where each move is [disk, from_peg, to_peg].
Disk numbering: 1 = smallest, n = largest.
Peg numbering: 0-indexed.
"""


def solve_hanoi(n, src=0, dst=2, aux=1):
    """Standard 3-peg recursive solver. Returns optimal 2^n - 1 moves."""
    moves = []
    _hanoi3(n, src, dst, aux, moves)
    return moves


def _hanoi3(n, src, dst, aux, moves):
    if n == 0:
        return
    _hanoi3(n - 1, src, aux, dst, moves)
    moves.append([n, src, dst])
    _hanoi3(n - 1, aux, dst, src, moves)


def solve_hanoi_four_pegs(n, src=0, dst=3, aux1=1, aux2=2):
    """
    4-peg recursive solver (Frame-Stewart heuristic).
    Moves top t disks to a spare peg using 4 pegs, moves bottom n-t
    using 3 pegs, then moves t back using 4 pegs.
    """
    moves = []
    _hanoi4(n, src, dst, aux1, aux2, moves)
    return moves


def _optimal_t(n):
    """Frame-Stewart optimal split for n disks with 4 pegs."""
    # t chosen to minimise: 2*T4(t) + T3(n-t)
    # Simple approximation: t = n - round(sqrt(2n))
    import math
    t = max(1, n - round(math.sqrt(2 * n)))
    return t


def _hanoi3_offset(n, src, dst, aux, moves, disk_offset):
    """Like _hanoi3 but disk IDs are shifted by disk_offset (for use inside _hanoi4)."""
    if n == 0:
        return
    _hanoi3_offset(n - 1, src, aux, dst, moves, disk_offset)
    moves.append([n + disk_offset, src, dst])
    _hanoi3_offset(n - 1, aux, dst, src, moves, disk_offset)


def _hanoi4(n, src, dst, aux1, aux2, moves, disk_offset=0):
    if n == 0:
        return
    if n == 1:
        moves.append([1 + disk_offset, src, dst])
        return
    t = _optimal_t(n)
    # Top t disks have IDs disk_offset+1 .. disk_offset+t
    _hanoi4(t, src, aux1, aux2, dst, moves, disk_offset)
    # Bottom n-t disks have IDs disk_offset+t+1 .. disk_offset+n
    _hanoi3_offset(n - t, src, dst, aux2, moves, disk_offset + t)
    # Top t disks again
    _hanoi4(t, aux1, dst, src, aux2, moves, disk_offset)


def solve_hanoi_adjacent(n, src=0, dst=2):
    """
    Adjacent-only 3-peg solver (pegs arranged in a line: 0-1-2).
    Only moves between adjacent pegs are allowed (|from - to| == 1).
    Produces 3^n - 1 moves.
    """
    moves = []
    _hanoi_adj(n, src, dst, moves)
    return moves


def _hanoi_adj(n, src, dst, moves):
    """Move n disks from src to dst using adjacent moves only."""
    if n == 0:
        return
    other = 3 - src - dst  # the third peg (0+1+2=3)
    if abs(src - dst) == 1:
        # Adjacent: standard 3-step recursion through the other peg
        _hanoi_adj(n - 1, src, other, moves)
        moves.append([n, src, dst])
        _hanoi_adj(n - 1, other, dst, moves)
    else:
        # Non-adjacent (src=0, dst=2 or vice versa): must route through middle
        _hanoi_adj(n - 1, src, dst, moves)   # move n-1 from src to dst
        moves.append([n, src, other])          # move disk n from src to middle
        _hanoi_adj(n - 1, dst, src, moves)   # move n-1 from dst to src
        moves.append([n, other, dst])          # move disk n from middle to dst
        _hanoi_adj(n - 1, src, dst, moves)   # move n-1 from src to dst
