"""
Main entry point for the Clinical Trial & Corporate Disclosure Extraction Pipeline.
Using Financial Modeling Prep API for SEC data.
"""

import os
import json
import sys
import re
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the project path to the system path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.append(project_root)

from src.data_fetchers.clinicaltrials_fetcher import ClinicalTrialsFetcher
from src.data_fetchers.sec_fetcher import FMPSecFetcher
from src.data_fetchers.web_fetcher import WebSearcher
from src.data_processors.trial_processor import TrialProcessor
from src.utils.paths import get_json_dir, create_directories

# Company website domains for the sponsors we've identified
COMPANY_DOMAINS = {
    "United Therapeutics": "unither.com",
    "Hoffmann-La Roche": "roche.com",
    "Acceleron Pharma": "acceleronpharma.com",
    "Merck": "merck.com",
    "Janssen": "janssen.com",
    "GlaxoSmithKline": "gsk.com",
    "Bayer": "bayer.com"
}

def get_company_domain(sponsor_name):
    """Get the company website domain for a sponsor."""
    for company, domain in COMPANY_DOMAINS.items():
        if company.lower() in sponsor_name.lower():
            return domain
    
    # Default to company name + .com
    simplified_name = sponsor_name.split(',')[0].split('(')[0].strip().lower()
    simplified_name = re.sub(r'[^\w]', '', simplified_name)
    return f"{simplified_name}.com"

def load_config():
    """Load configuration from config file."""
    config_path = os.path.join(project_root, "config", "config.json")
    try:
        with open(config_path, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        print(f"Warning: Could not load config from {config_path}. Using default values.")
        return {
            "clinicaltrials": {
                "condition": "Pulmonary Arterial Hypertension",
                "sponsor_type": "Industry",
                "study_type": "Interventional",
                "min_start_date": "2015-01-01"
            }
        }

def main():
    """Main entry point for the pipeline."""
    # Ensure directories exist
    create_directories()
    
    # Load configuration
    config = load_config()
    
    # Initialize the fetchers
    ct_fetcher = ClinicalTrialsFetcher()
    
    # Get FMP API key from environment variables
    fmp_api_key = os.getenv("FMP_API_KEY")
    
    if not fmp_api_key:
        print("Warning: FMP_API_KEY not found in environment variables. SEC data will be limited.")
    
    # Initialize FMP SEC fetcher
    sec_fetcher = FMPSecFetcher(api_key=fmp_api_key)
    
    # Get Google Search API credentials from environment variables
    google_api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
    google_search_engine_id = os.getenv("GOOGLE_SEARCH_ENGINE_ID")
    
    if not google_api_key or not google_search_engine_id:
        print("Warning: Google Search API credentials not set. Publication data may be limited.")
    
    # Initialize web searcher
    web_searcher = WebSearcher(
        api_key=google_api_key,
        search_engine_id=google_search_engine_id
    )
    
    # Initialize trial processor
    trial_processor = TrialProcessor()
    
    # Get trials by public companies
    condition = config.get("clinicaltrials", {}).get("condition", "Pulmonary Arterial Hypertension")
    trials = ct_fetcher.get_public_company_trials(condition=condition, limit=5)

    trials = trials[:5]  # Strictly limit to 5 trials
    
    print(f"\nRetrieved {len(trials)} public company {condition} trials.")
    
    # Process each trial
    for i, trial in enumerate(trials, 1):
        # Extract basic metadata
        metadata = ct_fetcher.extract_key_metadata(trial)
        
        print(f"\n{i}. Processing trial: {metadata['nct_identifier']} - {metadata['title']}")
        print(f"   Sponsor: {metadata['sponsor']}")
        
        # Create output directory for this trial
        json_dir = get_json_dir()
        os.makedirs(json_dir, exist_ok=True)
        
        # Get company domain for the sponsor
        company_domain = get_company_domain(metadata['sponsor'])
        
        # Fetch SEC filings and financial data for the sponsor
        print(f"\n   Fetching SEC filings and financial data for {metadata['sponsor']}...")
        sec_data = sec_fetcher.get_filings_mentioning_trial(
            company_name=metadata['sponsor'],
            trial_name=metadata['title'],
            nct_id=metadata['nct_identifier'],
            filing_types=["10-K", "8-K"],
            limit_per_type=3  # Increased from 2
        )
        
        # Fetch scientific publications and company presentations with expanded search
        print(f"\n   Searching for publications and presentations for {metadata['title']}...")
        publications = web_searcher.find_publications_for_trial(
            trial_name=metadata['title'],
            nct_id=metadata['nct_identifier'],
            sponsor=metadata['sponsor'],
            company_website=company_domain,
            publication_limit=5,  # Increased from 3
            presentation_limit=3  # Increased from 2
        )
        
        # Fetch full content for publications
        if publications.get("scientific_publications"):
            print(f"   Fetching full content for {len(publications['scientific_publications'])} publications...")
            publications["scientific_publications"] = web_searcher.fetch_publication_content(
                publications["scientific_publications"]
            )
        
        # Process and save the trial data
        trial_processor.process_and_save_trial(
            trial_data=trial,
            sec_filings=sec_data,
            publications=publications
        )
        
        print(f"   Saved trial data for {metadata['nct_identifier']}")
    
    print("\nCompleted processing all trials.")
    print("\nNext steps:")
    print("1. Run src/data_processors/endpoint_processor.py to generate endpoint visualizations")
    print("2. Run src/data_processors/visualization.py to generate additional visualizations")
    print("3. Run src/database/load_data.py to load the data into PostgreSQL")

if __name__ == "__main__":
    main()