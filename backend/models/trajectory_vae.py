import torch
import torch.nn as nn
from typing import Dict, Any, List, Union
import os
import pandas as pd
from torch.utils.data import Dataset, DataLoader

class TrajectoryDataset(Dataset):
    def __init__(self, csv_files: Union[str, List[str]], max_seq_len=50):
        self.max_seq_len = max_seq_len
        if isinstance(csv_files, str):
            csv_files = [csv_files]
        dfs = []
        for f in csv_files:
            df = pd.read_csv(f)
            dfs.append(df)
        df = pd.concat(dfs, ignore_index=True)
        if 'TIMESTAMP' in df.columns:
            df = df[df['TIMESTAMP'] != 'NA']
            df['TIMESTAMP'] = pd.to_datetime(df['TIMESTAMP'], format="%Y-%m-%d %I:%M:%S %p")
        self.sequences = []
        current_seq = []
        current_track_id = None
        for _, row in df.iterrows():
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
        if current_seq:
            result = self._process_sequence(current_seq)
            if result is not None:
                self.sequences.append(result)
    def _process_sequence(self, seq_rows):
        df_seq = pd.DataFrame(seq_rows)
        if 'TIMESTAMP' in df_seq.columns:
            df_seq = df_seq.sort_values('TIMESTAMP')
        import numpy as np
        raw = df_seq[['LON', 'LAT', 'COURSE', 'SPEED']].astype(float)
        MAX_SPEED_KNOTS = 25.0
        if raw['SPEED'].max() > MAX_SPEED_KNOTS:
            return None
        MAX_DT_HOURS = 12.0
        if 'TIMESTAMP' in df_seq.columns:
            dt_seconds = df_seq['TIMESTAMP'].diff().dt.total_seconds().fillna(0.0)
            dt_hours = dt_seconds / 3600.0
        else:
            dt_hours = pd.Series(np.zeros(len(df_seq)))
        dt_hours = np.clip(dt_hours, 0.0, MAX_DT_HOURS)
        dt_adj = dt_hours.replace(0, 1.0)
        v_lon = raw['LON'].diff().fillna(0.0) / dt_adj
        v_lat = raw['LAT'].diff().fillna(0.0) / dt_adj
        course_rad = raw['COURSE'] * (3.141592653589793 / 180.0)
        v_mag = np.sqrt(v_lon.values**2 + v_lat.values**2)
        v_mag_knots = v_mag * 60.0
        speed_mismatch = (raw['SPEED'].values - v_mag_knots)
        true_bearing = np.degrees(np.arctan2(v_lon.values, v_lat.values)) % 360
        angle_diff = np.abs(raw['COURSE'].values - true_bearing)
        heading_conflict = np.minimum(angle_diff, 360 - angle_diff)
        features = np.stack([
            v_lon.values / 0.25,
            v_lat.values / 0.25,
            np.sin(course_rad.values),
            np.cos(course_rad.values),
            raw['SPEED'].values / MAX_SPEED_KNOTS,
            speed_mismatch / 10.0,
            heading_conflict / 180.0,
        ], axis=1)
        if len(features) > self.max_seq_len:
            features = features[:self.max_seq_len]
            return torch.tensor(features, dtype=torch.float32)
        else:
            padding = torch.zeros(self.max_seq_len - len(features), 7)
            features = torch.cat([torch.tensor(features, dtype=torch.float32), padding])
        return features
    def __len__(self):
        return len(self.sequences)
    def __getitem__(self, idx):
        return self.sequences[idx]

class TransformerVAE(nn.Module):
    def __init__(self, input_dim=7, latent_dim=16, seq_len=50, hidden_dim=64):
        super(TransformerVAE, self).__init__()
        self.latent_dim = latent_dim
        self.seq_len = seq_len
        self.input_dim = input_dim
        self.flat_dim = seq_len * input_dim
        self.encoder = nn.Sequential(
            nn.Linear(self.flat_dim, hidden_dim * 2),
            nn.ReLU(),
            nn.Linear(hidden_dim * 2, hidden_dim),
            nn.ReLU()
        )
        self.fc_mu = nn.Linear(hidden_dim, latent_dim)
        self.fc_logvar = nn.Linear(hidden_dim, latent_dim)
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
        x_flat = x.view(-1, self.flat_dim)
        h = self.encoder(x_flat)
        mu = self.fc_mu(h)
        logvar = self.fc_logvar(h)
        z = self.reparameterize(mu, logvar)
        recon_flat = self.decoder(z)
        recon_x = recon_flat.view(-1, self.seq_len, self.input_dim)
        return recon_x, mu, logvar

def vae_loss(recon_x, x, mu, logvar):
    MSE = nn.functional.mse_loss(recon_x, x, reduction='sum')
    KLD = -0.5 * torch.sum(1 + logvar - mu.pow(2) - logvar.exp())
    return MSE + KLD

def train_vae(csv_file: str, epochs: int = 10, batch_size: int = 16, learning_rate: float = 1e-3):
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
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    max_seq_len = 50
    df_seq = pd.DataFrame(trajectory)
    if len(df_seq) == 0:
        return 0.0
    import numpy as np
    MAX_SPEED_KNOTS = 25.0
    MAX_DT_HOURS = 12.0
    if 'TIMESTAMP' in df_seq.columns:
        df_seq = df_seq[df_seq['TIMESTAMP'] != 'NA']
        df_seq['TIMESTAMP'] = pd.to_datetime(df_seq['TIMESTAMP'], format="%Y-%m-%d %I:%M:%S %p")
        df_seq = df_seq.sort_values('TIMESTAMP')
        dt_seconds = df_seq['TIMESTAMP'].diff().dt.total_seconds().fillna(0.0)
        dt_hours = dt_seconds / 3600.0
    else:
        dt_hours = pd.Series(np.zeros(len(df_seq)))
    dt_hours = np.clip(dt_hours, 0.0, MAX_DT_HOURS)
    raw = df_seq[['LON', 'LAT', 'COURSE', 'SPEED']].astype(float)
    dt_adj = dt_hours.replace(0, 1.0)
    v_lon = raw['LON'].diff().fillna(0.0) / dt_adj
    v_lat = raw['LAT'].diff().fillna(0.0) / dt_adj
    course_rad = raw['COURSE'] * (3.141592653589793 / 180.0)
    v_mag = np.sqrt(v_lon.values**2 + v_lat.values**2)
    v_mag_knots = v_mag * 60.0
    speed_mismatch = (raw['SPEED'].values - v_mag_knots)
    true_bearing = np.degrees(np.arctan2(v_lon.values, v_lat.values)) % 360
    angle_diff = np.abs(raw['COURSE'].values - true_bearing)
    heading_conflict = np.minimum(angle_diff, 360 - angle_diff)
    if (raw['SPEED'] > 3.0).any() and (heading_conflict > 100).any():
        return 1.0
    features = np.stack([
        v_lon.values / 0.25,
        v_lat.values / 0.25,
        np.sin(course_rad.values),
        np.cos(course_rad.values),
        raw['SPEED'].values / MAX_SPEED_KNOTS,
        speed_mismatch / 10.0,
        heading_conflict / 180.0,
    ], axis=1)
    if len(features) > max_seq_len:
        features = torch.tensor(features[:max_seq_len], dtype=torch.float32)
    else:
        padding = torch.zeros(max_seq_len - len(features), 7)
        features = torch.cat([torch.tensor(features, dtype=torch.float32), padding])
    features_tensor = features.unsqueeze(0).to(torch.float32).to(device)
    models_dir = os.path.dirname(os.path.abspath(__file__))
    model_path = os.path.join(models_dir, f'vae_{ship_type}.pth')
    model = TransformerVAE(input_dim=7, seq_len=max_seq_len).to(device)
    try:
        model.load_state_dict(torch.load(model_path, weights_only=True, map_location=device))
        model.eval()
    except FileNotFoundError:
        print(f"Warning: {model_path} not found. Train the model first with train_all.py.")
    with torch.no_grad():
        recon_batch, _, _ = model(features_tensor)
        actual_len = min(len(df_seq), max_seq_len)
        if actual_len > 2:
            diff_sq = (recon_batch[0, 2:actual_len, :] - features_tensor[0, 2:actual_len, :])**2
            weights = torch.tensor([1.0, 1.0, 1.0, 1.0, 1.0, 5.0, 5.0], device=device)
            weighted_diff = diff_sq * weights
            per_ping_mse = torch.mean(weighted_diff, dim=1)
            mse_error = torch.max(per_ping_mse).item()
        else:
            mse_error = 0.0
    baseline_mse = 1.0
    max_mse = 8.0
    spoofing_alert_score = (mse_error - baseline_mse) / (max_mse - baseline_mse)
    return max(0.0, min(spoofing_alert_score, 1.0))