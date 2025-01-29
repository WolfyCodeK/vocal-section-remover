from demucs.pretrained import get_model
import torch

def download_models():
    print("Downloading Demucs models...")
    # Download the models by attempting to load them
    model = get_model('htdemucs')
    print("Models downloaded successfully!")

if __name__ == "__main__":
    download_models() 