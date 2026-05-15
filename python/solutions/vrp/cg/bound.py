"""Reference Lagrangian lower bound (Trick 7).

For a set-partitioning master with K identical vehicles, customer covering
right-hand side b_i = 1, and an explicit vehicle-count constraint
sum_p x_p <= K with dual sigma <= 0:

    LB(pi, sigma) = sum_i pi_i + K * sigma + K * min(0, redcost*)

where redcost* = min_p (c_p - sum_i a_{ip} pi_i - sigma) is the optimal
reduced cost returned by the EXACT pricer this iteration.

Heuristic pricers do NOT produce a valid bound: only call this with
solutions returned by the exact label-setting algorithm.
"""

from typing import Iterable


def lagrangian_bound(mp_dual_by_id: dict[int, float],
                     sigma: float,
                     pricing_solutions: Iterable,
                     nb_vehicles: int) -> float:
    """Return the Lagrangian lower bound at the current iteration.

    Parameters
    ----------
    mp_dual_by_id
        dict customer_id -> pi_i.
    sigma
        Dual on the vehicle-count constraint sum_p x_p <= K. <= 0.
    pricing_solutions
        list of rcspp.Solution returned by the *exact* pricer this iteration.
    nb_vehicles
        K, the number of vehicles available.
    """
    # === EX-C.4 ===========================================
    # TODO: implement the formula
    #       LB = sum(pi_i) + K * sigma + K * min(0, min_redcost)
    # HINT:
    #   pi_sum = sum(mp_dual_by_id.values())
    #   redc   = min((s.cost for s in pricing_solutions), default=0.0)
    #   return pi_sum + nb_vehicles * sigma + nb_vehicles * min(0.0, redc)
    # =====================================================
    pi_sum = sum(mp_dual_by_id.values())
    redc = min((s.cost for s in pricing_solutions), default=0.0)
    return pi_sum + nb_vehicles * sigma + nb_vehicles * min(0.0, redc)
