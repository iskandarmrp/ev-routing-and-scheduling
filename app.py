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
        'battery_capacity': 130,
        'battery_now': 90,
        'charging_rate': 125,
        'current_lat': -1.5882215,
        'current_lon': 103.61938
    }

    route_nodes = [34, 1, 152, 5, 80]

    charging_at = {
        34: {'soc_start': 90, 'soc_target': 118, 'charging_rate': 22, 'charging_time': 76.36363636363636, 'waiting_time': 0.38},
        1: {'soc_start': 12.78, 'soc_target': 93.75, 'charging_rate': 22, 'charging_time': 220.82, 'waiting_time': 0.38},
        152: {'soc_start': 23.60, 'soc_target': 118, 'charging_rate': 30, 'charging_time': 188.80, 'waiting_time': 0.38},
        5: {'soc_start': 14.86, 'soc_target': 82.67, 'charging_rate': 50, 'charging_time': 81.37, 'waiting_time': 0.38},
    }

    def run_sim():
        sim = Simulation(
            graph_file="preprocessing_graph/spklu_sumatera_graph_with_parameters_231.pkl",
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
        "ev_status": status_data.get('ev_status'),
        "current_position": status_data.get("current_position"),
        "polyline": status_data.get("polyline"),
    }

# Endpoint default root (opsional)
@app.get("/")
def root():
    return {"message": [status_data.get('battery'), status_data.get('ev_status'), status_data.get('current_position')]}
