import pickle
from object.electric_vehicle import ElectricVehicle
from algorithm.algorithm import hybrid_pso_alns_evrp
from algorithm.evaluation import evaluate

file_path = 'preprocessing_graph/spklu_sumatera_graph_with_parameters_231_modified.pkl'
with open(file_path, 'rb') as f:
    graph = pickle.load(f)

ev_input = {
    'type': 'tesla',
    'max_speed_kmh': 80,
    'battery_capacity': 39,
    'battery_now': 30,
    'charging_rate': 33,
    'current_lat': -1.5882215,
    'current_lon': 103.61938
}

ev = ElectricVehicle(**ev_input)

start_node = 34
destination_node = 80

def get_route(start_node, destination_node, G, ev):
    """
    function yang melakukan routing dari init_node ke dest_node

    function ini merupakan pengganti route dari BE dan route dari myBlueBird(pokonya routing itu dari luar simulasi) -> simulasimah hanya nerima route dan mensimulasikannya

    param: 
    init_node -> id node awal
    dest_node -> id node tujuan
    G -> graph (G yang harus sudah ada kolom duration pada G.edges(keys=True, data=True))

    return route yang berupa array of node_id
    """
    gbest_position, gbest_route, gbest_charge, gbest_cost, trace, particles_trace = hybrid_pso_alns_evrp(G, ev, start_node, destination_node, n_particles=15, max_iter=1000, stagnation=500, max_time=30)
    # route = nx.shortest_path(G, init_node, dest_node, weight='duration')
    return gbest_position, gbest_route, gbest_charge, gbest_cost, trace

gbestpost, gbest_route, gbest_charge, gbest_cost, trace = get_route(start_node, destination_node, graph, ev)
print("G_best Post:", gbestpost)
print("G_best Route:", gbest_route)
print("G_best Charging:", gbest_charge)
print("G_best Cost:", gbest_cost)
print("Trace:", trace)
print("Cost Evaluation:", evaluate(graph, ev, gbest_route, gbest_charge))