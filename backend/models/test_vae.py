"""
test_vae.py
---
Tests the trained VAE models by passing in both a perfectly valid sequence and
an artificially spoofed sequence, demonstrating the difference in anomaly scores.
"""

import sys
import os
import glob
import pandas as pd
import json

# Make sure the backend directory is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.trajectory_vae import calculate_reconstruction_error

DATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

def get_real_trajectory(ship_type: str, min_len: int = 15):
    """
    Finds the first real sequence for a given ship type directly from the CSV data.
    """
    pattern = os.path.join(DATA_ROOT, '*', ship_type, '**', '*.csv')
    files = glob.glob(pattern, recursive=True)
    if not files:
        print(f"Warning: No data found for {ship_type}")
        return []

    df = pd.read_csv(files[0])
    valid_seq = []
    current_track_id = None
    
    for _, row in df.iterrows():
        is_end = str(row.get('CRAFT_ID', '')).upper() == 'END' or str(row.get('Track_ID', '')).upper() == 'NA'
        if is_end:
            if valid_seq and len(valid_seq) >= min_len:
                return valid_seq
            valid_seq = []
            current_track_id = None
            continue
            
        track_id = row['Track_ID']
        if track_id != current_track_id:
            if valid_seq and len(valid_seq) >= min_len:
                return valid_seq
            valid_seq = []
            current_track_id = track_id
            
        # Keep as dictionary since calculate_reconstruction_error expects List[Dict]
        valid_seq.append(row.to_dict())
        
    return valid_seq

def create_spoofed_trajectory(valid_seq):
    """
    Takes a valid sequence and injects artificial anomalies to simulate spoofing.
    We'll make the ship jump coordinates, radically alter course, and exceed normal speed.
    """
    import copy
    import pandas as pd
    spoofed = copy.deepcopy(valid_seq)
    
    # Inject impossible physics starting at timestep 5
    for i in range(5, len(spoofed)):
        # Suddenly teleport 5 degrees of longitude (~300 miles)
        spoofed[i]['LON'] = float(spoofed[i]['LON']) + 5.0
        # Jump to a physically impossible speed for standard vessels
        spoofed[i]['SPEED'] = 35.0 
        # Radical zig-zag course
        if i % 2 == 0:
            spoofed[i]['COURSE'] = 0.0
        else:
            spoofed[i]['COURSE'] = 180.0
            
        # Simulate Dark Vessel activity (turned off AIS)
        # We add 10 hours to all timestamps from ping 5 onwards
        if 'TIMESTAMP' in spoofed[i]:
            old_time = pd.to_datetime(spoofed[i]['TIMESTAMP'])
            new_time = old_time + pd.Timedelta(hours=10)
            spoofed[i]['TIMESTAMP'] = str(new_time)
            
    return spoofed

def test_ship_type(ship_type: str):
    print(f"\n{'='*50}")
    print(f"Testing VAE Model: {ship_type.upper()}")
    print(f"{'='*50}")

    # 1. Real Data
    print("Loading a real sequence from CSV...")
    valid_seq = get_real_trajectory(ship_type)
    if not valid_seq:
        return
        
    print(f"Got valid sequence of length {len(valid_seq)}.")
    score_valid = calculate_reconstruction_error(valid_seq, ship_type=ship_type)
    
    print(f"\n[ VALID ] Score: {score_valid:.4f}  (Should be 0.0 or very low)")
    if score_valid == 0.0:
        print("    -> VAE successfully recognized this as completely normal movement.")

    # 2. Fake Data
    print("\n------------------------------")
    print("Generating impossible spoofed sequence...")
    spoofed_seq = create_spoofed_trajectory(valid_seq)
    
    score_spoofed = calculate_reconstruction_error(spoofed_seq, ship_type=ship_type)
    print(f"\n[ SPOOFED ] Score: {score_spoofed:.4f}  (Should be near 1.0)")
    if score_spoofed > 0.8:
        print("    -> VAE successfully detected the physical anomalies!")


def main():
    test_ship_type("cargo")
    test_ship_type("tanker")

if __name__ == '__main__':
    main()
