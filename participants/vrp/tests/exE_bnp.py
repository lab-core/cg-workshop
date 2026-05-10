"""Exercise E check script -- arc-branching B&P."""

import argparse
import math
import sys
import time

from vrp.cg.bnp import (
    BnPNode,
    BnPIncumbent,
    branch_and_price,
)
from vrp.cg.diving import plain_dive, restricted_master_heuristic
from vrp.instance_reader import InstanceReader
from vrp.log import configure as configure_logging, get_logger
from vrp.tests._paths import find_instance
from vrp.vrp import VRP


_log = get_logger("ex.E")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--instance", default="toy.txt")
    ap.add_argument("--verbose", "-v", action="store_true",
                    help="enable DEBUG logs")
    ap.add_argument("--K", type=int, default=50)
    ap.add_argument("--rmh-every", type=int, default=10,
                    help="run RMH at every B&P node whose id is a multiple "
                         "of this (default 10)")
    args = ap.parse_args()
    configure_logging(verbose=args.verbose)

    inst = InstanceReader(find_instance(args.instance)).read()
    _log.info("instance: %s", args.instance)

    vrp_root = VRP(inst, K_MAX=args.K)
    master, lp_sol = vrp_root.solve_cg()
    _log.info("root LP=%.2f", lp_sol.cost)

    root = BnPNode(forbidden=set(), forced=set(),
                   pool=list(vrp_root.paths),
                   lp_value=lp_sol.cost,
                   lb=lp_sol.cost,
                   sol=lp_sol,
                   master=master)

    # Run CG for a child node by re-creating a VRP with its arc constraints.
    def run_cg_at_node(node: BnPNode, incumbent: BnPIncumbent) -> None:
        v = VRP(inst, forbidden_arcs=node.forbidden,
                forced_arcs=node.forced, K_MAX=args.K)
        v.paths = list(node.pool)
        m, s = v.solve_cg(incumbent_ub=incumbent.cost)
        node.sol = s
        node.lp_value = s.cost
        node.lb = s.cost                  # post-CG: LP value = LB
        node.pool = list(v.paths)
        node.master = m

    # Heuristics: dive at root, RMH every X nodes.
    def run_dive(node: BnPNode, incumbent: BnPIncumbent) -> float:
        def run_cg() -> object:
            return node.master.solve(relax=True)
        sol = plain_dive(node.master, run_cg, ub=incumbent.cost)
        ub = sol.cost if sol is not None else math.inf
        return ub

    def run_rmh(node: BnPNode, incumbent: BnPIncumbent) -> float:
        ub = restricted_master_heuristic(node.master).cost
        return ub

    t0 = time.time()
    incumbent = branch_and_price(
        root, run_cg_at_node, run_dive, run_rmh, rmh_every=args.rmh_every
    )
    _log.info("done in %.1fs, optimum=%.2f", time.time() - t0, incumbent.cost)
    return 0


if __name__ == "__main__":
    sys.exit(main())
