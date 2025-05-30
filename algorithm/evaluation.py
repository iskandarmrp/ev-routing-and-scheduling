import copy
from .utils import calculate_energy_model

def evaluate(graph, ev, route, charge_times):
    """
    fungsi untuk evaluasi waktu (Jika gagal mengeluarkan inf)
    """
    soc = copy.deepcopy(ev.battery_now)
    t_total = 0.0

    # Melakukan iterasi rute dari setiap node i menuju node j yang ada di dalam daftar rute yang sudah didapatkan
    for idx in range(len(route)-1):
        # Inisialisasi node [i] dan [j]
        i, j = route[idx], route[idx+1]

        # Durasi, jarak, kecepatan rata-rata setiap edges
        distance_km = copy.deepcopy(graph.edges[i, j].get("distance"))
        duration = copy.deepcopy(graph.edges[i, j].get('weight'))
        speed = distance_km / (duration / 60)

        if speed > ev.max_speed:
            speed = copy.deepcopy(ev.max_speed)

        # Menghitung energi
        energy_consumed = calculate_energy_model(distance_km, speed, ev.type)
        # print("SOC sebelum ngecas:", soc)

        # Pengecekan charging time
        if i in charge_times and charge_times[i]["charging_time"] > 0:
            max_valid_rate = copy.deepcopy(charge_times[i]["charging_rate"])
            
            t_charge = copy.deepcopy(charge_times[i]["charging_time"]) # menit
            t_wait = copy.deepcopy(charge_times[i]["waiting_time"]) # menit
            soc += max_valid_rate * (t_charge / 60) # kWh terisi
            soc = min(copy.deepcopy(ev.capacity), soc) # jangan melebihi kapasitas
            # print("SOC setelah mengecas:", soc)

            t_total += t_charge
            t_total += t_wait

        # print("SOC sebelumnya:", soc)

        # Menghitung SOC
        soc -= energy_consumed

        # Jika SOC kurang dari nol maka gagal dan mengeluarkan inf
        # print("SOC sekarang:", soc)
        if soc < 0:

            # Penalti kalau soc kurang dari 0
            t_total += abs(soc) * 10000
            # print("SOC < 0")

        soc = max(0, soc)
        
        t_total += duration

    return t_total