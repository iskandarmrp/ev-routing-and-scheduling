# import
import simpy
import osmnx as ox
import numpy as np
import pickle
import random
import time
import requests
import polyline

from object.charging_station import (
    ChargingSlot,
    ChargingStation
)
from object.electric_vehicle import (
    ElectricVehicle
)
from algorithm.algorithm import (hybrid_pso_alns_evrp)


# Status
status_data = {
    "battery": None,
    "capacity": None,
    "ev_status": None,
    "current_position": None,
    "charging_stations": [],
    "charging_plan": [],
    "polyline": [],
    "current_from_node": None,
    "current_to_node": None,
    "charging_at_node": None,
    "charging_stations": [],
    "time_now": None,
}

# function user_input
def user_input(vehicle_type):
    """
    function untuk user melakukan input data EV
    param:
    vehicle_type -> tipe kendaraan ('Tesla S', 'BMW i3', 'Nissan Leaf', or 'Other')
    """
    # Cek apakah input benar
    if vehicle_type not in ['tesla s', 'bmw i3', 'nissan leaf', 'other']:
        raise ValueError("Invalid vehicle type! Choose from 'Tesla S', 'BMW i3', 'Nissan Leaf', or 'Other'.")
    
    # Inisialisasi
    battery_capacity = 100
    charging_rate = 50

    # Masukkan input sesuai tipe kendaraan
    if vehicle_type == "tesla s":
        vehicle_type = "tesla"
        battery_capacity = 98
        charging_rate = 125
    elif vehicle_type == "bmw i3":
        vehicle_type = "bmw"
        battery_capacity = 37.9
        charging_rate = 47
    elif vehicle_type == "nissan leaf":
        vehicle_type = "leaf"
        battery_capacity = 39
        charging_rate = 40
    else:
        vehicle_type = "other"
        battery_capacity = float(input("Enter battery capacity in kWh: "))
        charging_rate = float(input("Enter charging rate in kW: "))
    
    # Melakukan input lanjutan EV dari User
    max_speed_kmh = float(input("Enter maximum speed in km/h: "))
    battery_now = float(input("Enter current battery level in kWh: "))
    current_lat = float(input("Enter current latitude: "))
    current_lon = float(input("Enter current longitude: "))

    # Menghasilkan dictionary untuk input EV
    return {
        'type': vehicle_type,
        'max_speed_kmh': max_speed_kmh,
        'battery_capacity': battery_capacity,
        'battery_now': battery_now,
        'charging_rate': charging_rate,
        'current_lat': current_lat,
        'current_lon': current_lon
    }

# todo: get_route (pakai algoritma yang dibuat)
# function get_route
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

def get_node_by_latlon(G, lat, lon):
    """
    mencari node sesuai dengan latitude dan longitude

    param:
    G -> graph
    lat -> latitude
    lon -> longitude
    """
    for node, data in G.nodes(data=True):
        if data.get('lat') == lat and data.get('lon') == lon:
            return node
    return None

def get_nearest_node(G, lat, lon):
    """
    mengambil node terdekat dari lat dan lon tertentu

    param:
    G -> graph (G yang harus sudah ada kolom duration pada G.edges(keys=True, data=True))
    lat -> latitude
    lon -> longitude
    """
    return ox.distance.nearest_nodes(G, float(lon), float(lat))

def get_node_lat_lon(G, node_id):
    """
    mengambil latitude dan longitude dari node_id

    param:
    G -> graph (G yang harus sudah ada kolom duration pada G.edges(keys=True, data=True))
    node_id -> id dari node

    return: 
    (lat, lon)
    """
    numpy_nodes = np.array(list(G.nodes(data=True)))
    mask = numpy_nodes[:, 0] == node_id
    filtered = numpy_nodes[mask]
    node = filtered[0]
    lat, lon = float(node[1]["y"]), float(node[1]["x"])
    return (lat, lon)

# function get edges
def find_edges(u, v, G):
    """
    menerima:
    u -> id node asal
    v -> id node tujuan
    G -> graph (G yang harus sudah ada kolom duration pada G.edges(keys=True, data=True))

    return: edges yang memiliki titik asal node dengan id u dan titik tujuan dengan node v
    """
    edges_numpy = np.array(list(G.edges(keys=True, data=True)))
    mask = (edges_numpy[:, 0] == u) & (edges_numpy[:, 1] == v)
    filtered = edges_numpy[mask]
    return filtered[0]

# procedure edges management (Weight: Duration) (Untuk graph awal)
# Ini masih asal ngerandomnya
# SOKIN
def manage_all_edges(graph):
    """
    Melakukan sampling weight (Durasi) untuk Graph awal sebelum menentukan rute
    param:
    G -> graph

    Contoh isi edge pada Graph: (0, 1, {'weight': 10.716666666666667, 'distance': 5.404, 'weight_mean': 716666666666667, 'weight_std': 1.0716666666666668})
    """
    for u, v, data in graph.edges(data=True):
        original_weight = data.get("weight", 1.0)
        perturbation = random.uniform(-0.1, 0.1) * original_weight
        data["weight"] = max(0.1, original_weight + perturbation)

# procedure nodes management (Charging Station Availability) (Untuk graph awal)
def manage_all_nodes(graph, charging_stations):
    """
    Melakukan sampling availability untuk Graph awal sebelum menentukan rute
    param:
    G -> graph

    Contoh isi Graph: (0, {'name': 'SPLU', 'lat': -6.920398, 'lon': 107.6088493, 'is_charging_station': True, 'total_slots': 2, 'slots_charging_rate': [1.0, 2.0], 'slots_availability_std': 0.5, 'slots_availability_mean': 1.55, 'slots_availability': [True, True]})
    """
    for node_id, station in charging_stations.items():
        # Ambil parameter dari ChargingStation
        slots_param = station.slots_parameter
        indicator = {}

        for rate, params in slots_param.items():
            p = params.get("p", 0.025)
            s = params.get("s", 1)
            occupied = sum(1 if random.random() < p else 0 for _ in range(s))
            indicator_value = round(occupied / s, 2)

            # Simpan dengan struktur dict lengkap
            indicator[rate] = {
                "indicator": indicator_value,
                "time_after_indicator_change": random.randint(0, 125)  # acak 15-45 menit
            }

        # Simpan hasil ke ChargingStation
        station.slots_indicators = indicator

        # Jika node_id juga ada di graph, update graph-nya juga
        if node_id in graph.nodes:
            graph.nodes[node_id]["slots_indicator"] = indicator

# todo: buat simulasi rute (simulasiin rute yang didapat dari function get route)
# procedure simulate route
def simulate_route(env, G, charging_at, charging_stations, ev, route):
    for i in range(len(route) - 1):
        OSRM_URL = "http://localhost:5000"
        lon1 = G.nodes[route[i]]['longitude']
        lat1 = G.nodes[route[i]]['latitude']
        lon2 = G.nodes[route[i + 1]]['longitude']
        lat2 = G.nodes[route[i + 1]]['latitude']

        try:
            url = f"{OSRM_URL}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=polyline"
            response = requests.get(url)
            data = response.json()

            if data["code"] == "Ok":
                route_data = data["routes"][0]
                polyline_str = route_data["geometry"]
                decoded_polyline = polyline.decode(polyline_str)  # list of (lat, lon)

                status_data["polyline"].append(decoded_polyline)

            else:
                print(f"❌ gagal ambil polyline")
        except Exception as e:
            print(f"⚠️ Error saat memproses polyline: {e}")

    for i in range(len(route) - 1):
        from_node = route[i]
        to_node = route[i + 1]

        status_data["current_from_node"] = None
        status_data["current_to_node"] = None
        status_data["charging_at_node"] = None  # reset charging status

        # Simulasi drive dan charging
        yield from ev.drive(env, G, charging_at, charging_stations, from_node, to_node, status_data)

# Object

# SOKIN (BACA CLASS BENER GA)


# todo: bikin class Simulation
class Simulation:
    def __init__(self, graph_file, ev_input, route, charging_at):
        self.env = simpy.Environment() # Inisialisasi ENV
        self.graph_file = graph_file # File Graph
        self.G = None # Graph
        self.ev_input = ev_input
        self.ev = None # EV
        self.charging_stations = {}
        self.route = route # Rute
        self.charging_at = charging_at # Schedule

    # Melakukan load graph file
    def load_graph(self):
        with open(self.graph_file, "rb") as f:
            self.G = pickle.load(f)

    # Membuat banyak charging station menggunakan class charging station dengan csv
    def setup_charging_stations(self):
        for node_id, data in self.G.nodes(data=True):
            if not data.get("is_charging_station", False):
                continue  # Skip kalau bukan charging station

            # Ambil informasi
            slots_parameter = data.get("slots_parameter")
            if not slots_parameter:
                continue  # Skip kalau tidak ada data slot

            # Kita ambil jumlah slot dari penjumlahan 'k' di setiap slot type
            total_slots = sum(slot_info["s"] for slot_info in slots_parameter.values())

            # Ambil charging rate per slot (e.g. [22, 22, ...] sebanyak total slot)
            slots_charging_rate = []
            for rate_str, slot_info in slots_parameter.items():
                rate = int(rate_str.split()[0])  # ambil angka dari "22 kW"
                slots_charging_rate.extend([rate] * slot_info["s"])

            # Simpan ChargingStation
            self.charging_stations[node_id] = ChargingStation(
                env=self.env,
                node_id=node_id,
                name=data.get("name"),
                latitude=data.get("latitude"),
                longitude=data.get("longitude"),
                total_slots=total_slots,
                slots_charging_rate=slots_charging_rate,
                slots_indicators=data.get("slots_indicator"),
                slots_parameter=data.get("slots_parameter"),
            )

    # Membuat EV menggunakan class EV dengan input ev
    def setup_electric_vehicle(self):
        self.ev = ElectricVehicle(
            **self.ev_input
        )
        print("EV berhasil dibuat")

    def run(self):
        global G
        global charging_stations
        global charging_at

        self.load_graph()
        self.setup_charging_stations()
        self.setup_electric_vehicle()

        G = self.G
        charging_stations = self.charging_stations

        charging_at = self.charging_at

        status_data["capacity"] = self.ev.capacity
        status_data["charging_plan"] = list(charging_at.items())

        status_data["current_position"] = [self.ev.current_lat, self.ev.current_lon]
        
        status_data["charging_stations"] = [
            {
                "node_id": station.node_id,
                "name": station.name,
                "latitude": station.latitude,
                "longitude": station.longitude,
                "total_slots": station.total_slots,
                "availability": {
                    rate: {
                        "available": round((1 - info.get("indicator", 0.0)) * station.slots_parameter[rate]["s"]),
                        "total": station.slots_parameter[rate]["s"],
                        "time_after_indicator_change": info.get("time_after_indicator_change", 0)
                    }
                    for rate, info in station.slots_indicators.items()
                }
            }
            for station in self.charging_stations.values()
        ]

        self.env.process(simulate_route(self.env, self.G, self.charging_at, self.charging_stations, self.ev, self.route))
        print('Simulasi sedang berjalan')
        # self.env.run()

        while True:
            if not self.env._queue:
                break

            now = self.env.now
            next_time = self.env.peek()  # waktu event berikutnya

            delta = next_time - now

            self.env.step()
            # Perbarui status setiap step
            status_data["battery"] = self.ev.battery_now
            status_data["ev_status"] = self.ev.status
            status_data["current_position"] = [self.ev.current_lat, self.ev.current_lon]
            status_data["charging_stations"] = [
                {
                    "node_id": station.node_id,
                    "name": station.name,
                    "latitude": station.latitude,
                    "longitude": station.longitude,
                    "total_slots": station.total_slots,
                    "availability": {
                        rate: {
                            "available": round((1 - info.get("indicator", 0.0)) * station.slots_parameter[rate]["s"]),
                            "total": station.slots_parameter[rate]["s"],
                            "time_after_indicator_change": info.get("time_after_indicator_change", 0)
                        }
                        for rate, info in station.slots_indicators.items()
                    }
                }
                for station in self.charging_stations.values()
            ]
            status_data["time_now"] = self.env.now
            # if not status_data["polyline"] or status_data["polyline"][-1] != [self.ev.current_lat, self.ev.current_lon]:
            #     status_data["polyline"].append([self.ev.current_lat, self.ev.current_lon])

            time.sleep(delta)  # real-time delay sesuai timeout simulasi

if __name__ == '__main__':
    # ev_input = {
    #     'type': 'bmw',
    #     'max_speed_kmh': 60,
    #     'battery_capacity': 50,
    #     'battery_now': 20,
    #     'charging_rate': 2.0,
    #     'current_lat': -6.2,
    #     'current_lon': 106.8
    # }

    ev_input = {
        'type': 'tesla',
        'max_speed_kmh': 100,
        'battery_capacity': 118,
        'battery_now': 100,
        'charging_rate': 125,
        'current_lat': -1.5882215,
        'current_lon': 103.61938
    }
    
    # vehicle_type = input("Enter vehicle type (Tesla S, BMW i3, Nissan Leaf, or Other): ").lower()
    # ev_input = user_input(vehicle_type)

    # Random charging station availability (Harusnya random buat Graph)
    # manage_all_nodes(charging_stations)

    # todo: Mendapatkan rute dari algoritma yang telah dibuat
    # get_route()

    # Sementara: Fixed Route, Nanti akan diganti dari algoritma
    # route_nodes = [0, 1, 3] # Osmnx kayak gini
    route_nodes = [34, 220, 54, 52, 186, 80]

    # charging_at = {
    #     1: 10  # node 1 ngecas manual 10 menit
    # }

    charging_at = {
        220: {'soc_start': 39.73169449489532, 'soc_target': 104.18162443114582, 'charging_rate': 22, 'charging_time': 175.7725361897741, 'waiting_time': 0.2},
        54: {'soc_start': 23.60000000000001, 'soc_target': 56.65666220673904, 'charging_rate': 50, 'charging_time': 39.66799464808684, 'waiting_time': 0.34},
        52: {'soc_start': 23.6, 'soc_target': 109.47820326199832, 'charging_rate': 50, 'charging_time': 103.05384391439799, 'waiting_time': 0.39},
        186: {'soc_start': 23.60000000000001, 'soc_target': 100.35456449293835, 'charging_rate': 100, 'charging_time': 46.052738695763004, 'waiting_time': 0.5}
    }
    
    sim = Simulation(
        graph_file="preprocessing_graph/spklu_sumatera_graph_with_parameters_231_modified.pkl",
        ev_input = ev_input,
        route=route_nodes,
        charging_at = charging_at
    )
    sim.run()