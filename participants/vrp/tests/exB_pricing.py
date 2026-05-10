"""Exercise B check script.

Loads a saved set of duals from instances/duals/<instance>/iter_<k>.txt,
runs the pricer, and checks that:
  * a route is found,
  * its reduced cost is negative.
"""

import argparse
import sys

from vrp.instance_reader import InstanceReader
from vrp.log import configure as configure_logging, get_logger
from vrp.tests._paths import find_duals, find_instance
from vrp.vrp import VRP


_log = get_logger("ex.B")


def load_duals(path: str) -> dict[int, float]:
    duals: dict[int, float] = {}
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            if len(parts) < 2:
                continue
            duals[int(parts[0])] = float(parts[1])
    return duals


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", default="toy.txt")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="enable DEBUG logs")
    ap.add_argument("--iter", type=int, default=0)
    args = ap.parse_args()
    configure_logging(verbose=args.verbose)

    inst_name = args.instance.replace(".txt", "")
    inst = InstanceReader(find_instance(args.instance)).read()
    duals_path = find_duals(inst_name, args.iter)
    _log.info("loading saved duals from %s", duals_path)
    duals = load_duals(duals_path)

    # Make sure depot dual is 0
    duals[inst.get_depot_customer().id] = 0.0

    vrp = VRP(inst)
    sols = vrp.solve_subproblem(duals)
    if not sols:
        _log.error("FAIL: pricer returned no solution")
        return 1

    best = sols[0]
    _log.info("best route        : %s", list(best.path_node_ids))
    _log.info("reduced cost      : %.2f", best.cost)
    nb_neg = sum(1 for s in sols if s.cost < -1e-6)
    _log.info("# neg-cost routes : %d", nb_neg)

    if best.cost > -1e-6:
        _log.error("FAIL: best reduced cost is non-negative")
        return 2
    _log.info("OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
