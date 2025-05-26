import copy
from algorithm.evaluation import evaluate
from algorithm.random_initialization import random_evrp_solution_greedy

class Particle:
    def __init__(self, graph, ev, start_node, destination_node):
        route, charging_at, position, velocity = random_evrp_solution_greedy(
            graph, ev, start_node, destination_node
        )
        # if random.random() < 0.6:
        #     # 60% gunakan solusi random
        #     route, charging_at, visit_decision, position, velocity = random_evrp_solution_random(graph, ev, start_node, destination_node)
        # else:
        #     # 40% gunakan solusi greedy
        #     route, charging_at, visit_decision, position, velocity = random_evrp_solution_greedy(graph, ev, start_node, destination_node)
        score = evaluate(graph, ev, route, charging_at)
        self.position = copy.deepcopy(position)
        self.velocity = copy.deepcopy(velocity)
        self.charging_at = copy.deepcopy(charging_at)
        # self.visit_decision = copy.deepcopy(visit_decision)
        self.decoded_particle = copy.deepcopy(route)
        self.score = copy.deepcopy(score)
        self.best_position = copy.deepcopy(position)
        self.best_charging_at = copy.deepcopy(charging_at)
        self.best_decoded_particle = copy.deepcopy(self.decoded_particle)
        self.best_score = copy.deepcopy(score)
        # self.best_visit_decision = copy.deepcopy(visit_decision)
        self.destroy_scores = [1.0] * 7
        self.repair_scores = [1.0] * 4