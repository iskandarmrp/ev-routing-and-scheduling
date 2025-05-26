import random
from .utils import (
    greedy_reachable_route,
    encode_route_to_position_alns
)
from .charging import validate_charging_after_backtrack

# Kayaknya ini perlu diubah (Jadi random banget, dan gaperlu ngecek bisa sampai atau ngga, soalnya harusnya dicek di evaluate)
def random_evrp_solution_greedy(graph, ev, start_node, destination_node):
    """
    Membuat solusi awal dengan pendekatan greedy menuju tujuan.
    """
    route = greedy_reachable_route(graph, ev, start_node, destination_node)

    position = encode_route_to_position_alns(route, len(graph.nodes), start_node, destination_node)
    velocity = [random.uniform(-0.1, 0.1) for _ in range(len(position))]

    # Validate charging
    validate_charging, charging_is_valid = validate_charging_after_backtrack(graph, ev, route)

    return route, validate_charging, position, velocity
