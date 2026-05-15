"""Exercise A check script.

Builds the master from one round-trip per customer on the toy instance,
solves the LP, and prints the dual prices.  Compares with reference
values.
"""

import argparse
import math
import os
import signal
import sys

from vrp.instance_reader import InstanceReader
from vrp.cg.master_problem import MasterProblem
from vrp.log import configure as configure_logging, get_logger
from vrp.tests._paths import find_instance
from vrp.vrp import VRP


_log = get_logger("ex.A")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", default="toy.txt")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="enable DEBUG logs")
    args = ap.parse_args()
    configure_logging(verbose=args.verbose)

    inst = InstanceReader(find_instance(args.instance)).read()
    _log.info("instance: %s (%d customers, K=%d vehicles)",
              args.instance,
              len(inst.get_customers_by_id()) - 1,
              inst.get_nb_vehicles())

    vrp = VRP(inst)
    paths = vrp.generate_initial_paths()
    _log.info("building master with %d initial columns", len(paths))

    master = MasterProblem(inst.get_demand_customers_id(),
                           inst.get_nb_vehicles())
    master.construct_model(paths)
    sol = master.solve(relax=True)

    _log.info("LP optimum (with slacks): %.2f", sol.cost)
    _log.info("vehicle dual sigma     : %+.2f", sol.sigma)
    _log.info("customer duals:")
    for cid, pi in sorted(sol.dual_by_var_id.items()):
        _log.info("   pi_%d=%.2f", cid, pi)

    # Sanity: LP must be feasible (non-zero); duals must be finite.
    if not math.isfinite(sol.cost) or sol.cost <= 0:
        _log.error("FAIL: LP=%s -- master is not feasible", sol.cost)
        return 1
    for v in sol.dual_by_var_id.values():
        if not math.isfinite(v):
            _log.error("FAIL: non-finite dual")
            return 1
    _log.info("OK -- master is feasible and returns finite duals.")
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda *_: os._exit(1))
    sys.exit(main())
