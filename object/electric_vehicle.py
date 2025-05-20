from algorithm.utils import calculate_energy_model
import requests
import polyline

class ElectricVehicle:
    def __init__(self, type, max_speed_kmh, battery_capacity, battery_now, charging_rate, current_lat, current_lon):
        self.type = type
        self.max_speed = max_speed_kmh  # Kecepatan Maksimal (km/jam)
        self.capacity = battery_capacity  # Kapasitas Baterai (total kWh)
        self.battery_now = battery_now  # Baterai Sekarang (kWh)
        self.charging_rate = charging_rate  # Kecepatan Ngecas (kWh per menit)
        self.current_lat = current_lat # Latitude Sekarang
        self.current_lon = current_lon # Longitude Sekarang
        self.status = "idle"  # idle, traveling, charging, waiting_for_charge

    def drive(self, env, G, charging_at, charging_stations, from_node, to_node):
        distance_km = G.edges[from_node, to_node].get("distance", 1)  # Sudah dalam bentuk km

        # Harusnya ngecas abis travel
        # SOKIN
        # Melakukan cas jika terdapat di schedule
        if (G.nodes[from_node].get("is_charging_station") and ((from_node in charging_at) or (self.battery_now < 0.2 * self.capacity))):
            # Cari rute sambil ngecas
            # SOKIN
            # 1. EV meninggalkan titik asal (origin)
            # 2. Ada perubahan pada Occupancy Indicator (OI) di salah satu CS
            # 3. EV tiba di Charging Station (CS)
            # 4. EV selesai menunggu dan CS menjadi tersedia
            # 5. EV selesai charging (mencapai target battery level)

            # Cek dulu full atau ngga (Kalau charging rate full, ambil yang paling tinggi)
            # charging_rate = max(self.slots_charging_rate)
            if (from_node in charging_at):
                charging_duration = charging_at[from_node]['charging_time']
                charging_rate = charging_at[from_node]['charging_rate']
                rate_str = str(charging_rate) + " kW"
                
                # Cek apakah full atau tidak
                time = 0
                while True:
                    indicator_val = charging_stations[from_node].slots_indicators.get(rate_str, 1.0)
                    if indicator_val < 1.0:
                        # Rate awal tersedia
                        print(f"Slot {rate_str} tersedia. Melanjutkan charging.")
                        break

                    # Coba cari rate alternatif dari yang tertinggi ke terendah
                    available_rates = sorted(
                        [
                            float(rate_key.replace(" kW", ""))
                            for rate_key in charging_stations[from_node].slots_indicators.keys()
                            if float(rate_key.replace(" kW", "")) <= self.charging_rate
                        ],
                        reverse=True
                    )

                    found = False
                    for rate in available_rates:
                        rate_str = str(rate) + " kW"
                        if charging_stations[from_node].slots_indicators[rate_str] < 1.0:
                            charging_rate = rate
                            charging_duration = 60 * (charging_at[from_node]['soc_target'] - charging_at[from_node]['soc_start']) / charging_rate
                            print(f"Mengganti ke slot rate {charging_rate} kW karena rate awal penuh.")
                            found = True
                            break

                    if found:
                        break  # Charging slot ditemukan

                    # Kalau tetap tidak ada, maka tunggu dan randomize ulang slot
                    print(f"Semua slot penuh di {from_node}, menunggu 10 detik simulasi...")

                    yield env.timeout(1)  # tunggu 1 detik simulasi

                    self.status = "waiting_for_charge"

                    if time % 10 == 0:
                        # SOKIN
                        # randomize_slots_indicator_for_all(G, charging_stations)
                        pass

                    time += 1
            else:
                charging_duration = 40

                # Ambil rate maksimal yang <= self.charging_rate
                eligible_rates = [r for r in self.slots_charging_rate if r <= self.charging_rate]

                if eligible_rates:
                    charging_rate = max(eligible_rates)
                else:
                    charging_rate = None  # atau fallback seperti min(self.slots_charging_rate)

                rate_str = str(charging_rate) + " kW"

                # Cek apakah full atau tidak
                time = 0
                while True:
                    indicator_val = charging_stations[from_node].slots_indicators.get(rate_str, 1.0)
                    if indicator_val < 1.0:
                        # Rate awal tersedia
                        print(f"Slot {rate_str} tersedia. Melanjutkan charging.")
                        break

                    # Coba cari rate alternatif dari yang tertinggi ke terendah
                    available_rates = sorted(
                        [
                            float(rate_key.replace(" kW", ""))
                            for rate_key in charging_stations[from_node].slots_indicators.keys()
                            if float(rate_key.replace(" kW", "")) <= self.charging_rate
                        ],
                        reverse=True
                    )

                    found = False
                    for rate in available_rates:
                        rate_str = str(rate) + " kW"
                        if charging_stations[from_node].slots_indicators[rate_str] < 1.0:
                            charging_rate = rate
                            print(f"Mengganti ke slot rate {charging_rate} kW karena rate awal penuh.")
                            found = True
                            break

                    if found:
                        break  # Charging slot ditemukan

                    # Kalau tetap tidak ada, maka tunggu dan randomize ulang slot
                    print(f"Semua slot penuh di {from_node}, menunggu 10 detik simulasi...")

                    yield env.timeout(1)  # tunggu 1 detik simulasi

                    self.status = "waiting_for_charge"

                    if time % 10 == 0:
                        # SOKIN
                        # randomize_slots_indicator_for_all(G, charging_stations)
                        pass

                    time += 1

            if charging_duration and charging_rate:
                self.status = "charging"

                # Mengubah indicator (karena masuk ngecas)
                rate_str = str(charging_rate) + " kW"
                station = charging_stations[from_node]

                s = station.slots_parameter[rate_str]["s"]
                indicator = station.slots_indicators.get(rate_str, 0.0)

                occupied = round(indicator * s)
                occupied += 1

                station.slots_indicators[rate_str] = round(occupied / s, 2)

                print("Indikator slot sekarang", station.slots_indicators[rate_str])

                # Masuk ke charging
                yield from charging_stations[from_node].charge(self, charging_duration, charging_rate)

                # Setelah mengecas cek rute lagi (Apakah ada node yang dirute yang indikatornya jadi 1)
                # Cek, kalau ada panggil algoritma lagi
                # SOKIN

        print(f"[{env.now:.2f}m] {self.type} mulai dari {from_node} ke {to_node} (jarak: {distance_km} km)")

        self.status = "traveling"

        # Ambil rute dari API OSRM
        OSRM_URL = "http://localhost:5000"
        lon1 = G.nodes[from_node]['longitude']
        lat1 = G.nodes[from_node]['latitude']
        lon2 = G.nodes[to_node]['longitude']
        lat2 = G.nodes[to_node]['latitude']

        try:
            url = f"{OSRM_URL}/route/v1/driving/{lon1},{lat1};{lon2},{lat2}?overview=full&geometries=polyline"
            response = requests.get(url)
            data = response.json()

            if data["code"] == "Ok":
                route = data["routes"][0]
                distance_km = round(route["distance"] / 1000, 2)
                duration_min = round(route["duration"] / 60, 2)
                polyline_str = route["geometry"]
                decoded_polyline = polyline.decode(polyline_str)  # list of (lat, lon)

                print(f"✅ {from_node} → {to_node}: {distance_km} km, {duration_min} min")
            else:
                print(f"❌ {from_node} → {to_node} gagal: {data['code']}")
        except Exception as e:
            print(f"⚠️ Error saat memproses {from_node} → {to_node}: {e}")

        # Ambil jarak antar node dari graph
        duration = G.edges[from_node, to_node].get("weight", 1)  # Durasi jalan dalam menit
        duration_in_hour = duration / 60 # Ubah durasi ke dalam jam untuk menghitung kecepatan
        speed = distance_km / duration_in_hour
        
        # Cek apakah kecepatannya tidak melebihi kecepatan maksimal pengendara
        if speed > self.max_speed:
            speed = self.max_speed

        # energy_consumed = calculate_energy_model(distance_km, speed, self.type)

        # Menghitung waktu
        travel_time = (distance_km / speed) * 60  # Waktu Travel (Ubah ke dalam menit)

        # Lihat jalur
        path_length = len(decoded_polyline)
        idx_now = 0

        while idx_now < path_length - 1:
            # Setiap beberapa detik update durasi
            # Tapi mungkin aja ini di fungsi lain buat updatenya (Masih blm tau)
            # SOKIN
            duration = duration
            duration_in_hour = duration / 60
            speed = distance_km / duration_in_hour

            if speed > self.max_speed:
                speed = self.max_speed

            travel_time = (distance_km / speed) * 60

            # Hitung konsumsi energi per menit (lalu dibagi 60 agar per detik)
            energy_per_minute = calculate_energy_model(distance_km, speed, self.type) / duration
            
            # Hitung progress posisi
            progress_per_minute = path_length / duration
            idx_now += progress_per_minute
            index_int = int(idx_now)

            if idx_now >= path_length - 1:
                last_minutes = 1 - ((idx_now - (path_length - 1)) / progress_per_minute)
                index_int = path_length - 1
                lat_now, lon_now = decoded_polyline[index_int]
                self.current_lat = lat2
                self.current_lon = lon2
                self.battery_now -= energy_per_minute * last_minutes
                print(f"[{env.now:.2f}m] Posisi {self.type}: ({self.current_lat:.5f}, {self.current_lon:.5f}) Baterai: {self.battery_now}")
                yield env.timeout(last_minutes)
            else:
                lat_now, lon_now = decoded_polyline[index_int]
                self.current_lat = lat_now
                self.current_lon = lon_now
                self.battery_now -= energy_per_minute
                print(f"[{env.now:.2f}m] Posisi {self.type}: ({self.current_lat:.5f}, {self.current_lon:.5f}) Baterai: {self.battery_now}")
                yield env.timeout(1)

            print(f"[{env.now:.2f}m] Posisi {self.type}: ({self.current_lat:.5f}, {self.current_lon:.5f}) Baterai: {self.battery_now}")

        print(f"[{env.now:.2f}m] {self.type} sampai di {to_node}, baterai: {self.battery_now:.2f} kWh")
        print("Node latitude, longitude:", lat2, lon2)
        print("EV latitude, longitude:", self.current_lat, self.current_lon)