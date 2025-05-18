import pickle
from object.electric_vehicle import ElectricVehicle
from algorithm.utils import decode_particle_with_visit
from algorithm.algorithm import hybrid_pso_alns_evrp

file_path = 'preprocessing_graph/spklu_sumatera_graph_with_parameters_231.pkl'
with open(file_path, 'rb') as f:
    graph = pickle.load(f)

ev_input = {
    'type': 'tesla',
    'max_speed_kmh': 100,
    'battery_capacity': 118,
    'battery_now': 90,
    'charging_rate': 125,
    'current_lat': -1.5882215,
    'current_lon': 103.61938
}

ev = ElectricVehicle(**ev_input)

start_node = 34
destination_node = 1
# 53

gbest_position, gbest_route, gbest_charge, gbest_cost, gbest_visit_decision, trace = hybrid_pso_alns_evrp(graph, ev, start_node, destination_node, n_particles=10, max_iter=10000, stagnation=500, max_time=120)
rute_decoded = decode_particle_with_visit(gbest_position, gbest_visit_decision, start_node, destination_node)

print("Rute terbaik:", gbest_route)
print("Charging schedule terbaik:", gbest_charge)
print("Cost terbaik:", gbest_cost)
print("Decoded Rute:", rute_decoded)
# rute_validasi, route_is_valid = validate_route_without_charging(graph, rute_decoded)
# rute_validasi = remove_path_loop(rute_validasi)
# print("Decoded Rute Validated:", rute_validasi)