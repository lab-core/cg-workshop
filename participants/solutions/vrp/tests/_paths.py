"""Helpers used by the check scripts to locate instance / dual files.

Lets the same script run from `participants/` (typical) or
`participants/solutions/` (when peeking at the reference).
"""

import os
import sys


def find_instance(name: str) -> str:
    """Return a usable path to instances/<name>, searching:

    1. the literal `name` if it already resolves,
    2. instances/<name> in the current working directory,
    3. ../instances/<name> (used by the solutions/ tree),
    4. ../../instances/<name> (deep nesting).
    """
    candidates = [name,
                  os.path.join("instances", name),
                  os.path.join("..", "instances", name),
                  os.path.join("..", "..", "instances", name)]
    for c in candidates:
        if os.path.exists(c):
            return c
    sys.stderr.write(
        f"[paths] cannot find instance {name!r}; tried: {candidates}\n"
    )
    raise FileNotFoundError(name)


def find_duals(instance_stem: str, iter_idx: int) -> str:
    """Return a path to instances/duals/<stem>/iter_<k>.txt."""
    rel = os.path.join("duals", instance_stem, f"iter_{iter_idx}.txt")
    return find_instance(rel)
