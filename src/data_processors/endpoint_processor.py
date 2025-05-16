"""
Endpoint data processor for the Clinical Trial & Corporate Disclosure Extraction Pipeline.
Modified to handle real-world data which may be incomplete or inconsistent.
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import re

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(src_dir)
sys.path.append(project_root)

from src.utils.paths import get_processed_dir, get_json_dir, get_visualizations_dir


class EndpointProcessor:
    """Processor for clinical trial endpoint data (real data version)."""
    
    def __init__(self):
        """Initialize the processor."""
        self.processed_dir = get_processed_dir()
        self.json_dir = get_json_dir()
        self.visualizations_dir = get_visualizations_dir()
        
        # Ensure directories exist
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.json_dir, exist_ok=True)
        os.makedirs(self.visualizations_dir, exist_ok=True)
        
        # Common endpoint names and their potential variations
        self.endpoint_aliases = {
            "pvr": ["pulmonary vascular resistance", "pvr", "pulmonary resistance"],
            "6mwd": ["6 minute walk distance", "6mwd", "6-minute walk", "six minute walk", "6 min walk"],
            "nt-probnp": ["nt-probnp", "nt probnp", "n-terminal pro-bnp", "brain natriuretic peptide"],
            "who fc": ["who functional class", "who fc", "functional class", "who class"],
            "time to clinical worsening": ["ttcw", "time to clinical worsening", "clinical worsening", "time to worsening"],
            "cardiac output": ["cardiac output", "co", "cardiac index", "ci"]
        }
    
    def load_all_trials(self):
        """
        Load all processed trial data.
        
        Returns:
            List of trial data dictionaries
        """
        trials = []
        
        # Get all JSON files in the processed directory
        json_files = [f for f in os.listdir(self.json_dir) if f.endswith('.json') and f.startswith('NCT')]
        
        for json_file in json_files:
            file_path = os.path.join(self.json_dir, json_file)
            
            try:
                with open(file_path, 'r') as f:
                    trial_data = json.load(f)
                    # Only include trials with endpoint data
                    if trial_data.get("endpoints") or trial_data.get("baseline_measures"):
                        trials.append(trial_data)
            except json.JSONDecodeError:
                print(f"Warning: Could not parse JSON file {file_path}")
                continue
        
        print(f"Loaded {len(trials)} trials with real data.")
        return trials
    
    def normalize_endpoint_name(self, name):
        """
        Normalize endpoint names to handle variations in real data.
        
        Args:
            name: Original endpoint name
            
        Returns:
            Normalized endpoint name
        """
        name_lower = name.lower()
        
        # Check against known endpoint aliases
        for standard_name, aliases in self.endpoint_aliases.items():
            if any(alias in name_lower for alias in aliases):
                return standard_name.upper()
        
        # If no match found, return original with minimal cleaning
        return re.sub(r'\s+', ' ', name).strip()
    
    def extract_endpoints_data(self, trials, endpoint_type=None):
        """
        Extract endpoint data from all trials.
        
        Args:
            trials: List of trial data dictionaries
            endpoint_type: Optional filter for endpoint type
            
        Returns:
            DataFrame with endpoint data
        """
        rows = []
        
        for trial in trials:
            study_info = trial.get("clinical_study", {})
            study_name = study_info.get("title", "Unknown")
            nct_id = study_info.get("nct_identifier", "Unknown")
            sponsor = study_info.get("sponsor", "Unknown")
            
            for endpoint in trial.get("endpoints", []):
                name = endpoint.get("name", "")
                if not name:
                    continue
                
                # Normalize the endpoint name for better comparison
                normalized_name = self.normalize_endpoint_name(name)
                
                # Filter by endpoint type if specified
                if endpoint_type:
                    endpoint_type_lower = endpoint_type.lower()
                    # Check if the endpoint type matches the normalized name or is in the original name
                    if (endpoint_type_lower not in normalized_name.lower() and 
                        endpoint_type_lower not in name.lower()):
                        continue
                
                arm = endpoint.get("arm", "Unknown")
                timepoint = endpoint.get("timepoint", "Unknown")
                avg_value = endpoint.get("average_value")
                upper_end = endpoint.get("upper_end")
                lower_end = endpoint.get("lower_end")
                significance = endpoint.get("statistical_significance", "")
                
                # Handle non-numeric values in avg_value (sometimes seen in real data)
                if avg_value and not isinstance(avg_value, (int, float)):
                    try:
                        avg_value = float(avg_value)
                    except (ValueError, TypeError):
                        avg_value = None
                
                # Same for upper and lower bounds
                if upper_end and not isinstance(upper_end, (int, float)):
                    try:
                        upper_end = float(upper_end)
                    except (ValueError, TypeError):
                        upper_end = None
                        
                if lower_end and not isinstance(lower_end, (int, float)):
                    try:
                        lower_end = float(lower_end)
                    except (ValueError, TypeError):
                        lower_end = None
                
                row = {
                    "study": study_name,
                    "nct_id": nct_id,
                    "sponsor": sponsor,
                    "original_endpoint": name,
                    "endpoint": normalized_name,
                    "arm": arm,
                    "timepoint": timepoint,
                    "average_value": avg_value,
                    "upper_end": upper_end,
                    "lower_end": lower_end,
                    "significance": significance
                }
                
                rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # If we have data but no endpoint_type was specified,
        # print a summary of available endpoints to help the user
        if not endpoint_type and not df.empty:
            endpoint_counts = df['endpoint'].value_counts()
            print("Available endpoints in the data:")
            for endpoint, count in endpoint_counts.items():
                print(f"  - {endpoint}: {count} data points")
        
        return df
    
    def extract_baseline_data(self, trials, measure_type=None):
        """
        Extract baseline measure data from all trials.
        
        Args:
            trials: List of trial data dictionaries
            measure_type: Optional filter for measure type
            
        Returns:
            DataFrame with baseline measure data
        """
        rows = []
        
        for trial in trials:
            study_info = trial.get("clinical_study", {})
            study_name = study_info.get("title", "Unknown")
            nct_id = study_info.get("nct_identifier", "Unknown")
            sponsor = study_info.get("sponsor", "Unknown")
            
            for measure in trial.get("baseline_measures", []):
                name = measure.get("name", "")
                if not name:
                    continue
                
                # Normalize the measure name for better comparison
                normalized_name = self.normalize_endpoint_name(name)
                
                # Filter by measure type if specified
                if measure_type:
                    measure_type_lower = measure_type.lower()
                    if (measure_type_lower not in normalized_name.lower() and 
                        measure_type_lower not in name.lower()):
                        continue
                
                arm = measure.get("arm", "Unknown")
                avg_value = measure.get("average_value")
                upper_end = measure.get("upper_end")
                lower_end = measure.get("lower_end")
                
                # Handle non-numeric values in avg_value (sometimes seen in real data)
                if avg_value and not isinstance(avg_value, (int, float)):
                    try:
                        avg_value = float(avg_value)
                    except (ValueError, TypeError):
                        avg_value = None
                
                # Same for upper and lower bounds
                if upper_end and not isinstance(upper_end, (int, float)):
                    try:
                        upper_end = float(upper_end)
                    except (ValueError, TypeError):
                        upper_end = None
                        
                if lower_end and not isinstance(lower_end, (int, float)):
                    try:
                        lower_end = float(lower_end)
                    except (ValueError, TypeError):
                        lower_end = None
                
                row = {
                    "study": study_name,
                    "nct_id": nct_id,
                    "sponsor": sponsor,
                    "original_measure": name,
                    "measure": normalized_name,
                    "arm": arm,
                    "average_value": avg_value,
                    "upper_end": upper_end,
                    "lower_end": lower_end
                }
                
                rows.append(row)
        
        df = pd.DataFrame(rows)
        
        # If we have data but no measure_type was specified,
        # print a summary of available measures to help the user
        if not measure_type and not df.empty:
            measure_counts = df['measure'].value_counts()
            print("Available baseline measures in the data:")
            for measure, count in measure_counts.items():
                print(f"  - {measure}: {count} data points")
        
        return df
    
    def find_common_endpoints(self, trials, top_n=3):
        """
        Find the most common endpoints across trials.
        
        Args:
            trials: List of trial data dictionaries
            top_n: Number of top endpoints to return
            
        Returns:
            List of common endpoint names
        """
        all_endpoints = []
        
        for trial in trials:
            # Track endpoints we've seen for this trial to avoid duplicates
            seen_in_trial = set()
            
            for endpoint in trial.get("endpoints", []):
                name = endpoint.get("name", "")
                if not name:
                    continue
                    
                # Normalize the endpoint name
                normalized_name = self.normalize_endpoint_name(name)
                
                # Only count each endpoint once per trial
                if normalized_name not in seen_in_trial:
                    all_endpoints.append(normalized_name)
                    seen_in_trial.add(normalized_name)
        
        # Count occurrences
        endpoint_counts = pd.Series(all_endpoints).value_counts()
        
        # Print all available endpoints
        print("All endpoints found (with occurrence count):")
        for endpoint, count in endpoint_counts.items():
            print(f"  - {endpoint}: {count} trials")
        
        # Return top N
        return endpoint_counts.head(top_n).index.tolist()
    
    def create_endpoint_comparison_chart(self, df, endpoint_type, save_path=None):
        """
        Create a comparison chart for an endpoint across trials.
        
        Args:
            df: DataFrame with endpoint data
            endpoint_type: Type of endpoint (used in chart title)
            save_path: Path to save the chart (if None, display instead)
            
        Returns:
            Path to the saved chart if save_path is provided
        """
        if df.empty:
            print(f"No data available for endpoint type: {endpoint_type}")
            return None
        
        # Filter out rows with missing values
        df_plot = df.dropna(subset=['average_value']).copy()
        
        if df_plot.empty:
            print(f"No valid numerical data for endpoint type: {endpoint_type}")
            return None
        
        # Set up the plotting style
        sns.set_style("whitegrid")
        plt.figure(figsize=(14, 8))
        
        # Shorten study names for better display
        df_plot["study_short"] = df_plot["nct_id"] + ": " + df_plot["study"].apply(lambda x: x[:30] + "..." if len(x) > 30 else x)
        
        # Create a grouped bar chart
        ax = sns.barplot(
            x="study_short",
            y="average_value",
            hue="arm",
            data=df_plot,
            palette={"intervention": "steelblue", "placebo": "lightgray"},
            errorbar=None  # Don't use built-in error bars
        )
        
        # Add value labels on top of bars
        for p in ax.patches:
            height = p.get_height()
            if not np.isnan(height):
                ax.annotate(
                    f"{height:.1f}",
                    (p.get_x() + p.get_width() / 2., height),
                    ha='center',
                    va='bottom',
                    fontsize=9,
                    color='black',
                    xytext=(0, 5),
                    textcoords='offset points'
                )
        
        # Add manual error bars if available
        for i, row in df_plot.iterrows():
            if pd.notnull(row["upper_end"]) and pd.notnull(row["lower_end"]):
                yerr = [[row["average_value"] - row["lower_end"]], [row["upper_end"] - row["average_value"]]]
                plt.errorbar(
                    i, 
                    row["average_value"],
                    yerr=yerr,
                    fmt="none", 
                    color="black",
                    capsize=5
                )
        
        # Customize the plot
        plt.title(f"Comparison of {endpoint_type} Across PAH Clinical Trials", fontsize=14)
        plt.xlabel("Clinical Trial", fontsize=12)
        plt.ylabel(f"{endpoint_type} Value", fontsize=12)
        plt.xticks(rotation=45, ha="right")
        plt.legend(title="Treatment Arm")
        plt.tight_layout()
        
        # Save or display the figure
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()
            print(f"Saved chart to {save_path}")
            return save_path
        else:
            plt.show()
            plt.close()
            return None
    
    def create_treatment_effect_chart(self, df, endpoint_type, save_path=None):
        """
        Create a chart showing treatment effect (difference between intervention and placebo).
        
        Args:
            df: DataFrame with endpoint data
            endpoint_type: Type of endpoint (used in chart title)
            save_path: Path to save the chart (if None, display instead)
            
        Returns:
            Path to the saved chart if save_path is provided
        """
        if df.empty:
            print(f"No data available for endpoint type: {endpoint_type}")
            return None
        
        # Filter out rows with missing values
        df_filtered = df.dropna(subset=['average_value']).copy()
        
        if df_filtered.empty:
            print(f"No valid numerical data for endpoint type: {endpoint_type}")
            return None
            
        # Filter data to only include trials that have both intervention and placebo arms
        study_arms = df_filtered.groupby("nct_id")["arm"].unique().apply(set)
        valid_studies = study_arms[study_arms.apply(lambda x: {"intervention", "placebo"}.issubset(x))].index.tolist()
        
        if not valid_studies:
            print(f"No studies with both intervention and placebo arms for {endpoint_type}")
            return None
        
        df_filtered = df_filtered[df_filtered["nct_id"].isin(valid_studies)]
        
        # Calculate treatment effect for each study
        effect_data = []
        
        for nct_id in valid_studies:
            study_data = df_filtered[df_filtered["nct_id"] == nct_id]
            
            # Get intervention data
            intervention_data = study_data[study_data["arm"] == "intervention"]
            if intervention_data.empty:
                continue
                
            # Get placebo data
            placebo_data = study_data[study_data["arm"] == "placebo"]
            if placebo_data.empty:
                continue
            
            # Use the first row for each arm if multiple exist
            intervention_row = intervention_data.iloc[0]
            placebo_row = placebo_data.iloc[0]
            
            # Calculate effect (treatment - placebo)
            effect = intervention_row["average_value"] - placebo_row["average_value"]
            
            # Check if the effect is statistically significant
            p_value = intervention_row["significance"]
            is_significant = False
            
            # Check for common p-value formats in real data
            if isinstance(p_value, str):
                p_value_lower = p_value.lower()
                if "p<0.05" in p_value_lower or "p = 0.05" in p_value_lower or "p<.05" in p_value_lower:
                    is_significant = True
                elif "p=" in p_value_lower or "p =" in p_value_lower:
                    # Extract the actual p-value if available
                    p_match = re.search(r'p\s*=\s*(0\.\d+)', p_value_lower)
                    if p_match:
                        try:
                            actual_p = float(p_match.group(1))
                            is_significant = actual_p < 0.05
                        except ValueError:
                            pass
            
            effect_data.append({
                "nct_id": nct_id,
                "study": intervention_row["study"],
                "effect": effect,
                "significance": p_value,
                "is_significant": is_significant
            })
        
        if not effect_data:
            print(f"No valid treatment effect data for {endpoint_type}")
            return None
            
        effect_df = pd.DataFrame(effect_data)
        
        # Create the chart
        sns.set_style("whitegrid")
        plt.figure(figsize=(12, 6))
        
        # Determine colors based on significance
        colors = ["lightgreen" if row["is_significant"] else "lightcoral" for _, row in effect_df.iterrows()]
        
        # Create horizontal bar chart of treatment effects
        ax = sns.barplot(
            y="nct_id",
            x="effect",
            data=effect_df,
            palette=colors,
            orient="h"
        )
        
        # Add value labels
        for i, row in effect_df.iterrows():
            significance_text = row["significance"] if row["significance"] else "Unknown"
            if isinstance(significance_text, str) and len(significance_text) > 10:
                significance_text = significance_text[:10] + "..."
                
            ax.text(
                row["effect"] + (0.1 if row["effect"] >= 0 else -0.1),
                i,
                f"{row['effect']:.1f} ({significance_text})",
                va='center',
                fontsize=9,
                color='black'
            )
        
        # Customize the plot
        plt.title(f"Treatment Effect for {endpoint_type} Across PAH Clinical Trials", fontsize=14)
        plt.xlabel(f"Effect Size (Intervention - Placebo)", fontsize=12)
        plt.ylabel("Clinical Trial", fontsize=12)
        plt.axvline(x=0, color='gray', linestyle='--')
        plt.tight_layout()
        
        # Save or display the figure
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()
            print(f"Saved treatment effect chart to {save_path}")
            return save_path
        else:
            plt.show()
            plt.close()
            return None
    
    def generate_endpoint_summary_table(self, trials):
        """
        Generate a summary table of endpoints across all trials.
        
        Args:
            trials: List of trial data dictionaries
            
        Returns:
            DataFrame with endpoint summary
        """
        # Find all unique normalized endpoints
        all_endpoints = set()
        for trial in trials:
            for endpoint in trial.get("endpoints", []):
                if endpoint.get("arm") == "intervention":  # Count each endpoint only once per trial
                    name = endpoint.get("name", "")
                    if name:
                        normalized_name = self.normalize_endpoint_name(name)
                        all_endpoints.add(normalized_name)
        
        # Create a matrix of trials vs. endpoints
        rows = []
        
        for trial in trials:
            study_info = trial.get("clinical_study", {})
            
            row = {
                "nct_id": study_info.get("nct_identifier", "Unknown"),
                "title": study_info.get("title", "Unknown"),
                "sponsor": study_info.get("sponsor", "Unknown"),
                "phase": study_info.get("phase", "Unknown"),
                "participants": study_info.get("number_of_participants", 0)
            }
            
            # Create a map of normalized endpoint names to endpoints for this trial
            trial_endpoints = {}
            for endpoint in trial.get("endpoints", []):
                if endpoint.get("arm") == "intervention":
                    name = endpoint.get("name", "")
                    if name:
                        normalized_name = self.normalize_endpoint_name(name)
                        trial_endpoints[normalized_name] = endpoint
            
            # Add a column for each endpoint
            for endpoint in all_endpoints:
                if endpoint in trial_endpoints:
                    # Add the p-value if available
                    p_value = trial_endpoints[endpoint].get("statistical_significance", "")
                    row[endpoint] = p_value
                else:
                    row[endpoint] = "-"
            
            rows.append(row)
        
        return pd.DataFrame(rows)
    
    def visualize_all_common_endpoints(self, trials, output_dir=None, top_n=3):
        """
        Create visualizations for the most common endpoints across trials.
        
        Args:
            trials: List of trial data dictionaries
            output_dir: Directory to save visualizations (default: visualizations_dir)
            top_n: Number of top endpoints to visualize
            
        Returns:
            List of paths to saved visualizations
        """
        if output_dir is None:
            output_dir = self.visualizations_dir
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Find common endpoints
        common_endpoints = self.find_common_endpoints(trials, top_n=top_n)
        print(f"Found {len(common_endpoints)} common endpoints: {common_endpoints}")
        
        visualization_paths = []
        
        # Create visualizations for each common endpoint
        for endpoint in common_endpoints:
            # Extract data for this endpoint
            df = self.extract_endpoints_data(trials, endpoint_type=endpoint)
            
            if not df.empty:
                # Create normalized name for the file
                endpoint_name = endpoint.split("(")[0].strip().replace(" ", "_")
                
                # Create standard comparison chart
                comparison_path = os.path.join(output_dir, f"{endpoint_name}_comparison.png")
                chart_path = self.create_endpoint_comparison_chart(df, endpoint, save_path=comparison_path)
                if chart_path:
                    visualization_paths.append(chart_path)
                
                # Create treatment effect chart
                effect_path = os.path.join(output_dir, f"{endpoint_name}_treatment_effect.png")
                effect_chart_path = self.create_treatment_effect_chart(df, endpoint, save_path=effect_path)
                if effect_chart_path:
                    visualization_paths.append(effect_chart_path)
        
        # Create summary table
        summary_df = self.generate_endpoint_summary_table(trials)
        summary_path = os.path.join(output_dir, "endpoint_summary.csv")
        summary_df.to_csv(summary_path, index=False)
        visualization_paths.append(summary_path)
        
        # Create a summary report HTML
        html_report_path = os.path.join(output_dir, "endpoint_report.html")
        self.create_html_report(trials, common_endpoints, html_report_path)
        visualization_paths.append(html_report_path)
        
        return visualization_paths
    
    def create_html_report(self, trials, endpoints, output_path):
        """
        Create an HTML report summarizing the trials and endpoints.
        
        Args:
            trials: List of trial data dictionaries
            endpoints: List of common endpoint names
            output_path: Path to save the HTML report
            
        Returns:
            Path to the saved HTML report
        """
        # Create HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>PAH Clinical Trial Endpoint Analysis</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
                h1, h2, h3 {{ color: #2c3e50; }}
                table {{ border-collapse: collapse; width: 100%; margin-bottom: 20px; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                tr:nth-child(even) {{ background-color: #f9f9f9; }}
                .summary {{ background-color: #e8f4f8; padding: 15px; border-radius: 5px; margin-bottom: 20px; }}
                .trial-card {{ border: 1px solid #ddd; padding: 15px; margin-bottom: 15px; border-radius: 5px; }}
                .significant {{ color: green; font-weight: bold; }}
                .non-significant {{ color: red; }}
            </style>
        </head>
        <body>
            <h1>PAH Clinical Trial Endpoint Analysis</h1>
            <div class="summary">
                <h2>Analysis Summary</h2>
                <p>This report analyzes endpoint data from clinical trials focused on Pulmonary Arterial Hypertension (PAH).</p>
                <ul>
                    <li><strong>Number of Trials Analyzed:</strong> {len(trials)}</li>
                    <li><strong>Common Endpoints:</strong> {", ".join(endpoints) if endpoints else "None found"}</li>
                </ul>
            </div>
            
            <h2>Trial Summary</h2>
            <table>
                <tr>
                    <th>NCT ID</th>
                    <th>Title</th>
                    <th>Sponsor</th>
                    <th>Phase</th>
                    <th>Participants</th>
                </tr>
        """
        
        # Add trial summary rows
        for trial in trials:
            study_info = trial.get("clinical_study", {})
            nct_id = study_info.get("nct_identifier", "Unknown")
            title = study_info.get("title", "Unknown")
            sponsor = study_info.get("sponsor", "Unknown")
            phase = study_info.get("phase", "Unknown")
            participants = study_info.get("number_of_participants", 0)
            
            html_content += f"""
                <tr>
                    <td>{nct_id}</td>
                    <td>{title}</td>
                    <td>{sponsor}</td>
                    <td>{phase}</td>
                    <td>{participants}</td>
                </tr>
            """
        
        html_content += """
            </table>
            
            <h2>Detailed Endpoint Analysis</h2>
        """
        
        # Add endpoint analysis for each endpoint
        for endpoint in endpoints:
            html_content += f"""
            <h3>Endpoint: {endpoint}</h3>
            <table>
                <tr>
                    <th>Trial</th>
                    <th>Intervention (Mean)</th>
                    <th>Placebo (Mean)</th>
                    <th>Effect Size</th>
                    <th>P-value</th>
                </tr>
            """
            
            # Extract data for this endpoint
            df = self.extract_endpoints_data(trials, endpoint_type=endpoint)
            
            # Get list of trials with this endpoint
            trial_ids = df["nct_id"].unique()
            
            for trial_id in trial_ids:
                trial_data = df[df["nct_id"] == trial_id]
                
                # Get intervention and placebo data
                intervention_data = trial_data[trial_data["arm"] == "intervention"]
                placebo_data = trial_data[trial_data["arm"] == "placebo"]
                
                # Extract values
                int_value = intervention_data["average_value"].values[0] if not intervention_data.empty and not pd.isna(intervention_data["average_value"].values[0]) else "N/A"
                placebo_value = placebo_data["average_value"].values[0] if not placebo_data.empty and not pd.isna(placebo_data["average_value"].values[0]) else "N/A"
                
                # Calculate effect size
                effect_size = "N/A"
                if isinstance(int_value, (int, float)) and isinstance(placebo_value, (int, float)):
                    effect_size = round(int_value - placebo_value, 2)
                
                # Get p-value
                p_value = intervention_data["significance"].values[0] if not intervention_data.empty else "N/A"
                
                # Determine if significant
                is_significant = False
                if isinstance(p_value, str):
                    p_value_lower = p_value.lower()
                    if "p<0.05" in p_value_lower or "p = 0.05" in p_value_lower or "p<.05" in p_value_lower:
                        is_significant = True
                    elif "p=" in p_value_lower or "p =" in p_value_lower:
                        p_match = re.search(r'p\s*=\s*(0\.\d+)', p_value_lower)
                        if p_match:
                            try:
                                actual_p = float(p_match.group(1))
                                is_significant = actual_p < 0.05
                            except ValueError:
                                pass
                
                # Get trial name
                trial_name = trial_data["study"].values[0] if not trial_data.empty else "Unknown"
                
                # Add to table
                significance_class = "significant" if is_significant else "non-significant"
                html_content += f"""
                <tr>
                    <td>{trial_name} ({trial_id})</td>
                    <td>{int_value}</td>
                    <td>{placebo_value}</td>
                    <td>{effect_size}</td>
                    <td class="{significance_class}">{p_value}</td>
                </tr>
                """
            
            html_content += """
            </table>
            """
        
        html_content += """
        </body>
        </html>
        """
        
        # Write HTML to file
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print(f"Created HTML report: {output_path}")
        return output_path


def main():
    """Main entry point for endpoint processing."""
    # Initialize the processor
    processor = EndpointProcessor()
    
    # Load all trials
    trials = processor.load_all_trials()
    
    if not trials:
        print("No trial data found. Please run trial_processor.py first.")
        return
    
    # Find common endpoints
    common_endpoints = processor.find_common_endpoints(trials)
    print(f"Most common endpoints: {common_endpoints}")
    
    # Visualize common endpoints
    visualization_paths = processor.visualize_all_common_endpoints(trials)
    
    print(f"Created {len(visualization_paths)} visualizations:")
    for path in visualization_paths:
        print(f"  - {path}")


if __name__ == "__main__":
    main()