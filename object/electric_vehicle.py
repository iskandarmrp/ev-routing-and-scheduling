from algorithm.utils import calculate_energy_model
import requests
import polyline

class ElectricVehicle:
    def __init__(self, type, max_speed_kmh, battery_capacity, battery_now, charging_rate, current_lat, current_lon):
        self.type = type
        self.max_speed = max_speed_kmh
        self.capacity = battery_capacity 
        self.battery_now = battery_now
        self.charging_rate = charging_rate
        self.current_lat = current_lat
        self.current_lon = current_lon
        self.status = "idle"

    def drive(self, env, G, charging_at, charging_stations, from_node, to_node, status_data):
        distance_km = G.edges[from_node, to_node].get("distance", 1)

        if (G.nodes[from_node].get("is_charging_station") and ((from_node in charging_at) or (self.battery_now < 0.2 * self.capacity))):

            if (from_node in charging_at):
                charging_duration = charging_at[from_node]['charging_time']
                charging_rate = charging_at[from_node]['charging_rate']
                rate_str = str(charging_rate) + " kW"
                
                time = 0
                while True:
                    indicator_val = charging_stations[from_node].slots_indicators.get(rate_str, {}).get("indicator", 1.0)
                    if indicator_val < 1.0:
                        print(f"Slot {rate_str} tersedia. Melanjutkan charging.")
                        break

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
                        if charging_stations[from_node].slots_indicators[rate_str].get("indicator", 1.0) < 1.0:
                            charging_rate = rate
                            charging_duration = 60 * (charging_at[from_node]['soc_target'] - charging_at[from_node]['soc_start']) / charging_rate
                            print(f"Mengganti ke slot rate {charging_rate} kW karena rate awal penuh.")
                            found = True
                            break

                    if found:
                        break

                    print(f"Semua slot penuh di {from_node}, menunggu 10 detik simulasi...")

                    yield env.timeout(1)

                    self.status = "waiting_for_charge"

                    if time % 10 == 0:
                        pass

                    time += 1
            else:
                charging_duration = 40

                station = charging_stations.get(from_node)
                if station:
                    eligible_rates = [r for r in station.slots_charging_rate if r <= self.charging_rate]
                else:
                    eligible_rates = []

                if eligible_rates:
                    charging_rate = max(eligible_rates)
                else:
                    charging_rate = None

                rate_str = str(charging_rate) + " kW"

                time = 0
                while True:
                    indicator_val = charging_stations[from_node].slots_indicators.get(rate_str, {}).get("indicator", 1.0)
                    if indicator_val < 1.0:
                        print(f"Slot {rate_str} tersedia. Melanjutkan charging.")
                        break

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
                        if charging_stations[from_node].slots_indicators[rate_str].get("indicator", 1.0) < 1.0:
                            charging_rate = rate
                            print(f"Mengganti ke slot rate {charging_rate} kW karena rate awal penuh.")
                            found = True
                            break

                    if found:
                        break

                    print(f"Semua slot penuh di {from_node}, menunggu 10 detik simulasi...")

                    yield env.timeout(1)

                    self.status = "waiting_for_charge"

                    if time % 10 == 0:
                        pass

                    time += 1

            if charging_duration and charging_rate:
                self.status = "charging"

                rate_str = str(charging_rate) + " kW"
                station = charging_stations[from_node]

                s = station.slots_parameter[rate_str]["s"]
                indicator = station.slots_indicators.get(rate_str, {}).get("indicator", 1.0)

                occupied = round(indicator * s)
                occupied += 1

                station.slots_indicators[rate_str]["indicator"] = round(occupied / s, 2)
                station.slots_indicators[rate_str]["time_after_indicator_change"] = 0

                print("Indikator slot sekarang", station.slots_indicators[rate_str]["indicator"])

                status_data["charging_at_node"] = G.nodes[from_node]['name']
                status_data["current_position"] = [G.nodes[from_node]['latitude'], G.nodes[from_node]['longitude']]

                yield from charging_stations[from_node].charge(self, charging_duration, charging_rate)

        print(f"[{env.now:.2f}m] {self.type} mulai dari {from_node} ke {to_node} (jarak: {distance_km} km)")

        self.status = "traveling"

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
                route_data = data["routes"][0]
                distance_km = round(route_data["distance"] / 1000, 2)
                duration_min = round(route_data["duration"] / 60, 2)
                polyline_str = route_data["geometry"]
                decoded_polyline = polyline.decode(polyline_str) 

                print(f"✅ {from_node} → {to_node}: {distance_km} km, {duration_min} min")
            else:
                print(f"❌ {from_node} → {to_node} gagal: {data['code']}")
        except Exception as e:
            print(f"⚠️ Error saat memproses {from_node} → {to_node}: {e}")

        duration = G.edges[from_node, to_node].get("weight", 1) 
        duration_in_hour = duration / 60 
        speed = distance_km / duration_in_hour
        
        if speed > self.max_speed:
            speed = self.max_speed

        travel_time = (distance_km / speed) * 60

        status_data["current_from_node"] = G.nodes[from_node]['name']
        status_data["current_to_node"] = G.nodes[to_node]['name']
        status_data["charging_at_node"] = None

        path_length = len(decoded_polyline)
        idx_now = 0

        while idx_now < path_length - 1:
            duration = duration
            duration_in_hour = duration / 60
            speed = distance_km / duration_in_hour

            if speed > self.max_speed:
                speed = self.max_speed

            travel_time = (distance_km / speed) * 60

            energy_per_minute = calculate_energy_model(distance_km, speed, self.type) / duration
            
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