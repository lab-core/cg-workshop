"""Pricing problem for the VRPTW master.

The pricer is a Resource-Constrained Shortest Path (RCSPP) on a graph
with three resources: cost, time, demand.  Arc cost = d_uv - pi_v - sigma_arc
where sigma_arc absorbs the vehicle-count dual on depot-leaving arcs.

Holes:
    EX-B.1  --  build the pricing graph (resources, nodes, arcs).
    EX-B.2  --  fill in arc costs and resource increments per arc.
    EX-E.4  --  remove forbidden arcs (B&P down branch).
"""

from __future__ import annotations

import math
from typing import Optional

from vrp.log import get_logger

from rcspp.graph import ResourceGraph, Row
from rcspp.resource import (
    AdditionExtensionFunction,
    MinMaxFeasibilityFunction,
    TimeWindowExtensionFunction,
    TimeWindowFeasibilityFunction,
    TrivialFeasibilityFunction,
    ValueCostFunction,
    ValueDominanceFunction,
)

from vrp.instance import Customer, Instance


_log = get_logger("pricing")


def euclidean(a: Customer, b: Customer) -> float:
    return math.sqrt((b.pos_x - a.pos_x) ** 2 + (b.pos_y - a.pos_y) ** 2)


class PricingGraph:
    """Builds the rcspp.ResourceGraph for one set of duals."""

    def __init__(self, instance: Instance,
                 forbidden_arcs: Optional[set[tuple[int, int]]] = None,
                 forced_arcs: Optional[set[tuple[int, int]]] = None):
        self.instance = instance
        self.forbidden_arcs = forbidden_arcs or set()
        self.forced_arcs = forced_arcs or set()
        self._depot_id = instance.get_depot_customer().id
        self._sink_id = len(instance.get_customers_by_id())

        self._min_tw: dict[int, float] = {}
        self._max_tw: dict[int, float] = {}
        self._init_time_windows()

        self.graph = ResourceGraph()
        self._register_resources()

    # ----------------------------------------------------------------
    #  Resources: cost, time, demand
    # ----------------------------------------------------------------
    def _init_time_windows(self) -> None:
        for cid, c in self.instance.get_customers_by_id().items():
            self._min_tw[cid] = c.ready_time
            self._max_tw[cid] = c.due_time
        sink_id = len(self.instance.get_customers_by_id())
        self._min_tw[sink_id] = 0.0
        self._max_tw[sink_id] = math.inf

    def _register_resources(self) -> None:
        # Resource 0: COST (cumulative reduced cost).
        self.graph.add_real_resource(
            AdditionExtensionFunction(),
            TrivialFeasibilityFunction(),
            ValueCostFunction(),
            ValueDominanceFunction(),
        )
        # Resource 1: TIME (with time windows).
        self.graph.add_real_resource(
            TimeWindowExtensionFunction(self._min_tw),
            TimeWindowFeasibilityFunction(self._max_tw),
            ValueCostFunction(),
            ValueDominanceFunction(),
        )
        # Resource 2: DEMAND / load.
        self.graph.add_real_resource(
            AdditionExtensionFunction(),
            MinMaxFeasibilityFunction(0.0, self.instance.get_capacity()),
            ValueCostFunction(),
            ValueDominanceFunction(),
        )

    # ----------------------------------------------------------------
    #  EX-B.1 -- nodes and arcs
    # ----------------------------------------------------------------
    def build(self) -> None:
        """Add nodes + arcs to the graph with base costs and dual rows.

        The graph is built once; call update_costs(dual_by_id) before each solve.

        Conventions:
        * sink_id = len(customers): same physical depot but a separate
          node so that empty paths are filtered out by the labelling.
        """
        # === EX-B.1 ===========================================
        # TODO:
        #   1. Add one node per customer using
        #          self.graph.add_node(node_id, is_source, is_sink=False)
        #      with is_source=True for the depot and False otherwise.
        #   2. Also add a sink node with id sink_id = len(customers),
        #      is_source=False, is_sink=True.
        #   3. For every (origin, destination) pair, call
        #      self._add_arc(...) below to build the arcs.
        #      Skip the self-loop, and add an arc to the sink for every
        #      customer (sink_customer = depot, but node id = sink_id).
        # =====================================================
        raise NotImplementedError("EX-B.1: build pricing graph")

    def update_costs(self, dual_by_id: dict[int, float]) -> None:
        """Recompute arc reduced costs from dual prices without rebuilding the graph."""
        self.graph.update_reduced_costs(dual_by_id)

    # ----------------------------------------------------------------
    #  EX-B.2 -- arc cost and resource increments
    #  EX-E.4 -- skip forbidden arcs (B&P down branches)
    # ----------------------------------------------------------------
    def _add_arc(self, origin_id: int, dest_id: int,
                 origin: Customer, dest: Customer,
                 arc_id: int) -> None:
        if (origin_id, dest_id) in self.forbidden_arcs:
            return

        # Skip arcs that violate forced arc constraints (B&P up branch).
        # For forced arc (u, v): from u only v is reachable; into v only u may arrive.
        # The depot appears as sink_id for incoming arcs in the pricing graph.
        for (fu, fv) in self.forced_arcs:
            fv_g = self._sink_id if fv == self._depot_id else fv
            if origin_id == fu and dest_id != fv_g:
                return
            if dest_id == fv_g and origin_id != fu:
                return

        # === EX-B.2 ===========================================
        # TODO: compute the three resource increments and add the arc.
        #
        # Convention: reduced_cost = distance - pi_origin
        # Instead of baking the dual in, store the *base cost* (distance)
        # and a dual Row so update_costs() can update reduced costs cheaply:
        #   rc = arc.cost - sum(row.coefficient * dual[row.index])
        #      = distance - 1.0 * pi_origin
        #
        # Special case: depot→sink arc is inert (prevents empty routes).
        # Assign infinite base cost and no dual row:
        #   if origin.depot and dest.depot: use math.inf as cost, no Row.
        #
        # Resource increments (in the order registered above):
        #   resource 0 (cost)   = distance  (or math.inf for depot→sink)
        #   resource 1 (time)   = origin.service_time + distance
        #   resource 2 (demand) = dest.demand
        #
        # API to call (normal arc):
        #   self.graph.add_arc(
        #       (distance, travel_time, demand),
        #       origin_id, dest_id, arc_id, distance,
        #       [Row(origin_id, 1.0)],
        #   )
        # API to call (depot→sink inert arc):
        #   self.graph.add_arc(
        #       (math.inf, travel_time, demand),
        #       origin_id, dest_id, arc_id, math.inf,
        #   )
        # =====================================================
        raise NotImplementedError("EX-B.2: arc cost & resource increments")

    # ----------------------------------------------------------------
    #  Solving
    # ----------------------------------------------------------------
    def solve(self):
        """Run label-setting; return list[Solution] sorted by reduced cost."""
        sols = self.graph.solve()
        if sols:
            _log.debug("pricing returned %d sink label(s); best redcost=%.2f",
                       len(sols), sols[0].cost)
        else:
            _log.debug("pricing returned no negative-reduced-cost label")
        return sols
