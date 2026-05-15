"""Reference arc-branching B&P with the same loop as the participant kit."""

from __future__ import annotations

import itertools
import math
import time
from dataclasses import dataclass, field
from typing import Callable, Optional

from vrp.cg.path import Path
from vrp.cg.mp_solution import MPSolution
from vrp.log import get_logger


_log = get_logger("bnp")
_node_id_counter = itertools.count()


def _next_node_id() -> int:
    return next(_node_id_counter)


@dataclass
class BnPNode:
    id:        int                       = field(default_factory=_next_node_id)
    depth:     int                       = 0
    forbidden: set[tuple[int, int]]      = field(default_factory=set)
    forced:    set[tuple[int, int]]      = field(default_factory=set)
    pool:      list[Path]                = field(default_factory=list)
    lp_value:  float                     = math.inf
    lb:        float                     = -math.inf
    sol:       Optional[MPSolution]      = None
    master:    object                    = None


@dataclass
class BnPIncumbent:
    node: Optional[BnPNode] = None
    cost: float = math.inf
    sol:  Optional[list[Path]] = None
    ub_history:   list[float] = field(default_factory=list)
    lb_history:   list[float] = field(default_factory=list)
    time_history: list[float] = field(default_factory=list)

    def update_sol(self, mp_sol: MPSolution, pool: list[Path]) -> None:
        """Extract integer routes from *mp_sol*, store them, and log them."""
        path_by_id = {p.id: p for p in pool}
        routes = [path_by_id[pid]
                  for pid, v in mp_sol.value_by_var_id.items()
                  if v > 0.5 and pid in path_by_id]
        self.sol = routes
        _log.info("incumbent solution (%d routes, cost=%.2f):",
                  len(routes), self.cost)


# ---------------- EX-E.1 ----------------
def aggregated_arc_flow(sol: MPSolution,
                        path_by_id: dict[int, Path]) -> dict[tuple[int, int], float]:
    """Return ybar_uv = sum_{p : (u,v) in p} xbar_p."""
    # === EX-E.1 ===========================================
    # TODO: iterate over sol.value_by_var_id; for each path id with
    # value > 0, walk through path.visited_nodes pair-by-pair and add
    # the value to a dict keyed by the (u,v) tuple.
    # =====================================================
    y: dict[tuple[int, int], float] = {}
    for pid, v in sol.value_by_var_id.items():
        if v <= 1e-9:
            continue
        nodes = path_by_id[pid].visited_nodes
        for u, w in zip(nodes[:-1], nodes[1:]):
            y[(u, w)] = y.get((u, w), 0.0) + v
    return y


# --------------------------------------------------------------------
#  EX-E.2 -- pick the most-fractional arc
# --------------------------------------------------------------------
def most_fractional_arc(ybar, eps=1e-6):
    """Return the arc (u,v) whose ybar value is closest to 0.5.

    Return None if every arc is essentially integer.
    """
    # === EX-E.2 ===========================================
    # TODO: find argmin_{(u,v)} |ybar_uv - 0.5| among entries with
    # eps < ybar_uv < 1 - eps.
    # =====================================================
    best_arc, best_dist = None, math.inf
    for arc, v in ybar.items():
        if v <= eps or v >= 1.0 - eps:
            continue
        d = abs(v - 0.5)
        if d < best_dist:
            best_arc, best_dist = arc, d
    return best_arc


# --------------------------------------------------------------------
#  EX-E.3 -- build the two children
# --------------------------------------------------------------------
def _up_compatible(p: Path, u: int, v: int) -> bool:
    """True iff path p is fully compatible with forcing arc (u → v).

    A path is compatible when every departure from u goes to v AND every
    arrival at v comes from u.  Paths that do not visit u or v at all are
    also compatible.  This is stricter than uses_arc(u, v) because it
    rejects non-elementary paths that visit u multiple times and use arc
    (u → w) for some w ≠ v on one of those visits.
    """
    n = p.visited_nodes
    for i in range(len(n) - 1):
        if n[i] == u and n[i + 1] != v:
            return False
        if n[i + 1] == v and n[i] != u:
            return False
    return True


def make_children(parent: BnPNode, arc: tuple[int, int]):
    """Return (down_child, up_child) for branching on the given arc.

    Down (forbid (u,v)): drop columns that *use* (u,v).
    Up   (force  (u,v)): drop columns incompatible with the forced arc —
                         i.e. any path that visits u but departs to a node
                         other than v, or arrives at v from a node other
                         than u.
    """
    # === EX-E.3 ===========================================
    # TODO: build two BnPNode instances:
    #   - shared pool filter using path.uses_arc(u, v) and _up_compatible.
    #   - depth = parent.depth + 1.
    #   - id auto via _next_node_id() (handled by the dataclass default).
    # Return (down, up) in that order.
    # =====================================================
    u, v = arc
    down_pool = [p for p in parent.pool if not p.uses_arc(u, v)]
    up_pool   = [p for p in parent.pool if _up_compatible(p, u, v)]
    _log.debug("make_children arc=%s: parent=%d, down=%d, up=%d",
               arc, len(parent.pool), len(down_pool), len(up_pool))
    down = BnPNode(
        depth=parent.depth + 1,
        lb=parent.lb,
        forbidden=parent.forbidden | {arc},
        forced=set(parent.forced),
        pool=down_pool,
    )
    up = BnPNode(
        depth=parent.depth + 1,
        lb=parent.lb,
        forbidden=set(parent.forbidden),
        forced=parent.forced | {arc},
        pool=up_pool,
    )
    return down, up


# ---------------- B&P loop (provided) ----------------
def branch_and_price(
    root: BnPNode,
    run_cg: Callable[[BnPNode, BnPIncumbent], None],
    run_dive: Callable[[BnPNode, BnPIncumbent], float],
    run_rmh:  Callable[[BnPNode, BnPIncumbent], float],
    rmh_every: int = 10,
    eps: float = 1e-6,
    gap_pct: float = 0.0,
    depth_first: bool = True,
    demand_node_ids: Optional[set[int]] = None,
) -> BnPIncumbent:
    open_nodes: list[BnPNode] = [root]
    incumbent = BnPIncumbent()
    nodes_processed = 0
    global_lb: float = -math.inf
    t_start = time.perf_counter()

    _log.info("B&P start: root LB=%.2f, %d columns in pool, depth_first=%s",
              root.lb, len(root.pool), depth_first)

    child = None  # for depth-first: the child we just created and want to dive into
    while open_nodes:
        # depth-first: always process the just-created child next (if depth_first).
        if depth_first and child is not None:
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
                incumbent.ub_history.append(incumbent.cost)
                incumbent.lb_history.append(global_lb)
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
        if demand_node_ids is not None:
            ybar = {a: v for a, v in ybar.items()
                    if a[0] in demand_node_ids and a[1] in demand_node_ids}
        arc = most_fractional_arc(ybar, eps=eps)
        if arc is None:
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

        # Record per-node history after potential incumbent update.
        incumbent.ub_history.append(incumbent.cost)
        incumbent.lb_history.append(global_lb)
        incumbent.time_history.append(time.perf_counter() - t_start)

        if arc is None:
            continue

        down, up = make_children(node, arc)
        _log.info("node %d (depth %d) branch on %s, ybar=%.2f "
                  "-> children %d, %d",
                  node.id, node.depth, arc, ybar[arc], down.id, up.id)
        open_nodes.append(down)
        if depth_first:
            child = up  # dive into up-child immediately
        else:
            open_nodes.append(up)

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
