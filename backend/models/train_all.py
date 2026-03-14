"""
train_all.py — Train one VAE per ship type and save model weights.

Usage:
    python train_all.py
    python train_all.py --epochs 20 --batch-size 32 --lr 0.001

Ship types trained: cargo, fishing, passenger, tanker
Output: backend/models/vae_<ship_type>.pth for each type
"""

import argparse
import glob
import os
import sys

import torch

# Make sure the backend directory is on the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models.trajectory_vae import TrajectoryDataset, TransformerVAE, vae_loss
from torch.utils.data import DataLoader

SHIP_TYPES = ['cargo', 'fishing', 'passenger', 'tanker']

# Root of the data folder relative to this script
DATA_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'data')
MODELS_DIR = os.path.dirname(os.path.abspath(__file__))

# Auto-detect GPU
DEVICE = torch.device('cuda' if torch.cuda.is_available() else 'cpu')


def find_csvs_for_ship_type(ship_type: str):
    """Glob all monthly CSVs for a given ship type across all years."""
    pattern = os.path.join(DATA_ROOT, '*', ship_type, '**', '*.csv')
    files = glob.glob(pattern, recursive=True)
    if not files:
        print(f"  [WARNING] No CSV files found for ship type '{ship_type}' under {DATA_ROOT}")
    return files


def train_ship_type(ship_type: str, epochs: int, batch_size: int, lr: float):
    print(f"\n{'='*50}")
    print(f"Training VAE for ship type: {ship_type.upper()} on {DEVICE}")
    print(f"{'='*50}")

    csv_files = find_csvs_for_ship_type(ship_type)
    print(f"  Found {len(csv_files)} CSV file(s)")

    if not csv_files:
        print(f"  Skipping {ship_type} — no data found.")
        return

    dataset = TrajectoryDataset(csv_files)
    print(f"  Loaded {len(dataset)} trajectory sequences.")

    if len(dataset) == 0:
        print(f"  Skipping {ship_type} — dataset is empty after parsing.")
        return

    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=True, drop_last=True)
#   TODO GPU will never be supported because I still need to install the right package
    model = TransformerVAE(input_dim=5, seq_len=50, latent_dim=16, hidden_dim=64).to(DEVICE)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    model.train()
    for epoch in range(epochs):
        train_loss = 0.0
        for data in dataloader:
            data = data.to(DEVICE)
            optimizer.zero_grad()
            recon_batch, mu, logvar = model(data)
            loss = vae_loss(recon_batch, data, mu, logvar)
            loss.backward()
            train_loss += loss.item()
            optimizer.step()

        avg_loss = train_loss / len(dataset)
        print(f"  Epoch [{epoch+1:>3}/{epochs}]  Avg Loss: {avg_loss:.4f}")

    # Save model weights
    output_path = os.path.join(MODELS_DIR, f'vae_{ship_type}.pth')
    torch.save(model.state_dict(), output_path)
    print(f"  Saved model to: {output_path}")


def main():
    parser = argparse.ArgumentParser(description="Train one VAE per ship type.")
    parser.add_argument('--epochs',     type=int,   default=10,   help='Number of training epochs (default: 10)')
    parser.add_argument('--batch-size', type=int,   default=16,   help='Batch size (default: 16)')
    parser.add_argument('--lr',         type=float, default=1e-3, help='Learning rate (default: 0.001)')
    parser.add_argument('--ship-types', nargs='+',  default=SHIP_TYPES,
                        help=f"Ship types to train (default: all — {SHIP_TYPES})")
    args = parser.parse_args()

    print(f"Device: {DEVICE}" + (f" ({torch.cuda.get_device_name(0)}" + ")" if torch.cuda.is_available() else ""))
    print(f"Training config: epochs={args.epochs}, batch_size={args.batch_size}, lr={args.lr}")
    print(f"Ship types: {args.ship_types}")

    for ship_type in args.ship_types:
        train_ship_type(ship_type, args.epochs, args.batch_size, args.lr)

    print(f"\nAll done! Model files saved in: {MODELS_DIR}")


if __name__ == '__main__':
    main()
