"""
Parses River Crossing trip sequences from free-form model text.

Expected format asked in the prompt:
  trip <N> : <person1>[, <person2>]
  e.g. trip 1 : A_1, a_1
       trip 2 : A_1

Direction is inferred from trip number (odd = L→R, even = R→L) and NOT stored
in the parsed output — the grader handles that.

Returns list of lists-of-strings: passengers for each trip in order.
"""
import re

# Matches agent/actor names: A_1, a_1, A1, a1 (with or without underscore), neutral/N
_PERSON_RE = re.compile(r"\b([Aa]_?\d+|neutral)\b", re.IGNORECASE)

# Annotation-start markers: anything after these is bank/state description, not passengers
_ANNOTATION_RE = re.compile(
    r"\s*[\(\[\{]|"                   # opening paren/bracket/brace
    r"\s+(?:left|right)\s+bank|"      # "left bank" / "right bank"
    r"\s*[–—]\s*",                    # em/en-dash separator
    re.IGNORECASE,
)


def _norm_person(p: str) -> str:
    p = p.strip()
    if p.lower() == "neutral":
        return "neutral"
    # Normalise A1 → A_1, a1 → a_1 (insert underscore if missing)
    p = re.sub(r"^([Aa])(\d+)$", r"\1_\2", p)
    return p


def _strip_markdown(text: str) -> str:
    """Remove bold/italic markdown markers."""
    return re.sub(r"\*+", "", text)


_DIR_ANNOTATION_RE = re.compile(
    r"\(?\s*(?:[LR]\s*[-–→←<>]+\s*[LR]|[LR]\s+to\s+[LR]|"
    r"left\s*[-–→←<>]+\s*right|right\s*[-–→←<>]+\s*left)\s*\)?",
    re.IGNORECASE,
)


def _passengers_from_rest(rest: str) -> list[str]:
    """Extract passenger names from the text after 'trip N :'.

    Strips direction annotations like (L->R) first, then truncates at the
    first bank-description marker so state text doesn't contribute names.
    """
    # Remove inline direction annotations before looking for passengers
    rest = _DIR_ANNOTATION_RE.sub("", rest)
    # Cut off at annotation boundary (bank descriptions, parentheticals, dashes)
    m = _ANNOTATION_RE.search(rest)
    if m:
        rest = rest[:m.start()]
    persons = [_norm_person(p) for p in _PERSON_RE.findall(rest)]
    # Deduplicate while preserving order
    seen: set[str] = set()
    out: list[str] = []
    for p in persons:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return out


def parse(text: str) -> list:
    """Return list of passenger lists, one per trip, in trip-number order."""
    trips: dict[int, list] = {}

    for raw_line in text.splitlines():
        line = _strip_markdown(raw_line).strip()
        if not line:
            continue

        # Primary: "trip N : person1, person2"  (colon/dash optional)
        m = re.match(
            r"trip\s+(\d+)\s*[:\-]?\s*(.*)",
            line, re.IGNORECASE,
        )
        if m:
            num = int(m.group(1))
            rest = m.group(2)
            persons = _passengers_from_rest(rest)
            if persons:
                trips[num] = persons
            continue

        # Fallback: lines that mention a direction arrow AND contain person names
        has_dir = re.search(r"(->|→|←|<-)", line)
        if has_dir:
            # Take only the portion before any annotation
            rest = line
            persons = _passengers_from_rest(rest)
            if persons:
                next_num = max(trips.keys(), default=0) + 1
                trips[next_num] = persons

    if not trips:
        return []

    return [trips[k] for k in sorted(trips.keys())]
