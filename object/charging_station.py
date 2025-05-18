import numpy as np

global charging_stations
global charging_at

class ChargingSlot:
    def __init__(self, charging_rate):
        self.charging_rate = charging_rate # kWh/h
        self.available = True

class ChargingStation:
    def __init__(self, env, node_id, total_slots, slots_charging_rate, slots_availability_std, slots_availability_mean):
        self.env = env
        self.node_id = node_id # Node ID
        self.total_slots = total_slots # Jumlah Slot
        self.slots_charging_rate = slots_charging_rate # Array dengan isi charging rate setiap slot
        self.slots = [ChargingSlot(rate) for rate in slots_charging_rate] # Array dengan isi Charging Slot
        self.slots_availability_std = slots_availability_std # STD Ketersediaan Slot
        self.slots_availability_mean = slots_availability_mean # Mean Ketersediaan Slot

    # Menemukan slot yang tersedia (is_available == True dan Charging Rate <= EV Charging Rate), serta mengambil yang nilainya paling max
    def find_available_slot(self, ev_charging_rate):
        available_slots = [slot for slot in self.slots if slot.available and slot.charging_rate <= ev_charging_rate]
        return max(available_slots, key=lambda slot: slot.charging_rate) if available_slots else None
    
    # Melakukan random charging station availability untuk Charging Station ini
    def random_availability(self):
        # Ambil sample jumlah slot yang available berdasarkan distribusi normal
        available_count = int(round(np.random.normal(
            loc=self.slots_availability_mean,
            scale=self.slots_availability_std
        )))

        # Clamp nilai available_count supaya tetap dalam batas 0 - total_slots
        available_count = max(0, min(available_count, self.total_slots))

        # todo: Melakukan random tetapi dengan data distribusi slot yang sudah ada
        # Randomize indeks slot yang akan available
        available_indices = np.random.choice(range(self.total_slots), available_count, replace=False)

        # Memasukkan availability
        for idx, slot in enumerate(self.slots):
            slot.available = (idx in available_indices)

        print(f"[Random Availability] Station {self.node_id}: "
              f"{available_count}/{self.total_slots} slot available")
    
    # Melakukan pengecasan
    def charge(self, ev, charging_time):
        # Melakukan random slots availability
        self.random_availability()

        # Mencari slot yang tersedia
        slot = self.find_available_slot(ev.charging_rate)
    
        # Kalau tidak menemukan slot makan skip charging
        if slot is None:
            print(f"[{ev.env.now:.2f}m] {ev.type} TIDAK menemukan slot yang kompatibel di {self.node_id}, lanjut tanpa charging.")
            return  # langsung skip charging

        slot.available = False

        # Hitung maksimum waktu yang dibutuhkan untuk full charge
        energy_needed = ev.capacity - ev.battery_now
        max_charging_duration = (energy_needed / slot.charging_rate) * 60  # menit

        # Ambil waktu charging yang lebih kecil: antara waktu yang diberikan atau sampai baterai penuh
        actual_charging_time = min(charging_time, max_charging_duration)

        print(f"[{ev.env.now:.2f}m] {ev.type} ngecas di {self.node_id} "
              f"dengan slot {slot.charging_rate:.2f} kWh/h selama {charging_time:.2f} menit")
        
        yield self.env.timeout(actual_charging_time)

        # Tambahkan energi ke baterai
        energy_added = (actual_charging_time / 60) * slot.charging_rate # dalam menit
        ev.battery_now = min(ev.battery_now + energy_added, ev.capacity)

        slot.available = True
        print(f"[{ev.env.now:.2f}m] {ev.type} selesai ngecas, baterai: {ev.battery_now:.2f} kWh")