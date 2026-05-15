#  Copyright (c) 2025 Laboratory for Combinatorial Optimization in Real-time Environment.
#  All rights reserved.

from vrp.instance import Instance
from vrp.log import get_logger


_log = get_logger("io")


class InstanceReader:
    def __init__(self, file_path: str):
        self.file_path_ = file_path

    def read(self) -> Instance:
        _log.debug("reading instance from %s", self.file_path_)

        with open(self.file_path_, "r") as f:
            instance_name = f.readline().strip()
            f.readline(); f.readline(); f.readline()
            nb_vehicles, capacity = map(int, f.readline().split())

            instance = Instance(nb_vehicles, capacity, instance_name)

            f.readline(); f.readline(); f.readline(); f.readline()

            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                id = int(parts[0])
                pos_x = float(parts[1])
                pos_y = float(parts[2])
                demand = int(parts[3])
                ready_time = int(parts[4])
                due_time = int(parts[5])
                service_time = int(parts[6])
                depot = id == 0
                instance.add_customer(
                    id, pos_x, pos_y, demand, ready_time, due_time, service_time, depot
                )

        _log.info("instance %s loaded: %d customers, %d vehicles, capacity %d",
                  instance_name,
                  len(instance.get_customers_by_id()) - 1,
                  nb_vehicles, capacity)
        return instance

    def read_duals(self, duals_file_path: str) -> dict[int, float]:
        _log.debug("reading duals from %s", duals_file_path)
        dual_by_var_id: dict[int, float] = {}
        with open(duals_file_path, "r") as f:
            for line in f:
                parts = line.strip().split()
                if not parts:
                    continue
                id = int(parts[0])
                dual_value = float(parts[1])
                dual_by_var_id[id] = dual_value
        return dual_by_var_id
