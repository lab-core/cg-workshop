"""Smoke test -- exercises highspy + rcspp on the toy instance.

Does not depend on any code you will modify.  If this fails, fix your
environment before doing any exercise.
"""

import argparse
import sys

from vrp.log import configure as configure_logging, get_logger


_log = get_logger("smoke")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="enable DEBUG logs")
    args = ap.parse_args()
    configure_logging(verbose=args.verbose)

    # ---------- highspy ------------------------------------------------
    try:
        import highspy as hp
    except ImportError as e:
        _log.error("cannot import highspy (%s).", e)
        return 1
    _log.info("highspy version: %s", getattr(hp, "__version__", "?"))

    # ---------- rcspp --------------------------------------------------
    try:
        from rcspp.graph import ResourceGraph
        from rcspp.resource import (
            AdditionExtensionFunction,
            ValueDominanceFunction,
            ValueCostFunction,
            TrivialFeasibilityFunction,
        )
        import rcspp
    except ImportError as e:
        _log.error("cannot import rcspp (%s).", e)
        return 2
    _log.info("rcspp version:   %s", getattr(rcspp, "__version__", "0.0.1"))

    # ---------- highspy: trivial LP -----------------------------------
    h = hp.Highs()
    h.silent()
    h.addCol(1.0, 0.0, hp.kHighsInf, 0, [], [])
    h.addCol(1.0, 0.0, hp.kHighsInf, 0, [], [])
    h.addRow(1.0, hp.kHighsInf, 2, [0, 1], [1.0, 1.0])
    h.run()
    obj = h.getObjectiveValue()
    if abs(obj - 1.0) > 1e-6:
        _log.error("trivial LP returned %s, expected 1.0", obj)
        return 3

    # ---------- rcspp: tiny shortest path -----------------------------
    g = ResourceGraph()
    g.add_real_resource(
        AdditionExtensionFunction(),
        TrivialFeasibilityFunction(),
        ValueCostFunction(),
        ValueDominanceFunction(),
    )
    g.add_node(0, True, False)
    g.add_node(1, False, True)
    g.add_arc(-2.0, 0, 1, 0, -2.0)
    sols = g.solve()
    if not sols:
        _log.error("rcspp returned no solution on a 2-node graph.")
        return 4
    _log.info("rcspp solve:     1 sink label, cost = %.2f", sols[0].cost)

    # ---------- toy instance load -------------------------------------
    try:
        from vrp.instance_reader import InstanceReader
        from vrp.tests._paths import find_instance
        ir = InstanceReader(find_instance("toy.txt"))
        inst = ir.read()
    except Exception as e:
        _log.error("cannot load instances/toy.txt (%s).", e)
        return 5
    _log.info("toy instance:    %d customers, capacity %d",
              len(inst.get_customers_by_id()) - 1, inst.get_capacity())

    _log.info("OK -- environment is ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
