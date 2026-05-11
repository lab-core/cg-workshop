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

from rcspp.graph import ResourceGraph
from rcspp.resource import (
    MinMaxFeasibilityFunction,
    RealAdditionExtensionFunction,
    RealTrivialFeasibilityFunction,
    RealValueCostFunction,
    RealValueDominanceFunction,
    TimeWindowExtensionFunction,
    TimeWindowFeasibilityFunction,
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
            RealAdditionExtensionFunction(),
            RealTrivialFeasibilityFunction(),
            RealValueCostFunction(),
            RealValueDominanceFunction(),
        )
        # Resource 1: TIME (with time windows).
        self.graph.add_real_resource(
            TimeWindowExtensionFunction(self._min_tw),
            TimeWindowFeasibilityFunction(self._max_tw),
            RealValueCostFunction(),
            RealValueDominanceFunction(),
        )
        # Resource 2: DEMAND / load.
        self.graph.add_real_resource(
            RealAdditionExtensionFunction(),
            MinMaxFeasibilityFunction(0.0, self.instance.get_capacity()),
            RealValueCostFunction(),
            RealValueDominanceFunction(),
        )

    # ----------------------------------------------------------------
    #  EX-B.1 -- nodes and arcs
    # ----------------------------------------------------------------
    def build(self, dual_by_id: dict[int, float]) -> None:
        """Add nodes + arcs to the graph using the given dual prices.

        Conventions:
        * pi_0 = sigma (vehicle-count dual) for the depot.
        * sink_id = len(customers); same physical depot but a separate
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

    # ----------------------------------------------------------------
    #  EX-B.2 -- arc cost and resource increments
    # ----------------------------------------------------------------
    def _add_arc(self, origin_id: int, dest_id: int,
                 origin: Customer, dest: Customer,
                 dual_by_id: dict[int, float], arc_id: int) -> None:
        # Skip arcs that B&P has forbidden (Exercise E).
        if (origin_id, dest_id) in self.forbidden_arcs:        # EX-E.4
            return                                              # EX-E.4

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
        # TODO: compute the arc cost and three resource increments,
        # then call self.graph.add_arc(...).
        #
        # Convention used in this workshop:
        #   reduced_cost = distance - pi_origin
        # i.e. the dual is paid when *leaving* a customer.
        # For the depot: pi_0 = sigma (vehicle-count dual), set by the
        # CG loop via dual_by_id[depot_id] = sol.sigma before pricing.
        #
        # Resource increments (in the order registered above):
        #   resource 0 (cost)   = reduced_cost
        #   resource 1 (time)   = origin.service_time + distance
        #   resource 2 (demand) = dest.demand
        #
        # API to call:
        #   self.graph.add_arc(
        #       ([(reduced_cost,), (travel_time,), (demand,)],),
        #       origin_id, dest_id, arc_id, reduced_cost,
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
