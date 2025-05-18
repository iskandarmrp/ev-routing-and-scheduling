class ElectricVehicle:
    def __init__(self, type, max_speed_kmh, battery_capacity, battery_now, charging_rate, current_lat, current_lon):
        self.type = type
        self.max_speed = max_speed_kmh  # Kecepatan Maksimal (km/jam)
        self.capacity = battery_capacity  # Kapasitas Baterai (total kWh)
        self.battery_now = battery_now  # Baterai Sekarang (kWh)
        self.charging_rate = charging_rate  # Kecepatan Ngecas (kWh per menit)
        self.current_lat = current_lat # Latitude Sekarang
        self.current_lon = current_lon # Longitude Sekarang