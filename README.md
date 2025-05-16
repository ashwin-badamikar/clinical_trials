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
- [Sample Output](#sample-output)
- [Technologies Used](#technologies-used)

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
