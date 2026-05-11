"""Exercise E check script -- arc-branching B&P."""

import argparse
import math
import os
import signal
import sys
import time

from vrp.cg.bnp import (
    BnPNode,
    BnPIncumbent,
    branch_and_price,
)
from vrp.cg.diving import plain_dive, restricted_master_heuristic
from vrp.instance import Instance
from vrp.instance_reader import InstanceReader
from vrp.log import configure as configure_logging, get_logger
from vrp.tests._paths import find_instance
from vrp.vrp import VRP


_log = get_logger("ex.E")


def make_bnp_callbacks(inst: Instance, K_MAX: int, alpha: float = 0.0):
    """Return (run_cg_at_node, run_dive, run_rmh) callbacks for branch_and_price.

    Parameters
    ----------
    inst    the parsed VRPTW instance.
    K_MAX   max columns added per pricing call.
    alpha   Wentges smoothing parameter (0 = disabled).
    """
    def run_cg_at_node(node: BnPNode, incumbent: BnPIncumbent) -> None:
        v = VRP(inst, forbidden_arcs=node.forbidden,
                forced_arcs=node.forced, K_MAX=K_MAX, alpha=alpha)
        v.paths = list(node.pool)
        if v.paths:
            v._next_path_id = max(p.id for p in v.paths) + 1
        m, s = v.solve_cg(incumbent_ub=incumbent.cost)
        node.sol = s
        node.lp_value = s.cost
        node.lb = v.stats.final_lb  # true LB; may exceed s.cost on early CG exit
        node.pool = list(v.paths)
        node.master = m

    def run_dive(node: BnPNode, incumbent: BnPIncumbent) -> float:
        def _cg():
            return node.master.solve(relax=True)
        sol = plain_dive(node.master, _cg, ub=incumbent.cost)
        if sol is None:
            return math.inf
        ub = sol.cost
        if ub < incumbent.cost:
            incumbent.update_sol(sol, node.pool)
        return ub

    def run_rmh(node: BnPNode, incumbent: BnPIncumbent) -> float:
        sol = restricted_master_heuristic(node.master)
        ub = sol.cost
        if ub < incumbent.cost:
            incumbent.update_sol(sol, node.pool)
        return ub

    return run_cg_at_node, run_dive, run_rmh


def run_bnp(inst: Instance, K_MAX: int = 50, alpha: float = 0.0,
            rmh_every: int = 10, gap_pct: float = 0.0,
            depth_first: bool = True) -> BnPIncumbent:
    """Run a full root-CG + B&P on *inst* and return the BnPIncumbent."""
    vrp_root = VRP(inst, K_MAX=K_MAX, alpha=alpha)
    master, lp_sol = vrp_root.solve_cg()

    root = BnPNode(
        forbidden=set(), forced=set(),
        pool=list(vrp_root.paths),
        lp_value=lp_sol.cost,
        lb=lp_sol.cost,
        sol=lp_sol,
        master=master,
    )

    run_cg_at_node, run_dive, run_rmh = make_bnp_callbacks(inst, K_MAX, alpha)

    return branch_and_price(
        root, run_cg_at_node, run_dive, run_rmh,
        rmh_every=rmh_every, gap_pct=gap_pct,
        depth_first=depth_first,
        demand_node_ids=set(inst.get_demand_customers_id()),
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", default="toy.txt")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="enable DEBUG logs")
    ap.add_argument("--K", type=int, default=50)
    ap.add_argument("--rmh-every", type=int, default=10,
                    help="run RMH at every B&P node whose id is a multiple "
                         "of this (default 10)")
    ap.add_argument("--gap", type=float, default=0.0,
                    help="stop B&P when UB-LB gap %% is at most this value (0 = exact)")
    ap.add_argument("--no-depth-first", action="store_true",
                    help="use pure best-first search instead of diving into the up-child")
    args = ap.parse_args()
    configure_logging(verbose=args.verbose)

    inst = InstanceReader(find_instance(args.instance)).read()
    _log.info("instance: %s", args.instance)

    t0 = time.time()
    incumbent = run_bnp(
        inst, K_MAX=args.K,
        rmh_every=args.rmh_every, gap_pct=args.gap,
        depth_first=not args.no_depth_first,
    )
    _log.info("done in %.1fs, optimum=%.2f", time.time() - t0, incumbent.cost)
    if incumbent.sol:
        _log.info("solution (%d routes):", len(incumbent.sol))
        for route in incumbent.sol:
            _log.info("  cost=%.2f  %s", route.cost, route.visited_nodes)
    return 0


if __name__ == "__main__":
    signal.signal(signal.SIGINT, lambda *_: os._exit(1))
    sys.exit(main())
