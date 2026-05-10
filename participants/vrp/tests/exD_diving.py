"""Exercise D check script -- RMH then plain diving."""

import argparse
import math
import sys
import time

from vrp.instance_reader import InstanceReader
from vrp.cg.diving import plain_dive, restricted_master_heuristic
from vrp.log import configure as configure_logging, get_logger
from vrp.tests._paths import find_instance
from vrp.vrp import VRP


_log = get_logger("ex.D")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", default="toy.txt")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="enable DEBUG logs")
    ap.add_argument("--K", type=int, default=50)
    args = ap.parse_args()
    configure_logging(verbose=args.verbose)

    inst = InstanceReader(find_instance(args.instance)).read()
    vrp = VRP(inst, K_MAX=args.K)

    _log.info("instance: %s", args.instance)
    t0 = time.time()
    master, lp_sol = vrp.solve_cg()
    _log.info("root LP=%.1f", lp_sol.cost)
    path_by_id = {p.id: p for p in vrp.paths}

    rmh_sol = restricted_master_heuristic(master)
    rmh_obj = rmh_sol.cost
    _log.info("RMH incumbent (UB)=%.1f, time=%.1fs",
              rmh_obj, time.time() - t0)
    _log.info("RMH solution:")
    for pid, v in rmh_sol.value_by_var_id.items():
        if v > 0.5:
            p = path_by_id[pid]
            _log.info("  cost=%.2f  %s", p.cost, p.visited_nodes)

    # For diving, refresh the LP after each fix.
    def run_cg() -> object:
        return master.solve(relax=True)

    t0 = time.time()
    dive_sol = plain_dive(master, run_cg)
    dive_obj = dive_sol.cost if dive_sol is not None else math.inf
    _log.info("dive incumbent (UB)=%.1f, time=%.1fs",
              dive_obj, time.time() - t0)
    if dive_sol is not None:
        _log.info("dive solution:")
        for pid, v in dive_sol.value_by_var_id.items():
            if v > 0.5:
                p = path_by_id[pid]
                _log.info("  cost=%.2f  %s", p.cost, p.visited_nodes)
    _log.info("summary: RMH UB=%.1f   dive UB=%.1f   LP=%.1f",
              rmh_obj, dive_obj, lp_sol.cost)
    return 0


if __name__ == "__main__":
    sys.exit(main())
