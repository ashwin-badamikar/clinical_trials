"""
Path utilities for the Clinical Trial & Corporate Disclosure Extraction Pipeline.
"""

import os
import sys
from pathlib import Path

# Get the project root directory
def get_project_root():
    """Get the absolute path to the project root directory."""
    # Get the directory of this file
    current_file = os.path.abspath(__file__)
    # Go up two levels: utils -> src -> project_root
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_file)))
    return project_root

# Define paths for various data directories
def get_data_dir():
    """Get the path to the data directory."""
    return os.path.join(get_project_root(), "data")

def get_raw_dir():
    """Get the path to the raw data directory."""
    return os.path.join(get_data_dir(), "raw")

def get_processed_dir():
    """Get the path to the processed data directory."""
    return os.path.join(get_data_dir(), "processed")

def get_outputs_dir():
    """Get the path to the outputs directory."""
    return os.path.join(get_data_dir(), "outputs")

def get_json_dir():
    """Get the path to the JSON output directory."""
    return os.path.join(get_outputs_dir(), "json")

def get_visualizations_dir():
    """Get the path to the visualizations directory."""
    return os.path.join(get_outputs_dir(), "visualizations")

def get_clinical_trials_dir():
    """Get the path to the clinical trials raw data directory."""
    return os.path.join(get_raw_dir(), "clinical_trials")

def get_sec_filings_dir():
    """Get the path to the SEC filings raw data directory."""
    return os.path.join(get_raw_dir(), "sec_filings")

def get_publications_dir():
    """Get the path to the publications raw data directory."""
    return os.path.join(get_raw_dir(), "publications")

def get_10k_dir():
    """Get the path to the 10-K filings directory."""
    return os.path.join(get_sec_filings_dir(), "10k")

def get_8k_dir():
    """Get the path to the 8-K filings directory."""
    return os.path.join(get_sec_filings_dir(), "8k")

# Create all required directories
def create_directories():
    """Create all required directories for the project."""
    directories = [
        get_data_dir(),
        get_raw_dir(),
        get_processed_dir(),
        get_outputs_dir(),
        get_json_dir(),
        get_visualizations_dir(),
        get_clinical_trials_dir(),
        get_sec_filings_dir(),
        get_publications_dir(),
        get_10k_dir(),
        get_8k_dir()
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

# Create a script to verify all paths
def print_all_paths():
    """Print all project paths for verification."""
    print("Project root:", get_project_root())
    print("Data directory:", get_data_dir())
    print("Raw data directory:", get_raw_dir())
    print("Processed data directory:", get_processed_dir())
    print("Outputs directory:", get_outputs_dir())
    print("JSON directory:", get_json_dir())
    print("Visualizations directory:", get_visualizations_dir())
    print("Clinical trials directory:", get_clinical_trials_dir())
    print("SEC filings directory:", get_sec_filings_dir())
    print("Publications directory:", get_publications_dir())
    print("10-K filings directory:", get_10k_dir())
    print("8-K filings directory:", get_8k_dir())

if __name__ == "__main__":
    # Create all directories when run directly
    create_directories()
    print_all_paths()