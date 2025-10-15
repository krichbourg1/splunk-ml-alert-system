# --------------------------
# 1️⃣ Install & import packages
# --------------------------
import pandas as pd
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
# from transformers import pipeline  # Removed for performance optimization
import json
import requests
import os
import time
from datetime import datetime
from flask import Flask, request, jsonify
from difflib import SequenceMatcher
import re
from apscheduler.schedulers.background import BackgroundScheduler
import atexit

# --------------------------
# 2️⃣ Time Conversion Helper Functions
# --------------------------
def convert_splunk_time_to_unix(time_str):
    """Convert Splunk _time format to Unix timestamp"""
    try:
        dt = datetime.strptime(time_str, "%Y-%m-%d %H:%M:%S")
        return int(dt.timestamp())
    except ValueError:
        return int(datetime.now().timestamp())

def get_current_time_string():
    """Get current time in same format as Splunk _time"""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def calculate_latency(original_time_str, current_time_str):
    """Calculate processing latency in seconds"""
    try:
        original_dt = datetime.strptime(original_time_str, "%Y-%m-%d %H:%M:%S")
        current_dt = datetime.strptime(current_time_str, "%Y-%m-%d %H:%M:%S")
        return (current_dt - original_dt).total_seconds()
    except:
        return 0

def convert_splunk_iso_to_simple(iso_time_str):
    """Convert Splunk ISO time format to simple format"""
    try:
        # Parse ISO format: "2025-10-02T09:18:31.000-04:00"
        dt = datetime.fromisoformat(iso_time_str.replace('Z', '+00:00'))
        # Return simple format: "2025-10-02 09:18:31"
        return dt.strftime("%Y-%m-%d %H:%M:%S")
    except ValueError:
        return iso_time_str  # Return original if parsing fails

# --------------------------
# 3️⃣ Load your data
# --------------------------
queries_df = pd.read_csv("o365_searchquery_training_full.csv")
sensitive_terms_df = pd.read_csv("Suspect_Words.csv")

# --------------------------
# 3️⃣ Initialize embedding model from local directory
# --------------------------
embedding_model_path = "./models/all-MiniLM-L6-v2/snapshots/c9745ed1d9f207416be6d2e6f8de32d1f16199bf"
embedding_model = SentenceTransformer(embedding_model_path)

def get_embedding(text):
    """
    Returns a mean-pooled embedding for the input text.
    """
    return embedding_model.encode([text])[0]

# --------------------------
# 4️⃣ Precompute sensitive term embeddings once
# --------------------------
print("Precomputing sensitive term embeddings...")
sensitive_embeddings = np.array([get_embedding(term) for term in sensitive_terms_df['term']])
print("Done precomputing embeddings.")

# --------------------------
# 5️⃣ Enhanced similarity functions with punctuation handling
# --------------------------
def normalize_text(text):
    """
    Normalize text by removing punctuation and normalizing whitespace.
    """
    # Replace punctuation with spaces
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    # Normalize multiple spaces to single space
    text = re.sub(r'\s+', ' ', text)
    return text.strip()

def calculate_substring_similarity(query, sensitive_term):
    """
    Calculate substring similarity between query and sensitive term.
    Uses normalized text to handle punctuation.
    Returns a score between 0 and 1.
    """
    # Normalize both texts to handle punctuation
    query_norm = normalize_text(query)
    term_norm = normalize_text(sensitive_term)
    
    # Exact substring match on normalized text
    if term_norm in query_norm:
        return 1.0
    
    # Fuzzy substring match using SequenceMatcher on normalized text
    matcher = SequenceMatcher(None, query_norm, term_norm)
    match = matcher.find_longest_match(0, len(query_norm), 0, len(term_norm))
    
    if match.size > 0:
        # Calculate similarity based on match length
        similarity = match.size / len(term_norm)
        return min(similarity, 1.0)
    
    return 0.0

def calculate_word_overlap_similarity(query, sensitive_term):
    """
    Calculate word-level overlap similarity using Jaccard similarity.
    Uses normalized text to handle punctuation.
    """
    # Use normalized text for better word extraction
    query_norm = normalize_text(query)
    term_norm = normalize_text(sensitive_term)
    
    query_words = set(query_norm.split())
    term_words = set(term_norm.split())
    
    if not query_words or not term_words:
        return 0.0
    
    intersection = query_words.intersection(term_words)
    union = query_words.union(term_words)
    
    return len(intersection) / len(union) if union else 0.0

def enhanced_similarity_score(query, sensitive_term, semantic_score):
    """
    Calculate enhanced similarity score combining substring, word overlap, and semantic similarity.
    """
    # Get substring similarity
    substring_score = calculate_substring_similarity(query, sensitive_term)
    
    # Get word overlap similarity
    word_overlap_score = calculate_word_overlap_similarity(query, sensitive_term)
    
    # Weighted combination: prioritize substring matches, then word overlap, then semantic
    if substring_score > 0.8:  # Strong substring match
        return max(substring_score, semantic_score * 0.7)
    elif word_overlap_score > 0.6:  # Good word overlap
        return max(word_overlap_score, semantic_score * 0.8)
    else:  # Fall back to semantic similarity
        return semantic_score

def find_all_sensitive_terms(query, sensitive_terms_df, sensitive_embeddings, threshold=0.5):
    """
    Find all sensitive terms in a query that exceed the similarity threshold.
    Returns a list of (term, score) tuples.
    """
    # Compute semantic similarities for all terms
    query_embedding = get_embedding(query).reshape(1, -1)
    semantic_similarities = cosine_similarity(query_embedding, sensitive_embeddings)
    
    matches = []
    for i, term in enumerate(sensitive_terms_df['term']):
        semantic_score = semantic_similarities[0][i]
        enhanced_score = enhanced_similarity_score(query, term, semantic_score)
        
        if enhanced_score >= threshold:
            matches.append((term, enhanced_score))
    
    # Sort by score (highest first)
    matches.sort(key=lambda x: x[1], reverse=True)
    return matches

# --------------------------
# 6️⃣ Main analysis function
# --------------------------
def analyze_query(query_text):
    """
    Enhanced analysis with punctuation handling and multiple term detection.
    Returns:
        - most similar sensitive term
        - enhanced similarity score
        - all detected sensitive terms (if multiple)
    """
    # Find all sensitive terms that exceed threshold
    all_matches = find_all_sensitive_terms(query_text, sensitive_terms_df, sensitive_embeddings, threshold=0.5)
    
    if not all_matches:
        return {
            "query": query_text,
            "most_similar_term": "none",
            "similarity_score": 0.0,
            "all_detected_terms": []
        }
    
    # Get the highest scoring term
    most_similar_term, max_similarity = all_matches[0]
    
    # Prepare all detected terms for the response
    all_detected_terms = [{"term": term, "score": float(score)} for term, score in all_matches]

    return {
        "query": query_text,
        "most_similar_term": most_similar_term,
        "similarity_score": float(max_similarity),
        "all_detected_terms": all_detected_terms
    }

# --------------------------
# 7️⃣ Splunk REST API Configuration
# --------------------------
SPLUNK_REST_URL = os.getenv('SPLUNK_REST_URL', 'https://host.docker.internal:8089')
SPLUNK_USERNAME = os.getenv('SPLUNK_USERNAME', 'admin')
SPLUNK_PASSWORD = os.getenv('SPLUNK_PASSWORD', 'your-password-here')
SPLUNK_SEARCH_NAME = os.getenv('SPLUNK_SEARCH_NAME', 'nlp_docker_test')

# --------------------------
# 8️⃣ HEC (HTTP Event Collector) Configuration
# --------------------------
HEC_URL = os.getenv('SPLUNK_HEC_URL', 'https://your-splunk-instance:8088/services/collector')
HEC_TOKEN = os.getenv('SPLUNK_HEC_TOKEN', 'your-hec-token-here')
HEC_INDEX = os.getenv('SPLUNK_INDEX', 'nlp_alerts')

def run_splunk_search():
    """
    Trigger a saved search in Splunk and return the job SID
    """
    try:
        url = f"{SPLUNK_REST_URL}/services/saved/searches/{SPLUNK_SEARCH_NAME}/dispatch"
        headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
        }
        
        # Use Basic Authentication
        auth = (SPLUNK_USERNAME, SPLUNK_PASSWORD)
        
        response = requests.post(url, headers=headers, auth=auth, verify=False, timeout=30)
        response.raise_for_status()
        
        # Extract SID from response
        sid = response.text.split("<sid>")[1].split("</sid>")[0]
        print(f"Started Splunk search job: {sid}")
        return sid
        
    except Exception as e:
        print(f"Error starting Splunk search: {e}")
        return None

def get_splunk_results(sid, max_wait=120, batch_size=1000):
    """
    Retrieve search results from Splunk by SID with batch processing
    """
    try:
        # First, check if job is complete
        status_url = f"{SPLUNK_REST_URL}/services/search/jobs/{sid}"
        headers = {
            'Content-Type': 'application/json'
        }
        
        # Add JSON output mode parameter
        status_params = {'output_mode': 'json'}
        
        # Use Basic Authentication
        auth = (SPLUNK_USERNAME, SPLUNK_PASSWORD)
        
        # Wait for job to complete
        for attempt in range(max_wait):
            status_response = requests.get(status_url, headers=headers, params=status_params, auth=auth, verify=False, timeout=30)
            
            if status_response.status_code == 200:
                try:
                    status_data = status_response.json()
                    is_done = status_data.get('entry', [{}])[0].get('content', {}).get('isDone', False)
                    print(f"Job status check {attempt + 1}: isDone={is_done}")
                    
                    if is_done:
                        print("Search job completed, retrieving results...")
                        break
                    else:
                        print(f"Waiting for search to complete... (attempt {attempt + 1}/{max_wait})")
                        time.sleep(2)
                except Exception as e:
                    print(f"Error parsing status response: {e}")
                    print(f"Status response: {status_response.text[:200]}...")
                    time.sleep(2)
            else:
                print(f"Error checking job status: {status_response.status_code}")
                print(f"Status response: {status_response.text[:200]}...")
                time.sleep(2)
        else:
            print("Search did not complete in time")
            return None
        
        # Get total count first
        count_url = f"{SPLUNK_REST_URL}/services/search/jobs/{sid}/results"
        count_params = {'output_mode': 'json', 'count': 0}
        count_response = requests.get(count_url, headers=headers, params=count_params, auth=auth, verify=False, timeout=30)
        
        if count_response.status_code != 200:
            print(f"Error getting result count: {count_response.status_code}")
            print(f"Response: {count_response.text}")
            return None
        
        try:
            count_data = count_response.json()
            total_results = len(count_data.get('results', []))
            print(f"Total results available: {total_results}")
            print(f"Response keys: {list(count_data.keys())}")
        except Exception as e:
            print(f"Error parsing count response: {e}")
            print(f"Response status: {count_response.status_code}")
            print(f"Response headers: {dict(count_response.headers)}")
            print(f"Response text: {count_response.text[:500]}...")
            return None
        
        # Process in batches
        all_results = []
        offset = 0
        
        while offset < total_results:
            batch_params = {
                'output_mode': 'json',
                'count': batch_size,
                'offset': offset
            }
            
            batch_response = requests.get(count_url, headers=headers, params=batch_params, auth=auth, verify=False, timeout=60)
            
            if batch_response.status_code == 200:
                batch_data = batch_response.json()
                batch_results = batch_data.get('results', [])
                all_results.extend(batch_results)
                print(f"Retrieved batch {offset//batch_size + 1}: {len(batch_results)} results (Total: {len(all_results)})")
                offset += batch_size
            else:
                print(f"Error retrieving batch at offset {offset}: {batch_response.status_code}")
                break
        
        print(f"Retrieved {len(all_results)} total results from Splunk")
        return all_results
        
    except Exception as e:
        print(f"Error retrieving Splunk results: {e}")
        return None

def send_to_splunk(event_data, source_type="nlp_analysis", original_time_str=None):
    """
    Send analysis results back to Splunk via HEC
    """
    if not HEC_URL or HEC_URL == 'https://your-splunk-instance:8088/services/collector':
        print("HEC not configured, skipping Splunk send")
        return False
    
    try:
        headers = {
            'Authorization': f'Splunk {HEC_TOKEN}',
            'Content-Type': 'application/json'
        }
        
        # Convert original time to Unix timestamp for HEC
        if original_time_str:
            hec_time = convert_splunk_time_to_unix(original_time_str)
        else:
            hec_time = int(datetime.now().timestamp())
        
        # Get current time for analysis
        current_time_str = get_current_time_string()
        
        # Add time fields to event data
        event_data['original_time'] = convert_splunk_iso_to_simple(original_time_str) if original_time_str else None
        event_data['hec_time'] = current_time_str
        if original_time_str:
            # Convert to simple format for latency calculation
            simple_original_time = convert_splunk_iso_to_simple(original_time_str)
            event_data['processing_latency_seconds'] = calculate_latency(simple_original_time, current_time_str)
        
        # Add metadata for Splunk
        splunk_event = {
            "time": hec_time,  # Original event time (Unix)
            "source": "nlp_alert_service",
            "sourcetype": source_type,
            "index": HEC_INDEX,
            "event": event_data
        }
        
        response = requests.post(HEC_URL, 
                               headers=headers, 
                               json=splunk_event, 
                               verify=False,  # Set to True in production
                               timeout=10)
        
        if response.status_code == 200:
            print(f"Successfully sent event to Splunk: {event_data.get('query', 'unknown')}")
            return True
        else:
            print(f"Failed to send to Splunk: {response.status_code} - {response.text}")
            return False
            
    except Exception as e:
        print(f"Error sending to Splunk: {e}")
        return False

# --------------------------
# 9️⃣ Scheduled Background Job
# --------------------------
def scheduled_splunk_pull():
    """
    Background job that runs every 15 minutes to pull Splunk data
    """
    print(f"[SCHEDULED] Starting automated Splunk pull at {datetime.now()}")
    
    try:
        # 1. Trigger the saved search
        sid = run_splunk_search()
        if not sid:
            print("[SCHEDULED] Failed to start Splunk search")
            return
        
        # 2. Get all results
        results = get_splunk_results(sid)
        if not results:
            print("[SCHEDULED] Failed to retrieve search results")
            return
        
        # 3. Process each result
        processed_count = 0
        for result in results:
            query_text = result.get('SearchQueryText', '')
            if not query_text:
                continue
                
            # Analyze the query
            analysis = analyze_query(query_text)
            
            # Add original Splunk data
            analysis['splunk_data'] = result
            analysis['timestamp'] = datetime.now().isoformat()
            analysis['source'] = 'scheduled_pull'
            
            # Preserve original _time field for HEC
            original_time = result.get('_time', '')
            if original_time:
                analysis['original_time'] = convert_splunk_iso_to_simple(original_time)
            
            # Send to Splunk HEC with original time
            send_to_splunk(analysis, "splunk_rest_analysis", original_time)
            processed_count += 1
        
        print(f"[SCHEDULED] Completed: Processed {processed_count} search results")
        
    except Exception as e:
        print(f"[SCHEDULED] Error during automated pull: {e}")

# --------------------------
# 🔟 Initialize Flask app
# --------------------------
app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "message": "NLP Alert Service is running"})

@app.route('/analyze', methods=['POST'])
def analyze_alert():
    """
    Analyze a single query/alert text.
    Expects JSON with 'query' field.
    """
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' field in request"}), 400
        
        query_text = data['query']
        result = analyze_query(query_text)
        
        # Add metadata for Splunk
        result['timestamp'] = datetime.now().isoformat()
        result['source_ip'] = request.remote_addr
        result['user_agent'] = request.headers.get('User-Agent', 'unknown')
        
        # Send to Splunk if configured
        send_to_splunk(result, "nlp_analysis")
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analyze_batch', methods=['POST'])
def analyze_batch():
    """
    Analyze multiple queries/alert texts.
    Expects JSON with 'queries' field containing array of strings.
    """
    try:
        data = request.get_json()
        if not data or 'queries' not in data:
            return jsonify({"error": "Missing 'queries' field in request"}), 400
        
        queries = data['queries']
        if not isinstance(queries, list):
            return jsonify({"error": "'queries' must be an array"}), 400
        
        results = []
        for query_text in queries:
            result = analyze_query(query_text)
            # Add metadata for Splunk
            result['timestamp'] = datetime.now().isoformat()
            result['source_ip'] = request.remote_addr
            result['user_agent'] = request.headers.get('User-Agent', 'unknown')
            results.append(result)
            
            # Send each result to Splunk
            send_to_splunk(result, "nlp_analysis", None)
        
        return jsonify({
            "results": results,
            "count": len(results)
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/analyze_detailed', methods=['POST'])
def analyze_detailed():
    """
    Analyze a single query with detailed multiple term detection.
    Returns all detected sensitive terms with scores.
    """
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Missing 'query' field in request"}), 400
        
        query_text = data['query']
        result = analyze_query(query_text)
        
        # Add metadata
        result['timestamp'] = datetime.now().isoformat()
        result['source_ip'] = request.remote_addr
        result['user_agent'] = request.headers.get('User-Agent', 'unknown')
        
        # Send to Splunk
        send_to_splunk(result, "nlp_detailed_analysis", None)
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/process_splunk_search', methods=['POST'])
def process_splunk_search():
    """
    Manually trigger Splunk search and process all results
    """
    try:
        print("Starting Splunk search...")
        
        # 1. Trigger the saved search
        sid = run_splunk_search()
        if not sid:
            return jsonify({"error": "Failed to start Splunk search"}), 500
        
        # 2. Get all results
        results = get_splunk_results(sid)
        if not results:
            return jsonify({"error": "Failed to retrieve search results"}), 500
        
        # 3. Process each result
        analyzed_results = []
        for result in results:
            # Extract search query
            query_text = result.get('SearchQueryText', '')
            if not query_text:
                continue
                
            # Analyze the query
            analysis = analyze_query(query_text)
            
            # Add original Splunk data
            analysis['splunk_data'] = result
            analysis['timestamp'] = datetime.now().isoformat()
            analysis['source'] = 'splunk_rest_api'
            
            # Preserve original _time field for HEC
            original_time = result.get('_time', '')
            if original_time:
                analysis['original_time'] = convert_splunk_iso_to_simple(original_time)
            
            analyzed_results.append(analysis)
            
            # Send to Splunk HEC with original time
            send_to_splunk(analysis, "splunk_rest_analysis", original_time)
        
        return jsonify({
            "message": f"Processed {len(analyzed_results)} search results",
            "results": analyzed_results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/splunk_webhook', methods=['POST'])
def splunk_webhook():
    """
    Webhook endpoint for Splunk to send alerts for analysis.
    Handles both single records and arrays of records from Splunk.
    """
    try:
        data = request.get_json()
        print(f"DEBUG: Received webhook data: {data}")
        print(f"DEBUG: Data type: {type(data)}")
        
        if not data:
            print("DEBUG: No data received")
            return jsonify({"error": "No data received"}), 400
        
        # Handle both single record and array of records
        if isinstance(data, list):
            search_results = data
        elif 'result' in data:
            # Check if result is a list or single dict
            if isinstance(data['result'], list):
                search_results = data['result']
            else:
                # Single record wrapped in result
                search_results = [data['result']]
        else:
            # Single record format from Splunk
            search_results = [data]
        
        if not search_results:
            return jsonify({"error": "No search results found"}), 400
        
        analyzed_results = []
        for result in search_results:
            # Extract the search query - handle different field names
            query_text = (result.get('SearchQueryText') or 
                         result.get('search') or 
                         result.get('query') or 
                         result.get('_raw', ''))
            
            if not query_text:
                continue
                
            # Analyze the query
            analysis = analyze_query(query_text)
            
            # Add original Splunk data
            analysis['splunk_data'] = result
            analysis['timestamp'] = datetime.now().isoformat()
            analysis['source_ip'] = request.remote_addr
            analysis['user_agent'] = request.headers.get('User-Agent', 'unknown')
            
            analyzed_results.append(analysis)
            
            # Extract original time from Splunk data
            original_time = result.get('_time', '')
            
            # Send to Splunk
            send_to_splunk(analysis, "splunk_alert_analysis", original_time)
        
        return jsonify({
            "message": f"Analyzed {len(analyzed_results)} alerts",
            "results": analyzed_results
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/scheduler_status', methods=['GET'])
def scheduler_status():
    """Check scheduler status and next run time"""
    jobs = scheduler.get_jobs()
    job_info = []
    for job in jobs:
        job_info.append({
            "job_id": job.id,
            "name": job.name,
            "next_run_time": str(job.next_run_time) if job.next_run_time else "N/A"
        })
    
    return jsonify({
        "scheduler_running": scheduler.running,
        "jobs": job_info
    })

# --------------------------
# 🔟 Initialize Background Scheduler
# --------------------------
scheduler = BackgroundScheduler()
# Run every 15 minutes at :00, :15, :30, :45
scheduler.add_job(
    scheduled_splunk_pull, 
    'cron', 
    minute='0,15,30,45',
    id='splunk_pull_job',
    name='Automated Splunk REST API Pull'
)
scheduler.start()
print("✅ Background scheduler started - will run every 15 minutes at :00, :15, :30, :45")

# Ensure scheduler shuts down cleanly when Flask stops
atexit.register(lambda: scheduler.shutdown())

if __name__ == "__main__":
    print("Starting NLP Alert Service...")
    print("Available endpoints:")
    print("  GET  /health - Health check")
    print("  POST /analyze - Analyze single query")
    print("  POST /analyze_batch - Analyze multiple queries")
    print("  POST /analyze_detailed - Analyze with multiple term detection")
    print("  POST /process_splunk_search - Pull all results from Splunk REST API (manual)")
    print("  POST /splunk_webhook - Splunk webhook for alerts")
    print("  GET  /scheduler_status - Check scheduler status and next run time")
    print(f"HEC URL: {HEC_URL}")
    print(f"HEC Index: {HEC_INDEX}")
    print(f"Splunk REST URL: {SPLUNK_REST_URL}")
    print(f"Splunk Username: {SPLUNK_USERNAME}")
    print(f"Splunk Search Name: {SPLUNK_SEARCH_NAME}")
    app.run(host='0.0.0.0', port=5000, debug=False)
