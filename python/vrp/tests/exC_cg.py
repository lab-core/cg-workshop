"""Exercise C check script -- run the full CG loop on a small instance."""

import argparse
import os
import signal
import sys
import time

from vrp.instance_reader import InstanceReader
from vrp.log import configure as configure_logging, get_logger
from vrp.tests._paths import find_instance
from vrp.vrp import VRP


_log = get_logger("ex.C")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", default="R101_25.txt")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="enable DEBUG logs")
    ap.add_argument("--nb-cols", type=int, default=50, help="multi-column cap")
    ap.add_argument("--nb-vehicles", type=int, default=25,
                    help="override vehicle count (default: use instance value)")
    ap.add_argument("--alpha", "-a", type=float, default=0.0,
                    help="Wentges smoothing parameter (0 disables)")
    ap.add_argument("--gap", type=float, default=0.0,
                    help="stop CG when LP-LB gap %% is at most this value (0 = exact)")
    args = ap.parse_args()
    configure_logging(verbose=args.verbose)

    inst = InstanceReader(find_instance(args.instance)).read()
    _log.info("instance: %s (%d customers)",
              args.instance, len(inst.get_customers_by_id()) - 1)
    _log.info("nb_cols=%d, alpha=%.2f", args.nb_cols, args.alpha)

    vrp = VRP(inst, nb_cols=args.nb_cols, alpha=args.alpha, K=args.nb_vehicles)
    t0 = time.time()
    master, sol = vrp.solve_cg(gap_pct=args.gap)
    dt = time.time() - t0

    _log.info("iterations    : %d",  vrp.stats.iterations)
    _log.info("columns added : %d",  vrp.stats.nb_columns_added)
    _log.info("LP final      : %.2f", sol.cost)
    _log.info("LB final      : %.2f", vrp.stats.final_lb)
    _log.info("pricing time  : %.2f s", vrp.stats.pricing_time_s)
    _log.info("master  time  : %.2f s", vrp.stats.master_time_s)
    _log.info("total   time  : %.2f s", dt)
    path_by_id = {p.id: p for p in vrp.paths}
    _log.info("LP solution:")
    for pid, v in sorted(sol.value_by_var_id.items()):
        if v > 1e-6:
            p = path_by_id[pid]
            _log.info("  x=%.3f  cost=%.2f  %s", v, p.cost, p.visited_nodes)
    _log.info("OK")
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda *_: os._exit(1))
    sys.exit(main())
