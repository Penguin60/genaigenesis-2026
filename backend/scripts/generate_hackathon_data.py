
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import random

# Simple bounding box for Gulf of Oman/Arabian Sea (water only)
def is_on_water(lat, lon):
    # Gulf of Oman/Arabian Sea region (approx)
    # Adjust as needed for your use case
    # lat: 23.5 to 27.5, lon: 55.5 to 61.0
    return 23.5 <= lat <= 27.5 and 55.5 <= lon <= 61.0


# Not used, but keep for reference
def generate_timestamp(base_time, index, interval_minutes=5):
    t = base_time + timedelta(minutes=index * interval_minutes)
    return t.strftime("%Y-%m-%d %I:%M:%S %p")



def generate_sequence(track_id, mmsi, ship_type, anomaly_type='none', seq_len=288):
    # 288 points for 5-min intervals in 24 hours
    rows = []
    base_time = datetime(2026, 3, 15, 0, 0, 0)
    # Ensure starting point is on water
    while True:
        lon = random.uniform(55.8, 56.5)
        lat = random.uniform(26.3, 27.0)
        if is_on_water(lat, lon):
            break
    if ship_type in ['cargo', 'tanker']:
        speed = random.uniform(8, 14)
        course = random.uniform(20, 70)
    else:
        speed = random.uniform(8, 15)
        course = random.uniform(20, 70)

    anomaly_point = random.randint(10, seq_len - 10)

    for i in range(seq_len):
        current_time = base_time + timedelta(minutes=i * 5)
        dt_hours = 5 / 60.0
        dist = speed * dt_hours
        lon += (dist / 60.0) * np.sin(np.radians(course))
        lat += (dist / 60.0) * np.cos(np.radians(course))

        # If point drifts onto land, nudge it back to water
        if not is_on_water(lat, lon):
            # Nudge back by reversing last step
            lon -= (dist / 60.0) * np.sin(np.radians(course))
            lat -= (dist / 60.0) * np.cos(np.radians(course))
            # Optionally, randomize course a bit to try to stay on water
            course = (course + random.uniform(-30, 30)) % 360

        if ship_type == 'cargo' or ship_type == 'tanker':
            if random.random() < 0.05:
                course = (course + random.uniform(-25, 25)) % 360
            display_speed = speed + random.uniform(-0.1, 0.1)
            display_course = (course + random.uniform(-0.5, 0.5)) % 360
        else:
            display_speed = speed
            display_course = course

        # Insert anomaly at the anomaly_point
        if anomaly_type != 'none' and i == anomaly_point:
            if anomaly_type == 'speed':
                display_speed = 45.0
            elif anomaly_type == 'jump':
                lon += 2.0
            elif anomaly_type == 'dark':
                current_time += timedelta(hours=8)
            elif anomaly_type == 'zigzag':
                display_course = (display_course + 180) % 360

        rows.append({
            'CRAFT_ID': f"SHIP_{mmsi}",
            'MMSI': mmsi,
            'TYPE': ship_type,
            'ANOMALY_TYPE': anomaly_type,
            'TIMESTAMP': current_time.strftime("%Y-%m-%d %I:%M:%S %p"),
            'LON': lon,
            'LAT': lat,
            'COURSE': display_course,
            'SPEED': display_speed,
            'Track_ID': track_id
        })

    rows.append({
        'CRAFT_ID': 'END',
        'MMSI': mmsi,
        'TYPE': ship_type,
        'ANOMALY_TYPE': 'none',
        'TIMESTAMP': 'NA',
        'LON': 'NA',
        'LAT': 'NA',
        'COURSE': 'NA',
        'SPEED': 'NA',
        'Track_ID': 'NA'
    })
    return rows


def main():
    dest_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data', 'test')
    if not os.path.exists(dest_dir):
        os.makedirs(dest_dir)

    total_sequences = 10
    all_rows = []
    types = ['cargo', 'tanker']


    # Hardcoded MMSI values for normal and anomaly ships
    normal_mmsis = [414485000, 352950000, 368087220, 338857000, 367163130, 367128220]
    anomaly_mmsis = [352004037, 636019777, 273213170, 616999005]
    # 6 normal
    for i, mmsi in enumerate(normal_mmsis):
        ship_type = random.choice(types)
        all_rows.extend(generate_sequence(f"TR_{i}", mmsi, ship_type, anomaly_type='none'))

    # 1 of each anomaly
    anomaly_types = ['speed', 'jump', 'dark', 'zigzag']
    for i, (anomaly, mmsi) in enumerate(zip(anomaly_types, anomaly_mmsis)):
        ship_type = random.choice(types)
        all_rows.extend(generate_sequence(f"TR_ANOM_{i}", mmsi, ship_type, anomaly_type=anomaly))

    df = pd.DataFrame(all_rows)
    target_path = os.path.join(dest_dir, "hackathon_test_data.csv")
    df.to_csv(target_path, index=False)
    print(f"Generated {total_sequences} sequences (6 normal, 1 each anomaly) to {target_path}")

if __name__ == "__main__":
    main()
