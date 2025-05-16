"""
Visualization module for the Clinical Trial & Corporate Disclosure Extraction Pipeline.

This module creates visualizations for clinical trial data, including:
- Endpoint comparisons across trials
- Baseline measure comparisons
- Interactive dashboards
- Financial data from SEC filings related to clinical trials
"""

import os
import sys
import json
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.gridspec import GridSpec
import matplotlib.ticker as mtick
from pathlib import Path
import re

# Add the project root to the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(src_dir)
sys.path.append(project_root)

from src.utils.paths import get_processed_dir, get_json_dir, get_visualizations_dir
from src.data_processors.endpoint_processor import EndpointProcessor


class VisualizationGenerator:
    """Generator for clinical trial data visualizations."""
    
    def __init__(self):
        """Initialize the visualization generator."""
        self.processed_dir = get_processed_dir()
        self.json_dir = get_json_dir()
        self.visualizations_dir = get_visualizations_dir()
        
        # Ensure directories exist
        os.makedirs(self.processed_dir, exist_ok=True)
        os.makedirs(self.json_dir, exist_ok=True)
        os.makedirs(self.visualizations_dir, exist_ok=True)
        
        # Create endpoint processor
        self.endpoint_processor = EndpointProcessor()
        
        # Set plot style
        sns.set_theme(style="whitegrid")
        plt.rcParams['font.family'] = 'sans-serif'
        plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'Liberation Sans']
        
    def load_all_trials(self):
        """
        Load all processed trial data.
        
        Returns:
            List of trial data dictionaries
        """
        return self.endpoint_processor.load_all_trials()
    
    def create_trial_summary_dashboard(self, trials, save_path=None):
        """
        Create a dashboard summarizing all trials.
        
        Args:
            trials: List of trial data dictionaries
            save_path: Path to save the dashboard (if None, display instead)
            
        Returns:
            Path to the saved dashboard if save_path is provided
        """
        # Create a figure with subplots
        fig = plt.figure(figsize=(15, 12))
        gs = GridSpec(3, 3, figure=fig)
        
        # Extract trial information
        trial_info = []
        for trial in trials:
            study_info = trial.get("clinical_study", {})
            trial_info.append({
                "nct_id": study_info.get("nct_identifier", "Unknown"),
                "title": study_info.get("title", "Unknown"),
                "sponsor": study_info.get("sponsor", "Unknown"),
                "phase": study_info.get("phase", "Unknown"),
                "participants": study_info.get("number_of_participants", 0),
                "avg_age": study_info.get("average_age", 0),
                "intervention_arms": study_info.get("study_arms", {}).get("intervention", 0),
                "placebo_arms": study_info.get("study_arms", {}).get("placebo", 0)
            })
        
        df = pd.DataFrame(trial_info)
        
        # 1. Number of participants by trial
        ax1 = fig.add_subplot(gs[0, 0:2])
        sns.barplot(x="nct_id", y="participants", data=df, ax=ax1, palette="Blues_d")
        ax1.set_title("Number of Participants by Trial", fontsize=12)
        ax1.set_xlabel("NCT ID", fontsize=10)
        ax1.set_ylabel("Number of Participants", fontsize=10)
        ax1.tick_params(axis='x', rotation=45)
        
        # 2. Phases distribution
        ax2 = fig.add_subplot(gs[0, 2])
        phase_counts = df["phase"].value_counts()
        colors = sns.color_palette("Blues_d", len(phase_counts))
        ax2.pie(phase_counts, labels=phase_counts.index, autopct='%1.1f%%', colors=colors, startangle=90)
        ax2.set_title("Distribution of Trial Phases", fontsize=12)
        
        # 3. Average age by trial
        ax3 = fig.add_subplot(gs[1, 0])
        sns.barplot(x="nct_id", y="avg_age", data=df, ax=ax3, palette="Greens_d")
        ax3.set_title("Average Age of Participants", fontsize=12)
        ax3.set_xlabel("NCT ID", fontsize=10)
        ax3.set_ylabel("Average Age (years)", fontsize=10)
        ax3.tick_params(axis='x', rotation=45)
        
        # 4. Intervention vs. Placebo Arms
        ax4 = fig.add_subplot(gs[1, 1:3])
        df_arms = pd.melt(df, id_vars=["nct_id"], value_vars=["intervention_arms", "placebo_arms"],
                          var_name="arm_type", value_name="count")
        sns.barplot(x="nct_id", y="count", hue="arm_type", data=df_arms, ax=ax4, palette=["steelblue", "lightgray"])
        ax4.set_title("Number of Intervention and Placebo Arms by Trial", fontsize=12)
        ax4.set_xlabel("NCT ID", fontsize=10)
        ax4.set_ylabel("Number of Arms", fontsize=10)
        ax4.tick_params(axis='x', rotation=45)
        ax4.legend(title="Arm Type", labels=["Intervention", "Placebo"])
        
        # 5. Sponsors
        ax5 = fig.add_subplot(gs[2, 0:3])
        sponsor_counts = df["sponsor"].value_counts().reset_index()
        sponsor_counts.columns = ["sponsor", "count"]
        sns.barplot(x="sponsor", y="count", data=sponsor_counts, ax=ax5, palette="Blues_d")
        ax5.set_title("Number of Trials by Sponsor", fontsize=12)
        ax5.set_xlabel("Sponsor", fontsize=10)
        ax5.set_ylabel("Number of Trials", fontsize=10)
        ax5.tick_params(axis='x', rotation=45)
        
        # Add title to the entire figure
        fig.suptitle("Clinical Trial Summary Dashboard", fontsize=16, y=0.98)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        # Save or display the figure
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()
            print(f"Saved dashboard to {save_path}")
            return save_path
        else:
            plt.show()
            plt.close()
            return None
    
    def create_endpoint_comparison_grid(self, trials, top_n=3, save_path=None):
        """
        Create a grid of visualizations for the top endpoints.
        
        Args:
            trials: List of trial data dictionaries
            top_n: Number of top endpoints to visualize
            save_path: Path to save the grid (if None, display instead)
            
        Returns:
            Path to the saved grid if save_path is provided
        """
        # Find common endpoints
        common_endpoints = self.endpoint_processor.find_common_endpoints(trials, top_n=top_n)
        
        if not common_endpoints:
            print("No common endpoints found across trials.")
            return None
        
        # Calculate grid dimensions
        n_endpoints = len(common_endpoints)
        n_cols = min(2, n_endpoints)
        n_rows = (n_endpoints + n_cols - 1) // n_cols
        
        # Create figure with subplots
        fig, axes = plt.subplots(n_rows, n_cols, figsize=(15, 6 * n_rows))
        if n_rows * n_cols == 1:  # Handle single subplot case
            axes = np.array([axes])
        axes = axes.flatten()
        
        # Create a visualization for each endpoint
        for i, endpoint in enumerate(common_endpoints):
            if i >= len(axes):
                break
                
            # Extract data for this endpoint
            df = self.endpoint_processor.extract_endpoints_data(trials, endpoint_type=endpoint)
            
            # Skip if no data
            if df.empty:
                axes[i].text(0.5, 0.5, f"No data for {endpoint}", 
                            ha='center', va='center', fontsize=12)
                axes[i].axis('off')
                continue
            
            # Filter for valid numeric data
            df_plot = df.dropna(subset=['average_value']).copy()
            
            if df_plot.empty:
                axes[i].text(0.5, 0.5, f"No numeric data for {endpoint}", 
                            ha='center', va='center', fontsize=12)
                axes[i].axis('off')
                continue
            
            # Create a grouped bar chart
            sns.barplot(
                x="nct_id", 
                y="average_value",
                hue="arm",
                data=df_plot,
                ax=axes[i],
                palette={"intervention": "steelblue", "placebo": "lightgray"},
                errorbar=None
            )
            
            # Add value labels
            for p in axes[i].patches:
                height = p.get_height()
                if not np.isnan(height):
                    axes[i].annotate(
                        f"{height:.1f}",
                        (p.get_x() + p.get_width() / 2., height),
                        ha='center',
                        va='bottom',
                        fontsize=8,
                        color='black',
                        xytext=(0, 5),
                        textcoords='offset points'
                    )
            
            # Customize plot
            axes[i].set_title(f"{endpoint} Comparison", fontsize=12)
            axes[i].set_xlabel("NCT ID", fontsize=10)
            axes[i].set_ylabel(f"{endpoint} Value", fontsize=10)
            axes[i].tick_params(axis='x', rotation=45)
            
            # Add legend only to the first plot to avoid duplication
            if i > 0:
                axes[i].get_legend().remove()
        
        # Remove any unused subplots
        for i in range(n_endpoints, len(axes)):
            fig.delaxes(axes[i])
        
        # Add title to the entire figure
        fig.suptitle("Endpoint Comparisons Across PAH Clinical Trials", fontsize=16, y=0.98)
        plt.tight_layout(rect=[0, 0, 1, 0.96])
        
        # Save or display the figure
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()
            print(f"Saved endpoint comparison grid to {save_path}")
            return save_path
        else:
            plt.show()
            plt.close()
            return None
    
    def create_treatment_effect_heatmap(self, trials, save_path=None):
        """
        Create a heatmap showing treatment effects across trials and endpoints.
        
        Args:
            trials: List of trial data dictionaries
            save_path: Path to save the heatmap (if None, display instead)
            
        Returns:
            Path to the saved heatmap if save_path is provided
        """
        # Extract all endpoints
        all_endpoints_df = self.endpoint_processor.extract_endpoints_data(trials)
        
        if all_endpoints_df.empty:
            print("No endpoint data found.")
            return None
        
        # Get unique normalized endpoints
        unique_endpoints = all_endpoints_df["endpoint"].unique()
        
        # Get all trial NCT IDs
        trial_ids = [t.get("clinical_study", {}).get("nct_identifier", "Unknown") for t in trials]
        trial_ids = [tid for tid in trial_ids if tid != "Unknown"]
        
        # Create a DataFrame to store treatment effects
        heatmap_data = []
        
        for endpoint in unique_endpoints:
            endpoint_df = all_endpoints_df[all_endpoints_df["endpoint"] == endpoint]
            
            for trial_id in trial_ids:
                trial_data = endpoint_df[endpoint_df["nct_id"] == trial_id]
                
                # Get intervention and placebo data
                intervention_data = trial_data[trial_data["arm"] == "intervention"]
                placebo_data = trial_data[trial_data["arm"] == "placebo"]
                
                if not intervention_data.empty and not placebo_data.empty:
                    int_value = intervention_data["average_value"].values[0]
                    placebo_value = placebo_data["average_value"].values[0]
                    
                    if pd.notnull(int_value) and pd.notnull(placebo_value):
                        # Calculate effect (treatment - placebo)
                        effect = int_value - placebo_value
                        
                        # Get p-value
                        p_value = intervention_data["significance"].values[0]
                        is_significant = False
                        
                        # Check for common p-value formats
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
                        
                        heatmap_data.append({
                            "trial_id": trial_id,
                            "endpoint": endpoint,
                            "effect": effect,
                            "is_significant": is_significant
                        })
                    
        if not heatmap_data:
            print("No treatment effect data available.")
            return None
            
        # Create DataFrame for the heatmap
        heatmap_df = pd.DataFrame(heatmap_data)
        
        # Pivot the data for the heatmap
        pivot_df = heatmap_df.pivot_table(index="trial_id", columns="endpoint", values="effect", aggfunc="first")
        
        # Create a mask for significant values
        significance_pivot = heatmap_df.pivot_table(
            index="trial_id", 
            columns="endpoint", 
            values="is_significant", 
            aggfunc="first"
        )
        
        # Create the figure
        plt.figure(figsize=(12, 8))
        
        # Create heatmap
        ax = sns.heatmap(
            pivot_df,
            cmap="RdBu_r",
            center=0,
            annot=True,
            fmt=".1f",
            linewidths=.5,
            cbar_kws={"label": "Treatment Effect (Intervention - Placebo)"}
        )
        
        # Add markers for statistical significance
        for i, idx in enumerate(pivot_df.index):
            for j, col in enumerate(pivot_df.columns):
                if significance_pivot.loc[idx, col]:
                    ax.text(j + 0.5, i + 0.85, '*', color='black', 
                           ha='center', va='center', fontsize=16)
        
        # Customize plot
        plt.title("Treatment Effect Heatmap Across PAH Clinical Trials", fontsize=14)
        plt.ylabel("Clinical Trial (NCT ID)", fontsize=12)
        plt.xlabel("Endpoint", fontsize=12)
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        
        # Add a note about significance
        plt.figtext(0.01, 0.01, "* Statistically significant (p<0.05)", fontsize=9)
        
        # Save or display the figure
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()
            print(f"Saved treatment effect heatmap to {save_path}")
            return save_path
        else:
            plt.show()
            plt.close()
            return None
    
    def create_baseline_comparison(self, trials, measure_type=None, save_path=None):
        """
        Create a comparison of baseline measures across trials.
        
        Args:
            trials: List of trial data dictionaries
            measure_type: Type of baseline measure to compare (if None, use the most common)
            save_path: Path to save the comparison (if None, display instead)
            
        Returns:
            Path to the saved comparison if save_path is provided
        """
        # Extract baseline data
        baseline_df = self.endpoint_processor.extract_baseline_data(trials, measure_type)
        
        if baseline_df.empty:
            print("No baseline data found.")
            return None
        
        # If no specific measure type provided, use the most common one
        if not measure_type:
            measure_counts = baseline_df['measure'].value_counts()
            if not measure_counts.empty:
                measure_type = measure_counts.index[0]
                print(f"Using most common baseline measure: {measure_type}")
                baseline_df = baseline_df[baseline_df['measure'] == measure_type]
            else:
                print("No baseline measures found.")
                return None
        
        # Filter for valid numeric data
        baseline_df = baseline_df.dropna(subset=['average_value']).copy()
        
        if baseline_df.empty:
            print(f"No valid numeric data for baseline measure: {measure_type}")
            return None
        
        # Create the figure
        plt.figure(figsize=(14, 8))
        
        # Create a grouped bar chart
        ax = sns.barplot(
            x="nct_id",
            y="average_value",
            hue="arm",
            data=baseline_df,
            palette={"intervention": "steelblue", "placebo": "lightgray"},
            errorbar=None
        )
        
        # Add value labels
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
        
        # Add error bars if available
        for i, row in baseline_df.iterrows():
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
        
        # Customize plot
        plt.title(f"Baseline {measure_type} Comparison Across PAH Clinical Trials", fontsize=14)
        plt.xlabel("Clinical Trial (NCT ID)", fontsize=12)
        plt.ylabel(f"Baseline {measure_type} Value", fontsize=12)
        plt.xticks(rotation=45, ha="right")
        plt.legend(title="Treatment Arm")
        plt.tight_layout()
        
        # Save or display the figure
        if save_path:
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            plt.savefig(save_path, dpi=300, bbox_inches="tight")
            plt.close()
            print(f"Saved baseline comparison to {save_path}")
            return save_path
        else:
            plt.show()
            plt.close()
            return None
    
    def create_all_visualizations(self, output_dir=None):
        """
        Create all visualizations for the clinical trial data.
        
        Args:
            output_dir: Directory to save visualizations (default: visualizations_dir)
            
        Returns:
            List of paths to saved visualizations
        """
        if output_dir is None:
            output_dir = self.visualizations_dir
        
        os.makedirs(output_dir, exist_ok=True)
        
        # Load all trials
        trials = self.load_all_trials()
        
        if not trials:
            print("No trial data found. Please run trial_processor.py first.")
            return []
        
        visualization_paths = []
        
        # 1. Create trial summary dashboard
        dashboard_path = os.path.join(output_dir, "trial_summary_dashboard.png")
        path = self.create_trial_summary_dashboard(trials, save_path=dashboard_path)
        if path:
            visualization_paths.append(path)
        
        # 2. Create endpoint comparison grid
        grid_path = os.path.join(output_dir, "endpoint_comparison_grid.png")
        path = self.create_endpoint_comparison_grid(trials, save_path=grid_path)
        if path:
            visualization_paths.append(path)
        
        # 3. Create treatment effect heatmap
        heatmap_path = os.path.join(output_dir, "treatment_effect_heatmap.png")
        path = self.create_treatment_effect_heatmap(trials, save_path=heatmap_path)
        if path:
            visualization_paths.append(path)
        
        # 4. Create baseline comparisons for common measures
        baseline_df = self.endpoint_processor.extract_baseline_data(trials)
        if not baseline_df.empty:
            measure_counts = baseline_df['measure'].value_counts()
            for i, measure in enumerate(measure_counts.index[:3]):  # Top 3 measures
                baseline_path = os.path.join(output_dir, f"baseline_{measure.replace(' ', '_')}_comparison.png")
                path = self.create_baseline_comparison(trials, measure, save_path=baseline_path)
                if path:
                    visualization_paths.append(path)
        
        # 5. Also include the visualizations from the endpoint processor
        ep_paths = self.endpoint_processor.visualize_all_common_endpoints(trials, output_dir=output_dir)
        if ep_paths:
            visualization_paths.extend(ep_paths)
        
        print(f"Created {len(visualization_paths)} visualizations:")
        for path in visualization_paths:
            print(f"  - {path}")
        
        return visualization_paths


def main():
    """Main entry point for visualization generation."""
    # Initialize the visualization generator
    generator = VisualizationGenerator()
    
    # Create all visualizations
    visualization_paths = generator.create_all_visualizations()
    
    if not visualization_paths:
        print("No visualizations were created. Please check if trial data is available.")


if __name__ == "__main__":
    main()