import numpy as np
import random
import copy
from geopy.distance import distance as geopy_distance

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
def decode_with_greedy(position, graph, ev, start_node, destination_node):
    """
    Decode rute dari start ke destination berdasarkan selected_nodes dengan pendekatan greedy + recheck.

    - position: list of float (prioritas)
    - graph: networkx DiGraph
    - ev: object dengan .capacity dan .type
    - start_node: node awal
    - destination_node: node tujuan
    - selected_nodes: hasil sorting dari posisi prioritas
    """
    list_of_nodes = list(range(len(position)))
    node_candidates = [n for n in list_of_nodes if n != start_node and n != destination_node]

    # Ambil k node dengan posisi terkecil
    sorted_nodes = sorted(node_candidates, key=lambda x: position[x])
    selected_nodes = sorted_nodes

    # Urutkan selected_nodes lagi berdasarkan prioritas agar urutannya sesuai
    selected_nodes.sort(key=lambda x: position[x])

    route = [start_node]
    capacity = copy.deepcopy(ev.capacity)

    current_node = start_node

    while True:
        # Cek apakah bisa langsung ke tujuan
        if graph.has_edge(current_node, destination_node):
            edge = graph[current_node][destination_node]
            dist = copy.deepcopy(edge["distance"])
            duration = copy.deepcopy(edge["weight"])
            speed = dist / (duration / 60)
            if speed > ev.max_speed:
                speed = copy.deepcopy(ev.max_speed)
            needed_energy = calculate_energy_model(dist, speed, ev.type)

            if current_node == start_node:
                if ev.battery_now >= needed_energy:
                    route.append(destination_node)
                    break
            else:
                if capacity >= needed_energy:
                    route.append(destination_node)
                    break

        is_insert = False

        for neighbor in selected_nodes:
            if neighbor in route:
                continue
            if not graph.has_edge(current_node, neighbor):
                continue

            edge = graph[current_node][neighbor]
            dist = copy.deepcopy(edge["distance"])
            duration = copy.deepcopy(edge["weight"])
            speed = dist / (duration / 60)

            if speed > ev.max_speed:
                speed = copy.deepcopy(ev.max_speed)

            energy = calculate_energy_model(dist, speed, ev.type)

            # Hanya masukkan jika bisa dicapai dan mendekati tujuan
            if current_node == start_node:
                if ev.battery_now >= energy:
                    dest_lat = copy.deepcopy(graph.nodes[destination_node]['latitude'])
                    dest_lon = copy.deepcopy(graph.nodes[destination_node]['longitude'])
                    neighbor_lat = copy.deepcopy(graph.nodes[neighbor]['latitude'])
                    neighbor_lon = copy.deepcopy(graph.nodes[neighbor]['longitude'])
                    curr_lat = copy.deepcopy(graph.nodes[current_node]['latitude'])
                    curr_lon = copy.deepcopy(graph.nodes[current_node]['longitude'])

                    curr_dist = geopy_distance((curr_lat, curr_lon), (dest_lat, dest_lon)).km
                    next_dist = geopy_distance((neighbor_lat, neighbor_lon), (dest_lat, dest_lon)).km

                    if next_dist < curr_dist + 5:  # searah tujuan dan plus 5 (toleransi)
                        route.append(neighbor)
                        selected_nodes = [node for node in selected_nodes if node != neighbor]
                        current_node = neighbor
                        is_insert = True
                        break
            else:
                if capacity >= energy:
                    dest_lat = copy.deepcopy(graph.nodes[destination_node]['latitude'])
                    dest_lon = copy.deepcopy(graph.nodes[destination_node]['longitude'])
                    neighbor_lat = copy.deepcopy(graph.nodes[neighbor]['latitude'])
                    neighbor_lon = copy.deepcopy(graph.nodes[neighbor]['longitude'])
                    curr_lat = copy.deepcopy(graph.nodes[current_node]['latitude'])
                    curr_lon = copy.deepcopy(graph.nodes[current_node]['longitude'])

                    curr_dist = geopy_distance((curr_lat, curr_lon), (dest_lat, dest_lon)).km
                    next_dist = geopy_distance((neighbor_lat, neighbor_lon), (dest_lat, dest_lon)).km

                    if next_dist < curr_dist:  # searah tujuan
                        route.append(neighbor)
                        selected_nodes = [node for node in selected_nodes if node != neighbor]
                        current_node = neighbor
                        is_insert = True
                        break

        if not is_insert:
            print(f"⚠️ Terhenti di node {current_node}, tidak ada kandidat yang bisa dicapai dengan SOC = {capacity:.2f} kWh")
            break  # tidak ada jalan yang feasible lagi

    # Pastikan tujuan tetap ditambahkan
    if route[-1] != destination_node:
        route.append(destination_node)

    return route

def encode_route_to_position_alns(route, total_nodes, start_node, end_node):
    position = [1.0] * total_nodes
    if len(route) <= 2:
        return position  # kembalikan posisi default 0 jika hanya start-end
    
    for idx, node in enumerate(route):
        if node != start_node:
            position[node] = idx / (len(route) - 2)  # Normalisasi ke 0–1
    return position

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

def greedy_reachable_route(graph, ev, start_node, destination_node):
    """
    Membentuk rute awal yang feasible dengan greedy approach berdasarkan SOC EV.
    Hanya memilih node yang bisa dicapai dengan sisa baterai dan mendekati tujuan.
    """
    current_node = start_node
    route = [current_node]
    capacity = copy.deepcopy(ev.capacity)
    ev_type = copy.deepcopy(ev.type)

    while current_node != destination_node:
        if graph.has_edge(current_node, destination_node):
            edge = graph[current_node][destination_node]
            dist = copy.deepcopy(edge["distance"])
            duration = copy.deepcopy(edge["weight"])
            speed = dist / (duration / 60)
            if speed > ev.max_speed:
                speed = copy.deepcopy(ev.max_speed)
            energy = calculate_energy_model(dist, speed, ev_type)

            if current_node == start_node:
                if ev.battery_now >= energy:
                    route.append(destination_node)
                    break  # Langsung ke tujuan karena SOC cukup
            else:
                if capacity >= energy:
                    route.append(destination_node)
                    break  # Langsung ke tujuan karena SOC cukup

        candidates = []
        for neighbor in graph.successors(current_node):
            if neighbor in route:
                continue
            if not graph.has_edge(current_node, neighbor):
                continue

            edge = graph[current_node][neighbor]
            dist = copy.deepcopy(edge["distance"])
            duration = copy.deepcopy(edge["weight"])
            speed = dist / (duration / 60)

            if speed > ev.max_speed:
                speed = copy.deepcopy(ev.max_speed)

            energy = calculate_energy_model(dist, speed, ev_type)

            # Hanya masukkan jika bisa dicapai dan mendekati tujuan
            if current_node == start_node:
                if ev.battery_now >= energy:
                    dest_lat = copy.deepcopy(graph.nodes[destination_node]['latitude'])
                    dest_lon = copy.deepcopy(graph.nodes[destination_node]['longitude'])
                    neighbor_lat = copy.deepcopy(graph.nodes[neighbor]['latitude'])
                    neighbor_lon = copy.deepcopy(graph.nodes[neighbor]['longitude'])
                    curr_lat = copy.deepcopy(graph.nodes[current_node]['latitude'])
                    curr_lon = copy.deepcopy(graph.nodes[current_node]['longitude'])

                    curr_dist = geopy_distance((curr_lat, curr_lon), (dest_lat, dest_lon)).km
                    next_dist = geopy_distance((neighbor_lat, neighbor_lon), (dest_lat, dest_lon)).km

                    if next_dist < curr_dist + 5:  # searah tujuan
                        candidates.append(neighbor)
            else:
                if capacity >= energy:
                    dest_lat = copy.deepcopy(graph.nodes[destination_node]['latitude'])
                    dest_lon = copy.deepcopy(graph.nodes[destination_node]['longitude'])
                    neighbor_lat = copy.deepcopy(graph.nodes[neighbor]['latitude'])
                    neighbor_lon = copy.deepcopy(graph.nodes[neighbor]['longitude'])
                    curr_lat = copy.deepcopy(graph.nodes[current_node]['latitude'])
                    curr_lon = copy.deepcopy(graph.nodes[current_node]['longitude'])

                    curr_dist = geopy_distance((curr_lat, curr_lon), (dest_lat, dest_lon)).km
                    next_dist = geopy_distance((neighbor_lat, neighbor_lon), (dest_lat, dest_lon)).km

                    if next_dist < curr_dist:  # searah tujuan
                        candidates.append(neighbor)

        if not candidates:
            print(f"⚠️ Terhenti di node {current_node}, tidak ada kandidat yang bisa dicapai dengan SOC = {capacity:.2f} kWh")
            break  # tidak ada jalan yang feasible lagi

        # Pilih random dari kandidat yang valid
        selected = random.choice(candidates)
        route.append(selected)
        current_node = selected

    if route[-1] != destination_node:
        route.append(destination_node)

    return route

def roulette_wheel_select(scores):
    total = sum(scores)
    r = random.uniform(0, total)
    upto = 0
    for idx, score in enumerate(scores):
        if upto + score >= r:
            return idx
        upto += score
    return len(scores) - 1