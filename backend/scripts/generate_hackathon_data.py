import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import random

def generate_timestamp(base_time, index, interval_minutes=5):
    t = base_time + timedelta(minutes=index * interval_minutes)
    return t.strftime("%Y-%m-%d %I:%M:%S %p")

def generate_sequence(track_id, mmsi, ship_type, is_anomalous=False, seq_len=50, anomaly_type=None):
    rows = []
    # All tracks start at 2026-03-15 00:00:00 and end at 2026-03-15 23:59:00
    start_time = datetime(2026, 3, 15, 0, 0, 0)
    end_time = datetime(2026, 3, 15, 23, 59, 0)
    time_range = [(start_time + (end_time - start_time) * i / (seq_len - 1)) for i in range(seq_len)]

    lon = random.uniform(55.8, 56.5)
    lat = random.uniform(26.3, 27.0)

    if ship_type in ['cargo', 'tanker']:
        speed = random.uniform(8, 14)
        course = random.uniform(20, 70)
    elif ship_type == 'passenger':
        speed = random.uniform(16, 24)
        course = random.uniform(20, 70)
    elif ship_type == 'fishing':
        speed = random.uniform(4, 12)
        course = random.uniform(0, 360)
    else:
        speed = random.uniform(8, 15)
        course = random.uniform(20, 70)

    if is_anomalous and anomaly_type is None:
        anomaly_type = random.choice(['speed', 'jump', 'dark', 'zigzag'])
    elif not is_anomalous:
        anomaly_type = 'none'

    anomaly_point = random.randint(10, 40) if is_anomalous else -1

    for i in range(seq_len):
        current_time = time_range[i]

        dt_hours = (24 * 60 - 1) / (seq_len - 1) / 60.0  # total minutes / (seq_len-1) / 60
        dist = speed * dt_hours
        lon += (dist / 60.0) * np.sin(np.radians(course))
        lat += (dist / 60.0) * np.cos(np.radians(course))

        if ship_type == 'fishing':
            course = (course + random.uniform(-15, 15)) % 360
            display_speed = speed + random.uniform(-2.0, 2.0)
            display_course = course
        else:
            if random.random() < 0.05:
                course = (course + random.uniform(-25, 25)) % 360

            display_speed = speed + random.uniform(-0.1, 0.1)
            display_course = (course + random.uniform(-0.5, 0.5)) % 360

        if is_anomalous and i == anomaly_point:
            if anomaly_type == 'speed':
                display_speed = 45.0
            elif anomaly_type == 'jump':
                lon += 2.0
            elif anomaly_type == 'dark':
                # For 'dark', skip a chunk of time by making a gap in timestamps
                # We'll simulate by skipping the next 5 points
                for skip in range(5):
                    if i + skip < seq_len:
                        time_range[i + skip] = time_range[i] + timedelta(hours=skip + 1)
            elif anomaly_type == 'zigzag':
                display_course = (display_course + 180) % 360

        rows.append({
            'CRAFT_ID': f"SHIP_{mmsi}",
            'MMSI': mmsi,
            'TYPE': ship_type,
            'ANOMALY_TYPE': anomaly_type if is_anomalous else 'none',
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

    all_rows = []
    normal_types = ['cargo', 'tanker', 'cargo', 'tanker', 'cargo', 'tanker']
    for i, ship_type in enumerate(normal_types):
        all_rows.extend(generate_sequence(f"TR_{i}", 1000000 + i, ship_type, is_anomalous=False))

    # One of each anomaly type
    anomaly_types = ['speed', 'jump', 'dark', 'zigzag']
    for i, anomaly_type in enumerate(anomaly_types):
        # Use cargo for all anomaly types for simplicity
        all_rows.extend(generate_sequence(f"TR_ANOM_{i}", 2000000 + i, 'cargo', is_anomalous=True, anomaly_type=anomaly_type))

    df = pd.DataFrame(all_rows)
    target_path = os.path.join(dest_dir, "hackathon_test_data.csv")
    df.to_csv(target_path, index=False)
    print(f"Generated 6 normal and 4 anomalous sequences to {target_path}")

if __name__ == "__main__":
    main()
