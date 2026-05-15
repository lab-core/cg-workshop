"""Reference plain-diving + RMH heuristics."""

from typing import Callable, Optional

from vrp.cg.master_problem import MasterProblem
from vrp.cg.mp_solution import MPSolution
from vrp.log import get_logger


_log = get_logger("diving")


def restricted_master_heuristic(master: MasterProblem) -> MPSolution:
    """Solve the integer MIP on the current column pool (frozen).

    Requires EX-D.1 (_set_integrality) to actually solve a binary MIP.
    """
    return master.solve(relax=False)


def plain_dive(master: MasterProblem,
               run_cg: Callable[[], MPSolution],
               ub: float = float("inf"),
               eps: float = 1e-6,
               max_iter: int = 200) -> Optional[MPSolution]:
    """Iterative diving heuristic."""
    sol = master.solve(relax=True)
    fixed: set[int] = set()
    _log.info("dive start: LP=%.2f", sol.cost)

    for _ in range(max_iter):
        if _is_integer(sol, eps):
            _log.info("dive end (integer): %d fixes, UB=%.2f",
                      len(fixed), sol.cost)
            return sol

        # === EX-D.2 -- pick the column to fix =================
        # TODO: among the path ids whose value is in (eps, 1-eps) and
        # not in `fixed`, pick the one with the largest
        # value_by_var_id[pid].  Fix it to 1 in the master via
        # master.fix_column_to_one(pid), and add it to `fixed`.
        # =====================================================
        best_pid, best_val = None, -1.0
        for pid, v in sol.value_by_var_id.items():
            if pid in fixed:
                continue
            if eps < v < 1.0 - eps and v > best_val:
                best_pid, best_val = pid, v
        if best_pid is None:
            return sol

        master.fix_column_to_one(best_pid)
        fixed.add(best_pid)
        _log.info("dive fix #%d: column %d (x=%.2f)",
                  len(fixed), best_pid, best_val)

        # === EX-D.3 -- refresh by CG =========================
        # TODO: re-run CG (call run_cg()) on the now-residual master,
        # then read the new LP solution into `sol`.
        # =====================================================
        sol = run_cg()

        # return a solution only if better than the provided UB
        if sol.cost >= ub:
            return None

    return sol


def _is_integer(sol: MPSolution, eps: float = 1e-6) -> bool:
    for v in sol.value_by_var_id.values():
        if eps < v < 1.0 - eps:
            return False
    return True
