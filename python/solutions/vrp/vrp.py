"""Reference CG / B&P driver."""

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
    lp_history: list[float] = field(default_factory=list)
    lb_history: list[float] = field(default_factory=list)


class VRP:
    EPSILON = 1e-7

    def __init__(self, instance: Instance,
                 forbidden_arcs: Optional[set[tuple[int, int]]] = None,
                 forced_arcs: Optional[set[tuple[int, int]]] = None,
                 K_MAX: int = 50,
                 alpha: float = 0.0):
        self.instance = instance
        self.forbidden_arcs = forbidden_arcs or set()
        self.forced_arcs = forced_arcs or set()
        self.K_MAX = K_MAX
        self.alpha = alpha
        self.paths: list[Path] = []
        self._next_path_id = 0
        self._prev_dual_by_id: dict[int, float] = {}
        self._path_signatures: set[tuple] = set()
        self.stats = CGStats()
        self._pricing_graph: Optional[PricingGraph] = None

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
        cust = self.instance.get_customers_by_id()
        for cid in self.instance.get_demand_customers_id():
            c = cust[cid]
            d = euclidean(depot, c)
            self.paths.append(self._new_path(2.0 * d, [depot.id, cid, depot.id]))
        return self.paths

    def _new_path(self, cost: float, visited_nodes: List[int]) -> Path:
        p = Path(self._next_path_id, cost, visited_nodes)
        self._next_path_id += 1
        self._path_signatures.add(tuple(p.visited_nodes))
        return p

    # ----------------------------------------------------------------
    #  EX-B.3 -- pricing call
    # ----------------------------------------------------------------
    def solve_subproblem(self, dual_by_id: dict[int, float]):
        """Update arc reduced costs from duals and solve the pricing problem."""
        # === EX-B.3 ===========================================
        # TODO:
        #   1. Build the graph once (lazy): if self._pricing_graph is None,
        #      create PricingGraph(...) and call .build() (no duals needed).
        #      Store it in self._pricing_graph.
        #   2. Call self._pricing_graph.update_costs(dual_by_id) to set
        #      the current reduced costs, then return .solve().
        # =====================================================
        if self._pricing_graph is None:
            self._pricing_graph = PricingGraph(self.instance,
                                               forbidden_arcs=self.forbidden_arcs,
                                               forced_arcs=self.forced_arcs)
            self._pricing_graph.build()
        self._pricing_graph.update_costs(dual_by_id)
        return self._pricing_graph.solve()

    # ----------------------------------------------------------------
    #  EX-C.* -- the CG main loop
    # ----------------------------------------------------------------
    def solve_cg(self, verbose: bool = True,
                 incumbent_ub: float = math.inf,
                 gap_pct: float = 0.0) -> tuple[MasterProblem, MPSolution]:
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
        _log.info("%-4s %-5s %-15s %-15s %-10s %-7s %-10s",
                  "iter", "cols", "LP", "LB", "UB", "gap%", "min_rc")

        nb_iter = 0
        min_redcost = -math.inf
        sol = MPSolution()

        while min_redcost < -self.EPSILON:
            t0 = time.time()
            sol = master.solve(relax=True)
            self.stats.master_time_s += time.time() - t0

            duals = dict(sol.dual_by_var_id)
            duals[self.instance.get_depot_customer().id] = sol.sigma

            # === EX-C.2 -- Wentges smoothing (optional) =========
            # TODO: if self.alpha > 0 and self._prev_dual_by_id is
            # non-empty, replace duals[i] by
            #   alpha * prev[i] + (1-alpha) * duals[i].
            # Save the (smoothed) duals into self._prev_dual_by_id.
            # ====================================================
            if self.alpha > 0 and self._prev_dual_by_id:
                for k, v in duals.items():
                    pv = self._prev_dual_by_id.get(k, v)
                    duals[k] = self.alpha * pv + (1 - self.alpha) * v
            self._prev_dual_by_id = dict(duals)
            duals[self.instance.get_depot_customer().id] = sol.sigma

            t0 = time.time()
            sols = self.solve_subproblem(duals)
            self.stats.pricing_time_s += time.time() - t0

            # === EX-C.1 -- multi-column add ====================
            # TODO:
            #   1. Cap the pricer output at self.K_MAX entries.
            #   2. For each rcspp.Solution `s` with s.cost < -EPSILON,
            #      build a Path with cost = real distance of the route
            #      (use _route_cost(s)) and visited_nodes = s.path_node_ids,
            #      then call master.add_column(path) AND store it in
            #      self.paths.  Update self.stats.nb_columns_added.
            #   3. min_redcost = min(s.cost for s in sols, default=+inf)
            # ====================================================
            kept = [s for s in sols[: self.K_MAX] if s.cost < -self.EPSILON]
            for s in kept:
                p = self._new_path(self._route_cost(s), s.path_node_ids)
                self.paths.append(p)
                master.add_column(p)
            self.stats.nb_columns_added += len(kept)

            min_redcost = min((s.cost for s in sols), default=math.inf)

            # === EX-C.4 -- Lagrangian bound + log ==============
            # TODO: compute
            #   LB = lagrangian_bound(duals, sol.sigma, sols, K)
            # where K = self.instance.get_nb_vehicles().
            # ====================================================
            LB = lagrangian_bound(duals, sol.sigma, sols,
                                  self.instance.get_nb_vehicles())

            # === EX-C.3 -- Log ==================================
            # TODO: ensure printing the right values for:
            #   nb_iter  n_cols  sol.cost  LB  UB  gap%  min_rc.
            # ====================================================
            self.stats.final_lb = LB
            self.stats.lp_history.append(sol.cost)
            self.stats.lb_history.append(LB)

            n_cols = len(master.col_by_path_id)
            ub_str = (f"{incumbent_ub:.2f}"
                      if math.isfinite(incumbent_ub) else "inf")
            gap = 100.0 * (sol.cost - LB) / abs(LB) if LB != 0 else math.inf
            _log.info("%-4d %-5d %-15.2f %-15.2f %-10s %-7.3f %-10.2f",
                      nb_iter, n_cols, sol.cost, LB, ub_str, gap, min_redcost)

            # Allow LB-vs-UB early termination at the root.
            if math.isfinite(incumbent_ub) and LB >= incumbent_ub - self.EPSILON:
                _log.info("CG cut short: LB=%.2f >= UB=%.2f", LB, incumbent_ub)
                break

            # Gap-based early termination.
            if gap_pct > 0.0 and math.isfinite(LB) and abs(sol.cost) > 1e-10:
                cg_gap = 100.0 * (sol.cost - LB) / abs(sol.cost)
                if cg_gap <= gap_pct:
                    _log.info("CG stopped: gap=%.3f%% <= %.2f%%", cg_gap, gap_pct)
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

    def _route_cost(self, solution) -> float:
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
