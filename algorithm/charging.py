import numpy as np
import copy
import torch
from .utils import calculate_energy_model
from model_queue.model import WaitingTimeNN, model_loaded, scaler_x_loaded, scaler_y_loaded

def add_charging_schedule(soc_start, soc_target, ev_capacity_kwh, charging_rate):
    """
    Menghitung waktu pengisian baterai EV secara linear (dalam menit).

    Parameters:
    - soc_start: SOC awal (%), antara 0–100
    - soc_target: SOC target (%), antara 0–100
    - ev_capacity_kwh: kapasitas baterai EV (kWh)
    - ev_max_rate: maksimum kecepatan pengisian yang didukung EV (kW)
    - cs_rate: kecepatan pengisian dari charging station (kW)

    Returns:
    - Waktu pengisian dalam menit
    """
    delta_soc = max(0.0, soc_target - soc_start) / ev_capacity_kwh
    energy_needed = delta_soc * ev_capacity_kwh  # kWh

    charging_time = (energy_needed / charging_rate) * 60  # dalam menit

    charging_schedule = {
        'soc_start': soc_start,
        'soc_target': soc_target,
        'charging_rate': charging_rate,
        'charging_time': charging_time
    }

    return charging_schedule

def validate_charging_after_backtrack(graph, ev, cleaned_route):
    """
    Membuat ulang rencana charging berdasarkan rute bersih (tanpa backtrack).
    
    Params:
    - graph: graf SPKLU
    - ev: objek kendaraan listrik
    - cleaned_route: rute hasil remove_simple_backtracks()

    Returns:
    - new_path: rute bersih (tidak berubah)
    - charging_at: dict {node_id: waktu charging (menit)}
    - is_valid: apakah rute valid secara SOC
    """
    charging_at = {}
    soc = copy.deepcopy(ev.battery_now)
    capacity = copy.deepcopy(ev.capacity)
    charging_rate_ev = copy.deepcopy(ev.charging_rate)

    time = 0

    for i in range(len(cleaned_route) - 1):
        # Buat soc 0 lagi, kalau soc kurang dari 0
        soc = max(0, soc)

        curr = cleaned_route[i]
        nxt = cleaned_route[i + 1]

        edge = graph.edges[curr, nxt]
        distance = copy.deepcopy(edge["distance"])
        duration = copy.deepcopy(edge["weight"])
        speed = distance / (duration / 60)

        if speed > ev.max_speed:
            speed = copy.deepcopy(ev.max_speed)

        # Hitung energi yang dibutuhkan
        energy_needed = calculate_energy_model(distance, speed, ev.type)
        
        # Cek cukup atau ngga ke node selanjutnya
        if curr != cleaned_route[0]:
            if soc < energy_needed:
                # Ekstrak data
                waiting_time_prediction = {}
                charging_time_prediction = {}

                slots_param = copy.deepcopy(graph.nodes[curr].get("slots_parameter", {}))
                slots_indicator = copy.deepcopy(graph.nodes[curr].get("slots_indicator", {}))

                for rate, param in slots_param.items():
                    rate_kW = int(rate.split()[0])

                    if rate_kW > charging_rate_ev:
                        continue  # skip kalau rate lebih tinggi dari kemampuan charging EV

                    indicator_data = slots_indicator.get(rate, None)

                    arrival_rate = param["arrival_rate"]
                    service_rate = param["service_rate"]
                    s = param["s"]

                    print("Time after indicator change:", indicator_data.get("time_after_indicator_change", 0))
                    
                    input_vector = [indicator_data.get("indicator", 0.0), indicator_data.get("time_after_indicator_change", 0) + time, rate_kW, arrival_rate, service_rate, s]

                    print("Time after indicator + time", indicator_data.get("time_after_indicator_change", 0) + time)

                    # Prediksi waiting time dari model
                    scaled = scaler_x_loaded.transform([input_vector])
                    tensor = torch.tensor(scaled, dtype=torch.float32)

                    with torch.no_grad():
                        pred = model_loaded(tensor).numpy()
                        pred_final = np.expm1(np.clip(scaler_y_loaded.inverse_transform(pred), a_min=None, a_max=6.5))

                    waiting_time_prediction[rate] = max(0.0, round(float(pred_final[0][0]), 2))

                    if energy_needed > ev.capacity:
                        charging_time_prediction[rate] = add_charging_schedule(soc, ev.capacity, capacity, rate_kW)
                    else:
                        energy_needed_plus_buffer = min(energy_needed + (0.2 * ev.capacity), ev.capacity) # Supaya setidaknya ada 10% baterai tambahan atau kapasitas baterai full
                        charging_time_prediction[rate] = add_charging_schedule(soc, energy_needed_plus_buffer, capacity, rate_kW)

                # Gabungkan waiting_time + charging_time untuk setiap rate
                if waiting_time_prediction and charging_time_prediction:
                    total_time_per_rate = {}

                    for rate in waiting_time_prediction:
                        wait = waiting_time_prediction[rate]
                        charge = charging_time_prediction[rate]["charging_time"]
                        total = wait + charge
                        total_time_per_rate[rate] = round(total, 2)

                    # Ambil rate dengan total waktu terkecil
                    best_rate = min(total_time_per_rate, key=total_time_per_rate.get)
                    best_time = total_time_per_rate[best_rate]

                    soc = charging_time_prediction[best_rate]["soc_target"] - energy_needed

                    charging_at[curr] = {
                        **charging_time_prediction[best_rate],  # isi dari charging_time_prediction
                        "waiting_time": waiting_time_prediction[best_rate]  # tambahkan waktu tunggu
                    }
                    time = time + charging_time_prediction[best_rate]["charging_time"] + waiting_time_prediction[best_rate]
                    print("Charging time:", charging_time_prediction[best_rate]["charging_time"])
                    print("Waiting time:", waiting_time_prediction[best_rate])
            else:
                soc -= energy_needed
        else:
            soc -= energy_needed

        time = time + (distance / speed * 60)
        print((distance / speed * 60))
        print("Time", time)

    return charging_at, True
