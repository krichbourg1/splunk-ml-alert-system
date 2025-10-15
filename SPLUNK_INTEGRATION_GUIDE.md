# Splunk NLP Alert Analysis Integration Guide

This guide explains how to integrate your Docker-based NLP alert analysis service with Splunk for real-time processing of search queries and alerts.

## 🏗️ Architecture Overview

```
Splunk Search → Webhook → Docker NLP Service → HEC → Splunk Index
     ↓              ↓              ↓              ↓
  Alerts      Analysis API    Embeddings    Results Index
```

## 📋 Prerequisites

1. **Docker Container Running**: Your NLP service should be running on port 5000
2. **Splunk Instance**: With HEC (HTTP Event Collector) enabled
3. **Network Access**: Splunk can reach your Docker container

## 🚀 Setup Instructions

### Step 1: Configure HEC in Splunk

1. **Enable HEC**:
   - Go to Settings → Data Inputs → HTTP Event Collector
   - Click "New Token"
   - Name: `nlp_analysis_token`
   - Index: `nlp_alerts` (create this index if it doesn't exist)
   - Click "Next" → "Review" → "Submit"

2. **Note your HEC details**:
   - HEC URL: `https://your-splunk-instance:8088/services/collector`
   - HEC Token: `your-generated-token-here`

### Step 2: Update Docker Container with HEC Configuration

Stop and restart your container with environment variables:

```bash
docker stop nlp-test
docker rm nlp-test

docker run -d -p 5000:5000 \
  --name nlp-alert-service \
  -e SPLUNK_HEC_URL="https://your-splunk-instance:8088/services/collector" \
  -e SPLUNK_HEC_TOKEN="your-generated-token-here" \
  -e SPLUNK_INDEX="nlp_alerts" \
  nlp-alert-service
```

### Step 3: Install Splunk App

1. **Copy the Splunk app** to your Splunk apps directory:
   ```bash
   # Copy the splunk_app folder to $SPLUNK_HOME/etc/apps/
   cp -r splunk_app $SPLUNK_HOME/etc/apps/nlp_alert_analyzer
   ```

2. **Restart Splunk**:
   ```bash
   $SPLUNK_HOME/bin/splunk restart
   ```

3. **Verify installation**:
   - Go to Apps → NLP Alert Analyzer
   - You should see the "NLP Dashboard" option

### Step 4: Configure Webhook (Optional)

If you want Splunk to automatically send alerts to your NLP service:

1. **Update webhook URL** in `splunk_app/default/webhook.conf`:
   ```
   endpoint = http://your-docker-host:5000/splunk_webhook
   ```

2. **Reload webhook configuration**:
   ```bash
   $SPLUNK_HOME/bin/splunk reload webhook
   ```

## 🔧 Usage Examples

### 1. Manual Analysis with Custom Search Command

```splunk
index=your_search_index | head 100 | nlp_analyze field=search | where nlp_similarity_score > 0.7
```

This will:
- Take search queries from your index
- Analyze them using the NLP service
- Filter for high similarity scores (>0.7)
- Add NLP analysis fields to each event

### 2. Real-time Alert Analysis

Create a saved search that runs every 5 minutes:

```splunk
index=your_search_index | head 100 | nlp_analyze field=search | where nlp_similarity_score > 0.7 | table _time, search, nlp_most_similar_term, nlp_similarity_score, nlp_sentiment_label
```

### 3. API Direct Usage

You can also call the API directly:

```bash
# Analyze single query
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "suspicious search term"}'

# Analyze batch
curl -X POST http://localhost:5000/analyze_batch \
  -H "Content-Type: application/json" \
  -d '{"queries": ["term1", "term2", "term3"]}'

# Splunk webhook (for alert actions)
curl -X POST http://localhost:5000/splunk_webhook \
  -H "Content-Type: application/json" \
  -d '{"result": [{"search": "suspicious query", "user": "john.doe"}]}'
```

## 📊 Dashboard Features

The included dashboard provides:

1. **High Similarity Alerts**: Shows queries with similarity scores > 0.7
2. **Similarity Score Distribution**: Histogram of similarity scores
3. **Sentiment Analysis**: Pie chart of sentiment labels
4. **Top Similar Terms**: Most frequently matched sensitive terms
5. **Analysis Over Time**: Timeline of sentiment analysis

## 🔍 Understanding the Output

Each analyzed event will contain these new fields:

- `nlp_most_similar_term`: The sensitive term most similar to the query
- `nlp_similarity_score`: Similarity score (0-1, higher = more similar)
- `nlp_sentiment_label`: Sentiment classification (POSITIVE/NEGATIVE)
- `nlp_sentiment_score`: Sentiment confidence (0-1)
- `nlp_analysis_timestamp`: When the analysis was performed
- `nlp_error`: Error message if analysis failed

## ⚙️ Configuration Options

### Environment Variables

- `SPLUNK_HEC_URL`: Splunk HEC endpoint URL
- `SPLUNK_HEC_TOKEN`: HEC authentication token
- `SPLUNK_INDEX`: Target index for analysis results

### Custom Search Command Options

- `field`: Field containing text to analyze (required)
- `endpoint`: NLP service endpoint (default: http://localhost:5000/analyze)

## 🚨 Troubleshooting

### Common Issues

1. **Connection Refused**:
   - Check if Docker container is running: `docker ps`
   - Verify port 5000 is accessible: `curl http://localhost:5000/health`

2. **HEC Authentication Failed**:
   - Verify HEC token is correct
   - Check HEC URL format (include https:// and port 8088)

3. **Custom Command Not Found**:
   - Restart Splunk after installing the app
   - Check file permissions on `nlp_analyze.py`

4. **No Results in Dashboard**:
   - Verify data is being sent to the `nlp_alerts` index
   - Check if HEC is properly configured

### Debug Commands

```bash
# Check container logs
docker logs nlp-alert-service

# Test API directly
curl http://localhost:5000/health

# Check Splunk logs
tail -f $SPLUNK_HOME/var/log/splunk/splunkd.log
```

## 📈 Performance Considerations

1. **Batch Processing**: Use the `/analyze_batch` endpoint for multiple queries
2. **Rate Limiting**: Consider implementing rate limiting for high-volume scenarios
3. **Caching**: The service caches model loading, but each analysis is real-time
4. **Indexing**: Monitor the `nlp_alerts` index size and implement retention policies

## 🔒 Security Notes

1. **HTTPS**: Use HTTPS for HEC in production
2. **Authentication**: Consider adding API authentication
3. **Network Security**: Ensure proper firewall rules
4. **Data Privacy**: Be aware of what data is being sent to the analysis service

## 📝 Next Steps

1. **Tune Similarity Thresholds**: Adjust the 0.7 threshold based on your data
2. **Add More Sensitive Terms**: Update `Suspect_Words.csv` with your specific terms
3. **Create Additional Dashboards**: Build custom visualizations for your use case
4. **Set Up Alerting**: Configure Splunk alerts based on similarity scores
5. **Monitor Performance**: Track analysis latency and throughput

## 🆘 Support

If you encounter issues:

1. Check the Docker container logs
2. Verify Splunk configuration
3. Test API endpoints directly
4. Review Splunk search logs

The service is designed to be resilient - if the NLP service is unavailable, Splunk searches will continue to work (just without NLP analysis).
