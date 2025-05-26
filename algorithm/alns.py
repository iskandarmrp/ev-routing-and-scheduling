import random
import copy
from geopy.distance import distance as geopy_distance
from .utils import (
    calculate_energy_model,
    roulette_wheel_select
)
from .charging import validate_charging_after_backtrack
from .evaluation import evaluate

def destroy_random(route, charging, degree=2):
    if len(route) <= 2:
        return route, charging
    middle_nodes = list(range(1, len(route) - 1))
    remove_count = random.randint(1, min(degree, len(middle_nodes)))
    remove_idx = random.sample(middle_nodes, remove_count)
    new_route = [node for idx, node in enumerate(route) if idx not in remove_idx]
    new_charging = {k: v for k, v in charging.items() if k in new_route}
    return new_route, new_charging

def destroy_farthest_pair(graph, route, charging, degree=2):
    if len(route) <= 2:
        return route, charging
    distances = {}
    for i in range(len(route)-1):
        for j in range(i+1, len(route)-1):
            node_i, node_j = route[i], route[j]
            dist = graph[node_i][node_j]["distance"] if graph.has_edge(node_i, node_j) else float('inf')
            distances[(i, j)] = dist
    farthest = sorted(distances.items(), key=lambda x: x[1], reverse=True)[:degree]
    remove_idx = [j for (i, j) in farthest]
    new_route = [node for idx, node in enumerate(route) if idx not in remove_idx]
    new_charging = {k: v for k, v in charging.items() if k in new_route}
    return new_route, new_charging

def destroy_nearest_pair(graph, route, charging, degree=2):
    if len(route) <= 2:
        return route, charging
    distances = {}
    for i in range(len(route)-1):
        for j in range(i+1, len(route)-1):
            node_i, node_j = route[i], route[j]
            dist = graph[node_i][node_j]["distance"] if graph.has_edge(node_i, node_j) else float('inf')
            distances[(i, j)] = dist
    nearest = sorted(distances.items(), key=lambda x: x[1])[:degree]
    remove_idx = [j for (i, j) in nearest]
    new_route = [node for idx, node in enumerate(route) if idx not in remove_idx]
    new_charging = {k: v for k, v in charging.items() if k in new_route}
    return new_route, new_charging

def destroy_longest_duration_pair(graph, route, charging, degree=2):
    if len(route) <= 2:
        return route, charging
    durations = {}
    for i in range(len(route)-1):
        for j in range(i+1, len(route)-1):
            node_i, node_j = route[i], route[j]
            dur = graph[node_i][node_j]["weight"] if graph.has_edge(node_i, node_j) else float('inf')
            durations[(i, j)] = dur
    longest_durations = sorted(durations.items(), key=lambda x: x[1], reverse=True)[:degree]
    remove_idx = [j for (i, j) in longest_durations]
    new_route = [node for idx, node in enumerate(route) if idx not in remove_idx]
    new_charging = {k: v for k, v in charging.items() if k in new_route}
    return new_route, new_charging

def destroy_reverse_direction(graph, route, charging, degree=2):
    """
    Menghapus node yang pergerakannya menjauh dari tujuan (secara spasial).
    """
    if len(route) <= 2:
        return route, charging

    dest_lat = graph.nodes[route[-1]]["latitude"]
    dest_lon = graph.nodes[route[-1]]["longitude"]

    remove_idx = []
    for i in range(1, len(route) - 1):  # hanya node tengah
        curr = route[i]
        prev = route[i - 1]
        curr_lat, curr_lon = graph.nodes[curr]["latitude"], graph.nodes[curr]["longitude"]
        prev_lat, prev_lon = graph.nodes[prev]["latitude"], graph.nodes[prev]["longitude"]

        dist_prev = geopy_distance((prev_lat, prev_lon), (dest_lat, dest_lon)).km
        dist_curr = geopy_distance((curr_lat, curr_lon), (dest_lat, dest_lon)).km

        if dist_curr > dist_prev:  # makin jauh dari tujuan
            remove_idx.append(i)

    # Batasi jumlah yang dihapus
    remove_idx = remove_idx[:degree]

    new_route = [node for idx, node in enumerate(route) if idx not in remove_idx]
    new_charging = {k: v for k, v in charging.items() if k in new_route}
    return new_route, new_charging

def destroy_capacity_violation(graph, route, charging, ev, degree=2):
    if len(route) <= 2:
        return route, charging

    new_route = [route[0]]
    capacity = ev.capacity * 0.9
    new_charging = {}
    remove_count = 0

    for i in range(1, len(route)):
        prev = new_route[-1]
        curr = route[i]

        if not graph.has_edge(prev, curr):
            continue

        distance = graph[prev][curr]["distance"]
        duration = graph[prev][curr]["weight"]
        duration_in_hour = duration / 60 # Ubah durasi ke dalam jam untuk menghitung kecepatan
        speed = distance / duration_in_hour
        consumption = calculate_energy_model(distance, speed, ev.type)

        if (capacity - consumption) >= 0:
            new_route.append(curr)
        else:
            remove_count += 1
            if remove_count == degree:
                for j in range(i+1, len(route)):
                    new_route.append(route[j])
                break

    if new_route[-1] != route[-1]:
        new_route.append(route[-1])
    new_charging = {k: v for k, v in charging.items() if k in new_route}

    return new_route, new_charging

def destroy_longest_waiting_time(route, charging, degree=2):
    start_node = route[0]
    end_node = route[-1]

    # Filter dan sort node yang waiting_time-nya tinggi dan bukan start/end node
    filtered_sorted = sorted(
        [
            (node_id, data)
            for node_id, data in charging.items()
            if data.get('waiting_time', 0) > 15 and node_id != start_node and node_id != end_node
        ],
        key=lambda item: item[1]['waiting_time'],
        reverse=True
    )

    # Ambil maksimal 'degree' node
    nodes_to_remove = [node_id for node_id, _ in filtered_sorted[:degree]]

    # Hapus dari route dan charging
    new_route = [node for node in route if node not in nodes_to_remove]
    new_charging = {k: v for k, v in charging.items() if k not in nodes_to_remove}

    print(f"⛔ Destroyed nodes (longest waiting, excluding start/end): {nodes_to_remove}")
    return new_route, new_charging

def repair_random(route, all_nodes, degree=2):
    remaining_nodes = list(set(all_nodes) - set(route))
    insert_target = random.randint(1, degree)
    for _ in range(insert_target):
        if not remaining_nodes:
            break
        candidate = random.choice(remaining_nodes)
        remaining_nodes.remove(candidate)
        insert_pos = random.randint(1, len(route) - 1)
        route.insert(insert_pos, candidate)
    return route

def repair_longest(route, graph, all_nodes, ev, degree=2):
    remaining_nodes = list(set(all_nodes) - set(route))

    distances = {}
    for i in range(1, len(route)):
        for j in range(i+1, len(route)):
            node_i, node_j = route[i], route[j]
            dist = graph[node_i][node_j]["distance"] if graph.has_edge(node_i, node_j) else float('inf')
            distances[(i, j)] = dist
    farthest = sorted(distances.items(), key=lambda x: x[1], reverse=True)[:degree]
    idx_to_insert = [j for (i, j) in farthest]

    for j in idx_to_insert:
        if j <= 0 or j >= len(route):
            continue

        j = int(j)
        prev_node = route[j - 1]
        next_node = route[j]
        lat_prev = graph.nodes[prev_node]['latitude']
        lat_next = graph.nodes[next_node]['latitude']

        candidate_nodes = []

        for candidate in remaining_nodes:
            candidate_lat = graph.nodes[candidate]['latitude']
            if (candidate_lat >= lat_prev and candidate_lat <= lat_next) or (candidate_lat <= lat_prev and candidate_lat >= lat_next):
                dist = graph[prev_node][candidate]["distance"]
                duration = graph[prev_node][candidate]["weight"]
                duration_in_hour = duration / 60 # Ubah durasi ke dalam jam untuk menghitung kecepatan
                speed_prev = dist / duration_in_hour
                consumption = calculate_energy_model(dist, speed_prev, ev.type)

                if ev.capacity >= consumption:
                    candidate_nodes.append(candidate)
        
        if candidate_nodes:
            candidate = random.choice(candidate_nodes)
            remaining_nodes.remove(candidate)
            route.insert(j, candidate)

    return route

def repair_progressive_toward_goal(route, graph, all_nodes, ev, degree=4):
    """
    Sisipkan node secara progresif menuju tujuan.
    Hanya sisipkan jika hasilnya mendekatkan ke tujuan.
    """
    remaining_nodes = list(set(all_nodes) - set(route))
    dest_lat = graph.nodes[route[-1]]['latitude']
    dest_lon = graph.nodes[route[-1]]['longitude']

    inserted = 0

    while remaining_nodes and inserted < degree:
        candidate = random.choice(remaining_nodes)
        remaining_nodes.remove(candidate)

        for i in range(1, len(route) - 1):
            curr = route[i]

            # Cek apakah kandidat lebih dekat ke tujuan dibanding prev dan next
            dist_curr = geopy_distance((graph.nodes[curr]['latitude'], graph.nodes[curr]['longitude']), (dest_lat, dest_lon)).km
            dist_candidate = geopy_distance((graph.nodes[candidate]['latitude'], graph.nodes[candidate]['longitude']), (dest_lat, dest_lon)).km

            if dist_candidate < dist_curr:  # pastikan lebih dekat
                dist = graph[curr][candidate]["distance"]
                duration = graph[curr][candidate]["weight"]
                duration_in_hour = duration / 60 # Ubah durasi ke dalam jam untuk menghitung kecepatan
                speed_prev = dist / duration_in_hour
                consumption = calculate_energy_model(dist, speed_prev, ev.type)

                if ev.capacity >= consumption:
                    route.insert(i+1, candidate)
                    remaining_nodes = list(set(all_nodes) - set(route))
                    inserted += 1
                    break

    return route

def repair_soc_aware(route, graph, all_nodes, ev, degree=4):
    remaining_nodes = list(set(all_nodes) - set(route))
    inserted = 0

    while remaining_nodes and inserted < degree:
        candidate = random.choice(remaining_nodes)
        remaining_nodes.remove(candidate)

        for i in range(1, len(route)):
            prev = route[i - 1]
            next = route[i]

            if not (graph.has_edge(prev, candidate) and graph.has_edge(candidate, next)):
                continue

            # Hitung jarak dan konsumsi baterai
            dist_prev = graph[prev][candidate]["distance"]
            dist_next = graph[candidate][next]["distance"]
            duration_prev = graph[prev][candidate]["weight"]
            duration_in_hour_prev = duration_prev / 60 # Ubah durasi ke dalam jam untuk menghitung kecepatan
            speed_prev = dist_prev / duration_in_hour_prev
            consumption_prev = calculate_energy_model(dist_prev, speed_prev, ev.type)
            duration_next = graph[candidate][next]["weight"]
            duration_in_hour_next = duration_next / 60 # Ubah durasi ke dalam jam untuk menghitung kecepatan
            speed_next = dist_next / duration_in_hour_next
            consumption_next = calculate_energy_model(dist_next, speed_next, ev.type)
            
            if ev.capacity >= consumption_prev and ev.capacity >= consumption_next:
                route.insert(i, candidate)
                remaining_nodes = list(set(all_nodes) - set(route))
                inserted += 1
                break  # lanjut ke kandidat berikutnya

    return route

def adaptive_degree(route, destroy=True, min_val=1, max_val=10):
    n = len(route)
    if destroy:
        # Rute pendek → degree kecil, Rute panjang → degree besar
        return max(min_val, min(max_val, n // 4))
    else:
        # Repair: Rute pendek → degree besar (eksplorasi), Rute panjang → degree kecil
        return max(min_val, min(max_val, (20 - n) // 4)) if n < 20 else min_val

def alns_search(graph, ev, route, charging, all_nodes, destroy_scores, repair_scores):
    destroy_methods = [
        lambda r, c: destroy_random(r, c, degree=adaptive_degree(r, destroy=True)),
        lambda r, c: destroy_farthest_pair(graph, r, c, degree=adaptive_degree(r, destroy=True)),
        lambda r, c: destroy_nearest_pair(graph, r, c, degree=adaptive_degree(r, destroy=True)),
        lambda r, c: destroy_longest_duration_pair(graph, r, c, degree=adaptive_degree(r, destroy=True)),
        lambda r, c: destroy_reverse_direction(graph, r, c, degree=adaptive_degree(r, destroy=True)),
        lambda r, c: destroy_capacity_violation(graph, r, c, ev, degree=adaptive_degree(r, destroy=True)),
        lambda r, c: destroy_longest_waiting_time(r, c, degree=adaptive_degree(r, destroy=True))
    ]

    repair_methods = [
        lambda r: repair_random(r, all_nodes, degree=adaptive_degree(r, destroy=False)),
        lambda r: repair_longest(r, graph, all_nodes, ev, degree=adaptive_degree(r, destroy=False)),
        lambda r: repair_progressive_toward_goal(r, graph, all_nodes, ev, degree=adaptive_degree(r, destroy=False)),
        lambda r: repair_soc_aware(r, graph, all_nodes, ev, degree=adaptive_degree(r, destroy=False))
    ]

    best_route = route
    best_charging = charging
    best_cost = evaluate(graph, ev, route, charging)

    # Pilih strategi secara random untuk sekarang (bisa diadaptasi ke probabilitas/score-based)
    # destroy = random.choice(destroy_methods)
    # repair = random.choice(repair_methods)

    destroy_idx = roulette_wheel_select(destroy_scores)
    repair_idx = roulette_wheel_select(repair_scores)

    destroy = destroy_methods[destroy_idx]
    repair = repair_methods[repair_idx]

    print(f"Destroy #{destroy_idx}, Repair #{repair_idx}")

    # Destroy
    print("lagi destroy")
    temp_route, temp_charging = destroy(copy.deepcopy(best_route), copy.deepcopy(best_charging))

    # Repair
    print("lagi repair")
    temp_route = repair(temp_route)

    if len(temp_route) >= 2 and temp_route[-1] == temp_route[-2]:
        temp_route.pop()

    # Validate
    temp_charging, _ = validate_charging_after_backtrack(graph, ev, temp_route)
    cost = evaluate(graph, ev, temp_route, temp_charging)

    # if cost < best_cost:
    #     return temp_route, temp_charging, cost
    # return best_route, best_charging, best_cost

    improved = cost < best_cost
    if improved:
        destroy_scores[destroy_idx] += 0.1
        repair_scores[repair_idx] += 0.1
        return temp_route, temp_charging, cost, destroy_scores, repair_scores
    else:
        destroy_scores[destroy_idx] *= 0.95
        repair_scores[repair_idx] *= 0.95
        return best_route, best_charging, best_cost, destroy_scores, repair_scores