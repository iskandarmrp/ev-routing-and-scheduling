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
        print(f"[{self.env.now:.2f}m] {ev.type} ngecas di {self.node_id} "
              f"dengan slot {charging_rate:.2f} kWh/h selama {charging_time:.2f} menit")

        # Tambahkan energi ke baterai
        charging_time_now = 0

        while charging_time_now < charging_time:
            charging_time_now += 1

            if charging_time_now >= charging_time:
                last_time = charging_time_now - charging_time
                energy_added = ((1 - last_time) / 60) * charging_rate # dalam menit
                ev.battery_now = min(ev.battery_now + energy_added, ev.capacity)
                print(f"[{self.env.now:.2f}m] {ev.type} sedang ngecas, baterai: {ev.battery_now:.2f} kWh")
                yield self.env.timeout(1 - last_time)
            else:
                energy_added = (1 / 60) * charging_rate # dalam menit
                ev.battery_now = min(ev.battery_now + energy_added, ev.capacity)
                print(f"[{self.env.now:.2f}m] {ev.type} sedang ngecas, baterai: {ev.battery_now:.2f} kWh")
                yield self.env.timeout(1)

        print(f"[{self.env.now:.2f}m] {ev.type} selesai ngecas, baterai: {ev.battery_now:.2f} kWh")