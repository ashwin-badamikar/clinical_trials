"""
Load JSON data into PostgreSQL database.
"""

import os
import json
import sys
from pathlib import Path
import argparse

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.append(project_root)

from src.database.models import Base, ClinicalStudy, Endpoint, BaselineMeasure, SECFiling, Publication
from src.database import get_engine, get_session

def load_config():
    """Load database configuration from config file."""
    config_path = os.path.join(project_root, "config", "config.json")
    with open(config_path, "r") as f:
        config = json.load(f)
    return config["database"]

def drop_tables(engine):
    """Drop all tables from the database."""
    Base.metadata.drop_all(engine)
    print("Dropped existing tables.")

def create_tables(engine):
    """Create database tables."""
    Base.metadata.create_all(engine)
    print("Database tables created.")

def load_json_data(json_dir, session):
    """
    Load all JSON files from a directory into the database.
    
    Args:
        json_dir: Directory containing JSON files
        session: SQLAlchemy session
    """
    json_files = [f for f in os.listdir(json_dir) if f.endswith('.json') and f.startswith('NCT')]
    
    for json_file in json_files:
        file_path = os.path.join(json_dir, json_file)
        
        print(f"Processing {json_file}...")
        
        with open(file_path, 'r') as f:
            data = json.load(f)
        
        # Extract clinical study data
        process_clinical_study(data, session)
    
    # Commit all changes
    session.commit()
    print("All data loaded successfully.")

def process_clinical_study(data, session):
    """
    Process clinical study data and insert into database.
    
    Args:
        data: Clinical study data dictionary
        session: SQLAlchemy session
    """
    clinical_study_data = data.get("clinical_study", {})
    
    # Check if this study already exists
    existing_study = session.query(ClinicalStudy).filter_by(
        nct_identifier=clinical_study_data.get("nct_identifier")
    ).first()
    
    if existing_study:
        print(f"Study {clinical_study_data.get('nct_identifier')} already exists. Skipping.")
        return
    
    # Create clinical study record
    study = ClinicalStudy(
        title=clinical_study_data.get("title"),
        nct_identifier=clinical_study_data.get("nct_identifier"),
        indication=clinical_study_data.get("indication"),
        intervention=clinical_study_data.get("intervention"),
        
        # Intervention details
        interventional_drug_name=clinical_study_data.get("interventional_drug", {}).get("name"),
        interventional_drug_dose=clinical_study_data.get("interventional_drug", {}).get("dose"),
        interventional_drug_frequency=clinical_study_data.get("interventional_drug", {}).get("frequency"),
        interventional_drug_formulation=clinical_study_data.get("interventional_drug", {}).get("formulation"),
        
        # Study arms
        intervention_arms=clinical_study_data.get("study_arms", {}).get("intervention", 0),
        placebo_arms=clinical_study_data.get("study_arms", {}).get("placebo", 0),
        
        # Participant information
        number_of_participants=clinical_study_data.get("number_of_participants", 0),
        average_age=clinical_study_data.get("average_age", 0),
        min_age=clinical_study_data.get("age_range", [0, 0])[0] if isinstance(clinical_study_data.get("age_range"), list) else 0,
        max_age=clinical_study_data.get("age_range", [0, 0])[1] if isinstance(clinical_study_data.get("age_range"), list) else 0,
        
        # Phase
        phase=clinical_study_data.get("phase"),
        
        # Sponsor
        sponsor=clinical_study_data.get("sponsor")
    )
    
    session.add(study)
    session.flush()  # Get the ID for relationships
    
    # Process endpoints
    endpoints_data = data.get("endpoints", [])
    for endpoint_data in endpoints_data:
        endpoint = Endpoint(
            clinical_study_id=study.id,
            name=endpoint_data.get("name"),
            description=endpoint_data.get("description"),
            timepoint=endpoint_data.get("timepoint"),
            arm=endpoint_data.get("arm"),
            average_value=endpoint_data.get("average_value"),
            upper_end=endpoint_data.get("upper_end"),
            lower_end=endpoint_data.get("lower_end"),
            statistical_significance=endpoint_data.get("statistical_significance")
        )
        session.add(endpoint)
    
    # Process baseline measures
    baseline_data = data.get("baseline_measures", [])
    for baseline_measure_data in baseline_data:
        baseline_measure = BaselineMeasure(
            clinical_study_id=study.id,
            name=baseline_measure_data.get("name"),
            description=baseline_measure_data.get("description"),
            arm=baseline_measure_data.get("arm"),
            average_value=baseline_measure_data.get("average_value"),
            upper_end=baseline_measure_data.get("upper_end"),
            lower_end=baseline_measure_data.get("lower_end")
        )
        session.add(baseline_measure)
    
    # Process SEC filings
    sec_filings_data = data.get("sec_filings", {})
    for form_type, filings in sec_filings_data.items():
        for filing_data in filings:
            try:
                filing = SECFiling(
                    clinical_study_id=study.id,
                    cik=filing_data.get("cik"),
                    accession_number=filing_data.get("accession_number"),
                    filing_date=filing_data.get("filing_date"),
                    form_type=filing_data.get("form", form_type),
                    total_mentions=filing_data.get("total_mentions", 0),
                    name_mentions=filing_data.get("name_mentions", 0),
                    nct_mentions=filing_data.get("nct_mentions", 0),
                    contexts=filing_data.get("contexts", [])
                )
                session.add(filing)
            except Exception as e:
                print(f"Error adding SEC filing: {e}")
                print(f"Filing data: {filing_data}")
    
    # Process publications
    publications_data = data.get("publications", {})
    
    # Scientific publications
    for pub_data in publications_data.get("scientific_publications", []):
        try:
            publication = Publication(
                clinical_study_id=study.id,
                title=pub_data.get("title"),
                link=pub_data.get("link"),
                snippet=pub_data.get("snippet"),
                source="scientific_publication",
                authors=pub_data.get("authors"),
                journal=pub_data.get("journal")
            )
            session.add(publication)
        except Exception as e:
            print(f"Error adding scientific publication: {e}")
            print(f"Publication data: {pub_data}")
    
    # Company presentations
    for pres_data in publications_data.get("company_presentations", []):
        try:
            presentation = Publication(
                clinical_study_id=study.id,
                title=pres_data.get("title"),
                link=pres_data.get("url", pres_data.get("link")),
                snippet=pres_data.get("snippet"),
                source="company_presentation",
                local_path=pres_data.get("local_path"),
                text_sample=pres_data.get("text_sample")
            )
            session.add(presentation)
        except Exception as e:
            print(f"Error adding company presentation: {e}")
            print(f"Presentation data: {pres_data}")

def main():
    """Main entry point for loading data into the database."""
    parser = argparse.ArgumentParser(description="Load clinical trial data into PostgreSQL")
    parser.add_argument("--json-dir", default=os.path.join(project_root, "data", "outputs", "json"),
                        help="Directory containing JSON files")
    args = parser.parse_args()
    
    # Load database config
    db_config = load_config()
    
    # Create database engine
    engine = get_engine(db_config)
    
    # Drop existing tables
    drop_tables(engine)
    
    # Create tables
    create_tables(engine)
    
    # Get database session
    session = get_session(engine)
    
    try:
        # Load JSON data
        load_json_data(args.json_dir, session)
    except Exception as e:
        print(f"Error loading data: {e}")
        session.rollback()
        raise
    finally:
        session.close()

if __name__ == "__main__":
    main()