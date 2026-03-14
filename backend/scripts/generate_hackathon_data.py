import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import os
import random

def generate_timestamp(base_time, index, interval_minutes=5):
    t = base_time + timedelta(minutes=index * interval_minutes)
    return t.strftime("%Y-%m-%d %I:%M:%S %p")

def generate_sequence(track_id, mmsi, ship_type, is_anomalous=False, seq_len=50):
    rows = []
    # Randomize start hour so it's not the same every run
    start_hour = random.randint(0, 23)
    base_time = datetime(2026, 3, 14, start_hour, 0, 0)
    
    # Start coordinates Close to Strait of Hormuz
    lon = random.uniform(55.8, 56.5)
    lat = random.uniform(26.3, 27.0)
    
    # Profile-based movement
    if ship_type in ['cargo', 'tanker']:
        speed = random.uniform(8, 14)  # Slow and steady
        course = random.uniform(20, 70) # Straight line
    elif ship_type == 'passenger':
        speed = random.uniform(16, 24) # Fast ferries
        course = random.uniform(20, 70) # Straight line
    elif ship_type == 'fishing':
        speed = random.uniform(4, 12)  # Slow
        course = random.uniform(0, 360) # Wandering
    else:
        speed = random.uniform(8, 15)
        course = random.uniform(20, 70)
            
    # Randomize when the bad thing happens
    anomaly_point = random.randint(10, 40)
    anomaly_type = random.choice(['speed', 'jump', 'dark', 'zigzag']) if is_anomalous else 'none'
    
    for i in range(seq_len):
        current_time = base_time + timedelta(minutes=i * 5)
        
        # Physics update
        dt_hours = 5 / 60.0
        # rough dist ~ speed * dt (very simplified nautical miles to degrees)
        dist = speed * dt_hours
        lon += (dist / 60.0) * np.sin(np.radians(course))
        lat += (dist / 60.0) * np.cos(np.radians(course))
        
        # Add jitter
        if ship_type == 'fishing':
            # Fishing boats wander a lot while trawling
            course = (course + random.uniform(-15, 15)) % 360
            display_speed = speed + random.uniform(-2.0, 2.0)
            display_course = course
        else:
            # Commercial ships stay steady
            display_speed = speed + random.uniform(-0.1, 0.1)
            display_course = (course + random.uniform(-0.5, 0.5)) % 360
            
        # Inject Anomaly
        if is_anomalous and i == anomaly_point:
            if anomaly_type == 'speed':
                display_speed = 45.0 # Way too fast
            elif anomaly_type == 'jump':
                lon += 2.0 # Sudden 120 mile teleport
            elif anomaly_type == 'dark':
                base_time += timedelta(hours=random.randint(4, 12)) # Randomized gap
            elif anomaly_type == 'zigzag':
                display_course = (display_course + 180) % 360

        rows.append({
            'CRAFT_ID': f"SHIP_{mmsi}",
            'MMSI': mmsi,
            'TYPE': ship_type,
            'ANOMALY_TYPE': anomaly_type if is_anomalous else 'none', # For observation
            'TIMESTAMP': current_time.strftime("%Y-%m-%d %I:%M:%S %p"),
            'LON': lon,
            'LAT': lat,
            'COURSE': display_course,
            'SPEED': display_speed,
            'Track_ID': track_id
        })
        
    # Append END row
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
        
    total_sequences = 100
    anomalous_count = 20
    
    all_rows = []
    
    # Distribution of ship types in the strait
    types = ['cargo'] * 45 + ['tanker'] * 35 + ['fishing'] * 10 + ['passenger'] * 10
    
    # Generate 80 normal
    for i in range(total_sequences - anomalous_count):
        ship_type = random.choice(types)
        all_rows.extend(generate_sequence(f"TR_{i}", 1000000 + i, ship_type, is_anomalous=False))
        
    # Generate 20 anomalous
    for i in range(anomalous_count):
        idx = (total_sequences - anomalous_count) + i
        ship_type = random.choice(types)
        all_rows.extend(generate_sequence(f"TR_ANOM_{idx}", 2000000 + i, ship_type, is_anomalous=True))
        
    df = pd.DataFrame(all_rows)
    target_path = os.path.join(dest_dir, "hackathon_test_data.csv")
    df.to_csv(target_path, index=False)
    print(f"Generated {total_sequences} sequences (20% anomalous) to {target_path}")

if __name__ == "__main__":
    main()
