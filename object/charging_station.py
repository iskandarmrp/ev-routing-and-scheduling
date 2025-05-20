import numpy as np

global charging_stations
global charging_at

class ChargingSlot:
    def __init__(self, charging_rate):
        self.charging_rate = charging_rate # kWh/h
        self.available = True

class ChargingStation:
    def __init__(self, env, node_id, name, latitude, longitude, total_slots, slots_charging_rate, slots_indicators, slots_parameter):
        self.env = env
        self.node_id = node_id # Node ID
        self.name = name
        self.latitude = latitude
        self.longitude = longitude
        self.total_slots = total_slots # Jumlah Slot
        self.slots_charging_rate = slots_charging_rate # Array dengan isi charging rate setiap slot
        self.slots_indicators = slots_indicators
        self.slots_parameter = slots_parameter
    
    # Melakukan pengecasan
    def charge(self, ev, charging_time, charging_rate):
        # # Melakukan random slots availability
        # self.random_availability()

        # # Mencari slot yang tersedia
        # slot = self.find_available_slot(ev.charging_rate)
    
        # Kalau tidak menemukan slot makan skip charging
        # if slot is None:
        #     print(f"[{ev.env.now:.2f}m] {ev.type} TIDAK menemukan slot yang kompatibel di {self.node_id}, lanjut tanpa charging.")
        #     return  # langsung skip charging

        # slot.available = False

        # Hitung maksimum waktu yang dibutuhkan untuk full charge
        # energy_needed = ev.capacity - ev.battery_now
        # max_charging_duration = (energy_needed / slot.charging_rate) * 60  # menit

        # Ambil waktu charging yang lebih kecil: antara waktu yang diberikan atau sampai baterai penuh
        # actual_charging_time = min(charging_time, max_charging_duration)
        if charging_rate == 999:
            charging_rate = max(self.slots_charging_rate)

        print(f"[{self.env.now:.2f}m] {ev.type} ngecas di {self.node_id} "
              f"dengan slot {charging_rate:.2f} kWh/h selama {charging_time:.2f} menit")
        
        # yield self.env.timeout(actual_charging_time)

        # Tambahkan energi ke baterai
        # energy_added = (actual_charging_time / 60) * slot.charging_rate # dalam menit
        # ev.battery_now = min(ev.battery_now + energy_added, ev.capacity)
        energy_added = (charging_time / 60) * charging_rate # dalam menit
        ev.battery_now = min(ev.battery_now + energy_added, ev.capacity)

        yield self.env.timeout(charging_time)

        print(f"[{self.env.now:.2f}m] {ev.type} selesai ngecas, baterai: {ev.battery_now:.2f} kWh")