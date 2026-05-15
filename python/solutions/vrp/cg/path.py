"""A column in the master problem.

A path is a feasible depot-to-depot route. We store its cost (sum of
travel distances along the visited nodes), and the ordered list of
visited nodes (with depots at both ends).
"""


class Path:
    def __init__(self, path_id: int, cost: float, visited_nodes):
        self.id = path_id
        self.cost = float(cost)
        self.visited_nodes = list(visited_nodes)

    def visits(self, customer_id: int) -> int:
        """Number of times the customer is visited (0, 1, or 2 for SPPRC)."""
        return self.visited_nodes.count(customer_id)

    def uses_arc(self, u: int, v: int) -> bool:
        n = self.visited_nodes
        for i in range(len(n) - 1):
            if n[i] == u and n[i + 1] == v:
                return True
        return False

    def __repr__(self):
        return f"Path(id={self.id}, cost={self.cost:.2f}, n={self.visited_nodes})"
