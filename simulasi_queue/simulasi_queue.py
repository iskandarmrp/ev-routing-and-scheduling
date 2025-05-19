import pandas as pd
import numpy as np
import heapq

# Fungsi modifikasi untuk simulasi seperti di atas, tapi dengan initial_q yang bisa dipilih (0 atau 1)
def simulate_queue_event_based_with_q(
    arrival_rate, service_rate, servers, capacity, p, charging_rate_label,
    sim_time_minutes=2880, initial_q=0
):
    arrival_rate_in_minute = 60 / arrival_rate
    service_rate_in_minute = 60 / service_rate
    current_time = 0
    ev_id = 0
    indicator_history = []
    prev_indicator_time = 0.0
    events = []
    ev_records = []
    server_release_times = []
    time_now = 0

    total_slots_occupied = int(initial_q * servers)

    for i in range(total_slots_occupied):
        initial_service_time = np.random.exponential(scale=service_rate_in_minute)
        release_time = current_time + initial_service_time
        heapq.heappush(events, (release_time, "departure", -i))
        server_release_times.append(release_time)

    heapq.heappush(events, (np.random.exponential(arrival_rate_in_minute), "arrival", ev_id))

    current_time, event_type, ev = heapq.heappop(events)
    print(initial_q, current_time)

    while time_now < sim_time_minutes:
        if time_now > sim_time_minutes:
            break

        if time_now % 6 == 0:
            server_release_times = [t for t in server_release_times if t > time_now]
            busy_servers = len(server_release_times)
            waiting_time = 0

            if busy_servers < servers:
                waiting_time = 0
            elif busy_servers >= servers and capacity > busy_servers:
                earliest_release = min(server_release_times)
                waiting_time = earliest_release - time_now
            else:
                waiting_time = server_release_times[1] - time_now

            ev_records.append({
                "initial_q": initial_q,
                "Charging Rate": charging_rate_label,
                "arrival_rate": arrival_rate,
                "service_rate": service_rate,
                "s": servers,
                "k": capacity,
                "p": p,
                "time": time_now,
                "waiting_time": waiting_time
            })
        
        if time_now > current_time:
            print(initial_q, "Oit")
            server_release_times = [t for t in server_release_times if t > current_time]
            busy_servers = len(server_release_times)
            charging_indicator = min(1.0, busy_servers / servers)
            time_after_indicator_change = current_time - prev_indicator_time

            if not indicator_history or charging_indicator != indicator_history[-1]["charging_indicator"]:
                indicator_history.append({
                    "time": current_time,
                    "charging_indicator": charging_indicator,
                    "time_after_indicator_change": time_after_indicator_change
                })
                prev_indicator_time = current_time

            if event_type == "arrival":
                wait_time = 0
                service_time = np.random.exponential(scale=service_rate_in_minute)
                if busy_servers < servers:
                    start_service = current_time
                    end_service = start_service + service_time
                    heapq.heappush(events, (end_service, "departure", ev_id))
                    server_release_times.append(end_service)
                elif busy_servers >= servers and capacity > busy_servers:
                    earliest_release = min(server_release_times)
                    start_service = earliest_release
                    wait_time = start_service - current_time
                    end_service = start_service + service_time
                    heapq.heappush(events, (end_service, "departure", ev_id))
                    server_release_times.append(end_service)
                else:
                    next_arrival = current_time + service_time
                    heapq.heappush(events, (next_arrival, "arrival", ev_id + 1))
                    ev_id += 1
                    time_now += 1
                    current_time, event_type, ev = heapq.heappop(events)
                    continue

                next_arrival = current_time + np.random.exponential(arrival_rate_in_minute)
                heapq.heappush(events, (next_arrival, "arrival", ev_id + 1))
                ev_id += 1
            elif event_type == "departure":
                indicator_history.append({
                    "time": current_time,
                    "charging_indicator": charging_indicator,
                    "time_after_indicator_change": time_after_indicator_change
                })
                prev_indicator_time = current_time

            current_time, event_type, ev = heapq.heappop(events)

        time_now += 1

    return pd.DataFrame(ev_records)


# Load parameter file
df = pd.read_csv("unique_charging_rate_parameters_cleaned.csv")

# Simulasi seluruh parameter untuk q = 0 dan q = 1

for i in range(5):
    all_records = []
    for idx, row in df.iterrows():
        indicators = [round(i, 2) for i in np.linspace(0, 1, int(row["s"]) + 1)]
        for q_init in indicators:
            result = simulate_queue_event_based_with_q(
                arrival_rate=row["arrival_rate"],
                service_rate=row["service_rate"],
                servers=int(row["s"]),
                capacity=int(row["k"]),
                p=row["p"],
                charging_rate_label=row["Charging Rate"],
                sim_time_minutes=2880,
                initial_q=q_init
            )
            result["param_id"] = idx
            result["count"] = i + 1
            all_records.append(result)
    # Gabungkan dan simpan ke CSV
    prev_df = pd.read_csv("all_event_based_with_initial_q.csv")
    last_df = pd.concat(all_records, ignore_index=True)

    for idx, row in last_df.iterrows():
        last_df.at[idx, 'waiting_time'] = prev_df.at[idx, 'waiting_time'] + last_df.at[idx, 'waiting_time']

    last_df.to_csv("all_event_based_with_initial_q.csv", index=False)