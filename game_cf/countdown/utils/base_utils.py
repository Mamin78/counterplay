"""Base conversion utilities."""

DIGIT_CHARS = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"


def int_to_base(n, base):
    assert 2 <= base <= 36
    if n == 0:
        return "0"
    if n < 0:
        return "-" + int_to_base(-n, base)
    digits = []
    while n:
        digits.append(DIGIT_CHARS[n % base])
        n //= base
    return "".join(reversed(digits))


def base_to_int(s, base):
    s = s.upper()
    negative = s.startswith("-")
    if negative:
        s = s[1:]
    result = 0
    for c in s:
        idx = DIGIT_CHARS.find(c)
        if idx == -1 or idx >= base:
            raise ValueError(f"Digit '{c}' is not valid in base {base}")
        result = result * base + idx
    return -result if negative else result
