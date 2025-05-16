"""
Financial Modeling Prep API integration for SEC data.
"""

import os
import json
import time
import requests
from datetime import datetime
import sys
from dotenv import load_dotenv

# Add project path to system path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(src_dir)
sys.path.append(project_root)

from src.utils.paths import get_10k_dir, get_8k_dir, get_processed_dir, create_directories

# Load environment variables
load_dotenv()

class FMPSecFetcher:
    """Fetch SEC data using Financial Modeling Prep API."""
    
    BASE_URL = "https://financialmodelingprep.com/api/v3"
    
    def __init__(self, api_key=None):
        """
        Initialize the fetcher.
        
        Args:
            api_key: FMP API key (optional, can be set via env var)
        """
        # Ensure directories exist
        create_directories()
        
        # Set the directories for SEC filings
        self.raw_10k_dir = get_10k_dir()
        self.raw_8k_dir = get_8k_dir()
        self.processed_dir = get_processed_dir()
        
        print(f"10-K filings will be saved to: {self.raw_10k_dir}")
        print(f"8-K filings will be saved to: {self.raw_8k_dir}")
        
        # Get API key from parameter or environment variable
        self.api_key = api_key or os.getenv("FMP_API_KEY")
        
        if not self.api_key:
            print("Warning: No FMP API key provided. Set FMP_API_KEY environment variable.")
        
        # Map of known companies to ticker symbols
        self.known_tickers = {
            "united therapeutics": "UTHR",
            "hoffmann-la roche": "RHHBY",
            "roche": "RHHBY",
            "merck": "MRK",
            "acceleron": "XLRN",  # Now part of Merck
            "glaxosmithkline": "GSK",
            "gsk": "GSK",
            "janssen": "JNJ",  # Part of J&J
            "johnson & johnson": "JNJ",
            "pfizer": "PFE",
            "novartis": "NVS",
            "bristol-myers squibb": "BMY",
            "astrazeneca": "AZN",
            "lilly": "LLY",
            "abbvie": "ABBV",
            "amgen": "AMGN",
            "gilead": "GILD",
            "biogen": "BIIB",
            "vertex": "VRTX"
        }
    
    def get_ticker_for_company(self, company_name):
        """
        Get ticker symbol for a company.
        
        Args:
            company_name: Name of the company
            
        Returns:
            Ticker symbol
        """
        # Check our known mappings first
        company_name_lower = company_name.lower()
        for known_name, ticker in self.known_tickers.items():
            if known_name in company_name_lower:
                print(f"Found ticker {ticker} for {company_name} in known mappings")
                return ticker
        
        # If not found, search using FMP API
        url = f"{self.BASE_URL}/search?query={company_name}&limit=10&apikey={self.api_key}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            data = response.json()
            
            # Find the best match
            best_match = None
            for result in data:
                name = result.get("name", "").lower()
                if company_name_lower in name:
                    best_match = result
                    break
            
            # If no direct match found, use the first result
            if not best_match and data:
                best_match = data[0]
            
            if best_match:
                ticker = best_match.get("symbol")
                print(f"Found ticker {ticker} for {company_name} via API")
                return ticker
                
        except Exception as e:
            print(f"Error searching for ticker of {company_name}: {e}")
        
        print(f"Could not find ticker for {company_name}")
        return None
    
    def get_company_filings(self, company_name, filing_type="10-K", limit=4):
        """
        Get SEC filings for a company.
        
        Args:
            company_name: Name of the company
            filing_type: Type of filing to fetch (10-K, 8-K, etc.)
            limit: Maximum number of filings to return
            
        Returns:
            List of filings with metadata
        """
        # Get ticker for the company
        ticker = self.get_ticker_for_company(company_name)
        
        if not ticker:
            print(f"Cannot fetch filings without ticker for: {company_name}")
            return []
        
        print(f"Getting {filing_type} filings for {ticker} ({company_name})...")
        
        url = f"{self.BASE_URL}/sec_filings/{ticker}?type={filing_type}&apikey={self.api_key}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            filings = response.json()
            
            # Limit the number of filings
            filings = filings[:limit]
            
            # Format the filings to match the expected structure
            formatted_filings = []
            for filing in filings:
                formatted_filing = {
                    "ticker": ticker,
                    "company_name": company_name,
                    "accession_number": filing.get("accessionNumber", ""),
                    "filing_date": filing.get("fillingDate", ""),
                    "form": filing_type,
                    "filing_url": filing.get("finalLink", "")
                }
                
                # Extract CIK if available
                cik = filing.get("cik", "")
                if cik:
                    formatted_filing["cik"] = cik
                
                formatted_filings.append(formatted_filing)
            
            print(f"Found {len(formatted_filings)} {filing_type} filings for {ticker}")
            return formatted_filings
            
        except Exception as e:
            print(f"Error fetching {filing_type} filings for {ticker}: {e}")
            return []
    
    def get_financial_statements(self, company_name):
        """
        Get financial statements for a company.
        
        Args:
            company_name: Name of the company
            
        Returns:
            Financial statements data
        """
        # Get ticker for the company
        ticker = self.get_ticker_for_company(company_name)
        
        if not ticker:
            print(f"Cannot fetch financial statements without ticker for: {company_name}")
            return None
        
        print(f"Getting financial statements for {ticker} ({company_name})...")
        
        # Income statement
        url = f"{self.BASE_URL}/income-statement/{ticker}?apikey={self.api_key}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            income_statement = response.json()
            
            # If we have statements, save them to file
            if income_statement:
                save_path = os.path.join(self.processed_dir, f"{ticker}_income_statement.json")
                with open(save_path, "w") as f:
                    json.dump(income_statement, f, indent=2)
                
                print(f"Saved income statement to {save_path}")
            
            return income_statement
            
        except Exception as e:
            print(f"Error fetching income statement for {ticker}: {e}")
            return None
    
    def get_annual_reports(self, company_name):
        """
        Get annual reports for a company.
        
        Args:
            company_name: Name of the company
            
        Returns:
            Annual reports data
        """
        # Get ticker for the company
        ticker = self.get_ticker_for_company(company_name)
        
        if not ticker:
            print(f"Cannot fetch annual reports without ticker for: {company_name}")
            return None
        
        print(f"Getting annual reports for {ticker} ({company_name})...")
        
        url = f"{self.BASE_URL}/financial-statement-full-as-reported/{ticker}?apikey={self.api_key}"
        
        try:
            response = requests.get(url)
            response.raise_for_status()
            
            reports = response.json()
            
            # If we have reports, save them to file
            if reports:
                save_path = os.path.join(self.processed_dir, f"{ticker}_annual_reports.json")
                with open(save_path, "w") as f:
                    json.dump(reports, f, indent=2)
                
                print(f"Saved annual reports to {save_path}")
            
            return reports
            
        except Exception as e:
            print(f"Error fetching annual reports for {ticker}: {e}")
            return None
    
    def search_data_for_trial(self, data, trial_name, nct_id):
        """
        Search data for mentions of a trial.
        
        Args:
            data: Data to search
            trial_name: Name of the clinical trial
            nct_id: NCT identifier of the trial
            
        Returns:
            Dictionary with search results
        """
        if not data:
            return {
                "total_mentions": 0,
                "name_mentions": 0,
                "nct_mentions": 0,
                "contexts": []
            }
        
        # Convert the data to a string for searching
        content = json.dumps(data).lower()
        trial_name_lower = trial_name.lower()
        nct_id_lower = nct_id.lower()
        
        # Count mentions
        name_mentions = content.count(trial_name_lower)
        nct_mentions = content.count(nct_id_lower)
        
        # Extract contexts
        contexts = []
        
        # For trial name
        if name_mentions > 0:
            pos = content.find(trial_name_lower)
            context_start = max(0, pos - 100)
            context_end = min(len(content), pos + len(trial_name) + 100)
            context = content[context_start:context_end].replace("\n", " ").strip()
            
            contexts.append({
                "matched_term": trial_name,
                "context": context
            })
        
        # For NCT ID
        if nct_mentions > 0:
            pos = content.find(nct_id_lower)
            context_start = max(0, pos - 100)
            context_end = min(len(content), pos + len(nct_id) + 100)
            context = content[context_start:context_end].replace("\n", " ").strip()
            
            contexts.append({
                "matched_term": nct_id,
                "context": context
            })
        
        return {
            "total_mentions": name_mentions + nct_mentions,
            "name_mentions": name_mentions,
            "nct_mentions": nct_mentions,
            "contexts": contexts
        }
    
    def get_filings_mentioning_trial(self, company_name, trial_name, nct_id, filing_types=["10-K", "8-K"], limit_per_type=2):
        """
        Get SEC filings and financial data that might contain information about a clinical trial.
        
        Args:
            company_name: Name of the company
            trial_name: Name of the clinical trial
            nct_id: NCT identifier of the trial
            filing_types: Types of filings to search
            limit_per_type: Maximum number of filings to return per type
            
        Returns:
            Dictionary with filing information and financial data
        """
        results = {}
        
        # Initialize results for each filing type
        for filing_type in filing_types:
            results[filing_type] = []
        
        # Get filings metadata for each type
        for filing_type in filing_types:
            filings = self.get_company_filings(company_name, filing_type=filing_type, limit=limit_per_type)
            
            # Add filings to results
            for filing in filings:
                results[filing_type].append({
                    "ticker": filing.get("ticker", ""),
                    "cik": filing.get("cik", ""),
                    "accession_number": filing.get("accession_number", ""),
                    "filing_date": filing.get("filing_date", ""),
                    "form": filing_type,
                    "filing_url": filing.get("filing_url", "")
                })
        
        # Get financial statements
        financial_statements = self.get_financial_statements(company_name)
        
        # Get annual reports
        annual_reports = self.get_annual_reports(company_name)
        
        # Search financial data for trial mentions
        if financial_statements:
            fin_results = self.search_data_for_trial(financial_statements, trial_name, nct_id)
            if fin_results["total_mentions"] > 0:
                results["financial_statements"] = {
                    "mentions": fin_results,
                    "data": financial_statements[:2]  # Include just a summary
                }
        
        if annual_reports:
            report_results = self.search_data_for_trial(annual_reports, trial_name, nct_id)
            if report_results["total_mentions"] > 0:
                results["annual_reports"] = {
                    "mentions": report_results,
                    "data": annual_reports[:2]  # Include just a summary
                }
        
        # Add a summary of what we found
        total_filings = sum(len(filings) for filing_type, filings in results.items() if filing_type in filing_types)
        results["summary"] = {
            "company": company_name,
            "ticker": self.get_ticker_for_company(company_name),
            "total_filings": total_filings,
            "has_financial_statements": financial_statements is not None,
            "has_annual_reports": annual_reports is not None
        }
        
        return results