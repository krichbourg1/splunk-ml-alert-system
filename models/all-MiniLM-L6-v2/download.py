from sentence_transformers import SentenceTransformer

# Specify cache folder to your local 'models' directory
model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2', cache_folder='./models/all-MiniLM-L6-v2')
