#!/usr/bin/env python3
"""
Model download script for Docker container.
Downloads the sentence transformer model if not already present.
"""

import os
import sys
from sentence_transformers import SentenceTransformer

def download_model():
    """Download the sentence transformer model"""
    model_path = "./models/all-MiniLM-L6-v2"
    
    # Check if model already exists
    if os.path.exists(model_path) and os.path.exists(os.path.join(model_path, "config.json")):
        print(f"Model already exists at {model_path}")
        return True
    
    try:
        print("Downloading sentence transformer model...")
        # This will download the model to the specified path
        model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')
        model.save(model_path)
        print(f"Model downloaded successfully to {model_path}")
        return True
    except Exception as e:
        print(f"Error downloading model: {e}")
        return False

if __name__ == "__main__":
    success = download_model()
    sys.exit(0 if success else 1)
