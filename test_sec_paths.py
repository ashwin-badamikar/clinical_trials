"""
Test SEC file paths to ensure they're correct.
"""

import os
import sys

# Add the src directory to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from src.data_fetchers.sec_fetcher import SECFetcher

def main():
    """Test SEC file paths."""
    print("Current working directory:", os.getcwd())
    
    # Initialize the SEC fetcher
    sec_fetcher = SECFetcher()
    
    # Create a test filing
    test_filing = {
        "cik": "0001234567",
        "accession_number": "000123456789-00-000000",
        "filing_date": "2025-01-01",
        "form": "10-K"
    }
    
    # Try to save a test filing
    content = f"""
    TEST FILING
    CIK: {test_filing['cik']}
    Accession Number: {test_filing['accession_number']}
    Filing Date: {test_filing['filing_date']}
    Form: {test_filing['form']}
    """
    
    # Save to both 10-K and 8-K directories
    for form_type in ["10-K", "8-K"]:
        test_filing["form"] = form_type
        
        # Call the download method to save the file
        sec_fetcher.download_filing_content(test_filing)
        
        # Verify that the file was created
        if form_type == "10-K":
            save_dir = sec_fetcher.raw_10k_dir
        else:
            save_dir = sec_fetcher.raw_8k_dir
        
        clean_accession = test_filing["accession_number"].replace("-", "")
        filename = f"{test_filing['cik']}_{clean_accession}_{form_type}.txt"
        save_path = os.path.join(save_dir, filename)
        
        if os.path.exists(save_path):
            print(f"✓ Successfully created {form_type} filing at: {save_path}")
        else:
            print(f"✗ Failed to create {form_type} filing at: {save_path}")

if __name__ == "__main__":
    main()