"""Container for the result of a master-problem solve."""


class MPSolution:
    def __init__(self, value_by_var_id=None, dual_by_var_id=None,
                 cost=0.0, sigma=0.0):
        self.value_by_var_id = value_by_var_id if value_by_var_id is not None else {}
        self.dual_by_var_id = dual_by_var_id if dual_by_var_id is not None else {}
        self.cost = float(cost)
        # Dual on the vehicle-count constraint sum_p x_p <= K.
        # sigma <= 0 in any LP optimum.
        self.sigma = float(sigma)

    def __repr__(self):
        return (
            f"MPSolution(cost={self.cost:.2f}, sigma={self.sigma:.2f}, "
            f"#x={len(self.value_by_var_id)}, "
            f"#pi={len(self.dual_by_var_id)})"
        )
