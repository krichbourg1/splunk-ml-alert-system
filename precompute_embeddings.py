# precompute_embeddings.py
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer

# Load sensitive terms
print("Loading Suspect_Words.csv...")
sensitive_terms_df = pd.read_csv("Suspect_Words.csv")
print(f"Found {len(sensitive_terms_df)} sensitive terms")

# Load the SAME model used in app.py (all-MiniLM-L6-v2)
print("Loading sentence transformer model...")
embedding_model_path = "./models/all-MiniLM-L6-v2/snapshots/c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
embedding_model = SentenceTransformer(embedding_model_path)

def get_embedding(text):
    """
    Returns a mean-pooled embedding for the input text.
    Same function as in app.py (lines 66-70)
    """
    return embedding_model.encode([text])[0]

# Compute embeddings
print("Computing embeddings (this may take 10-30 seconds)...")
sensitive_embeddings = np.array([get_embedding(term) for term in sensitive_terms_df['term']])

# Save embeddings and terms together
np.save("sensitive_embeddings.npy", sensitive_embeddings)
sensitive_terms_df.to_csv("sensitive_terms_order.csv", index=False)

print(f"✅ Success! Saved embeddings for {len(sensitive_embeddings)} terms")
print(f"   - sensitive_embeddings.npy ({sensitive_embeddings.nbytes / 1024:.1f} KB)")
print(f"   - sensitive_terms_order.csv (backup)")
print("Ready to rebuild Docker image!")
