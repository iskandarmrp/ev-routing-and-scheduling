import numpy as np
import pickle
import random
import copy
import time
from concurrent.futures import ThreadPoolExecutor
import threading
from .utils import (
    decode_with_greedy,
    encode_route_to_position_alns,
    update_velocity,
    update_position
)
from .charging import (validate_charging_after_backtrack)
from .evaluation import (evaluate)
from .alns import (alns_search)
from object.particle import Particle

def particle_update_worker(args):
    global graph_global
    (
        particle_idx, particle,
        ev,
        start_node, destination_node,
        y, phi1, phi2,
        all_nodes,
        p1_position, p2_position, gbest, gbest_route
    ) = args

    start = time.time()
    print(f"➡️ [Start] Worker {particle_idx} (Thread: {threading.current_thread().name})")

    graph = graph_global

    particle.velocity = update_velocity(particle.velocity, particle.position, particle.best_position, gbest, phi1, phi2)
    particle.position = update_position(particle.position, particle.velocity, p1_position, p2_position, y)
    # particle.decoded_particle = decode_particle_with_visit(particle.position, particle.visit_decision, start_node, destination_node)
    # particle.decoded_particle = decode_particle_k_smallest(particle.position, start_node, destination_node, len(particle.best_decoded_particle), delta_k=2)
    particle.decoded_particle = decode_with_greedy(particle.position, graph, ev, start_node, destination_node)

    alns_route, alns_charging, alns_cost, destroy_scores, repair_scores = alns_search(graph, ev, particle.decoded_particle, particle.charging_at, all_nodes, particle.destroy_scores, particle.repair_scores)
    alns_position = encode_route_to_position_alns(alns_route, len(graph.nodes), start_node, destination_node)
    # alns_visit_decision = create_visit_decision_from_route(alns_route, list(graph.nodes))
    # decoded_route = decode_particle_with_visit(alns_position, alns_visit_decision, start_node, destination_node)
    decoded_route = alns_route

    news_path = decoded_route
    news_charging, charging_is_valid = validate_charging_after_backtrack(graph, ev, news_path)
    # news_path = [news_path[0]] + [node for node in news_path[1:-1] if node in news_charging] + [news_path[-1]]
    # news_path_visit_decision = create_visit_decision_from_route(news_path, list(graph.nodes))

    new_score = evaluate(graph, ev, news_path, news_charging)

    end = time.time()
    print(f"✅ [Done] Worker {particle_idx} in {end - start:.2f}s")

    result = {
        "idx": particle_idx,
        "position": alns_position,
        "decoded": news_path,
        # "visit_decision": news_path_visit_decision,
        "charging": news_charging,
        "score": new_score,
        "destroy_scores": destroy_scores,
        "repair_scores": repair_scores,
    }

    return result

def hybrid_pso_alns_evrp(graph, ev, start_node, destination_node, n_particles=10, max_iter=500, stagnation=50, max_time=300):
    global graph_global
    graph_global = graph  # Set global reference

    y = 0.2
    phi1 = 0.4
    phi2 = 0.4
    all_nodes = list(graph.nodes)
    start_time = time.time()

    particles = [Particle(graph, ev, start_node, destination_node) for _ in range(n_particles)]

    gbest_idx = np.argmin([p.best_score for p in particles])
    gbest = copy.deepcopy(particles[gbest_idx].best_position)
    gbest_route = copy.deepcopy(particles[gbest_idx].best_decoded_particle)
    # gbest_visit_decision = copy.deepcopy(particles[gbest_idx].best_visit_decision)
    gbest_charge = copy.deepcopy(particles[gbest_idx].best_charging_at)
    gbest_cost = copy.deepcopy(particles[gbest_idx].best_score)

    no_improvement = 0
    trace = [gbest_cost]
    particles_trace = [[] for _ in range(n_particles)]

    for _ in range(max_iter):
        if (time.time() - start_time >= max_time) and (gbest_cost <= 5000):
            print("⏱️ Timeout reached: terminating early")
            actual_duration = time.time() - start_time
            actual_iterations = len(trace)

            print(f"⏱️ Total runtime: {actual_duration:.2f} seconds")
            print(f"🔁 Total iterations: {actual_iterations}")
            break

        task_inputs = []
        for i, particle in enumerate(particles):
            candidates = [x for x in range(len(particles)) if x != i]
            p1, p2 = random.sample(candidates, 2)
            task_inputs.append((
                i, particle,
                ev,
                start_node, destination_node,
                y, phi1, phi2,
                all_nodes,
                particles[p1].position, particles[p2].position, copy.deepcopy(gbest), copy.deepcopy(gbest_route)
            ))

        with ThreadPoolExecutor() as executor:
            results = list(executor.map(particle_update_worker, task_inputs))

        for result in results:
            idx = result["idx"]
            score = result["score"]

            particles[idx].destroy_scores = result["destroy_scores"]
            particles[idx].repair_scores = result["repair_scores"]

            if score < particles[idx].best_score:
                particles[idx].best_score = score
                particles[idx].best_position = result["position"]
                particles[idx].best_decoded_particle = result["decoded"]
                # particles[idx].best_visit_decision = result["visit_decision"]
                particles[idx].best_charging_at = result["charging"]

            if score < gbest_cost:
                gbest_cost = score
                gbest = result["position"]
                gbest_route = result["decoded"]
                # gbest_visit_decision = result["visit_decision"]
                gbest_charge = result["charging"]
                no_improvement = 0

            particles_trace[idx].append({
                "route": result["decoded"],
                "best_route": particles[idx].best_decoded_particle,
                "position": particles[idx].position,
                "best_position": particles[idx].best_position,
                "score": score,
                "best_score": particles[idx].best_score,
            })

        if (_ != 0) and (_ % 20 == 0):
            particles = [Particle(graph, ev, start_node, destination_node) for _ in range(n_particles)]

        trace.append(gbest_cost)
        no_improvement += 1
        if no_improvement >= stagnation:
            print("📉 Stagnation reached: stopping early")
            break

    # return gbest, gbest_route, gbest_charge, gbest_cost, gbest_visit_decision, trace, particles_trace
    return gbest, gbest_route, gbest_charge, gbest_cost, trace, particles_trace