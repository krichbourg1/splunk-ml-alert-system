# precompute_embeddings.py
import numpy as np
import pandas as pd
from transformers import AutoTokenizer, AutoModel
import torch

# Load sensitive terms
sensitive_terms_df = pd.read_csv("Suspect_Words.csv")

# Load model for embeddings
embedding_model_name = "distilbert-base-uncased"
tokenizer = AutoTokenizer.from_pretrained(embedding_model_name)
model = AutoModel.from_pretrained(embedding_model_name)

def get_embedding(text):
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True)
    with torch.no_grad():
        outputs = model(**inputs)
    return outputs.last_hidden_state.mean(dim=1).numpy()[0]

# Compute embeddings
sensitive_embeddings = np.array([get_embedding(term) for term in sensitive_terms_df['term']])

# Save embeddings and terms together
np.save("sensitive_embeddings.npy", sensitive_embeddings)
sensitive_terms_df.to_csv("sensitive_terms_order.csv", index=False)
print("Saved embeddings for sensitive terms!")
