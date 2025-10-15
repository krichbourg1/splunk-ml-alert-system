# NLP Docker Deployment Checklist

## 📋 Migration Checklist for Company Computer/Server

### 1️⃣ **Prerequisites - Install Software**
- [ ] Install Docker Desktop (Windows/Mac) or Docker Engine (Linux server)
- [ ] Verify Docker is running: `docker --version`
- [ ] Install Docker Compose: `docker-compose --version`
- [ ] Ensure network connectivity to company Splunk instance

---

### 2️⃣ **Copy Project Files**
Transfer the entire `nlp_docker` directory to your company computer/server:
- [ ] All Python files (`app.py`, `download_model.py`, `precompute_embeddings.py`)
- [ ] Docker files (`Dockerfile`, `docker-compose.yml`)
- [ ] Data files:
  - [ ] `o365_searchquery_training_full.csv` (training data)
  - [ ] `Suspect_Words.csv` (sensitive terms list)
  - [ ] `sensitive_embeddings.npy` (precomputed embeddings)
  - [ ] `sensitive_terms_order.csv`
- [ ] Model directory: `models/all-MiniLM-L6-v2/` (entire folder)
- [ ] Splunk app directory: `splunk_app/` (if deploying custom command)
- [ ] Documentation files (README, guides)

---

### 3️⃣ **Splunk Configuration - COMPANY INSTANCE**

#### A. Get Company Splunk Details
- [ ] **Splunk Web URL**: `https://[company-splunk]:8000`
- [ ] **Splunk REST API URL**: `https://[company-splunk]:8089`
- [ ] **Username**: (your company Splunk username)
- [ ] **Password**: (your company Splunk password)

#### B. Create HEC Token in Company Splunk
1. [ ] Log into company Splunk Web UI
2. [ ] Go to **Settings → Data Inputs → HTTP Event Collector**
3. [ ] Click **Global Settings**:
   - [ ] Enable **"All Tokens"**
   - [ ] Click **Save**
4. [ ] Click **"New Token"**:
   - [ ] **Name**: `nlp_analysis_token` (or your company naming convention)
   - [ ] **Source type**: `_json`
   - [ ] **Index**: Select or create index (see next section)
   - [ ] Click **Review** → **Submit**
5. [ ] **COPY THE TOKEN** (format: `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`)
   - Token: `_______________________________________________`

#### C. Create/Verify Splunk Index
- [ ] Check if `nlp_test` index exists or create new index:
  - [ ] Go to **Settings → Indexes**
  - [ ] Click **New Index**
  - [ ] **Index Name**: `nlp_test` (or company naming: `nlp_analysis`, `security_nlp`, etc.)
  - [ ] **Index Data Type**: Events
  - [ ] Set retention policy as needed
  - [ ] Click **Save**
- [ ] **Index name to use**: `_______________________________________________`

#### D. Create Saved Search
- [ ] Go to **Settings → Searches, reports, and alerts**
- [ ] Click **New Search**
- [ ] Enter search query (example):
  ```splunk
  index=main earliest=-24h 
  | head 1000 
  | table _time, SearchQueryText, user, action
  ```
- [ ] Click **Save As** → **Report**
- [ ] **Title**: `nlp_docker_test` (or your preferred name)
- [ ] **Permissions**: Shared in App (ensure service account can access)
- [ ] Click **Save**
- [ ] **Saved search name**: `_______________________________________________`

#### E. Data Source Configuration
- [ ] Identify which Splunk index contains the data to analyze: `_______________`
- [ ] Identify the field name containing search queries/text: `_______________`
- [ ] Test the search query in Splunk to ensure it returns data
- [ ] Update the saved search query with correct index and fields

---

### 4️⃣ **Update docker-compose.yml**

Edit `docker-compose.yml` and update these environment variables:

```yaml
environment:
  # Splunk REST API Configuration
  - SPLUNK_REST_URL=https://[COMPANY_SPLUNK_HOST]:8089
  - SPLUNK_USERNAME=[YOUR_SPLUNK_USERNAME]
  - SPLUNK_PASSWORD=[YOUR_SPLUNK_PASSWORD]
  - SPLUNK_SEARCH_NAME=[YOUR_SAVED_SEARCH_NAME]
  
  # Splunk HEC Configuration
  - SPLUNK_HEC_URL=https://[COMPANY_SPLUNK_HOST]:8088/services/collector
  - SPLUNK_HEC_TOKEN=[YOUR_HEC_TOKEN_FROM_STEP_3B]
  - SPLUNK_INDEX=[YOUR_INDEX_NAME_FROM_STEP_3C]
```

**Fill in these values:**
- [ ] SPLUNK_REST_URL: `_______________________________________________`
- [ ] SPLUNK_USERNAME: `_______________________________________________`
- [ ] SPLUNK_PASSWORD: `_______________________________________________`
- [ ] SPLUNK_SEARCH_NAME: `_______________________________________________`
- [ ] SPLUNK_HEC_URL: `_______________________________________________`
- [ ] SPLUNK_HEC_TOKEN: `_______________________________________________`
- [ ] SPLUNK_INDEX: `_______________________________________________`

---

### 5️⃣ **Security Considerations**

#### Option A: Use Environment Variables (Recommended for Production)
- [ ] Create `.env` file (NOT checked into git):
  ```bash
  SPLUNK_REST_URL=https://company-splunk:8089
  SPLUNK_USERNAME=service_account
  SPLUNK_PASSWORD=SecurePassword123!
  SPLUNK_SEARCH_NAME=nlp_docker_test
  SPLUNK_HEC_URL=https://company-splunk:8088/services/collector
  SPLUNK_HEC_TOKEN=your-token-here
  SPLUNK_INDEX=nlp_test
  ```
- [ ] Update docker-compose.yml to use `.env` file:
  ```yaml
  environment:
    - SPLUNK_REST_URL=${SPLUNK_REST_URL}
    - SPLUNK_USERNAME=${SPLUNK_USERNAME}
    - SPLUNK_PASSWORD=${SPLUNK_PASSWORD}
    # etc...
  ```
- [ ] Add `.env` to `.gitignore` file

#### Option B: Use Docker Secrets (For Server/Production)
- [ ] Create Docker secrets for sensitive data
- [ ] Update docker-compose.yml to use secrets
- [ ] Never commit credentials to version control

#### Company-Specific Security
- [ ] Check if company requires service account instead of personal credentials
- [ ] Check if company has certificate requirements (SSL/TLS)
- [ ] Check if company firewall allows Docker → Splunk communication
- [ ] Check if company has Docker registry for approved images

---

### 6️⃣ **Network Configuration**

#### Company Computer (Development)
- [ ] Verify Docker can reach Splunk:
  ```bash
  docker run --rm curlimages/curl https://[company-splunk]:8089 -k
  ```
- [ ] Check company firewall/VPN requirements
- [ ] Test from inside container:
  ```bash
  docker run --rm curlimages/curl https://host.docker.internal:8089 -k
  ```

#### Server (Production)
- [ ] Replace `host.docker.internal` with actual Splunk hostname/IP
- [ ] Update docker-compose.yml:
  ```yaml
  - SPLUNK_REST_URL=https://splunk-prod.company.com:8089
  - SPLUNK_HEC_URL=https://splunk-prod.company.com:8088/services/collector
  ```
- [ ] Configure DNS resolution if needed
- [ ] Open firewall ports: 8089 (REST API), 8088 (HEC)
- [ ] Configure SSL certificates if required

---

### 7️⃣ **Customize Data Files (Optional)**

#### Update Sensitive Terms List
- [ ] Review `Suspect_Words.csv`
- [ ] Add company-specific sensitive terms
- [ ] Remove irrelevant terms
- [ ] Format: One term per line with header `term`

#### Update Training Data (Optional)
- [ ] Replace `o365_searchquery_training_full.csv` with company data if available
- [ ] Or keep existing for general use

#### Regenerate Embeddings (If you modified Suspect_Words.csv)
- [ ] Run: `python precompute_embeddings.py`
- [ ] This will regenerate `sensitive_embeddings.npy`

---

### 8️⃣ **Build and Test**

#### On Company Computer
- [ ] Navigate to project directory
- [ ] Build the Docker image:
  ```bash
  docker-compose build
  ```
- [ ] Start the container:
  ```bash
  docker-compose up -d
  ```
- [ ] Check logs:
  ```bash
  docker logs nlp-alert-service
  ```
- [ ] Verify health:
  ```bash
  curl http://localhost:5000/health
  ```
- [ ] Test manual analysis:
  ```bash
  curl -X POST http://localhost:5000/analyze \
    -H "Content-Type: application/json" \
    -d '{"query": "social security number"}'
  ```
- [ ] Test Splunk integration:
  ```bash
  curl -X POST http://localhost:5000/process_splunk_search
  ```
- [ ] Check scheduler status:
  ```bash
  curl http://localhost:5000/scheduler_status
  ```
- [ ] Verify data in Splunk:
  ```splunk
  index=[YOUR_INDEX] | head 10
  ```

---

### 9️⃣ **Server Deployment (Production)**

#### Prepare Server
- [ ] Server OS: `_______________________________________________`
- [ ] Docker installed: [ ] Yes [ ] No
- [ ] Access credentials: `_______________________________________________`
- [ ] Server hostname/IP: `_______________________________________________`

#### Transfer Files
- [ ] Copy entire project directory to server
- [ ] Use SCP, SFTP, or company deployment tool:
  ```bash
  scp -r nlp_docker/ user@server:/opt/nlp_docker/
  ```

#### Server Configuration
- [ ] SSH into server
- [ ] Navigate to project directory: `cd /opt/nlp_docker`
- [ ] Verify docker-compose.yml has correct settings
- [ ] Update `SPLUNK_REST_URL` and `SPLUNK_HEC_URL` to use actual hostname (not host.docker.internal)
- [ ] Build and start:
  ```bash
  docker-compose up -d
  ```
- [ ] Enable auto-restart:
  ```yaml
  # In docker-compose.yml
  restart: unless-stopped  # Already configured
  ```
- [ ] Set up container to start on boot:
  ```bash
  # Add to systemd or use Docker restart policy
  docker update --restart=unless-stopped nlp-alert-service
  ```

#### Monitoring
- [ ] Set up log rotation for Docker logs
- [ ] Configure monitoring/alerting if container stops
- [ ] Document server maintenance procedures

---

### 🔟 **Validation Checklist**

After deployment, verify:
- [ ] Container is running: `docker ps`
- [ ] Container is healthy: `docker ps` (shows "healthy" status)
- [ ] No errors in logs: `docker logs nlp-alert-service | grep -i error`
- [ ] Scheduler is running: `curl http://localhost:5000/scheduler_status`
- [ ] Next scheduled run time is correct
- [ ] Manual test works: `curl -X POST http://localhost:5000/process_splunk_search`
- [ ] Data appears in Splunk index: `index=[YOUR_INDEX] | stats count`
- [ ] HEC connection working (Status 200 in logs)
- [ ] REST API connection working (can retrieve saved search)
- [ ] Analysis results include:
  - [ ] `query` field
  - [ ] `most_similar_term` field
  - [ ] `similarity_score` field
  - [ ] `all_detected_terms` array
  - [ ] Original Splunk data preserved

---

### 1️⃣1️⃣ **Optional: Deploy Splunk App (Custom Search Command)**

If you want to use the `| nlp_analyze` custom search command:

- [ ] Copy `splunk_app/` directory to Splunk apps folder:
  ```bash
  # On Splunk server
  cp -r splunk_app/ $SPLUNK_HOME/etc/apps/nlp_alert_analyzer/
  ```
- [ ] Update `splunk_app/bin/nlp_analyze.py` line 28:
  ```python
  endpoint = Option(
      doc='NLP service endpoint URL',
      default='http://[YOUR_SERVER]:5000/analyze'  # Update this
  )
  ```
- [ ] Set correct permissions:
  ```bash
  chmod +x $SPLUNK_HOME/etc/apps/nlp_alert_analyzer/bin/nlp_analyze.py
  ```
- [ ] Restart Splunk:
  ```bash
  $SPLUNK_HOME/bin/splunk restart
  ```
- [ ] Test the command:
  ```splunk
  | makeresults 
  | eval SearchQueryText="password leak" 
  | nlp_analyze field=SearchQueryText
  ```

---

### 1️⃣2️⃣ **Troubleshooting Common Issues**

#### Issue: Container can't reach Splunk
- [ ] Check firewall rules
- [ ] Verify VPN connection
- [ ] Test connectivity: `docker run --rm curlimages/curl https://splunk-host:8089 -k`
- [ ] Check if using correct hostname (not `host.docker.internal` on Linux server)

#### Issue: 401 Unauthorized
- [ ] Verify Splunk username/password are correct
- [ ] Check if account is locked
- [ ] Verify account has permissions to access saved search
- [ ] Try logging into Splunk Web UI manually

#### Issue: HEC token invalid
- [ ] Verify HEC token is correct
- [ ] Check if HEC is enabled globally in Splunk
- [ ] Verify token hasn't been deleted
- [ ] Test HEC manually with curl

#### Issue: Saved search not found
- [ ] Verify saved search name matches exactly (case-sensitive)
- [ ] Check if saved search is in correct app
- [ ] Verify permissions allow service account to access it
- [ ] Test search manually in Splunk UI

#### Issue: No data in target index
- [ ] Check container logs for errors
- [ ] Verify index name is correct
- [ ] Check HEC token has permission to write to that index
- [ ] Test HEC connection manually
- [ ] Search with longer time range: `index=nlp_test earliest=-7d`

---

### 1️⃣3️⃣ **Documentation for Company IT**

Create documentation including:
- [ ] Purpose of the application
- [ ] Architecture diagram (Splunk → Docker → HEC → Splunk)
- [ ] Security considerations
- [ ] Network requirements (ports 8088, 8089, 5000)
- [ ] Resource requirements (CPU, RAM, Disk)
- [ ] Maintenance procedures
- [ ] Contact information for support

---

### 1️⃣4️⃣ **Quick Reference - URLs and Ports**

| Component | Port | Purpose |
|-----------|------|---------|
| Splunk Web UI | 8000 | Web interface |
| Splunk REST API | 8089 | API for saved searches |
| Splunk HEC | 8088 | HTTP Event Collector |
| NLP Service | 5000 | Docker container API |

---

## 📝 Summary of Required Changes

### Minimum Required Updates:
1. ✅ Splunk REST API URL (company Splunk host)
2. ✅ Splunk credentials (company account)
3. ✅ Splunk HEC URL (company Splunk host)
4. ✅ HEC Token (create in company Splunk)
5. ✅ Index name (create in company Splunk)
6. ✅ Saved search name (create in company Splunk)

### Files to Update:
- `docker-compose.yml` - All environment variables
- (Optional) Create `.env` file for secrets
- (Optional) Update `Suspect_Words.csv` with company-specific terms

### Server-Specific Changes:
- Replace `host.docker.internal` with actual Splunk hostname
- Configure auto-start on server reboot
- Set up monitoring and log rotation

---

## 🚀 Quick Start Commands

```bash
# 1. Build the container
docker-compose build

# 2. Start the service
docker-compose up -d

# 3. Check logs
docker logs nlp-alert-service

# 4. Test health
curl http://localhost:5000/health

# 5. Test analysis
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "test query"}'

# 6. Check scheduler
curl http://localhost:5000/scheduler_status

# 7. Stop the service
docker-compose down
```

---

## 📧 Support

For issues or questions:
- Check container logs: `docker logs nlp-alert-service`
- Check Splunk logs: `$SPLUNK_HOME/var/log/splunk/splunkd.log`
- Review this checklist
- Contact: [Your contact info]

---

**Last Updated**: October 15, 2025

