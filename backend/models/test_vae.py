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

DATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')

from trajectory_vae import calculate_reconstruction_error

def run_hackathon_demo():
    print("="*60)
    print("🚀 RUNNING HACKATHON DEMO ON REALISTIC DATASET")
    print("="*60)
    
    test_data_path = os.path.join(DATA_ROOT, 'test', 'hackathon_test_data.csv')
    if not os.path.exists(test_data_path):
        print(f"Error: {test_data_path} not found. Run generate_hackathon_data.py first.")
        return
        
    df = pd.read_csv(test_data_path)
    sequences = []
    current_seq = []
    current_track_id = None
    
    # 1. Parse CSV into distinct sequences
    for _, row in df.iterrows():
        is_end = str(row.get('CRAFT_ID', '')).upper() == 'END' or str(row.get('Track_ID', '')).upper() == 'NA'
        if is_end:
            if current_seq and len(current_seq) >= 10:
                sequences.append(current_seq)
            current_seq = []
            current_track_id = None
            continue
            
        track_id = row['Track_ID']
        if track_id != current_track_id:
            if current_seq and len(current_seq) >= 10:
                sequences.append(current_seq)
            current_seq = []
            current_track_id = track_id
            
        current_seq.append(row.to_dict())
        
    print(f"Parsed {len(sequences)} distinct ship sequences from test dataset.\n")
    
    true_positives = 0
    false_positives = 0
    false_negatives = 0
    true_negatives = 0
    total_anomalous = 0
    total_legit = 0
    
    # 2. Run analysis on each sequence
    for seq in sequences:
        ship_type = seq[0]['TYPE'].lower()
        
        # Skip fishing and passenger ships for now
        if ship_type in ['fishing', 'passenger']:
            continue
            
        track_id = seq[0]['Track_ID']
        mmsi = seq[0]['MMSI']
        
        # We know if it's anomalous based on how we generated the Track_ID
        is_actually_anomalous = "ANOM" in track_id
        if is_actually_anomalous:
            total_anomalous += 1
        else:
            total_legit += 1
            
        # Run specific VAE for this specific ship type
        score = calculate_reconstruction_error(seq, ship_type=ship_type)
        
        # Our threshold for raising an alarm
        alarm_raised = score > 0.05
        
        # Logging
        status = "🚨 ALERT " if alarm_raised else "✅ NORMAL"
        truth = "[FRAUD]" if is_actually_anomalous else "[LEGIT]"
        print(f"{status} | MMSI: {mmsi} | Type: {ship_type.upper():<9} | Score: {score:.4f} | Truth: {truth}")
        
        # Metrics
        if alarm_raised and is_actually_anomalous:
            true_positives += 1
        elif alarm_raised and not is_actually_anomalous:
            false_positives += 1
        elif not alarm_raised and is_actually_anomalous:
            false_negatives += 1
        elif not alarm_raised and not is_actually_anomalous:
            true_negatives += 1
            
    print("\n" + "="*60)
    print("📊 DETECTION SUMMARY")
    print("="*60)
    print(f"Correctly flagged   (True Positives)  : {true_positives} / {total_anomalous}")
    print(f"Correctly cleared   (True Negatives)  : {true_negatives} / {total_legit}")
    print(f"False Alarms        (False Positives) : {false_positives}")
    print(f"Missed Spoofing     (False Negatives) : {false_negatives}")
    
    total_analyzed = total_anomalous + total_legit
    accuracy = (true_positives + true_negatives) / total_analyzed * 100 if total_analyzed > 0 else 0
    print(f"\nOverall System Accuracy: {accuracy:.1f}%\n")


def main():
    run_hackathon_demo()

if __name__ == '__main__':
    main()
