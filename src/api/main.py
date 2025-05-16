"""
FastAPI backend for Clinical Trials Pipeline.
"""

import os
import sys
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Query, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(src_dir)
sys.path.append(project_root)

from src.database.models import ClinicalStudy, Endpoint, BaselineMeasure

# Create FastAPI app
app = FastAPI(title="Clinical Trials API", 
              description="API for accessing clinical trial data")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # For development - restrict in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection function with explicit PostgreSQL
def get_db():
    """Get database session with explicit PostgreSQL connection."""
    # Load database config
    try:
        config_path = os.path.join(project_root, "config", "config.json")
        with open(config_path, "r") as f:
            config = json.load(f)
        db_config = config["database"]
        
        # Create PostgreSQL connection string directly
        connection_string = (
            f"postgresql://{db_config.get('user')}:{db_config.get('password')}"
            f"@{db_config.get('host')}:{db_config.get('port')}/{db_config.get('database')}"
        )
        
        # Create engine and session
        engine = create_engine(connection_string)
        SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        
        # Create session
        db = SessionLocal()
        try:
            # Test connection with a simple query
            db.execute(text("SELECT 1"))
            yield db
        except Exception as e:
            print(f"Database error: {e}")
            raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")
        finally:
            db.close()
    except Exception as e:
        print(f"Error setting up database: {e}")
        raise HTTPException(status_code=500, detail=f"Database setup error: {str(e)}")

# Fallback to read from JSON files if database fails
def get_json_data():
    """Load data from JSON files as fallback."""
    try:
        json_dir = os.path.join(project_root, "data", "outputs", "json")
        
        # Load all NCT files
        json_files = [f for f in os.listdir(json_dir) if f.endswith('.json') and f.startswith('NCT')]
        
        # Read data from JSON files
        trials = []
        trial_details = {}
        
        for json_file in json_files:
            file_path = os.path.join(json_dir, json_file)
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            study = data.get("clinical_study", {})
            nct_id = study.get("nct_identifier", "")
            
            if nct_id:
                # Add to trials list
                trial_summary = {
                    "id": len(trials) + 1,
                    "title": study.get("title", ""),
                    "nct_identifier": nct_id,
                    "indication": study.get("indication", ""),
                    "intervention": study.get("intervention", ""),
                    "phase": study.get("phase", ""),
                    "sponsor": study.get("sponsor", ""),
                    "number_of_participants": study.get("number_of_participants", 0),
                    "average_age": study.get("average_age", 0)
                }
                trials.append(trial_summary)
                
                # Store full data
                trial_details[nct_id] = data
        
        return trials, trial_details
    except Exception as e:
        print(f"Error loading JSON data: {e}")
        return [], {}

# Load JSON data at startup as fallback
json_trials, json_trial_details = get_json_data()

# API routes
@app.get("/")
def read_root():
    return {"message": "Welcome to the Clinical Trials API"}

@app.get("/trials", response_model=List[dict])
def get_trials(
    skip: int = 0, 
    limit: int = 10, 
    indication: Optional[str] = None,
    sponsor: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get a list of clinical trials with optional filtering."""
    try:
        # Try to get data from database
        query = db.query(ClinicalStudy)
        
        if indication:
            query = query.filter(ClinicalStudy.indication.ilike(f"%{indication}%"))
        
        if sponsor:
            query = query.filter(ClinicalStudy.sponsor.ilike(f"%{sponsor}%"))
        
        trials = query.offset(skip).limit(limit).all()
        
        # Convert to dict for response
        result = []
        for trial in trials:
            trial_dict = {
                "id": trial.id,
                "title": trial.title,
                "nct_identifier": trial.nct_identifier,
                "indication": trial.indication,
                "intervention": trial.intervention,
                "phase": trial.phase,
                "sponsor": trial.sponsor,
                "number_of_participants": trial.number_of_participants,
                "average_age": trial.average_age
            }
            result.append(trial_dict)
        
        return result
    except Exception as e:
        # Log the error
        print(f"Database error in get_trials: {e}")
        
        # Fall back to JSON data
        filtered_trials = json_trials
        
        # Apply filters if specified
        if indication:
            filtered_trials = [t for t in filtered_trials if indication.lower() in t.get("indication", "").lower()]
        
        if sponsor:
            filtered_trials = [t for t in filtered_trials if sponsor.lower() in t.get("sponsor", "").lower()]
        
        # Apply pagination
        paginated_trials = filtered_trials[skip:skip+limit]
        
        return paginated_trials

@app.get("/trials/{nct_id}")
def get_trial_by_nct(nct_id: str, db: Session = Depends(get_db)):
    """Get detailed information about a specific trial by NCT ID."""
    try:
        # Try to get data from database
        trial = db.query(ClinicalStudy).filter(ClinicalStudy.nct_identifier == nct_id).first()
        
        if not trial:
            # Check if we have it in JSON data
            if nct_id in json_trial_details:
                return json_trial_details[nct_id]
            else:
                raise HTTPException(status_code=404, detail="Trial not found")
        
        # Get endpoints
        endpoints = db.query(Endpoint).filter(Endpoint.clinical_study_id == trial.id).all()
        endpoints_data = []
        
        for endpoint in endpoints:
            endpoint_dict = {
                "name": endpoint.name,
                "description": endpoint.description,
                "timepoint": endpoint.timepoint,
                "arm": endpoint.arm,
                "average_value": endpoint.average_value,
                "upper_end": endpoint.upper_end,
                "lower_end": endpoint.lower_end,
                "statistical_significance": endpoint.statistical_significance
            }
            endpoints_data.append(endpoint_dict)
        
        # Get baseline measures
        baseline_measures = db.query(BaselineMeasure).filter(BaselineMeasure.clinical_study_id == trial.id).all()
        baseline_data = []
        
        for measure in baseline_measures:
            measure_dict = {
                "name": measure.name,
                "description": measure.description,
                "arm": measure.arm,
                "average_value": measure.average_value,
                "upper_end": measure.upper_end,
                "lower_end": measure.lower_end
            }
            baseline_data.append(measure_dict)
        
        # Construct full response
        response = {
            "clinical_study": {
                "id": trial.id,
                "title": trial.title,
                "nct_identifier": trial.nct_identifier,
                "indication": trial.indication,
                "intervention": trial.intervention,
                "interventional_drug": {
                    "name": trial.interventional_drug_name,
                    "dose": trial.interventional_drug_dose,
                    "frequency": trial.interventional_drug_frequency,
                    "formulation": trial.interventional_drug_formulation
                },
                "phase": trial.phase,
                "sponsor": trial.sponsor,
                "study_arms": {
                    "intervention": trial.intervention_arms,
                    "placebo": trial.placebo_arms
                },
                "number_of_participants": trial.number_of_participants,
                "average_age": trial.average_age,
                "age_range": [trial.min_age, trial.max_age]
            },
            "endpoints": endpoints_data,
            "baseline_measures": baseline_data
        }
        
        return response
    except HTTPException:
        raise
    except Exception as e:
        # Log the error
        print(f"Database error in get_trial_by_nct: {e}")
        
        # Fall back to JSON data
        if nct_id in json_trial_details:
            return json_trial_details[nct_id]
        else:
            raise HTTPException(status_code=404, detail="Trial not found")

@app.get("/endpoints/{endpoint_name}")
def compare_endpoint(
    endpoint_name: str, 
    include_placebo: bool = True,
    db: Session = Depends(get_db)
):
    """Compare a specific endpoint across trials."""
    try:
        # Try to get data from database
        endpoints = db.query(Endpoint).filter(Endpoint.name.ilike(f"%{endpoint_name}%")).all()
        
        if not endpoints:
            # Fall back to JSON data for endpoints
            endpoint_data = []
            for trial_data in json_trial_details.values():
                for endpoint in trial_data.get("endpoints", []):
                    if endpoint_name.lower() in endpoint.get("name", "").lower():
                        # Skip if we don't want placebo and this is placebo
                        if not include_placebo and endpoint.get("arm") == "placebo":
                            continue
                        
                        study_info = trial_data.get("clinical_study", {})
                        
                        endpoint_data.append({
                            "nct_id": study_info.get("nct_identifier", ""),
                            "study_title": study_info.get("title", ""),
                            "sponsor": study_info.get("sponsor", ""),
                            "endpoint_name": endpoint.get("name", ""),
                            "arm": endpoint.get("arm", ""),
                            "timepoint": endpoint.get("timepoint", ""),
                            "value": endpoint.get("average_value"),
                            "upper_end": endpoint.get("upper_end"),
                            "lower_end": endpoint.get("lower_end"),
                            "p_value": endpoint.get("statistical_significance", "")
                        })
            
            if endpoint_data:
                return endpoint_data
            else:
                raise HTTPException(status_code=404, detail=f"No data found for endpoint: {endpoint_name}")
        
        # Filter by arm if needed
        if not include_placebo:
            endpoints = [e for e in endpoints if e.arm == "intervention"]
        
        # Get trial information for these endpoints
        result = []
        for endpoint in endpoints:
            trial = db.query(ClinicalStudy).filter(ClinicalStudy.id == endpoint.clinical_study_id).first()
            
            if trial:
                data = {
                    "nct_id": trial.nct_identifier,
                    "study_title": trial.title,
                    "sponsor": trial.sponsor,
                    "endpoint_name": endpoint.name,
                    "arm": endpoint.arm,
                    "timepoint": endpoint.timepoint,
                    "value": endpoint.average_value,
                    "upper_end": endpoint.upper_end,
                    "lower_end": endpoint.lower_end,
                    "p_value": endpoint.statistical_significance
                }
                result.append(data)
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        # Log the error
        print(f"Database error in compare_endpoint: {e}")
        
        # Fall back to JSON data for endpoints
        endpoint_data = []
        for trial_data in json_trial_details.values():
            for endpoint in trial_data.get("endpoints", []):
                if endpoint_name.lower() in endpoint.get("name", "").lower():
                    # Skip if we don't want placebo and this is placebo
                    if not include_placebo and endpoint.get("arm") == "placebo":
                        continue
                    
                    study_info = trial_data.get("clinical_study", {})
                    
                    endpoint_data.append({
                        "nct_id": study_info.get("nct_identifier", ""),
                        "study_title": study_info.get("title", ""),
                        "sponsor": study_info.get("sponsor", ""),
                        "endpoint_name": endpoint.get("name", ""),
                        "arm": endpoint.get("arm", ""),
                        "timepoint": endpoint.get("timepoint", ""),
                        "value": endpoint.get("average_value"),
                        "upper_end": endpoint.get("upper_end"),
                        "lower_end": endpoint.get("lower_end"),
                        "p_value": endpoint.get("statistical_significance", "")
                    })
        
        if endpoint_data:
            return endpoint_data
        else:
            raise HTTPException(status_code=404, detail=f"No data found for endpoint: {endpoint_name}")

# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint to verify API is running."""
    return {
        "status": "healthy",
        "db_type": "PostgreSQL with JSON fallback",
        "trials_loaded": len(json_trials),
        "version": "1.0"
    }

# Run with: uvicorn src.api.main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)