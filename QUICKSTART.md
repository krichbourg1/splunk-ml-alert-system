# Quick Start - Testing NLP Docker with Your Splunk Instance

## Current Configuration Check

Your `docker-compose.yml` currently has:
```yaml
SPLUNK_REST_URL=https://host.docker.internal:8089
SPLUNK_USERNAME=admin
SPLUNK_PASSWORD=NewPassword123!
SPLUNK_SEARCH_NAME=nlp_docker_test
SPLUNK_HEC_URL=https://host.docker.internal:8088/services/collector
SPLUNK_HEC_TOKEN=cbe8d021-1431-400e-9ed4-398ccff67486
SPLUNK_INDEX=nlp_test
```

**✅ If these values are correct for your Splunk, you're ready to go!**

**❌ If not, update docker-compose.yml lines 10-16 with your actual values**

---

## Step-by-Step Startup

### 1️⃣ Open PowerShell in your project directory
```powershell
cd C:\nlp_docker
```

### 2️⃣ Build the Docker container
```powershell
docker-compose build
```
*This will take 2-5 minutes the first time (downloads Python packages)*

### 3️⃣ Start the service
```powershell
docker-compose up -d
```
*The `-d` flag runs it in the background*

### 4️⃣ Check if container is running
```powershell
docker ps
```
*You should see `nlp-alert-service` in the list*

### 5️⃣ View the logs
```powershell
docker logs nlp-alert-service
```
*Look for: "✅ Background scheduler started - will run every 15 minutes"*

---

## Testing the Service

### Test 1: Health Check
```powershell
curl http://localhost:5000/health
```
**Expected Output:**
```json
{"status":"healthy","message":"NLP Alert Service is running"}
```

### Test 2: Analyze a Single Query
```powershell
curl -X POST http://localhost:5000/analyze -H "Content-Type: application/json" -d '{\"query\": \"social security number\"}'
```
**Expected Output:**
```json
{
  "query": "social security number",
  "most_similar_term": "Social Security Number",
  "similarity_score": 1.0,
  "all_detected_terms": [
    {"term": "Social Security Number", "score": 1.0}
  ]
}
```

### Test 3: Check Scheduler Status
```powershell
curl http://localhost:5000/scheduler_status
```
**Expected Output:**
```json
{
  "scheduler_running": true,
  "jobs": [
    {
      "job_id": "splunk_pull_job",
      "name": "Automated Splunk REST API Pull",
      "next_run_time": "2025-10-21 15:00:00"
    }
  ]
}
```

### Test 4: Manual Splunk Integration Test
```powershell
curl -X POST http://localhost:5000/process_splunk_search
```
**Expected Output:**
```json
{
  "message": "Processed 100 search results",
  "results": [...]
}
```

---

## Verify Results in Splunk

### 1. Search for the results in Splunk
```splunk
index=nlp_test | head 20
```

### 2. View high-scoring matches
```splunk
index=nlp_test similarity_score>0.7 
| table query, most_similar_term, similarity_score, original_time
```

### 3. See all detected terms
```splunk
index=nlp_test 
| spath output=terms path=all_detected_terms{} 
| mvexpand terms
| table query, terms
```

---

## Common Issues & Fixes

### ❌ Issue: "Connection refused" to Splunk
**Fix:**
- Make sure Splunk is running: `http://localhost:8000`
- On Windows/Mac: Use `host.docker.internal` (already configured)
- On Linux: Replace with `172.17.0.1` or actual IP address

### ❌ Issue: "401 Unauthorized"
**Fix:**
- Verify username/password in docker-compose.yml
- Try logging into Splunk Web UI manually

### ❌ Issue: "Saved search not found"
**Fix:**
- Verify search name is exactly: `nlp_docker_test`
- Check it's saved as "Report" not "Alert"
- Verify permissions are "Shared in App"

### ❌ Issue: "HEC token invalid"
**Fix:**
- Verify HEC is enabled globally in Splunk
- Check token is correct in docker-compose.yml
- Verify index `nlp_test` exists

### ❌ Issue: No data in Splunk index
**Fix:**
```powershell
# Check container logs for errors
docker logs nlp-alert-service | Select-String "error" -CaseSensitive

# Check if HEC is reachable
curl -k https://localhost:8088/services/collector/health
```

---

## Stop/Restart Commands

### Stop the service
```powershell
docker-compose down
```

### Restart after config changes
```powershell
docker-compose down
docker-compose up -d
```

### View real-time logs
```powershell
docker logs -f nlp-alert-service
```

### Rebuild after code changes
```powershell
docker-compose down
docker-compose build
docker-compose up -d
```

---

## Success Checklist

- [ ] Container is running (`docker ps` shows nlp-alert-service)
- [ ] Health check passes (`curl http://localhost:5000/health`)
- [ ] Manual analysis works (`/analyze` endpoint)
- [ ] Splunk connection works (`/process_splunk_search` returns results)
- [ ] Data appears in Splunk (`index=nlp_test | stats count` > 0)
- [ ] Scheduler is running (`/scheduler_status` shows next run time)

---

## Next Steps After Successful Test

1. **Customize Sensitive Terms**: Edit `Suspect_Words.csv` with your company-specific terms
2. **Update Saved Search**: Point to your actual data source (O365, SharePoint, etc.)
3. **Set Up Dashboards**: Create Splunk dashboards for monitoring
4. **Configure Alerts**: Set up alerts for high-risk queries (score > 0.8)
5. **Production Deployment**: Move to production server if testing on local machine

---

**Need Help?**
- Check logs: `docker logs nlp-alert-service`
- Check full documentation: `DEPLOYMENT_CHECKLIST.md`
- Debug mode: `docker-compose up` (without -d to see live output)

