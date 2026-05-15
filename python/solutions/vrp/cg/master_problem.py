"""Reference implementation of the RMP in HiGHS (Trick 7-ready).

The master is

    min  sum_p c_p x_p   +   M * sum_i s_i      (s_i = artificial slacks)
    s.t. sum_p x_p                       <= K          [sigma]
         sum_p a_{ip} x_p   +   s_i      == 1   forall i  [pi_i]
         x_p, s_i >= 0

Slacks s_i ensure the LP is always feasible regardless of the column pool
(Phase-I trick). They are penalised with a big-M cost so that any feasible
real solution dominates them. The vehicle dual sigma stays well-defined.
"""

from typing import Iterable

import highspy as hp

from vrp.cg.mp_solution import MPSolution
from vrp.cg.path import Path
from vrp.log import get_logger


# Penalty for slack variables (big enough to dominate any real route).
SLACK_COST = 1.0e6

_log = get_logger("master")


class MasterProblem:
    VEHICLE_ROW: int = -1

    def __init__(self, customer_ids: Iterable[int], nb_vehicles: int):
        self.customer_ids = list(customer_ids)
        self.nb_vehicles  = int(nb_vehicles)

        self._h = hp.Highs()
        self._h.silent()

        self.col_by_path_id: dict[int, int] = {}
        self.path_by_id: dict[int, Path] = {}
        self.row_by_customer: dict[int, int] = {}
        # column index of the artificial slack for each customer row.
        self.slack_col_by_customer: dict[int, int] = {}

        self.fixed_to_one:  set[int] = set()
        self.fixed_to_zero: set[int] = set()
        self._built = False

    # -----------------------------------------------------------
    def construct_model(self, paths: list[Path]) -> None:
        self._h.clear()
        self._h.silent()
        self._h.changeObjectiveSense(hp.ObjSense.kMinimize)
        self.col_by_path_id.clear()
        self.path_by_id.clear()
        self.row_by_customer.clear()
        self.slack_col_by_customer.clear()
        self.VEHICLE_ROW = -1

        self._add_constraints()                     # EX-A.1
        self._built = True   # rows are in HiGHS, ok to add columns now
        self._add_slacks()
        for p in paths:
            self.add_column(p)                      # EX-A.2

        _log.info("master built: %d rows, %d cols (incl. %d slacks)",
                  self._h.getNumRow(), self._h.getNumCol(),
                  len(self.slack_col_by_customer))

    # ----------------------------------------------------------------
    #  EX-A.1 -- one == 1 covering row per customer + vehicle row
    # ----------------------------------------------------------------
    def _add_constraints(self) -> None:
        # === EX-A.1 ===========================================
        # TODO:
        #   1. Add the vehicle-count row sum_p x_p <= K. Use
        #         self._h.addRow(-hp.kHighsInf, float(self.nb_vehicles),
        #                        0, [], [])
        #      and remember the row index in self.VEHICLE_ROW.
        #
        #   2. For every customer in self.customer_ids, add an empty
        #      EQUALITY row (lower=upper=1.0) and store its index in
        #      self.row_by_customer.
        #
        # HINT: self._h.getNumRow() right after addRow gives you the
        # 0-based index of the row you just added (= getNumRow() - 1).
        # =====================================================
        # Vehicle-count row:  sum_p x_p <= K
        self._h.addRow(-hp.kHighsInf, float(self.nb_vehicles), 0, [], [])
        self.VEHICLE_ROW = self._h.getNumRow() - 1

        # Customer covering rows:  sum_p a_{ip} x_p == 1
        for cid in self.customer_ids:
            self._h.addRow(1.0, 1.0, 0, [], [])
            self.row_by_customer[cid] = self._h.getNumRow() - 1

    # -----------------------------------------------------------
    # Big-M artificial slacks make the LP feasible from iter 0.
    # They sit on the customer rows only -- not on the vehicle row.
    # -----------------------------------------------------------
    def _add_slacks(self) -> None:
        for cid, row in self.row_by_customer.items():
            self._h.addCol(SLACK_COST, 0.0, hp.kHighsInf,
                           1, [row], [1.0])
            self.slack_col_by_customer[cid] = self._h.getNumCol() - 1

    # ----------------------------------------------------------------
    #  EX-A.2 -- one column per path
    # ----------------------------------------------------------------
    def add_column(self, path: Path) -> None:
        """Add a new column (= a Path) to the master."""
        if not self._built:
            self.path_by_id[path.id] = path
            return

        # === EX-A.2 ===========================================
        # TODO: append a column to HiGHS that
        #   - has objective coefficient = path.cost
        #   - has lower bound 0 and NO upper bound: pass
        #     upper = highspy.kHighsInf.  The covering constraints
        #     already bound x_p from above; an explicit x_p <= 1 would
        #     create an extra dual variable for the pricer to track.
        #   - has coefficient 1.0 on self.VEHICLE_ROW
        #   - has coefficient a_{ip} = (# times customer i is visited
        #     in path) on row self.row_by_customer[i], for every
        #     customer i in self.customer_ids.
        #
        # Use self._h.addCol(cost, lower, upper, num_new_elements, indices,
        # values).  Build "indices" as a list of row indices and
        # "values" as the matching list of coefficients (drop entries
        # whose coefficient is zero).
        # Update self.col_by_path_id and self.path_by_id.
        # You can use getNumCol() to build the id.
        # =====================================================
        idx: list[int] = [self.VEHICLE_ROW]
        val: list[float] = [1.0]
        for cid in self.customer_ids:
            a = path.visits(cid)
            if a:
                idx.append(self.row_by_customer[cid])
                val.append(float(a))

        self._h.addCol(path.cost, 0.0, hp.kHighsInf, len(idx), idx, val)
        j = self._h.getNumCol() - 1
        self.col_by_path_id[path.id] = j
        self.path_by_id[path.id] = path

    # -----------------------------------------------------------
    def solve(self, relax: bool = True) -> MPSolution:
        self._set_integrality(integer=not relax)        # EX-D.1
        _log.debug("solving master: %s, %d cols, %d rows",
                   "LP" if relax else "MIP",
                   self._h.getNumCol(), self._h.getNumRow())
        self._h.run()

        sol = MPSolution()
        sol.cost = self._h.getObjectiveValue()
        col_vals = list(self._h.getSolution().col_value)
        for pid, j in self.col_by_path_id.items():
            sol.value_by_var_id[pid] = col_vals[j]

        if relax:
            row_duals = list(self._h.getSolution().row_dual)
            for cid, i in self.row_by_customer.items():
                sol.dual_by_var_id[cid] = row_duals[i]
            sol.sigma = row_duals[self.VEHICLE_ROW] if self.VEHICLE_ROW >= 0 else 0.0
            _log.debug("master LP solved: cost=%.2f, sigma=%+.2f",
                       sol.cost, sol.sigma)
        else:
            sol.sigma = 0.0
            _log.info("master MIP solved: cost=%.2f", sol.cost)
        return sol

    # ----------------------------------------------------------------
    #  EX-D.1 -- toggle variable integrality
    # ----------------------------------------------------------------
    def _set_integrality(self, integer: bool) -> None:
        # === EX-D.1 ===========================================
        # TODO: for every column j in self.col_by_path_id.values(),
        # call self._h.changeColIntegrality(j, kind) where
        #   kind = hp.HighsVarType.kInteger    if integer else
        #          hp.HighsVarType.kContinuous.
        #
        # NOTE: when you fix a column to 1 or 0 (B&P / diving), use
        # changeColBounds(j, lo, up) -- not the integrality field, see below..
        # =====================================================
        kind = (hp.HighsVarType.kInteger if integer
                else hp.HighsVarType.kContinuous)
        for j in self.col_by_path_id.values():
            self._h.changeColIntegrality(j, kind)

    # -----------------------------------------------------------
    def fix_column_to_one(self, path_id: int) -> None:
        j = self.col_by_path_id[path_id]
        self._h.changeColBounds(j, 1.0, 1.0)
        self.fixed_to_one.add(path_id)

    def fix_column_to_zero(self, path_id: int) -> None:
        j = self.col_by_path_id[path_id]
        self._h.changeColBounds(j, 0.0, 0.0)
        self.fixed_to_zero.add(path_id)

    def reset_column_bounds(self, path_id: int) -> None:
        j = self.col_by_path_id[path_id]
        self._h.changeColBounds(j, 0.0, hp.kHighsInf)
        self.fixed_to_one.discard(path_id)
        self.fixed_to_zero.discard(path_id)
