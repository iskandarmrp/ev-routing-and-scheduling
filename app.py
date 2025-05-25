from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from threading import Thread
# from simulasi import start_simulation, status_data
from simulasi import Simulation, status_data

app = FastAPI()

# Middleware agar React Native bisa fetch data dari API ini
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Ganti dengan domain tertentu jika ingin lebih aman
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Saat server FastAPI dinyalakan, jalankan simulasi di thread terpisah
@app.on_event("startup")
def startup_event():
    ev_input = {
        'type': 'tesla',
        'max_speed_kmh': 100,
        'battery_capacity': 118,
        'battery_now': 90,
        'charging_rate': 125,
        'current_lat': -1.5882215,
        'current_lon': 103.61938
    }

    route_nodes = [34, 220, 54, 52, 186, 80]

    charging_at = {
        220: {'soc_start': 39.73169449489532, 'soc_target': 104.18162443114582, 'charging_rate': 22, 'charging_time': 175.7725361897741, 'waiting_time': 0.2},
        54: {'soc_start': 23.60000000000001, 'soc_target': 56.65666220673904, 'charging_rate': 50, 'charging_time': 39.66799464808684, 'waiting_time': 0.34},
        52: {'soc_start': 23.6, 'soc_target': 109.47820326199832, 'charging_rate': 50, 'charging_time': 103.05384391439799, 'waiting_time': 0.39},
        186: {'soc_start': 23.60000000000001, 'soc_target': 100.35456449293835, 'charging_rate': 100, 'charging_time': 46.052738695763004, 'waiting_time': 0.5}
    }

    def run_sim():
        sim = Simulation(
            graph_file="preprocessing_graph/spklu_sumatera_graph_with_parameters_231_modified.pkl",
            ev_input = ev_input,
            route=route_nodes,
            charging_at = charging_at
        )
        sim.run()

    thread = Thread(target=run_sim, daemon=True)
    thread.start()

# Endpoint untuk mendapatkan data status EV secara real-time
@app.get("/status")
def get_status():
    return {
        "battery": status_data.get("battery"),
        "capacity": status_data.get("capacity"),
        "ev_status": status_data.get('ev_status'),
        "current_position": status_data.get("current_position"),
        "polyline": status_data.get("polyline"),
        "current_from_node": status_data.get("current_from_node"),
        "current_to_node": status_data.get("current_to_node"),
        "charging_at_node": status_data.get("charging_at_node"),
        "charging_stations": status_data.get("charging_stations"),
        "charging_plan": status_data.get("charging_plan"),
        "time_now": status_data.get("time_now"),
    }

# Endpoint default root (opsional)
@app.get("/")
def root():
    return {"message": [status_data.get('battery'), status_data.get('ev_status'), status_data.get('current_position')]}
