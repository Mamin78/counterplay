"""ASCII grid display with box separators."""


def grid_to_text(grid, n, box_size, digit_to_str, empty_char='.'):
    """
    Render an n×n grid as a human-readable string.
    Empty cells (value 0 or None) are shown as empty_char.
    Box separators are inserted every box_size rows/columns.
    """
    lines = []
    for r in range(n):
        row_blocks = []
        for bc in range(n // box_size):
            block = []
            for j in range(box_size):
                v = grid[r][bc * box_size + j]
                block.append(empty_char if (v is None or v == 0) else digit_to_str(v))
            row_blocks.append(' '.join(block))
        lines.append(' | '.join(row_blocks))

        if r < n - 1 and (r + 1) % box_size == 0:
            # Horizontal separator between box rows
            row_width = len(lines[-1])
            lines.append('-' * row_width)

    return '\n'.join(lines)
