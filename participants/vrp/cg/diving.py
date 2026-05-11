"""Plain diving heuristic.

Repeatedly fix the column with the largest fractional value to 1, then
re-run column generation on the residual master.  At most |customers|
fixings are needed.
"""

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
    """Iterative diving heuristic.

    Parameters
    ----------
    master   the master problem (already CG-converged at root).
    run_cg   a callable that runs CG on the *current* master and returns
             the LP solution (used to refresh columns after each fix).
    eps      tolerance for "fractional" / "integer".
    max_iter safeguard.
    """
    sol = master.solve(relax=True)
    fixed: set[int] = set()
    _log.info("dive start: LP=%.2f", sol.cost)

    for k in range(max_iter):
        # Already integer?
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
        raise NotImplementedError("EX-D.2: pick column and fix to 1")

        # === EX-D.3 -- refresh by CG =========================
        # TODO: re-run CG (call run_cg()) on the now-residual master,
        # then read the new LP solution into `sol`.
        # =====================================================
        # raise NotImplementedError("EX-D.3: refresh CG after fix")

    return sol


def _is_integer(sol: MPSolution, eps: float = 1e-6) -> bool:
    for v in sol.value_by_var_id.values():
        if eps < v < 1.0 - eps:
            return False
    return True
