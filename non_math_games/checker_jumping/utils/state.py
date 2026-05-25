"""
State representation and move logic for Checker Jumping variants.

Board is a list of characters: 'R' (red, moves right), 'B' (blue, moves left), '_' (empty).
A move is [color, from_pos, to_pos].
"""


def make_initial_state(n_red, n_blue, n_empty=1):
    """n_red reds on left, n_empty spaces, n_blue blues on right."""
    return ['R'] * n_red + ['_'] * n_empty + ['B'] * n_blue


def make_goal_state(n_red, n_blue, n_empty=1):
    """Blues on left, n_empty spaces, reds on right."""
    return ['B'] * n_blue + ['_'] * n_empty + ['R'] * n_red


def get_valid_moves(board, max_jump_distance=1):
    """
    Return all valid moves as list of [color, from_pos, to_pos].

    Rules:
    - R moves right (increasing index), B moves left (decreasing index).
    - Slide: move into an adjacent empty space (always allowed).
    - Jump: jump over 1..max_jump_distance consecutive opposite-color checkers
      into an empty space. Baseline uses max_jump_distance=1; CF2 uses 2
      (allows jumping over 1 or 2 frogs).
    """
    moves = []
    n = len(board)
    seen = set()
    for i, cell in enumerate(board):
        if cell == '_':
            continue
        color = cell
        direction = 1 if color == 'R' else -1
        opposite = 'B' if color == 'R' else 'R'

        # Slide one step forward
        j = i + direction
        if 0 <= j < n and board[j] == '_':
            key = (i, j)
            if key not in seen:
                seen.add(key)
                moves.append([color, i, j])

        # Jump over 1..max_jump_distance consecutive opposite-color checkers
        for dist in range(1, max_jump_distance + 1):
            jump_end = i + direction * (dist + 1)
            if not (0 <= jump_end < n and board[jump_end] == '_'):
                break  # can't extend further
            intermediates = [i + direction * k for k in range(1, dist + 1)]
            if not all(0 <= idx < n and board[idx] == opposite for idx in intermediates):
                break  # intermediate cells not all opposite → can't extend
            key = (i, jump_end)
            if key not in seen:
                seen.add(key)
                moves.append([color, i, jump_end])

    return moves


def apply_move(board, color, from_pos, to_pos):
    board = list(board)
    board[to_pos] = board[from_pos]
    board[from_pos] = '_'
    return board
