import torch
import torch.nn as nn
from typing import Dict, Any, List, Union
import os

import pandas as pd
from torch.utils.data import Dataset, DataLoader

class TrajectoryDataset(Dataset):
    """Dataset to parse Trajectories by Track_ID and END row terminators.
    Accepts a single CSV path or a list of CSV paths.
    """
    def __init__(self, csv_files: Union[str, List[str]], max_seq_len=50):
        self.max_seq_len = max_seq_len
        
        # Accept a single file or a list of files
        if isinstance(csv_files, str):
            csv_files = [csv_files]
        
        # Load and concatenate all CSVs
        dfs = []
        for f in csv_files:
            df = pd.read_csv(f)
            dfs.append(df)
        df = pd.concat(dfs, ignore_index=True)

        # Ensure timestamp is parsed if present
        if 'TIMESTAMP' in df.columns:
            df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'])
            
        self.sequences = []
        current_seq = []
        current_track_id = None
        
        for _, row in df.iterrows():
            # Check for END row
            if str(row.get('CRAFT_ID', '')).upper() == 'END' or str(row.get('Track_ID', '')).upper() == 'NA':
                if current_seq:
                    result = self._process_sequence(current_seq)
                    if result is not None:
                        self.sequences.append(result)
                    current_seq = []
                current_track_id = None
                continue
                
            track_id = row['Track_ID']
            if track_id != current_track_id:
                if current_seq:
                    result = self._process_sequence(current_seq)
                    if result is not None:
                        self.sequences.append(result)
                    current_seq = []
                current_track_id = track_id
                
            current_seq.append(row)
            
        # Catch the last sequence if it didn't have an END row
        if current_seq:
            result = self._process_sequence(current_seq)
            if result is not None:
                self.sequences.append(result)
            
    def _process_sequence(self, seq_rows):
        df_seq = pd.DataFrame(seq_rows)
        # Sort by timestamp
        if 'TIMESTAMP' in df_seq.columns:
            df_seq = df_seq.sort_values('TIMESTAMP')
        
        import numpy as np
        raw = df_seq[['LON', 'LAT', 'COURSE', 'SPEED']].astype(float)

        # --- Filter: discard sequences with any physically impossible speed ---
        MAX_SPEED_KNOTS = 25.0
        if raw['SPEED'].max() > MAX_SPEED_KNOTS:
            return None

        # Calculate Time Delta (dt) in hours
        MAX_DT_HOURS = 12.0
        if 'TIMESTAMP' in df_seq.columns:
            # Assumes pandas datetime format and handles missing rows safely
            dt_seconds = df_seq['TIMESTAMP'].diff().dt.total_seconds().fillna(0.0)
            dt_hours = dt_seconds / 3600.0
        else:
            # Fallback if no timestamp
            dt_hours = pd.Series(np.zeros(len(df_seq)))
            
        dt_hours = np.clip(dt_hours, 0.0, MAX_DT_HOURS)

        # Calculate Velocity Components (implied speed in degrees per hour)
        # We use fillna(0) to handle the first point in a sequence
        dt_adj = dt_hours.replace(0, 1.0) # Avoid division by zero
        v_lon = raw['LON'].diff().fillna(0.0) / dt_adj
        v_lat = raw['LAT'].diff().fillna(0.0) / dt_adj

        # Encode COURSE as sin/cos
        course_rad = raw['COURSE'] * (3.141592653589793 / 180.0)

        # --- Normalize all features ---
        # v_LON/v_LAT: Max expected change is ~0.25 deg/hour (at 15 knots) -> / 0.25
        # Derived Speed (Calculated from position)
        v_mag = np.sqrt(v_lon.values**2 + v_lat.values**2) # In degrees/hour
        v_mag_knots = v_mag * 60.0 # Rough conversion to knots
        
        # Mismatch Feature: (Reported Speed - Derived Speed)
        # This is the "Smoking Gun" for shadow vessels
        speed_mismatch = (raw['SPEED'].values - v_mag_knots)
        
        features = np.stack([
            v_lon.values / 0.25,
            v_lat.values / 0.25,
            np.sin(course_rad.values),
            np.cos(course_rad.values),
            raw['SPEED'].values / MAX_SPEED_KNOTS,
            speed_mismatch / 10.0, # Target feature for capture
        ], axis=1)  # shape: (seq_len, 6)
        
        # Pad or truncate to max_seq_len
        if len(features) > self.max_seq_len:
            features = features[:self.max_seq_len]
            return torch.tensor(features, dtype=torch.float32)
        else:
            padding = torch.zeros(self.max_seq_len - len(features), 6)
            features = torch.cat([torch.tensor(features, dtype=torch.float32), padding])
            
        return features

    def __len__(self):
        return len(self.sequences)

    def __getitem__(self, idx):
        return self.sequences[idx]

class TransformerVAE(nn.Module):
    """
    Stub for the Transformer-VAE (Variational Autoencoder) implemented in PyTorch.
    Trained on 'Normal' tanker routes to detect Movement Fraud.
    """
    def __init__(self, input_dim=6, latent_dim=16, seq_len=50, hidden_dim=64):
        super(TransformerVAE, self).__init__()
        self.latent_dim = latent_dim
        self.seq_len = seq_len
        self.input_dim = input_dim
        
        # Flattened input dimension
        self.flat_dim = seq_len * input_dim
        
        # Simple Linear Encoder
        self.encoder = nn.Sequential(
            nn.Linear(self.flat_dim, hidden_dim * 2),
            nn.ReLU(),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU()
        )
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)
        
        # Simple Linear Decoder
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, hidden_dim),
            nn.ReLU(),
            nn.Linear(hidden_dim, hidden_dim * 2),
            nn.ReLU(),
            nn.Linear(hidden_dim * 2, self.flat_dim)
        )

    def reparameterize(self, mu, logvar):
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        return mu + eps * std

    def forward(self, x):
        # Flatten the input sequence (batch_size, seq_len * input_dim)
        x_flat = x.view(-1, self.flat_dim)
        
        h = self.encoder(x_flat)
        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        
        z = self.reparameterize(mu, logvar)
        
        recon_flat = self.decoder(z)
        
        # Unflatten to basic shape (batch_size, seq_len, input_dim)
        recon_x = recon_flat.view(-1, self.seq_len, self.input_dim)
        
        return recon_x, mu, logvar

def vae_loss(recon_x, x, mu, logvar):
    """
    Calculates reconstruction loss (MSE) and Kullback-Leibler divergence.
    """
    # Reconstruction loss
    MSE = nn.functional.mse_loss(recon_x, x, reduction='sum')
    
    # KL Divergence
    # 0.5 * sum(1 + log(sigma^2) - mu^2 - sigma^2)
    KLD = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
    
    return MSE + KLD

def train_vae(csv_file: str, epochs: int = 10, batch_size: int = 16, learning_rate: float = 1e-3):
    """
    Trains the sequence VAE on trajectory CSV data.
    """
    print(f"Loading data from {csv_file}")
    dataset = TrajectoryDataset(csv_file)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True)
    
    model = TransformerVAE()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    
    model.train()
    print("Starting Training...")
    
    for epoch in range(epochs):
        train_loss = 0
        for batch_idx, data in enumerate(dataloader):
            optimizer.zero_grad()
            
            recon_batch, mu, logvar = model(data)
            loss = vae_loss(recon_batch, data, mu, logvar)
            
            loss.backward()
            train_loss += loss.item()
            optimizer.step()
            
        avg_loss = train_loss / len(dataloader.dataset)
        print(f"Epoch: {epoch+1}/{epochs} \t Average Loss: {avg_loss:.4f}")
        
    print("Training complete. Saving weights to transformer_vae.pth")
    torch.save(model.state_dict(), 'transformer_vae.pth')
    return model


def calculate_reconstruction_error(trajectory: List[Dict[str, float]], ship_type: str = 'tanker') -> float:
    """
    Evaluates movement (speed/heading). Spiking reconstruction error indicates spoofing.
    """
    # 1. Prepare the trajectory data into a Tensor matching the VAE input shape
    # We need a shape of (1, max_seq_len, 4) for (batch_size, seq_len, features)
    max_seq_len = 50
    df_seq = pd.DataFrame(trajectory)
    
    if len(df_seq) == 0:
        return 0.0
        
    import numpy as np
    MAX_SPEED_KNOTS = 25.0
    MAX_DT_HOURS = 12.0
    
    # Parse timestamps for dt feature
    if 'TIMESTAMP' in df_seq.columns:
        df_seq['TIMESTAMP'] = pd.to_datetime(df_seq['TIMESTAMP'])
        df_seq = df_seq.sort_values('TIMESTAMP')
        dt_seconds = df_seq['TIMESTAMP'].diff().dt.total_seconds().fillna(0.0)
        dt_hours = dt_seconds / 3600.0
    else:
        dt_hours = pd.Series(np.zeros(len(df_seq)))
        
    dt_hours = np.clip(dt_hours, 0.0, MAX_DT_HOURS)
    
    raw = df_seq[['LON', 'LAT', 'COURSE', 'SPEED']].astype(float)
    
    # Calculate Velocity Components (implied speed in degrees per hour)
    dt_adj = dt_hours.replace(0, 1.0)
    v_lon = raw['LON'].diff().fillna(0.0) / dt_adj
    v_lat = raw['LAT'].diff().fillna(0.0) / dt_adj
    
    course_rad = raw['COURSE'] * (3.141592653589793 / 180.0)
    # Derived values for conflict detection
    v_mag = np.sqrt(v_lon.values**2 + v_lat.values**2)
    v_mag_knots = v_mag * 60.0
    speed_mismatch = (raw['SPEED'].values - v_mag_knots)
    
    # Apply same normalization as training
    features = np.stack([
        v_lon.values / 0.25,
        v_lat.values / 0.25,
        np.sin(course_rad.values),
        np.cos(course_rad.values),
        raw['SPEED'].values / MAX_SPEED_KNOTS,
        speed_mismatch / 10.0, # Explicit Conflict feature
    ], axis=1)  # shape: (seq_len, 6)
    
    # Pad to max_seq_len
    if len(features) > max_seq_len:
        features = torch.tensor(features[:max_seq_len], dtype=torch.float32)
    else:
        padding = torch.zeros(max_seq_len - len(features), 6)
        features = torch.cat([torch.tensor(features, dtype=torch.float32), padding])
        
    # Add batch dimension
    features_tensor = features.unsqueeze(0).to(torch.float32)
    
    # 2. Load the pre-trained VAE model for the given ship type
    models_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(models_dir, f'vae_{ship_type}.pth')
    model = TransformerVAE(input_dim=6, seq_len=max_seq_len)
    try:
        model.load_state_dict(torch.load(model_path, weights_only=True))
        model.eval()
    except FileNotFoundError:
        print(f"Warning: {model_path} not found. Train the model first with train_all.py.")

    # 3. Calculate Reconstruction Error (MSE Loss between Input and Output)
    with torch.no_grad():
        recon_batch, _, _ = model(features_tensor)
        
        # We only want basic Mean Squared Error for the anomaly score
        # CRITICAL: We skip the first 2 frames so the "0 velocity start" doesn't ruin legitimate scores
        actual_len = min(len(df_seq), max_seq_len)
        if actual_len > 2:
            # Calculate MSE per timestep: (seq_len, feature_dim) -> (seq_len,)
            per_ping_mse = torch.mean((recon_batch[0, 2:actual_len, :] - features_tensor[0, 2:actual_len, :])**2, dim=1)
            # Use max to catch localized anomalies (like a single teleport jump)
            mse_error = torch.max(per_ping_mse).item()
        else:
            mse_error = 0.0

    # 4. Synthesize Spoofing Score
    # The MSE represents how anomalous the path is compared to normal routes.
    # Training loss settled at ~8.3 per batch (sum reduction), which equates 
    # to roughly ~0.033 MSE per element (mean reduction) on normalized data.
    
    # Updated for MAX MSE logic: 
    # Legit jitter can hit ~1.0, but a teleport jump hits 50.0+
    baseline_mse = 1.0  # Ignore anything that isn't a massive physical jump
    max_mse = 8.0      # Anything above this is 100% spoofed
    
    spoofing_alert_score = (mse_error - baseline_mse) / (max_mse - baseline_mse)
    return max(0.0, min(spoofing_alert_score, 1.0))