"""
Test SEC scraper to ensure it can retrieve real filings.
"""

import os
import sys

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.data_fetchers.sec_fetcher import SECFetcher

def main():
    """Test the SEC scraper with a real company."""
    print("Testing SEC scraper...")
    
    # Initialize the SEC fetcher
    sec_fetcher = SECFetcher()
    
    # Test with a well-known company
    company_name = "United Therapeutics"
    
    # Get CIK
    cik = sec_fetcher.get_cik_number(company_name)
    if not cik:
        print("Failed to get CIK")
        return
    
    print(f"Found CIK for {company_name}: {cik}")
    
    # Get filings
    filings = sec_fetcher.get_company_filings(cik, filing_type="10-K", limit=2)
    
    if not filings:
        print("Failed to get filings")
        return
    
    print(f"Found {len(filings)} 10-K filings")
    
    # Download the first filing
    if filings:
        filing = filings[0]
        content = sec_fetcher.download_filing_content(filing)
        
        # Check if it's a real filing
        if "This is a simulated filing" in content:
            print("Warning: Downloaded a simulated filing, not a real one")
        else:
            print("Success! Downloaded a real SEC filing")
            
            # Save a sample
            sample_path = os.path.join(current_dir, "sec_filing_sample.txt")
            with open(sample_path, "w", encoding="utf-8") as f:
                f.write(content[:1000])  # Save first 1000 characters
            
            print(f"Saved a sample of the filing to {sample_path}")

if __name__ == "__main__":
    main()