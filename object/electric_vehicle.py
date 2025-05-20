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
            self.status = "charging"

            # Cari rute sambil ngecas
            # SOKIN
            # 1. EV meninggalkan titik asal (origin)
            # 2. Ada perubahan pada Occupancy Indicator (OI) di salah satu CS
            # 3. EV tiba di Charging Station (CS)
            # 4. EV selesai menunggu dan CS menjadi tersedia
            # 5. EV selesai charging (mencapai target battery level)

            # Cek dulu full atau ngga (Kalau charging rate full, ambil yang paling tinggi)
            if (from_node in charging_at):
                charging_duration = charging_at[from_node]['charging_time']
                charging_rate = charging_at[from_node]['charging_rate']
            else:
                charging_duration = 20
                charging_rate = 999
            yield from charging_stations[from_node].charge(self, charging_duration, charging_rate)

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