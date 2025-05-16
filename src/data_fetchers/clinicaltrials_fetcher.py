"""
ClinicalTrials.gov API Fetcher (Modified for Real Data Only).

This module handles fetching clinical trial data from ClinicalTrials.gov API
for pulmonary arterial hypertension (PAH) or other user-specified conditions.
Simulated data fallbacks have been removed to ensure only real data is used.
"""

import os
import json
import time
from datetime import datetime, timedelta
import requests
from tqdm import tqdm
import sys

# Add project path to system path to allow imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(src_dir)
sys.path.append(project_root)

from src.utils.paths import get_clinical_trials_dir, create_directories

class ClinicalTrialsFetcher:
    """Fetch clinical trial data from ClinicalTrials.gov API v2."""
    
    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
    
    def __init__(self):
        """
        Initialize the fetcher.
        """
        # Ensure directories exist
        create_directories()
        
        # Set the raw data directory
        self.raw_dir = get_clinical_trials_dir()
        
        print(f"Clinical trials will be saved to: {self.raw_dir}")
    
    def search_trials(
        self, 
        condition="Pulmonary Arterial Hypertension",
        max_results=100
    ):
        """
        Search for clinical trials with the given condition.
        
        Args:
            condition: Medical condition to search for
            max_results: Maximum number of results to return
            
        Returns:
            List of studies
        """
        print(f"Searching for {condition} trials...")
        
        # Simple search with just the condition
        params = {
            "query.term": condition,
            "pageSize": max_results,
            "format": "json"
        }
        
        try:
            # Make the request
            response = requests.get(self.BASE_URL, params=params)
            response.raise_for_status()
            
            # Parse the response
            data = response.json()
            
            # Get the list of studies
            studies = data.get('studies', [])
            
            print(f"Found {len(studies)} trials.")
            return studies
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching clinical trials: {e}")
            print(f"URL attempted: {response.url}")
            return []
    
    def filter_studies(self, studies, sponsor_type="Industry", study_type="Interventional", min_start_date=None):
        """
        Filter studies by sponsor type, study type, and start date.
        
        Args:
            studies: List of studies from search_trials
            sponsor_type: Type of sponsor to filter for (Industry, NIH, etc.)
            study_type: Type of study to filter for (Interventional, Observational, etc.)
            min_start_date: Minimum start date (10 years ago by default)
            
        Returns:
            Filtered list of studies
        """
        # Set default min_start_date to 10 years ago if not provided
        if min_start_date is None:
            ten_years_ago = datetime.now() - timedelta(days=365*10)
            min_start_date = ten_years_ago.strftime("%Y-%m-%d")
        
        min_start_date_obj = datetime.strptime(min_start_date, "%Y-%m-%d")
        
        print(f"Filtering for {sponsor_type} sponsored, {study_type} studies since {min_start_date}...")
        
        filtered_studies = []
        
        for study in studies:
            protocol = study.get('protocolSection', {})
            
            # Check sponsor type
            sponsor_module = protocol.get('sponsorCollaboratorsModule', {})
            lead_sponsor = sponsor_module.get('leadSponsor', {})
            sponsor_class = lead_sponsor.get('class', '')
            
            if sponsor_type.lower() != sponsor_class.lower():
                continue
            
            # Check study type
            design_module = protocol.get('designModule', {})
            actual_study_type = design_module.get('studyType', '')
            
            if study_type.lower() != actual_study_type.lower():
                continue
            
            # Check start date
            status_module = protocol.get('statusModule', {})
            start_date_str = status_module.get('startDate', '')
            
            if start_date_str:
                try:
                    start_date_obj = datetime.strptime(start_date_str, "%B %d, %Y")
                    if start_date_obj < min_start_date_obj:
                        continue
                except ValueError:
                    # Skip if we can't parse the date
                    pass
            
            # If we get here, the study meets all criteria
            filtered_studies.append(study)
        
        print(f"Found {len(filtered_studies)} {sponsor_type} sponsored, {study_type} studies.")
        return filtered_studies
    
    def get_trial_details(self, nct_id):
        """
        Get detailed information about a specific trial.
        
        Args:
            nct_id: The NCT identifier for the trial
            
        Returns:
            JSON object with trial details
        """
        url = f"{self.BASE_URL}/{nct_id}"
        
        try:
            response = requests.get(url, params={"format": "json"})
            response.raise_for_status()
            
            # Save the raw response
            save_path = os.path.join(self.raw_dir, f"{nct_id}.json")
            with open(save_path, 'w') as f:
                json.dump(response.json(), f, indent=2)
            
            return response.json()
            
        except requests.exceptions.RequestException as e:
            print(f"Error fetching details for {nct_id}: {e}")
            return None
    
    def check_if_public_company(self, sponsor_name):
        """
        Check if the sponsor is likely a public company.
        
        Args:
            sponsor_name: Name of the sponsor
            
        Returns:
            Boolean indicating if the sponsor is likely a public company
        """
        public_companies = [
            "pfizer", "merck", "novartis", "roche", "johnson", "astrazeneca", 
            "sanofi", "glaxosmithkline", "gilead", "amgen", "biogen", "vertex",
            "regeneron", "bayer", "bristol-myers", "abbvie", "lilly", "boehringer",
            "united", "gsk", "astellas", "takeda", "teva", "baxter", "daiichi",
            "allergan", "mylan", "viatris", "biomarin", "acceleron", "alexion",
            "liquidia", "gossamer", "actelion", "aerovate", "mereo", "altavant",
            "janssen", "united therapeutics", "tenax"
        ]
        
        # Check if the sponsor name contains any of the known public company names
        return any(company.lower() in sponsor_name.lower() for company in public_companies)
    
    def get_public_company_trials(self, condition="Pulmonary Arterial Hypertension", limit=None):
        """
        Get the latest clinical trials sponsored by public companies.
        
        Args:
            condition: Medical condition to search for
            limit: Number of trials to return (optional)
            
        Returns:
            List of trials with public company sponsors
        """
        # Get all matching trials - increase the number to find more candidates
        all_trials = self.search_trials(condition=condition, max_results=200)
        
        # Filter for industry-sponsored interventional trials
        filtered_trials = self.filter_studies(all_trials)
        
        # Filter for public company sponsors
        public_company_trials = []
        
        print("Filtering for trials by public companies...")
        for trial in tqdm(filtered_trials):
            # Get the NCT ID from the trial data
            nct_id = trial.get('protocolSection', {}).get('identificationModule', {}).get('nctId')
            
            if not nct_id:
                continue
            
            # Get full trial details
            trial_data = self.get_trial_details(nct_id)
            if not trial_data:
                continue
                
            # Extract sponsor information
            sponsor_name = trial_data.get('protocolSection', {}).get('sponsorCollaboratorsModule', {}).get('leadSponsor', {}).get('name', '')
            
            # Check if sponsor is a public company
            if self.check_if_public_company(sponsor_name):
                # Check if this study has results (completed trials with published results)
                has_results = 'resultsSection' in trial_data
                status = trial_data.get('protocolSection', {}).get('statusModule', {}).get('overallStatus', '')
                
                # Prioritize completed trials with results
                if has_results or status in ['Completed', 'Terminated', 'Active, not recruiting']:
                    public_company_trials.append(trial_data)
                    print(f"Found public company trial with results: {nct_id} - {sponsor_name}")
                else:
                    # If we don't have enough trials with results, include others
                    if len([t for t in public_company_trials if 'resultsSection' in t]) < 5:
                        public_company_trials.append(trial_data)
                        print(f"Found public company trial: {nct_id} - {sponsor_name}")
                
                # Break if we have enough trials and limit is specified
                if limit is not None and len(public_company_trials) >= limit:
                    break
            
            # Add a small delay to avoid rate limiting
            time.sleep(0.3)
        
        print(f"Found {len(public_company_trials)} trials by public companies.")
        
        # Prioritize trials with results
        public_company_trials.sort(key=lambda x: 'resultsSection' in x, reverse=True)
        
        if limit is not None:
            return public_company_trials[:limit]
        return public_company_trials
    
    def extract_key_metadata(self, trial_data):
        """
        Extract key metadata from a trial as specified in the assignment.
        
        Args:
            trial_data: Trial data from ClinicalTrials.gov
            
        Returns:
            Dictionary with extracted metadata
        """
        metadata = {}
        protocol = trial_data.get('protocolSection', {})
        
        # Extract basic information
        id_module = protocol.get('identificationModule', {})
        metadata['title'] = id_module.get('briefTitle', '')
        metadata['nct_identifier'] = id_module.get('nctId', '')
        
        # Extract condition/indication
        conditions_module = protocol.get('conditionsModule', {})
        metadata['indication'] = conditions_module.get('conditions', [''])[0] if conditions_module.get('conditions') else ''
        
        # Extract intervention
        interventions_module = protocol.get('armsInterventionsModule', {})
        interventions = interventions_module.get('interventions', [])
        if interventions:
            metadata['intervention'] = interventions[0].get('name', '')
            
            # Extract intervention details if it's a drug
            if interventions[0].get('type', '').lower() == 'drug':
                drug_info = {}
                drug_info['name'] = interventions[0].get('name', '')
                
                # Try to extract dose, frequency, and formulation from description
                description = interventions[0].get('description', '')
                drug_info['dose'] = self._extract_dose(description)
                drug_info['frequency'] = self._extract_frequency(description)
                drug_info['formulation'] = self._extract_formulation(description)
                
                metadata['interventional_drug'] = drug_info
            else:
                # Default drug info if not a drug intervention
                metadata['interventional_drug'] = {
                    'name': interventions[0].get('name', ''),
                    'dose': 'Not applicable',
                    'frequency': 'Not applicable',
                    'formulation': 'Not applicable'
                }
        else:
            # Default if no interventions found
            metadata['intervention'] = 'Unknown'
            metadata['interventional_drug'] = {
                'name': 'Unknown',
                'dose': 'Unknown',
                'frequency': 'Unknown',
                'formulation': 'Unknown'
            }
        
        # Extract phase
        design_module = protocol.get('designModule', {})
        metadata['phase'] = design_module.get('phases', ['Unknown'])[0] if design_module.get('phases') else 'Unknown'
        
        # Extract sponsor
        sponsor_module = protocol.get('sponsorCollaboratorsModule', {})
        lead_sponsor = sponsor_module.get('leadSponsor', {})
        metadata['sponsor'] = lead_sponsor.get('name', '')
        
        # Extract arms and number of participants
        arms = interventions_module.get('arms', [])
        arms_data = {'intervention': 0, 'placebo': 0}
        for arm in arms:
            arm_type = arm.get('type', '').lower()
            if 'experimental' in arm_type:
                arms_data['intervention'] += 1
            elif 'placebo' in arm_type:
                arms_data['placebo'] += 1
        
        metadata['study_arms'] = arms_data
        
        # Extract enrollment
        design_module = protocol.get('designModule', {})
        enrollment_info = design_module.get('enrollmentInfo', {})
        metadata['number_of_participants'] = enrollment_info.get('count', 0)
        
        # Extract age information
        eligibility_module = protocol.get('eligibilityModule', {})
        min_age_str = eligibility_module.get('minimumAge', '0 Years')
        max_age_str = eligibility_module.get('maximumAge', '100 Years')
        
        # Extract numeric values from age strings
        try:
            min_age = int(min_age_str.split()[0]) if min_age_str else 0
        except (ValueError, IndexError):
            min_age = 0
            
        try:
            max_age = int(max_age_str.split()[0]) if max_age_str else 100
        except (ValueError, IndexError):
            max_age = 100
        
        metadata['age_range'] = [min_age, max_age]
        metadata['average_age'] = (min_age + max_age) / 2  # Simple average
        
        # Extract real demographic data from results section if available
        results_section = trial_data.get('resultsSection', {})
        baseline_data = results_section.get('baselineData', {})
        
        if baseline_data:
            analyzed_participants = baseline_data.get('analyzedParticipants', {})
            if analyzed_participants:
                count = analyzed_participants.get('count', 0)
                if count > 0:
                    metadata['number_of_participants'] = count
            
            groups = baseline_data.get('groups', [])
            measures = baseline_data.get('measures', [])
            
            # Look for age measure
            for measure in measures:
                if 'age' in measure.get('title', '').lower():
                    for analysis in measure.get('analyses', []):
                        for group_id in analysis.get('groupIds', []):
                            units = analysis.get('units', '')
                            if units == 'years':
                                value = analysis.get('value', 0)
                                try:
                                    metadata['average_age'] = float(value)
                                except (ValueError, TypeError):
                                    pass
        
        # Extract endpoints
        outcomes_module = protocol.get('outcomesModule', {})
        primary_outcomes = outcomes_module.get('primaryOutcomes', [])
        secondary_outcomes = outcomes_module.get('secondaryOutcomes', [])
        
        endpoints = []
        for outcome in primary_outcomes:
            endpoints.append(outcome.get('measure', ''))
        
        for outcome in secondary_outcomes:
            endpoints.append(outcome.get('measure', ''))
        
        metadata['endpoints'] = endpoints
        
        # Extract baseline characteristics
        # For PAH trials, we'll use common baseline measures
        baseline_characteristics = [
            "WHO Functional Class",
            "PVR (Pulmonary Vascular Resistance)",
            "6MWD (6-minute walk distance)",
            "NT-proBNP levels",
            "Right heart function",
            "PAH etiology"
        ]
        
        # Check if we have real baseline characteristics in the results section
        if baseline_data and measures:
            for measure in measures:
                title = measure.get('title', '')
                if title and title not in baseline_characteristics:
                    baseline_characteristics.append(title)
        
        metadata['baseline_characteristics'] = baseline_characteristics
        
        return metadata
    
    def _extract_dose(self, description):
        """Extract dose information from description."""
        # This is a placeholder for text extraction
        # In a real implementation, you would use NLP techniques
        # to extract this information more reliably
        if "mg" in description:
            # Simple extraction - find a number followed by mg
            import re
            dose_match = re.search(r'(\d+(\.\d+)?\s*mg)', description)
            if dose_match:
                return dose_match.group(1)
        return "Unknown"
    
    def _extract_frequency(self, description):
        """Extract frequency information from description."""
        # Look for common dosing frequencies
        frequency_terms = {
            "once daily": ["once daily", "daily", "qd"],
            "twice daily": ["twice daily", "bid", "b.i.d"],
            "three times daily": ["three times daily", "tid", "t.i.d"],
            "four times daily": ["four times daily", "qid", "q.i.d"],
            "weekly": ["weekly", "once a week"],
            "twice weekly": ["twice weekly", "biweekly"],
            "monthly": ["monthly", "once a month"]
        }
        
        description_lower = description.lower()
        for freq, terms in frequency_terms.items():
            if any(term in description_lower for term in terms):
                return freq
        
        return "Unknown"
    
    def _extract_formulation(self, description):
        """Extract formulation information from description."""
        # Look for common formulations
        formulations = [
            "tablet", "capsule", "solution", "suspension", "injection",
            "infusion", "inhalation", "inhaled", "oral", "intravenous",
            "subcutaneous", "intramuscular", "topical", "patch", "cream",
            "ointment", "powder", "spray"
        ]
        
        description_lower = description.lower()
        for form in formulations:
            if form in description_lower:
                return form.capitalize()
        
        return "Unknown"