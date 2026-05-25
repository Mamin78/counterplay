"""
River Crossing state representation.

People:
  A_i = agent (missionary) — protects their paired actor
  a_i = actor (cannibal) — must not be with another agent without their own agent

Naming matches the Illusion of Thinking paper.

Safety rule: on any bank, if there are agents present, every actor must
have their own agent present too (cannibals never outnumber missionaries
unless there are no missionaries at all on that bank).
"""


def make_people(n, include_neutral=False):
    """Return the full set of people for n pairs."""
    people = set()
    for i in range(1, n + 1):
        people.add(f"A_{i}")  # agent
        people.add(f"a_{i}")  # actor
    if include_neutral:
        people.add("neutral")
    return people


def make_initial_state(n, include_neutral=False):
    """Everyone on the left bank."""
    return frozenset(make_people(n, include_neutral)), frozenset()


def make_goal_state(n, include_neutral=False):
    """Everyone on the right bank."""
    return frozenset(), frozenset(make_people(n, include_neutral))


def is_safe(bank, n):
    """
    Check if a bank configuration is safe for n pairs.
    Safe if: for every actor a_i present, agent A_i is also present,
    OR no agents are present at all.
    The neutral person (if any) never creates or solves safety issues.
    """
    agents_present = {p for p in bank if p.startswith("A_")}
    actors_present = {p for p in bank if p.startswith("a_")}
    if not agents_present:
        return True  # no agents → actors are safe
    for actor in actors_present:
        idx = actor.split("_")[1]
        if f"A_{idx}" not in agents_present:
            return False
    return True
