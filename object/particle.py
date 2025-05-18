import copy
from algorithm.evaluation import evaluate
from algorithm.random_initialization import random_evrp_solution
from algorithm.utils import decode_particle_with_visit

class Particle:
    def __init__(self, graph, ev, start_node, destination_node):
        route, charging_at, visit_decision, position, velocity = random_evrp_solution(
            graph, ev, start_node, destination_node
        )
        self.position = copy.deepcopy(position)
        self.velocity = copy.deepcopy(velocity)
        self.charging_at = copy.deepcopy(charging_at)
        self.visit_decision = copy.deepcopy(visit_decision)
        self.decoded_particle = decode_particle_with_visit(position, visit_decision, start_node, destination_node)
        self.score = evaluate(graph, ev, route, charging_at)
        self.best_position = copy.deepcopy(position)
        self.best_charging_at = copy.deepcopy(charging_at)
        self.best_decoded_particle = copy.deepcopy(self.decoded_particle)
        self.best_score = copy.deepcopy(self.score)
        self.best_visit_decision = copy.deepcopy(visit_decision)