"""
Parses Hanoi move sequences from free-form model text.

Expected format asked in the prompt:
  disk <N> : <SRC> -> <DST>
  e.g. disk 1 : A -> C

Also accepts several fallback formats to be robust.
Returns list of [disk, src_peg, dst_peg] (all ints, 0-indexed pegs).
"""
import re

# Map peg names to 0-indexed integers
_PEG = {
    "a": 0, "b": 1, "c": 2, "d": 3,
    "0": 0, "1": 1, "2": 2, "3": 3,
    "left": 0, "middle": 1, "center": 1, "right": 2,
    "peg0": 0, "peg1": 1, "peg2": 2, "peg3": 3,
}


def _peg(s: str) -> int | None:
    s = s.strip().lower().replace(" ", "")
    return _PEG.get(s)


def parse(text: str) -> list:
    """Return list of [disk, src, dst] extracted from text."""
    moves = []

    # Primary format: "disk N : X -> Y" (or disk N: X->Y, disk N X->Y, etc.)
    primary = re.findall(
        r"disk\s+(\d+)\s*[:\-]?\s*([A-Da-d]|\d)\s*(?:->|→|to)\s*([A-Da-d]|\d)",
        text, re.IGNORECASE,
    )
    for disk_s, src_s, dst_s in primary:
        src = _peg(src_s)
        dst = _peg(dst_s)
        if src is not None and dst is not None:
            moves.append([int(disk_s), src, dst])

    if moves:
        return moves

    # Fallback 1: "N: X -> Y" where N is disk number (line-level)
    for line in text.splitlines():
        m = re.match(
            r"^\s*(\d+)\s*[:\.]?\s*([A-Da-d]|\d)\s*(?:->|→)\s*([A-Da-d]|\d)\s*$",
            line.strip(), re.IGNORECASE,
        )
        if m:
            disk, src_s, dst_s = m.group(1), m.group(2), m.group(3)
            src, dst = _peg(src_s), _peg(dst_s)
            if src is not None and dst is not None:
                moves.append([int(disk), src, dst])

    if moves:
        return moves

    # Fallback 2: JSON-like "[N, X, Y]"
    json_like = re.findall(r"\[\s*(\d+)\s*,\s*([A-Da-d0-3])\s*,\s*([A-Da-d0-3])\s*\]", text, re.IGNORECASE)
    for disk_s, src_s, dst_s in json_like:
        src, dst = _peg(src_s), _peg(dst_s)
        if src is not None and dst is not None:
            moves.append([int(disk_s), src, dst])

    return moves
