from algorithm.utils import calculate_energy_model

class ElectricVehicle:
    def __init__(self, type, max_speed_kmh, battery_capacity, battery_now, charging_rate, current_lat, current_lon):
        self.type = type
        self.max_speed = max_speed_kmh  # Kecepatan Maksimal (km/jam)
        self.capacity = battery_capacity  # Kapasitas Baterai (total kWh)
        self.battery_now = battery_now  # Baterai Sekarang (kWh)
        self.charging_rate = charging_rate  # Kecepatan Ngecas (kWh per menit)
        self.current_lat = current_lat # Latitude Sekarang
        self.current_lon = current_lon # Longitude Sekarang

    def drive(self, env, G, charging_at, charging_stations, from_node, to_node, distance_km, duration, duration_in_hour, speed):
        # Cek apakah kecepatannya tidak melebihi kecepatan maksimal pengendara
        if speed > self.max_speed:
            speed = self.max_speed

        energy_consumed = calculate_energy_model(distance_km, speed, self.type)

        # Menghitung waktu
        travel_time = (distance_km / speed) * 60  # Waktu Travel (Ubah ke dalam menit)

        # Melakukan cas jika terdapat di schedule
        if (G.nodes[from_node].get("is_charging_station") and ((from_node in charging_at) or (self.battery_now < 0.2 * self.capacity))):
            if (from_node in charging_at):
                charging_duration = charging_at[from_node]['charging_time']
                charging_rate = charging_at[from_node]['charging_rate']
            else:
                charging_duration = 20
                charging_rate = 999
            yield from charging_stations[from_node].charge(self, charging_duration, charging_rate)

        print(f"[{env.now:.2f}m] {self.type} mulai dari {from_node} ke {to_node} (jarak: {distance_km} km)")
        yield env.timeout(travel_time)
        self.battery_now -= energy_consumed
        print(f"[{env.now:.2f}m] {self.type} sampai di {to_node}, baterai: {self.battery_now:.2f} kWh")