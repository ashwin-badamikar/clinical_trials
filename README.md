# Clinical Trial & Corporate Disclosure Extraction Pipeline

![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Python](https://img.shields.io/badge/python-3.7+-brightgreen.svg)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-13+-blue.svg)
![Status](https://img.shields.io/badge/status-complete-success.svg)

A comprehensive data pipeline that extracts, processes, and analyzes clinical trial data from ClinicalTrials.gov, SEC filings, and scientific publications. This project focuses on industry-sponsored interventional clinical trials for Pulmonary Arterial Hypertension (PAH) and structures the data into PostgreSQL-compatible objects with rich metadata.

<p align="center">
  <img src="https://ucarecdn.com/a46fb778-5be6-405b-bd93-8ce2a67e5fcd/-/preview/500x500/" width="500" alt="Pipeline Architecture">
</p>

## 📋 Table of Contents

- [Features](#features)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
- [How to Change Indication](#how-to-change-indication)
- [Notes on APIs Used](#notes-on-apis-used)
- [Known Limitations](#known-limitations)
- [Technologies Used](#technologies-used)
- [Sample Output](#sample-output)

## ✨ Features

- **Data Extraction** from multiple sources:
  - ClinicalTrials.gov API for clinical trial data
  - SEC filings (10-K, 8-K) via Financial Modeling Prep API
  - Scientific publications and company presentations via web search

- **Comprehensive Data Processing**:
  - Extraction of key trial metadata (title, ID, indication, intervention, phase, sponsor)
  - Structured representation of study arms and participant information
  - Detailed endpoint and baseline measure extraction with statistical significance

- **Advanced Analysis**:
  - Cross-trial endpoint comparison
  - Treatment effect visualization
  - Baseline characteristic analysis

- **Multiple Output Formats**:
  - Structured JSON compatible with PostgreSQL
  - Interactive visualizations
  - Web-based dashboard

## 🏗 Project Structure

clinicaltrials/
├── config/                  # Configuration files
├── data/                    # Data directory
│   ├── outputs/             # Processed outputs
│   │   ├── json/            # JSON output files
│   │   └── visualizations/  # Generated visualizations
│   ├── processed/           # Intermediate processed data
│   └── raw/                 # Raw data from APIs
├── src/                     # Source code
│   ├── api/                 # FastAPI backend
│   ├── data_fetchers/       # API integration modules
│   │   ├── clinicaltrials_fetcher.py
│   │   ├── sec_fetcher.py
│   │   └── web_fetcher.py
│   ├── data_processors/     # Data processing modules
│   │   ├── trial_processor.py
│   │   ├── endpoint_processor.py
│   │   └── visualization.py
│   ├── database/            # Database models and loading scripts
│   │   ├── models.py
│   │   └── load_data.py
│   ├── streamlit/           # Streamlit dashboard
│   └── utils/               # Utility functions
└── README.md


## 🚀 Setup Instructions

### Prerequisites

- Python 3.7 or higher
- PostgreSQL database server
- API keys for:
  - Financial Modeling Prep API (for SEC filings)
  - Google Search API and Custom Search Engine ID

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/ashwin-badamikar/clinical_trials.git
   cd clinical_trials


2. **Create and activate a virtual environment:**
   ```bash
   # Windows
    python -m venv venv
    venv\Scripts\activate

    # macOS/Linux
    python -m venv venv
    source venv/bin/activate

3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt

4. **Set up environment variables:**
   ```bash
   FMP_API_KEY=your_financial_modeling_prep_api_key
   GOOGLE_SEARCH_API_KEY=your_google_search_api_key
   GOOGLE_SEARCH_ENGINE_ID=your_google_search_engine_id

5. **Configure the database:**
   Update the database connection details in config/config.json:
   ```bash
   {
    "database": {
    "host": "localhost",
    "port": 5433,
    "database": "clinicaltrials",
    "user": "postgres",
    "password": "your_password"
    }
    }

6. **Create the PostgreSQL database:**
   ```bash
   createdb clinicaltrials

# Running the Pipeline #
1. **Run the main data extraction pipeline:**
   ```bash
   python src/main.py

2. **Generate endpoint visualizations:**
   ```bash
   python src/data_processors/endpoint_processor.py

3. **Generate additional visualizations:**
   ```bash
   python src/data_processors/visualization.py

4. **Load data into PostgreSQL:**
   ```bash
   python src/database/load_data.py

## Interactive Components (Optional) ##

1. **Start the FastAPI server:**
   ```bash
   uvicorn src.api.main:app --reload --port 8000

2. **Launch the Streamlit dashboard:**
   ```bash
   streamlit run src/streamlit/app.py

## 🔄 How to Change Indication ##

The pipeline is currently configured to extract data for Pulmonary Arterial Hypertension (PAH) trials, but this can be easily changed:

1. **Open the configuration file:**
   Edit config/config.json and update the "condition" field:

   ```bash
   {
   "clinicaltrials":
    {
    "condition": "Your Medical Condition",
    "sponsor_type": "Industry",
    "study_type": "Interventional",
    "min_start_date": "2015-01-01"
    }
    }
2. **Run the pipeline as normal:**
   ```bash
   python src/main.py

## 🌐 Notes on APIs Used ##

**ClinicalTrials.gov API**
* Purpose: Primary source for clinical trial data
* Base URL: https://clinicaltrials.gov/api/v2/studies
* Authentication: No API key required
* Limitations: Limited results per query, no real-time data
* Documentation: https://clinicaltrials.gov/api/gui/home

**Financial Modeling Prep API**
* Purpose: Access to SEC filings (10-K, 8-K) for public companies
* Base URL: https://financialmodelingprep.com/api/v3
* Authentication: Requires API key
* Limitations: Rate limits based on subscription tier
* Documentation: https://financialmodelingprep.com/developer/docs/

**Google Custom Search API**
* Purpose: Searching for scientific publications and company presentations
* Authentication: Requires API key and Custom Search Engine ID
* Limitations: 100 free searches per day (standard quota)
* Documentation: https://developers.google.com/custom-search/v1/overview

## ⚠️ Known Limitations ##

**Data Availability**
* Real endpoint and baseline data is often not available directly from ClinicalTrials.gov API
* For trials without published results, the pipeline uses literature-based data from similar trials
* Not all trials have associated SEC filings or scientific publications

**API Limitations**
* Financial Modeling Prep API has rate limits and may not have complete data for smaller companies
* Google Search API has daily quotas that may be quickly exhausted when processing many trials
* PDF extraction from scientific publications can be imperfect, especially for complex formatting

**Data Quality**
* Endpoint and baseline measure extraction from publications relies on pattern matching
* Statistical significance information is not consistently available across trials
* Some trials may have inconsistent naming conventions for similar endpoints

## 🔧 Technologies Used ##

* Python 3.7+: Core implementation language
* PostgreSQL: Database for structured storage
* FastAPI: RESTful API for data access
* Streamlit: Interactive data visualization dashboard
* SQLAlchemy: ORM for database interactions
* Pandas/NumPy: Data processing and analysis
* Matplotlib/Seaborn/Plotly: Data visualization
* PyPDF2: PDF text extraction
* Requests: API interaction

## 📊 Sample Output ##

The pipeline generates structured JSON output for each trial, following this format:

```bash
{
  "clinical_study": {
    "title": "Study Title",
    "nct_identifier": "NCT00000000",
    "indication": "Pulmonary Arterial Hypertension",
    "intervention": "Drug Name",
    "interventional_drug": {
      "name": "Drug Name",
      "dose": "10 mg",
      "frequency": "twice daily",
      "formulation": "Tablet"
    },
    "study_arms": {
      "intervention": 1,
      "placebo": 1
    },
    "number_of_participants": 100,
    "average_age": 45.5,
    "age_range": [18, 75],
    "phase": "Phase 3"
  },
  "endpoints": [
    {
      "name": "PVR",
      "description": "Change in pulmonary vascular resistance",
      "timepoint": "Week 16",
      "arm": "intervention",
      "average_value": -30.0,
      "upper_end": -20.0,
      "lower_end": -40.0,
      "statistical_significance": "p<0.001"
    }
  ],
  "baseline_measures": [
    {
      "name": "6MWD",
      "description": "Baseline 6-minute walk distance",
      "arm": "intervention",
      "average_value": 360.0,
      "upper_end": 375.0,
      "lower_end": 345.0
    }
  ]
}


