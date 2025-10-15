#!/usr/bin/env python3
"""
Splunk Custom Search Command for NLP Analysis
Usage: | nlp_analyze field=<field_name>
"""

import sys
import json
import requests
import urllib3
from splunklib.searchcommands import dispatch, GeneratingCommand, Configuration, Option, validators

# Disable SSL warnings for development
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

@Configuration()
class NlpAnalyzeCommand(GeneratingCommand):
    """Custom Splunk command to analyze text using NLP service"""
    
    field = Option(
        doc='Field containing text to analyze',
        require=True,
        validate=validators.Fieldname()
    )
    
    endpoint = Option(
        doc='NLP service endpoint URL',
        default='http://localhost:5000/analyze'
    )
    
    def generate(self):
        """Generate results for each event"""
        
        # Get the field value from each event
        for event in self.events:
            if self.field in event:
                text_to_analyze = event[self.field]
                
                try:
                    # Call the NLP service
                    response = requests.post(
                        self.endpoint,
                        json={'query': text_to_analyze},
                        timeout=10,
                        verify=False
                    )
                    
                    if response.status_code == 200:
                        analysis = response.json()
                        
                        # Create new event with analysis results
                        new_event = dict(event)
                        new_event['nlp_most_similar_term'] = analysis.get('most_similar_term', '')
                        new_event['nlp_similarity_score'] = analysis.get('similarity_score', 0)
                        new_event['nlp_sentiment_label'] = analysis.get('sentiment_label', '')
                        new_event['nlp_sentiment_score'] = analysis.get('sentiment_score', 0)
                        new_event['nlp_analysis_timestamp'] = analysis.get('timestamp', '')
                        
                        yield new_event
                    else:
                        # Log error but continue processing
                        error_event = dict(event)
                        error_event['nlp_error'] = f"HTTP {response.status_code}: {response.text}"
                        yield error_event
                        
                except Exception as e:
                    # Log error but continue processing
                    error_event = dict(event)
                    error_event['nlp_error'] = str(e)
                    yield error_event
            else:
                # Field not found, pass through original event
                yield event

if __name__ == '__main__':
    dispatch(NlpAnalyzeCommand, sys.argv)
