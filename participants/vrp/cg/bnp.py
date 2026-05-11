"""Arc-branching branch-and-price.

A node is described by:
    - a unique incremental id and a depth in the tree,
    - a set of forbidden arcs (down-branches imposed on the way down),
    - a set of forced     arcs (up-branches),
    - a column pool restricted to columns compatible with both sets,
    - an LP value and a Lagrangian bound (set after CG runs at the node).

Holes:
    EX-E.1  --  aggregated arc flow ybar_uv from x_p and visited nodes.
    EX-E.2  --  pick the most-fractional arc (closest to 0.5).
    EX-E.3  --  build the two children (forbid / force) of a node.

The B&P search loop itself (best-first over LB, with the dive-at-root /
RMH-every-X-nodes heuristic schedule) is fully provided -- you do not
need to modify it.
"""

from __future__ import annotations

import itertools
import math
from dataclasses import dataclass, field
from typing import Callable, Optional

from vrp.cg.path import Path
from vrp.cg.mp_solution import MPSolution
from vrp.log import get_logger


_log = get_logger("bnp")


# --------------------------------------------------------------------
#  BnPNode
# --------------------------------------------------------------------
_node_id_counter = itertools.count()


def _next_node_id() -> int:
    return next(_node_id_counter)


@dataclass
class BnPNode:
    """One node in the B&P tree.

    Attributes
    ----------
    id         incremental, unique inside this Python process.
    depth      0 at the root; child = parent.depth + 1.
    forbidden  set of (u, v) arcs forbidden in this subtree.
    forced     set of (u, v) arcs forced in this subtree.
    pool       columns inherited from the parent and compatible with
               both arc sets.
    lp_value   LP value at this node (set by run_cg).
    lb         Lagrangian lower bound (also set by run_cg).
    sol        MPSolution at this node (LP).
    master     handle on the (already populated) MasterProblem.
    """
    id:        int                       = field(default_factory=_next_node_id)
    depth:     int                       = 0
    forbidden: set[tuple[int, int]]      = field(default_factory=set)
    forced:    set[tuple[int, int]]      = field(default_factory=set)
    pool:      list[Path]                = field(default_factory=list)
    lp_value:  float                     = math.inf
    lb:        float                     = -math.inf
    sol:       Optional[MPSolution]      = None
    master:    object                    = None  # MasterProblem after CG


@dataclass
class BnPIncumbent:
    node: Optional[BnPNode] = None
    cost: float = math.inf
    sol:  Optional[list[Path]] = None

    def update_sol(self, mp_sol: MPSolution, pool: list[Path]) -> None:
        """Extract integer routes from *mp_sol*, store them, and log them."""
        path_by_id = {p.id: p for p in pool}
        routes = [path_by_id[pid]
                  for pid, v in mp_sol.value_by_var_id.items()
                  if v > 0.5 and pid in path_by_id]
        self.sol = routes
        _log.info("incumbent solution (%d routes, cost=%.2f):",
                  len(routes), self.cost)


# --------------------------------------------------------------------
#  EX-E.1 -- aggregated arc flow
# --------------------------------------------------------------------
def aggregated_arc_flow(sol: MPSolution,
                        path_by_id: dict[int, Path]) -> dict[tuple[int, int], float]:
    """Return ybar_uv = sum_{p : (u,v) in p} xbar_p."""
    # === EX-E.1 ===========================================
    # TODO: iterate over sol.value_by_var_id; for each path id with
    # value > 0, walk through path.visited_nodes pair-by-pair and add
    # the value to a dict keyed by the (u,v) tuple.
    # =====================================================
    raise NotImplementedError("EX-E.1: aggregated arc flow")


# --------------------------------------------------------------------
#  EX-E.2 -- pick the most-fractional arc
# --------------------------------------------------------------------
def most_fractional_arc(ybar: dict[tuple[int, int], float],
                        eps: float = 1e-6) -> Optional[tuple[int, int]]:
    """Return the arc (u,v) whose ybar value is closest to 0.5.

    Return None if every arc is essentially integer (LP is integer or the
    fractional structure is hidden in another constraint family).
    """
    # === EX-E.2 ===========================================
    # TODO: find argmin_{(u,v)} |ybar_uv - 0.5| among entries with
    # eps < ybar_uv < 1 - eps.
    # =====================================================
    raise NotImplementedError("EX-E.2: most-fractional arc")


# --------------------------------------------------------------------
#  EX-E.3 -- build the two children
# --------------------------------------------------------------------
def make_children(parent: BnPNode, arc: tuple[int, int]) -> tuple[BnPNode, BnPNode]:
    """Return (down_child, up_child) for branching on the given arc.

    Down (forbid (u,v)):
        - inherit parent.forbidden | {(u,v)}
        - drop columns that *use* (u,v).

    Up (force (u,v)):
        - inherit parent.forced | {(u,v)}
        - drop columns that visit u or v but do not contain the arc
          (those routes will never be compatible with the contraction).
    """
    # === EX-E.3 ===========================================
    # TODO: build two BnPNode instances:
    #   - shared pool filter using path.uses_arc(u, v) and path.visits(.).
    #   - depth = parent.depth + 1.
    #   - id auto via _next_node_id() (handled by the dataclass default).
    # Return (down, up) in that order.
    # =====================================================
    raise NotImplementedError("EX-E.3: make B&P children")


# --------------------------------------------------------------------
#  B&P main loop -- FULLY PROVIDED
# --------------------------------------------------------------------
def branch_and_price(
    root: BnPNode,
    run_cg: Callable[[BnPNode, BnPIncumbent], None],
    run_dive: Callable[[BnPNode, BnPIncumbent], float],
    run_rmh:  Callable[[BnPNode, BnPIncumbent], float],
    rmh_every: int = 10,
    eps: float = 1e-6,
    gap_pct: float = 0.0,
) -> BnPIncumbent:
    """Best-first arc-branching B&P with Lagrangian pruning.

    Parameters
    ----------
    root         initial BnPNode (empty forbid/force sets, root pool).
    run_cg       function that runs CG on a node IN PLACE -- after the
                 call, node.lp_value, node.lb, node.sol, node.master must
                 be set.
    run_dive     incumbent heuristic used at the root only.
    run_rmh      cheap incumbent heuristic (binary MIP on node pool).
    rmh_every    run RMH at every node whose id is a multiple of this.

    Returns
    -------
    (best_obj, best_node)
    """
    open_nodes: list[BnPNode] = [root]
    incumbent = BnPIncumbent()
    nodes_processed = 0
    global_lb: float = -math.inf

    _log.info("B&P start: root LB=%.2f, %d columns in pool",
              root.lb, len(root.pool))

    child = None  # for depth-first: the child we just created and want to dive into
    while open_nodes:
        # ---- depth-first: always dive into just the created child (child is not None) ----
        if child is not None:
            node = child
        else:
            open_nodes.sort(key=lambda n: n.lb)
            node = open_nodes.pop(0)

        # reset child for the next iteration
        child = None

        if node.lb >= incumbent.cost - eps:
            _log.info("node %d (depth %d) pruned (LB=%.2f >= inc=%.2f)",
                      node.id, node.depth, node.lb, incumbent.cost)
            continue

        # ---- solve the node's LP by CG ----
        _log.info("processing node %d (depth %d, %d open nodes left, "
                  "incumbent=%.2f)",
                  node.id, node.depth, len(open_nodes), incumbent.cost)
        run_cg(node, incumbent)
        nodes_processed += 1
        open_lbs = [n.lb for n in open_nodes if n.lb > -math.inf]
        global_lb = min([node.lb] + open_lbs)
        if math.isfinite(incumbent.cost) and math.isfinite(global_lb):
            gap = 100.0 * (incumbent.cost - global_lb) / abs(incumbent.cost)
            _log.info("node %d: node LB=%.2f  global LB=%.2f  UB=%.2f  gap=%.2f%%",
                      node.id, node.lb, global_lb, incumbent.cost, gap)
            if gap_pct > 0.0 and gap <= gap_pct:
                _log.info("B&P stopped: gap=%.3f%% <= %.2f%%", gap, gap_pct)
                break
        else:
            _log.info("node %d: node LB=%.2f  global LB=%.2f  UB=%.2f",
                      node.id, node.lb, global_lb, incumbent.cost)

        if node.lb >= incumbent.cost - eps:
            _log.info("node %d pruned after CG (LB=%.2f >= inc=%.2f)",
                      node.id, node.lb, incumbent.cost)
            continue

        # ---- incumbent: LP integer takes priority, else heuristic ----
        ybar = aggregated_arc_flow(node.sol, {p.id: p for p in node.pool})
        arc = most_fractional_arc(ybar, eps=eps)
        if arc is None:  # integer LP solution
            ub = node.lp_value
        elif node.depth == 0:
            ub = run_dive(node, incumbent)
        elif node.id % rmh_every == 0:
            ub = run_rmh(node, incumbent)
        else:
            ub = math.inf
        if ub < incumbent.cost:
            incumbent.cost = ub
            incumbent.node = node
            if arc is None and node.sol is not None:
                incumbent.update_sol(node.sol, node.pool)
            _log.info("new incumbent %.2f at node %d", ub, node.id)
        if arc is None:
            continue

        # ---- branch ----
        down, up = make_children(node, arc)
        _log.info("node %d (depth %d) branch on %s, ybar=%.2f "
                  "-> children %d, %d",
                  node.id, node.depth, arc, ybar[arc], down.id, up.id)
        open_nodes.append(down)
        child = up  # keep up to branch immediately on it (depth-first)

    n_routes = len(incumbent.sol) if incumbent.sol is not None else "?"
    _log.info("B&P done in %d nodes, optimum=%.2f (%s routes), global LB=%.2f",
              nodes_processed, incumbent.cost, n_routes, global_lb)
    _log.info("best solution:")
    if incumbent.sol:
        for route in incumbent.sol:
            _log.info("  cost=%.2f  %s", route.cost, route.visited_nodes)
    else:
        _log.info("  (none found)")
    return incumbent
