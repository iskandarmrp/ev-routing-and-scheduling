import numpy as np
import pickle
import random
import copy
import time
from .utils import (
    calculate_energy_model,
    decode_particle_with_visit,
    encode_route_to_position_alns,
    create_visit_decision_from_route,
    update_velocity,
    update_position
)
from .charging import (add_charging_schedule, validate_charging_after_backtrack)
from .evaluation import (evaluate)
from object.particle import Particle

def destroy(route, charging, degree=2):
    # degree: berapa banyak node yang mungkin dihancurkan
    if len(route) <= 2:
        return route, charging
    
    # Node yang berada ditengah (Mengeluarkan node awal dan node tujuan)
    middle_nodes = list(range(1, len(route) - 1))

    # Clamp degree supaya tidak lebih dari jumlah node tengah
    max_removable = min(degree, len(middle_nodes))
    remove_count = random.randint(1, max_removable)

    # Pilih node tengah yang akan dihancurkan (Sekarang masih random (Harusnya bisa Adaptive))
    remove_idx = random.sample(middle_nodes, remove_count)

    # Build new route (skip removed indices)
    new_route = [node for idx, node in enumerate(route) if idx not in remove_idx]

    # Charging info juga diupdate
    print(charging)
    new_charging = {k: v for k, v in charging.items() if k in new_route}

    return new_route, new_charging

def repair_method(route, G_max, all_nodes):
    """
    Menyisipkan node secara acak ke dalam rute tanpa mengecek keterhubungan.
    G_max: maksimum jumlah node yang ingin disisipkan.
    """

    remaining_nodes = list(set(all_nodes) - set(route))
    insert_target = random.randint(1, G_max)
    inserted = 0

    while inserted < insert_target and remaining_nodes:
        candidate = random.choice(remaining_nodes)
        remaining_nodes.remove(candidate)

        # Tentukan posisi random di route untuk penyisipan (selain pertama dan terakhir)
        if len(route) > 2:
            insert_pos = random.randint(1, len(route) - 2)
        else:
            insert_pos = 1  # minimal posisi sisipan

        route.insert(insert_pos, candidate)
        inserted += 1

    return route

def alns_search(graph, ev, route, charging, all_nodes, G_max=2):
    """
    Hybrid ALNS search:
    - destroy beberapa node dari rute
    - repair dengan shortest path dan charging jika perlu
    - hanya update jika solusi valid dan lebih baik
    """

    # Inisialisasi
    best_route = route
    best_charging = charging
    # news_path, news_charging, is_valids = validate_route_with_charging(graph, ev, route, charging)
    # news_path = remove_simple_backtracks(news_path)
    
    news_path = route

    # Validate charging
    news_charging, charging_is_valid = validate_charging_after_backtrack(graph, ev, news_path)
    best_cost = evaluate(graph, ev, news_path, news_charging)

    # Step 1: Destroy
    temp_route, temp_charging = destroy(
        copy.deepcopy(best_route),
        copy.deepcopy(best_charging),
        round(G_max/2)
    )

    # Step 2: Repair
    temp_route = repair_method(
        temp_route, min(G_max,10), all_nodes
    )

    # Step 3: Validasi + charging SOC check
    validated_route = temp_route
    validated_charging, charging_is_valid = validate_charging_after_backtrack(graph, ev, validated_route)

    # validated_route, validated_charging, is_valid = validate_route_with_charging(
    #     graph, ev, temp_route, temp_charging
    # )
    # validated_route = remove_simple_backtracks(validated_route)

    # Harusnya kalau invalid bukannya pass aja? supaya cari solusi valid? (Eh kayaknya bener)
    # if not route_is_valid:
    #     no_improve += 1
    #     continue  # skip solusi invalid

    # Step 4: Evaluate cost
    cost = evaluate(graph, ev, validated_route, validated_charging)
    print("Cost:", cost)

    return best_route, best_charging, best_cost

def hybrid_pso_alns_evrp(graph, ev, start_node, destination_node, n_particles=10, max_iter=500, stagnation=50, max_time=300):
    y = 0.7
    phi1 = 1.5
    phi2 = 1.5
    all_nodes = list(graph.nodes)

    start_time = time.time()

    particles = [Particle(graph, ev, start_node, destination_node) for _ in range(n_particles)]

    # Ambil partikel terbaik
    gbest_idx = np.argmin([p.best_score for p in particles])
    gbest = copy.deepcopy(particles[gbest_idx].best_position)
    gbest_route = copy.deepcopy(particles[gbest_idx].best_decoded_particle)
    gbest_visit_decision = copy.deepcopy(particles[gbest_idx].best_visit_decision)
    gbest_charge = copy.deepcopy(particles[gbest_idx].best_charging_at)
    gbest_cost = copy.deepcopy(particles[gbest_idx].best_score)

    no_improvement = 0

    # Buat ngetrack
    trace = [gbest_cost]

    for _ in range(max_iter):
        # Timeout
        if (time.time() - start_time >= max_time):
            print("⏱️ Timeout reached: terminating early")
            break

        for i in range(n_particles):
            particle = particles[i]

            # Buat daftar kandidat yang bukan i
            candidates = [x for x in range(len(particles)) if x != i]

            # Pilih 2 nilai berbeda dari kandidat
            p1, p2 = random.sample(candidates, 2)

            particle.velocity = update_velocity(particle.velocity, particle.position, particle.best_position, gbest, phi1, phi2)
            particle.position = update_position(particle.position, particle.velocity, particles[p1].position, particles[p2].position, y)
            particle.decoded_particle = decode_particle_with_visit(particle.position, particle.visit_decision, start_node, destination_node)

            alns_route, alns_charging, alns_cost = alns_search(graph, ev, particle.decoded_particle, particle.charging_at, all_nodes, G_max=15)

            # Encode Hasil Rute ALNS
            alns_position = encode_route_to_position_alns(alns_route, len(graph.nodes), start_node, destination_node)

            alns_visit_decision = create_visit_decision_from_route(alns_route, list(graph.nodes))

            # Decode position jadi rute lagi
            # Validasi rute
            # if valid baru evaluasi
            # Sementara blm di decode aja dulu (Pake alns)
            decoded_route = decode_particle_with_visit(alns_position, alns_visit_decision, start_node, destination_node)

            # news_path, news_charging, is_valids = validate_route_with_charging(graph, ev, decoded_route, alns_charging)
            # news_path = remove_simple_backtracks(news_path)
            # news_charging = {k: v for k, v in news_charging.items() if k in news_path}

            # news_path, route_is_valid = validate_route_without_charging(graph, decoded_route)
            # news_path = remove_path_loop(news_path)
            news_path = decoded_route
            news_charging, charging_is_valid = validate_charging_after_backtrack(graph, ev, news_path)

            news_path = [news_path[0]] + [
                node for node in news_path[1:-1] if node in news_charging
            ] + [news_path[-1]]

            news_path_visit_decision = create_visit_decision_from_route(news_path, list(graph.nodes))

            # if route_is_valid:
                # Ini blm bener cuma nyoba2 aja (Harusnya di decode encode dulu itu ALNS nya)

                # Ini visit decision harusnya digunain pas ngelakuin decode dari position
            if evaluate(graph, ev, news_path, news_charging) < gbest_cost:
                particle.best_position = copy.deepcopy(alns_position)
                particle.best_decoded_particle = copy.deepcopy(news_path)
                particle.best_visit_decision = copy.deepcopy(news_path_visit_decision)
                particle.best_charging_at = copy.deepcopy(news_charging)
                particle.best_score = evaluate(graph, ev, news_path, news_charging)

            if evaluate(graph, ev, news_path, news_charging) < gbest_cost:
                gbest = copy.deepcopy(alns_position)
                gbest_route = copy.deepcopy(news_path)
                gbest_visit_decision = copy.deepcopy(news_path_visit_decision)
                gbest_charge = copy.deepcopy(news_charging)
                gbest_cost = evaluate(graph, ev, news_path, news_charging)
                no_improvement = 0

        trace.append(gbest_cost)
        no_improvement += 1
        if no_improvement >= stagnation:
            break

    return gbest, gbest_route, gbest_charge, gbest_cost, gbest_visit_decision, trace