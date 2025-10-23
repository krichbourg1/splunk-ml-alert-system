# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV TRANSFORMERS_CACHE=/app/models
ENV SENTENCE_TRANSFORMERS_HOME=/app/models

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory in container
WORKDIR /app

# Copy requirements first (for caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Copy model files first (they're large and change infrequently)
COPY models/ ./models/

# Copy data files
COPY *.csv ./
COPY *.npy ./

# Copy application code
COPY app.py ./
COPY download_model.py ./

# Download model if not present (fallback)
RUN python download_model.py || echo "Using existing model files"

# Create logs directory
RUN mkdir -p logs

# Expose port for Flask
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:5000/health || exit 1

# Command to run app
CMD ["python", "app.py"]
