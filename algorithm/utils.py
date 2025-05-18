import numpy as np

def calculate_energy_model(distance, speed, ev_type):
    if ev_type == "tesla":
        energy = (7.41 * speed**5 - 266 * speed**4 + 51590 * speed**3 + 679 * speed**2 + 29.83 * speed - 0.061) / \
                 (speed**4 + 458.1 * speed**3 - 1647 * speed**2 - 758.8 * speed + 490.3) * distance
        energy /= 1000  # Convert Wh to kWh
    elif ev_type == "bmw":
        energy = (0.00625 * speed**2 + 0.725 * speed + 50) * distance / 1000
    elif ev_type == "leaf":
        energy = (0.008837 * speed**2 + 0.1393 * speed + 63.26) * distance / 1000
    else:
        energy = 0.15 * distance
    return energy

# Mengubah particle kontinu menjadi urutan node
def decode_particle_with_visit(position, visit_decision, start_node, destination_node):
    """
    Decode partikel kontinu + visit decision 0/1 ke urutan rute.
    - position: list of float priorities.
    - visit_decision: dictionary {node_id: 0/1}
    """

    list_of_nodes = list(range(len(position)))  # List node id

    # Pilih hanya node yang visit_decision==1
    visiting_nodes = [node for node in list_of_nodes if visit_decision.get(node, 0) == 1 and node != destination_node and node != start_node]

    # Urutkan visiting nodes berdasarkan priority position
    visiting_nodes.sort(key=lambda x: position[x])

    route = [start_node] + visiting_nodes +[destination_node]

    return route

def encode_route_to_position_alns(route, total_nodes, start_node, end_node):
    position = [1.0] * total_nodes
    for idx, node in enumerate(route):
        if node != start_node and node != end_node:
            position[node] = idx / (len(route) - 2)  # Normalisasi ke 0–1
    return position

def create_visit_decision_from_route(route, graph_nodes):
    route_set = set(route)
    visit_decision = {}
    for node in graph_nodes:
        visit_decision[node] = 1 if node in route_set else 0
    return visit_decision

def update_velocity(velocity, pnow, pbest, gbest, phi1, phi2):
    v = np.array(velocity)
    x = np.array(pnow)
    pb = np.array(pbest)
    gb = np.array(gbest)
    return (v + phi1 * (pb - x) + phi2 * (gb - x)).tolist()

def update_position(pnow, velocity, p1, p2, gamma):
    x = np.array(pnow)
    v = np.array(velocity)
    p1 = np.array(p1)
    p2 = np.array(p2)
    return (x + v + gamma * (p1 - p2)).tolist()