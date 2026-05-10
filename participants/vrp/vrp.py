"""Top-level CG / B&P driver for the VRPTW lab.

Glues together
    instance + master + pricer + bound + diving + bnp.

Holes (cross-referenced in lab.pdf):
    EX-A.3  --  generate_initial_paths (one round-trip per customer).
    EX-B.3  --  solve_subproblem (call PricingGraph.build then .solve).
    EX-C.2  --  the CG main loop with multi-column return.
    EX-C.3  --  Wentges dual smoothing (optional, recommended).
    EX-C.4  --  per-iteration log line including the Lagrangian bound.
"""

from __future__ import annotations

import math
import time
from dataclasses import dataclass, field
from typing import Optional

from vrp.cg.bound import lagrangian_bound
from vrp.cg.master_problem import MasterProblem
from vrp.cg.mp_solution import MPSolution
from vrp.cg.path import Path
from vrp.cg.pricing import PricingGraph, euclidean
from vrp.instance import Instance
from vrp.log import get_logger


_log = get_logger("cg")


@dataclass
class CGStats:
    iterations: int = 0
    nb_columns_added: int = 0
    final_lp: float = math.inf
    final_lb: float = -math.inf
    pricing_time_s: float = 0.0
    master_time_s: float = 0.0


class VRP:
    EPSILON = 1e-7

    def __init__(self, instance: Instance,
                 forbidden_arcs: Optional[set[tuple[int, int]]] = None,
                 forced_arcs: Optional[set[tuple[int, int]]] = None,
                 K_MAX: int = 50,
                 alpha: float = 0.0):
        """
        Parameters
        ----------
        instance        the parsed VRPTW instance.
        forbidden_arcs  forbidden arcs (used by B&P down branches).
        forced_arcs     forced arcs (used by B&P up branches).
        K_MAX           cap on columns added per CG iteration.
        alpha           Wentges smoothing parameter; 0 disables smoothing.
        """
        self.instance = instance
        self.forbidden_arcs = forbidden_arcs or set()
        self.forced_arcs = forced_arcs or set()
        self.K_MAX = K_MAX
        self.alpha = alpha

        self.paths: list[Path] = []
        self._next_path_id = 0
        self._prev_dual_by_id: dict[int, float] = {}
        self.stats = CGStats()

    # ----------------------------------------------------------------
    #  EX-A.3 -- initial pool: one round-trip per customer
    # ----------------------------------------------------------------
    def generate_initial_paths(self) -> list[Path]:
        depot = self.instance.get_depot_customer()
        # === EX-A.3 ===========================================
        # TODO: for every customer in
        # self.instance.get_demand_customers_id() (depot excluded), build
        # the route [depot.id, customer.id, depot.id] with cost equal to
        # 2 * Euclidean distance.  Store the routes in self.paths and
        # return them.
        # =====================================================
        raise NotImplementedError("EX-A.3: generate initial paths")

    def _new_path(self, cost: float, visited_nodes) -> Path:
        p = Path(self._next_path_id, cost, visited_nodes)
        self._next_path_id += 1
        return p

    # ----------------------------------------------------------------
    #  EX-B.3 -- pricing call
    # ----------------------------------------------------------------
    def solve_subproblem(self, dual_by_id: dict[int, float]):
        """Build a PricingGraph for the current duals and solve it."""
        # === EX-B.3 ===========================================
        # TODO:
        #   1. Make sure dual_by_id contains an entry for the depot:
        #      dual_by_id[self.instance.get_depot_customer().id] = 0.0
        #   2. Build a PricingGraph(...).build(dual_by_id).
        #   3. Return the result of graph.solve()  (sorted ascending
        #      by reduced cost; we will filter < -EPSILON in the loop).
        # =====================================================
        raise NotImplementedError("EX-B.3: pricing graph build & solve")

    # ----------------------------------------------------------------
    #  EX-C.2 ... EX-C.4 -- the CG main loop
    # ----------------------------------------------------------------
    def solve_cg(self, verbose: bool = True,
                 incumbent_ub: float = math.inf) -> tuple[MasterProblem, MPSolution]:
        """Run column generation until no negative-reduced-cost column.

        IMPORTANT
        ---------
        We build the master ONCE (via ``construct_model``).  Every CG
        iteration just calls ``master.add_column(...)`` on the new columns
        and re-solves the LP.  HiGHS warm-starts the simplex from the
        previous basis -- this is the single biggest performance win.
        Don't be tempted to rebuild from scratch each iteration.

        ``verbose`` is kept for backwards compatibility, but progress now
        comes from the ``vrp.cg`` logger (configure via ``vrp.log``).
        """
        if not self.paths:
            self.generate_initial_paths()
        master = MasterProblem(
            self.instance.get_demand_customers_id(),
            self.instance.get_nb_vehicles(),
        )
        master.construct_model(self.paths)

        _log.info("CG start: %d initial columns, K=%d vehicles, K_MAX=%d, alpha=%.2f, UB=%s",
                  len(self.paths), self.instance.get_nb_vehicles(),
                  self.K_MAX, self.alpha,
                  f"{incumbent_ub:.2f}" if math.isfinite(incumbent_ub) else "inf")
        _log.info("%-4s %-5s %-10s %-10s %-10s %-7s %-10s",
                  "iter", "cols", "LP", "LB", "UB", "gap%", "min_rc")

        nb_iter = 0
        min_redcost = -math.inf
        sol = MPSolution()

        while min_redcost < -self.EPSILON:
            t0 = time.time()
            sol = master.solve(relax=True)
            self.stats.master_time_s += time.time() - t0

            duals = dict(sol.dual_by_var_id)

            # === EX-C.3 -- Wentges smoothing (optional) =========
            # TODO: if self.alpha > 0 and self._prev_dual_by_id is
            # non-empty, replace duals[i] by
            #   alpha * prev[i] + (1-alpha) * duals[i].
            # Save the (smoothed) duals into self._prev_dual_by_id.
            # ====================================================

            t0 = time.time()
            sols = self.solve_subproblem(duals)
            self.stats.pricing_time_s += time.time() - t0
            min_redcost = 0

            # === EX-C.2 -- multi-column add ====================
            # TODO:
            #   1. Cap the pricer output at self.K_MAX entries.
            #   2. For each rcspp.Solution `s` with s.cost < -EPSILON,
            #      build a Path with cost = real distance of the route
            #      (use _route_cost(s)) and visited_nodes = s.path_node_ids,
            #      then call master.add_column(path) AND store it in
            #      self.paths.  Update self.stats.nb_columns_added.
            #   3. min_redcost = min(s.cost for s in sols, default=+inf)
            # ====================================================
            raise NotImplementedError("EX-C.2: multi-column add to master")

            # === EX-C.4 -- Lagrangian bound + log ==============
            # TODO: compute
            #   LB = lagrangian_bound(duals, sol.sigma, sols, K)
            # where K = self.instance.get_nb_vehicles().  If verbose, print
            #   nb_iter   #cols   sol.cost   LB   gap%.
            # ====================================================
            LB = math.inf  # placeholder

            n_cols = len(master.col_by_path_id)
            ub_str = (f"{incumbent_ub:.2f}"
                      if math.isfinite(incumbent_ub) else "inf")
            if math.isfinite(LB):
                gap = 100.0 * (sol.cost - LB) / abs(LB) if LB != 0 else math.inf
                _log.info("%-4d %-5d %-10.2f %-10.2f %-10s %-7.3f %-10.2f",
                          nb_iter, n_cols, sol.cost, LB, ub_str,
                          gap, min_redcost)
            else:
                _log.info("%-4d %-5d %-10.2f %-10s %-10s %-7s %-10.2f",
                          nb_iter, n_cols, sol.cost, "-", ub_str, "-",
                          min_redcost)

            # Allow LB-vs-UB early termination at the root.
            if math.isfinite(incumbent_ub) and LB >= incumbent_ub - self.EPSILON:
                _log.info("CG cut short: LB=%.2f >= UB=%.2f", LB, incumbent_ub)
                break

            nb_iter += 1

        self.stats.iterations = nb_iter
        self.stats.final_lp = sol.cost
        _log.info("CG done in %d iters, LP=%.2f, LB=%.2f, UB=%s, "
                  "%d columns added, pricing=%.2fs, master=%.2fs",
                  nb_iter, self.stats.final_lp, self.stats.final_lb,
                  f"{incumbent_ub:.2f}" if math.isfinite(incumbent_ub) else "inf",
                  self.stats.nb_columns_added,
                  self.stats.pricing_time_s, self.stats.master_time_s)
        return master, sol

    # ----------------------------------------------------------------
    #  Convenience: cost of an rcspp.Solution as a *real* route cost
    #  (we translate from reduced cost back to distance).
    # ----------------------------------------------------------------
    def _route_cost(self, solution) -> float:
        """Recompute distance(route) from the visited node ids."""
        nodes = list(solution.path_node_ids)
        cust = self.instance.get_customers_by_id()
        depot = self.instance.get_depot_customer()
        sink_id = len(cust)
        total = 0.0
        for u, v in zip(nodes[:-1], nodes[1:]):
            cu = cust[u] if u != sink_id else depot
            cv = cust[v] if v != sink_id else depot
            total += euclidean(cu, cv)
        return total
