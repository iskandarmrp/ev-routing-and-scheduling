import random
from .utils import (
    decode_particle_with_visit,
    create_visit_decision_from_route
)
from .charging import validate_charging_after_backtrack

# Kayaknya ini perlu diubah (Jadi random banget, dan gaperlu ngecek bisa sampai atau ngga, soalnya harusnya dicek di evaluate)
def random_evrp_solution(graph, ev, start_node, destination_node):
    """
    fungsi untuk membuat solusi random EVRP dengan awal start_node dan akhir destination_node

    param:
    graph -> graph
    ev -> electric vehicle object
    start_node -> node id awal
    destination_node -> node id tujuan
    """
    total_nodes = len(graph.nodes)

    # Inisialisasi visit_decision: semua 0 dulu
    visit_decision = {node: 0 for node in graph.nodes}

    visit_decision[start_node] = 1
    visit_decision[destination_node] = 1

    # Pilih random node selain start & destination untuk dikunjungi
    other_nodes = [n for n in graph.nodes if n not in (start_node, destination_node)]
    selected = random.sample(other_nodes, k=random.randint(1, len(other_nodes)))  # 1 - panjang node

    for node in selected:
        visit_decision[node] = 1

    position = [1.0] * total_nodes  # default tinggi = tidak diprioritaskan

    idx_map = {node: i for i, node in enumerate(graph.nodes)}

    # Random untuk node lainnya (kecuali start dan destination)
    for node in graph.nodes:
        if node not in (start_node, destination_node):
            position[idx_map[node]] = random.uniform(0.05, 0.95)

    velocity = [random.uniform(-0.1, 0.1) for _ in range(len(position))]

    # Coba decode 
    decoded_particle = decode_particle_with_visit(position, visit_decision, start_node, destination_node)

    # Validate charging
    validate_charging, charging_is_valid = validate_charging_after_backtrack(graph, ev, decoded_particle)

    filtered_route = [decoded_particle[0]] + [
        node for node in decoded_particle[1:-1] if node in validate_charging
    ] + [decoded_particle[-1]]

    visit_decision = create_visit_decision_from_route(filtered_route, list(graph.nodes))
    
    return filtered_route, validate_charging, visit_decision, position, velocity
