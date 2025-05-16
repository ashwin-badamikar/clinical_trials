"""
Web Search and PDF Extraction (Modified for Real Data Only).

This module handles searching for scientific publications and company presentations
related to clinical trials, downloading PDFs, and extracting text from them.
Simulated data fallbacks have been removed.
"""

import os
import json
import time
import requests
from tqdm import tqdm
import re
from googleapiclient.discovery import build
from PyPDF2 import PdfReader
from io import BytesIO
import urllib.parse
import sys
import random

# Add project path to system path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(src_dir)
sys.path.append(project_root)

from src.utils.paths import get_publications_dir, create_directories

class WebSearcher:
    """Search for scientific publications and company presentations."""
    
    def __init__(self, api_key=None, search_engine_id=None):
        """
        Initialize the searcher.
        
        Args:
            api_key: Google Custom Search API key
            search_engine_id: Google Custom Search engine ID
        """
        self.api_key = api_key or os.getenv("GOOGLE_SEARCH_API_KEY")
        self.search_engine_id = search_engine_id or os.getenv("GOOGLE_SEARCH_ENGINE_ID")
        
        # Ensure directories exist
        create_directories()
        
        # Set the publications directory
        self.publications_dir = get_publications_dir()
        
        print(f"Publications will be saved to: {self.publications_dir}")
        
        # Create the publications directory if it doesn't exist
        if not os.path.exists(self.publications_dir):
            print(f"Creating publications directory: {self.publications_dir}")
            os.makedirs(self.publications_dir, exist_ok=True)
        
        # Verify the directory exists
        if os.path.exists(self.publications_dir):
            print(f"Publications directory exists: {self.publications_dir}")
        else:
            print(f"WARNING: Failed to create publications directory: {self.publications_dir}")
    
    def search_for_publications(self, trial_name, nct_id, sponsor, limit=5):
        """
        Search for scientific publications about a clinical trial with expanded search.
        
        Args:
            trial_name: Name of the clinical trial
            nct_id: NCT identifier of the trial
            sponsor: Name of the sponsor
            limit: Maximum number of results to return
            
        Returns:
            List of publication information
        """
        if not self.api_key or not self.search_engine_id:
            print("Google Search API key or engine ID not provided. Cannot search for publications.")
            return []
        
        # Create broader search queries
        queries = [
            f'"{nct_id}" pulmonary arterial hypertension "results"',
            f'"{trial_name}" pulmonary arterial hypertension {sponsor} "results"',
            f'pulmonary arterial hypertension {sponsor} clinical trial results',
            f'pulmonary hypertension treatment {sponsor} outcome',
            f'{nct_id} OR "{trial_name}" site:pubmed.ncbi.nlm.nih.gov'
        ]
        
        all_publications = []
        
        for query in queries:
            try:
                # Create a service object for the Custom Search API
                service = build("customsearch", "v1", developerKey=self.api_key)
                
                # Execute the search
                result = service.cse().list(
                    q=query,
                    cx=self.search_engine_id,
                    num=limit
                ).execute()
                
                # Extract publication information
                if "items" in result:
                    for item in result["items"]:
                        # Skip if we already have this publication
                        if any(pub.get("link") == item.get("link") for pub in all_publications):
                            continue
                        
                        # Extract authors and journal from the snippet if available
                        snippet = item.get("snippet", "")
                        authors = ""
                        journal = ""
                        
                        # Try to extract authors (typically appears as "Author1, Author2, ... - Journal")
                        author_journal_match = re.search(r'([A-Za-z\s,]+)-\s*([^-]+)', snippet)
                        if author_journal_match:
                            authors = author_journal_match.group(1).strip()
                            journal = author_journal_match.group(2).strip()
                        
                        all_publications.append({
                            "title": item.get("title", ""),
                            "link": item.get("link", ""),
                            "snippet": snippet,
                            "authors": authors,
                            "journal": journal,
                            "source": "scientific_publication"
                        })
                        
                # Don't overwhelm the API
                time.sleep(1)
                
            except Exception as e:
                print(f"Error searching for publications with query '{query}': {e}")
        
        print(f"Found {len(all_publications)} scientific publications across all search queries")
        return all_publications[:limit]  # Return the top publications up to the limit
    
    def search_for_company_presentations(self, trial_name, nct_id, company_website, limit=3):
        """
        Search for company presentations about a clinical trial.
        
        Args:
            trial_name: Name of the clinical trial
            nct_id: NCT identifier of the trial
            company_website: Company website domain
            limit: Maximum number of results to return
            
        Returns:
            List of presentation information
        """
        if not self.api_key or not self.search_engine_id:
            print("Google Search API key or engine ID not provided. Cannot search for company presentations.")
            return []
        
        # Clean up the company website to just the domain
        if company_website.startswith("http"):
            domain = urllib.parse.urlparse(company_website).netloc
        else:
            domain = company_website
        
        # Create broader search queries
        queries = [
            f'"{nct_id}" OR "{trial_name}" "pulmonary arterial hypertension" filetype:pdf site:{domain}',
            f'clinical trial results filetype:pdf site:{domain}',
            f'investor presentation pulmonary hypertension filetype:pdf site:{domain}',
            f'annual report clinical trial filetype:pdf site:{domain}'
        ]
        
        all_presentations = []
        
        for query in queries:
            try:
                # Create a service object for the Custom Search API
                service = build("customsearch", "v1", developerKey=self.api_key)
                
                # Execute the search
                result = service.cse().list(
                    q=query,
                    cx=self.search_engine_id,
                    num=limit
                ).execute()
                
                # Extract presentation information
                if "items" in result:
                    for item in result["items"]:
                        # Skip duplicates
                        if any(pres.get("link") == item.get("link") for pres in all_presentations):
                            continue
                            
                        all_presentations.append({
                            "title": item.get("title", ""),
                            "link": item.get("link", ""),
                            "snippet": item.get("snippet", ""),
                            "source": "company_presentation"
                        })
                
                # Don't overwhelm the API
                time.sleep(1)
                
            except Exception as e:
                print(f"Error searching for company presentations with query '{query}': {e}")
        
        print(f"Found {len(all_presentations)} company presentations across all search queries")
        return all_presentations[:limit]  # Return the top presentations up to the limit
    
    def download_pdf(self, url, save_path):
        """
        Download a PDF file.
        
        Args:
            url: URL of the PDF
            save_path: Path to save the PDF
            
        Returns:
            Path to the saved PDF or None if download fails
        """
        try:
            print(f"Downloading PDF from URL: {url}")
            print(f"Saving to path: {save_path}")
            
            # Make sure the directory exists
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Check if file already exists
            if os.path.exists(save_path):
                print(f"File already exists, using cached version: {save_path}")
                return save_path
            
            # Get the PDF content
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(url, stream=True, headers=headers, timeout=30)
            response.raise_for_status()
            
            # Save the PDF
            with open(save_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:  # filter out keep-alive new chunks
                        f.write(chunk)
            
            print(f"Successfully downloaded PDF: {save_path}")
            
            # Verify the file was created
            if os.path.exists(save_path) and os.path.getsize(save_path) > 0:
                print(f"Verified file exists: {save_path}")
                return save_path
            else:
                print(f"Warning: File was not created or is empty: {save_path}")
                return None
                
        except requests.exceptions.RequestException as e:
            print(f"Error downloading PDF {url}: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error downloading PDF {url}: {e}")
            return None
    
    def extract_text_from_pdf(self, pdf_path):
        """
        Extract text from a PDF file with enhanced extraction for clinical trial results.
        
        Args:
            pdf_path: Path to the PDF file
            
        Returns:
            Extracted text
        """
        try:
            # Check if this is a real PDF or a text file
            if pdf_path.endswith(".pdf"):
                try:
                    with open(pdf_path, "rb") as f:
                        reader = PdfReader(f)
                        text = ""
                        
                        # Process each page
                        for page in reader.pages:
                            page_text = page.extract_text()
                            if page_text:
                                text += page_text + "\n"
                    
                    # Clean up the extracted text
                    text = self._clean_extracted_text(text)
                    return text
                except Exception as e:
                    print(f"Error extracting text from PDF {pdf_path}: {e}")
                    # For non-PDF files or errors, read as text
                    with open(pdf_path, "r", encoding="utf-8", errors="ignore") as f:
                        return f.read()
            else:
                # For non-PDF files, read as text
                with open(pdf_path, "r", encoding="utf-8", errors="ignore") as f:
                    return f.read()
                    
        except Exception as e:
            print(f"Error extracting text from file {pdf_path}: {e}")
            return f"Error extracting text: {str(e)}"
    
    def _clean_extracted_text(self, text):
        """
        Clean up extracted text to improve readability and parsing.
        
        Args:
            text: Raw extracted text
            
        Returns:
            Cleaned text
        """
        # Replace multiple spaces with a single space
        text = re.sub(r'\s+', ' ', text)
        
        # Remove page numbers and headers/footers (common patterns)
        text = re.sub(r'\n\s*\d+\s*\n', '\n', text)
        
        # Replace unusual Unicode characters with their ASCII equivalents
        text = text.replace('–', '-').replace('—', '-').replace(''', "'").replace(''', "'")
        text = text.replace('"', '"').replace('"', '"').replace('•', '*')
        
        # Make sure paragraph breaks are preserved
        text = re.sub(r'\n\s*\n', '\n\n', text)
        
        # Special handling for clinical trial results
        # Look for results sections
        results_section = re.search(r'(?:results|findings|outcomes).*?(?:discussion|conclusion)', text, re.IGNORECASE | re.DOTALL)
        if results_section:
            # Extract the results section for special processing
            results_text = results_section.group(0)
            
            # Look for tables (often have characteristic patterns in PDFs)
            tables = re.findall(r'(?:Table \d+[\.\:].*?)\n\n', results_text, re.IGNORECASE | re.DOTALL)
            
            # Enhanced processing for tables could be added here
            
            # Add markers to help with extraction
            for i, table in enumerate(tables):
                # Add marker to indicate this is tabular data
                marked_table = f"\n\nTABLE_START\n{table}\nTABLE_END\n\n"
                text = text.replace(table, marked_table)
        
        # Look for endpoints specifically
        endpoints = ["PVR", "6MWD", "NT-proBNP", "WHO FC", "CI"]
        for endpoint in endpoints:
            # Add markers around mentions of important endpoints
            pattern = f"({endpoint}(?:.*?(?:\\d+[\\.,]\\d*).*?)(?:\\.|\\n))"
            text = re.sub(pattern, f"\nENDPOINT_{endpoint}: \\1\n", text, flags=re.IGNORECASE)
        
        return text
    
    def fetch_publication_content(self, publications):
        """
        Fetch and extract text from publication URLs.
        
        Args:
            publications: List of publication information
            
        Returns:
            List of publications with extracted text
        """
        enhanced_publications = []
        
        for pub in publications:
            url = pub.get("link")
            
            if not url:
                enhanced_publications.append(pub)
                continue
            
            try:
                # Skip if not an HTML page or PDF
                if not url.endswith('.html') and not url.endswith('.htm') and not url.endswith('.pdf') and 'pdf' not in url:
                    enhanced_publications.append(pub)
                    continue
                    
                # For PDFs, download and extract
                if url.endswith('.pdf') or 'pdf' in url:
                    # Create a safe filename
                    safe_title = re.sub(r'[^\w\-_\. ]', '_', pub.get("title", "Untitled"))[:50]
                    filename = f"{safe_title}.pdf"
                    save_path = os.path.join(self.publications_dir, filename)
                    
                    # Download the PDF
                    pdf_path = self.download_pdf(url, save_path)
                    
                    if pdf_path:
                        # Extract text
                        try:
                            text = self.extract_text_from_pdf(pdf_path)
                            pub["full_text"] = text
                            pub["text_length"] = len(text)
                            print(f"Successfully extracted {len(text)} characters from PDF: {url}")
                        except Exception as e:
                            print(f"Error extracting text from PDF {url}: {e}")
                else:
                    # For HTML pages, use requests
                    headers = {
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
                    }
                    response = requests.get(url, headers=headers, timeout=30)
                    response.raise_for_status()
                    
                    # Extract text from HTML (this is very simplified - consider using a proper HTML parser)
                    content = response.text
                    
                    # Basic HTML tag removal
                    content = re.sub(r'<[^>]+>', ' ', content)
                    content = re.sub(r'\s+', ' ', content).strip()
                    
                    pub["full_text"] = content
                    pub["text_length"] = len(content)
                    print(f"Successfully extracted {len(content)} characters from HTML: {url}")
                    
                enhanced_publications.append(pub)
                    
            except Exception as e:
                print(f"Error fetching content from {url}: {e}")
                enhanced_publications.append(pub)
        
        return enhanced_publications
    
    def find_and_download_presentations(self, trial_name, nct_id, company_name, company_website, limit=3):
        """
        Find and download company presentations about a clinical trial.
        
        Args:
            trial_name: Name of the clinical trial
            nct_id: NCT identifier of the trial
            company_name: Name of the company
            company_website: Company website domain
            limit: Maximum number of presentations to download
            
        Returns:
            List of downloaded presentation information
        """
        # Search for presentations
        presentations = self.search_for_company_presentations(trial_name, nct_id, company_website, limit=limit)
        
        downloaded_presentations = []
        
        for i, presentation in enumerate(presentations):
            # Create a safe filename
            safe_title = re.sub(r'[^\w\-_\. ]', '_', presentation["title"])[:50]
            filename = f"{nct_id}_{company_name.replace(' ', '_')}_{i}_{safe_title}.pdf"
            save_path = os.path.join(self.publications_dir, filename)
            
            # Try to download the PDF
            pdf_path = self.download_pdf(presentation["link"], save_path)
            
            if pdf_path:
                # Extract text
                try:
                    text = self.extract_text_from_pdf(pdf_path)
                except:
                    # If text extraction fails, create a placeholder text
                    text = "Error: Could not extract text from PDF"
                
                downloaded_presentations.append({
                    "title": presentation["title"],
                    "url": presentation["link"],
                    "local_path": pdf_path,
                    "text_length": len(text),
                    "text_sample": text[:2000] + "..." if len(text) > 2000 else text,  # Increased text sample size
                    "source": "company_presentation"
                })
            else:
                # If download fails, just include metadata
                downloaded_presentations.append({
                    "title": presentation["title"],
                    "url": presentation.get("link", ""),
                    "snippet": presentation.get("snippet", ""),
                    "source": "company_presentation (metadata only)"
                })
        
        return downloaded_presentations
    
    def extract_clinical_data_from_publications(self, publications, keywords=None):
        """
        Extract clinical trial data from publications and presentations.
        
        Args:
            publications: List of publications and presentations
            keywords: List of keywords to look for
            
        Returns:
            Extracted clinical data
        """
        if not keywords:
            keywords = ["PVR", "6MWD", "NT-proBNP", "WHO FC", "baseline", "endpoint", 
                        "pulmonary vascular resistance", "6-minute walk", "brain natriuretic peptide",
                        "functional class", "p<", "p =", "statistically significant"]
        
        extracted_data = {
            "endpoints": [],
            "baseline_measures": [],
            "other_findings": []
        }
        
        # Process scientific publications
        for pub in publications.get("scientific_publications", []):
            snippet = pub.get("snippet", "")
            if not snippet:
                continue
            
            # Check for presence of keywords
            for keyword in keywords:
                if keyword.lower() in snippet.lower():
                    # Extract context around the keyword
                    keyword_pos = snippet.lower().find(keyword.lower())
                    context_start = max(0, keyword_pos - 100)
                    context_end = min(len(snippet), keyword_pos + len(keyword) + 100)
                    context = snippet[context_start:context_end]
                    
                    # Determine if it's an endpoint or baseline measure
                    if any(term in context.lower() for term in ["endpoint", "outcome", "result", "change", "improvement"]):
                        extracted_data["endpoints"].append({
                            "keyword": keyword,
                            "context": context,
                            "source": f"Scientific publication: {pub.get('title', '')}"
                        })
                    elif any(term in context.lower() for term in ["baseline", "characteristic", "initial"]):
                        extracted_data["baseline_measures"].append({
                            "keyword": keyword,
                            "context": context,
                            "source": f"Scientific publication: {pub.get('title', '')}"
                        })
                    else:
                        extracted_data["other_findings"].append({
                            "keyword": keyword,
                            "context": context,
                            "source": f"Scientific publication: {pub.get('title', '')}"
                        })
        
        # Process company presentations - these have more complete text
        for presentation in publications.get("company_presentations", []):
            text_sample = presentation.get("text_sample", "")
            if not text_sample:
                continue
            
            # Check for presence of keywords
            for keyword in keywords:
                # Find all occurrences of the keyword
                for match in re.finditer(re.escape(keyword), text_sample, re.IGNORECASE):
                    pos = match.start()
                    context_start = max(0, pos - 150)
                    context_end = min(len(text_sample), pos + len(keyword) + 150)
                    context = text_sample[context_start:context_end]
                    
                    # Determine if it's an endpoint or baseline measure
                    if any(term in context.lower() for term in ["endpoint", "outcome", "result", "change", "improvement"]):
                        extracted_data["endpoints"].append({
                            "keyword": keyword,
                            "context": context,
                            "source": f"Company presentation: {presentation.get('title', '')}"
                        })
                    elif any(term in context.lower() for term in ["baseline", "characteristic", "initial"]):
                        extracted_data["baseline_measures"].append({
                            "keyword": keyword,
                            "context": context,
                            "source": f"Company presentation: {presentation.get('title', '')}"
                        })
                    else:
                        extracted_data["other_findings"].append({
                            "keyword": keyword,
                            "context": context,
                            "source": f"Company presentation: {presentation.get('title', '')}"
                        })
        
        return extracted_data
    
    def find_publications_for_trial(self, trial_name, nct_id, sponsor, company_website, publication_limit=5, presentation_limit=3):
        """
        Find scientific publications and company presentations for a clinical trial.
        
        Args:
            trial_name: Name of the clinical trial
            nct_id: NCT identifier of the trial
            sponsor: Name of the sponsor
            company_website: Company website domain
            publication_limit: Maximum number of publications to return
            presentation_limit: Maximum number of presentations to download
            
        Returns:
            Dictionary with publication and presentation information
        """
        results = {
            "scientific_publications": [],
            "company_presentations": []
        }
        
        # Search for scientific publications with expanded search
        publications = self.search_for_publications(trial_name, nct_id, sponsor, limit=publication_limit)
        
        # Fetch full content where possible
        publications = self.fetch_publication_content(publications)
        results["scientific_publications"] = publications
        
        # Find and download company presentations with broader search
        presentations = self.find_and_download_presentations(trial_name, nct_id, sponsor, company_website, limit=presentation_limit)
        results["company_presentations"] = presentations
        
        # Try to extract clinical data from publications and presentations
        clinical_data = self.extract_clinical_data_from_publications(results)
        if clinical_data and (clinical_data["endpoints"] or clinical_data["baseline_measures"]):
            results["extracted_clinical_data"] = clinical_data
            print(f"Found {len(clinical_data['endpoints'])} endpoint mentions and {len(clinical_data['baseline_measures'])} baseline measure mentions")
        
        return results