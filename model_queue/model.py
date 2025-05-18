import pickle
import torch
import torch.nn as nn
import os

MODEL_PATH = os.path.join(os.path.dirname(__file__), "model_waiting_time.pkl")

class WaitingTimeNN(nn.Module):
    def __init__(self):
        super(WaitingTimeNN, self).__init__()
        self.model = nn.Sequential(
            nn.Linear(6, 128),
            nn.ReLU(),
            nn.Linear(128, 64),
            nn.ReLU(),
            nn.Linear(64, 1)  # no ReLU at output
        )
    def forward(self, x):
        return self.model(x)

# Load kembali model dan scaler
with open(MODEL_PATH, "rb") as f:
    loaded = pickle.load(f)

# Inisialisasi model dan load state dict
model_loaded = WaitingTimeNN()
model_loaded.load_state_dict(loaded["model_state_dict"])
model_loaded.eval()

# Ambil scaler
scaler_x_loaded = loaded["scaler_x"]
scaler_y_loaded = loaded["scaler_y"]