# NLP Alert Analysis Service for Splunk

A Docker-based NLP service that automatically analyzes search queries and text from Splunk to detect sensitive terms using semantic similarity (sentence transformers).

## 🎯 Features

- **Semantic Similarity Detection**: Uses sentence transformers to detect sensitive terms with contextual understanding
- **Automated Splunk Integration**: Pulls data from Splunk every 15 minutes via REST API
- **Real-time Analysis**: Analyzes queries and sends enriched results back to Splunk via HEC
- **Multiple Similarity Algorithms**: Combines substring matching, word overlap, and semantic similarity
- **Flask API**: Provides REST endpoints for manual analysis and integration
- **Scheduled Background Jobs**: APScheduler runs automated pulls every 15 minutes
- **Custom Splunk Command**: Optional `| nlp_analyze` custom search command

## 📋 Prerequisites

- Docker & Docker Compose
- Splunk instance with:
  - REST API access (port 8089)
  - HTTP Event Collector (HEC) enabled (port 8088)
  - Saved search configured
  - Index for storing results

## 🚀 Quick Start

### 1. Clone the Repository

```bash
git clone <repository-url>
cd nlp_docker
```

### 2. Configure Splunk Connection

Edit `docker-compose.yml` and update the environment variables:

```yaml
environment:
  - SPLUNK_REST_URL=https://your-splunk-host:8089
  - SPLUNK_USERNAME=your-username
  - SPLUNK_PASSWORD=your-password
  - SPLUNK_SEARCH_NAME=your-saved-search-name
  - SPLUNK_HEC_URL=https://your-splunk-host:8088/services/collector
  - SPLUNK_HEC_TOKEN=your-hec-token
  - SPLUNK_INDEX=nlp_test
```

**Security Note**: For production, use `.env` file instead of hardcoding credentials.

### 3. Set Up Splunk

#### A. Create HEC Token
1. Go to **Settings → Data Inputs → HTTP Event Collector**
2. Enable **"All Tokens"** in Global Settings
3. Create **New Token** with name: `nlp_analysis_token`
4. Select or create target index: `nlp_test`
5. Copy the token

#### B. Create Index (if needed)
1. Go to **Settings → Indexes**
2. Create new index: `nlp_test`

#### C. Create Saved Search
1. Go to **Settings → Searches, reports, and alerts**
2. Create new search with SPL query:
   ```splunk
   index=main earliest=-24h
   | table _time, SearchQueryText, user, action
   ```
3. Save as **Report** with name: `nlp_docker_test`
4. Set permissions to **Shared in App**

### 4. Build and Run

```bash
# Build the Docker image
docker-compose build

# Start the service
docker-compose up -d

# Check logs
docker logs nlp-alert-service

# Verify health
curl http://localhost:5000/health
```

### 5. Verify in Splunk

Search for the analyzed results:
```splunk
index=nlp_test | head 10
```

## 📊 Architecture

```
┌─────────────┐         ┌──────────────────┐         ┌─────────────┐
│   Splunk    │  REST   │  Docker NLP      │   HEC   │   Splunk    │
│ (Saved      │ ──────> │  Service         │ ──────> │  (Results   │
│  Search)    │         │  - Embeddings    │         │   Index)    │
│             │         │  - Analysis      │         │             │
└─────────────┘         └──────────────────┘         └─────────────┘
      │                         │                           │
      │                    Port 5000                        │
      │                    Flask API                        │
      └─────────────────────────┴───────────────────────────┘
```

## 🔧 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Health check |
| `/analyze` | POST | Analyze single query |
| `/analyze_batch` | POST | Analyze multiple queries |
| `/analyze_detailed` | POST | Detailed analysis with all detected terms |
| `/process_splunk_search` | POST | Manually trigger Splunk pull |
| `/splunk_webhook` | POST | Webhook endpoint for Splunk alerts |
| `/scheduler_status` | GET | Check scheduler status |

### Example API Call

```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "social security number"}'
```

**Response:**
```json
{
  "query": "social security number",
  "most_similar_term": "Social Security Number",
  "similarity_score": 1.0,
  "all_detected_terms": [
    {"term": "Social Security Number", "score": 1.0},
    {"term": "social security #", "score": 0.95},
    {"term": "SSN#", "score": 0.85}
  ],
  "timestamp": "2025-10-15T10:00:00.000000"
}
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SPLUNK_REST_URL` | Splunk REST API URL | `https://splunk:8089` |
| `SPLUNK_USERNAME` | Splunk username | `admin` |
| `SPLUNK_PASSWORD` | Splunk password | `password123` |
| `SPLUNK_SEARCH_NAME` | Name of saved search | `nlp_docker_test` |
| `SPLUNK_HEC_URL` | Splunk HEC endpoint | `https://splunk:8088/services/collector` |
| `SPLUNK_HEC_TOKEN` | HEC authentication token | `xxxx-xxxx-xxxx-xxxx` |
| `SPLUNK_INDEX` | Target index for results | `nlp_test` |

### Customizing Sensitive Terms

Edit `Suspect_Words.csv` to add company-specific sensitive terms:

```csv
term
password
social security number
credit card
confidential
your custom term
```

Then regenerate embeddings:

```bash
python precompute_embeddings.py
```

## 📅 Scheduled Execution

The service automatically runs every 15 minutes at:
- :00
- :15
- :30
- :45

To check next scheduled run:
```bash
curl http://localhost:5000/scheduler_status
```

## 🔒 Security Best Practices

### Production Deployment

1. **Use Environment Variables**:
   Create a `.env` file (not committed to git):
   ```bash
   SPLUNK_USERNAME=service_account
   SPLUNK_PASSWORD=SecurePassword123!
   SPLUNK_HEC_TOKEN=your-token-here
   ```

2. **Update docker-compose.yml**:
   ```yaml
   environment:
     - SPLUNK_USERNAME=${SPLUNK_USERNAME}
     - SPLUNK_PASSWORD=${SPLUNK_PASSWORD}
     # etc...
   ```

3. **Network Security**:
   - Enable SSL/TLS certificate verification
   - Use firewall rules to restrict access
   - Run on internal network only

4. **Use Service Accounts**:
   - Create dedicated Splunk service account
   - Grant minimum required permissions
   - Rotate credentials regularly

## 📦 Project Structure

```
nlp_docker/
├── app.py                          # Main Flask application
├── Dockerfile                      # Docker image definition
├── docker-compose.yml              # Docker Compose configuration
├── requirements.txt                # Python dependencies
├── download_model.py               # Model download script
├── precompute_embeddings.py        # Generate embeddings
├── Suspect_Words.csv               # Sensitive terms list
├── o365_searchquery_training_full.csv  # Training data
├── sensitive_embeddings.npy        # Precomputed embeddings
├── models/                         # Sentence transformer model
│   └── all-MiniLM-L6-v2/
├── splunk_app/                     # Optional Splunk app
│   ├── bin/
│   │   └── nlp_analyze.py         # Custom search command
│   └── default/
│       ├── app.conf
│       └── commands.conf
├── DEPLOYMENT_CHECKLIST.md         # Deployment guide
├── SPLUNK_INTEGRATION_GUIDE.md     # Splunk integration docs
└── README.md                        # This file
```

## 🧪 Testing

### Test NLP Analysis
```bash
# Test health endpoint
curl http://localhost:5000/health

# Test single query analysis
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "password leak"}'

# Test Splunk integration
curl -X POST http://localhost:5000/process_splunk_search
```

### Test in Splunk
```splunk
# View recent results
index=nlp_test | head 20

# View high-risk queries
index=nlp_test similarity_score>0.8 
| table query, most_similar_term, similarity_score

# Analyze specific terms
index=nlp_test most_similar_term="social security number"
| stats count by query, user
```

## 🐛 Troubleshooting

### Container Can't Reach Splunk
- Check firewall rules
- Verify Splunk hostname/IP is correct
- Use `host.docker.internal` on Windows/Mac, actual hostname on Linux
- Test: `docker run --rm curlimages/curl https://splunk-host:8089 -k`

### 401 Unauthorized
- Verify username/password are correct
- Check account permissions
- Verify saved search permissions

### No Data in Splunk Index
- Check container logs: `docker logs nlp-alert-service`
- Verify HEC token is correct
- Verify index exists and HEC token has write permissions
- Test HEC manually with curl

### Saved Search Not Found
- Verify saved search name matches exactly (case-sensitive)
- Check saved search app/permissions
- Verify search is saved as "Report" not "Alert"

## 📚 Documentation

- **[DEPLOYMENT_CHECKLIST.md](DEPLOYMENT_CHECKLIST.md)**: Complete deployment guide
- **[SPLUNK_INTEGRATION_GUIDE.md](SPLUNK_INTEGRATION_GUIDE.md)**: Splunk integration details

## 🤝 Contributing

Contributions are welcome! Please:
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## 📝 License

[Add your license here]

## 📧 Support

For issues or questions:
- Check the logs: `docker logs nlp-alert-service`
- Review documentation files
- Open an issue on GitHub

---

**Note**: This is a security-focused tool. Always handle credentials securely and follow your organization's security policies.

