"""
Streamlit frontend for Clinical Trials Pipeline.
"""

import os
import sys
import json
import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from PIL import Image
import time
import altair as alt
from io import BytesIO
import base64
import math

# Add project root to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.dirname(current_dir)
project_root = os.path.dirname(src_dir)
sys.path.append(project_root)

# Set API URL (change if deployed elsewhere)
API_URL = "http://localhost:8000"

# ---- THEME CONFIGURATION ----
# Set Streamlit theme
st.set_page_config(
    page_title="PAH Clinical Trials Analytics",
    page_icon="🫀",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for more professional look
st.markdown("""
<style>
    /* Main header styling */
    .main-header {
        font-size: 2.5rem;
        color: #1E88E5;
        font-weight: 700;
    }
    
    /* Subheader styling */
    .sub-header {
        font-size: 1.8rem;
        color: #0D47A1;
        font-weight: 600;
    }
    
    /* Section header styling */
    .section-header {
        font-size: 1.5rem;
        font-weight: 600;
        color: #1565C0;
        margin-top: 1rem;
        margin-bottom: 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 1px solid #E0E0E0;
    }
    
    /* Card styling */
    .card {
        padding: 1.5rem;
        border-radius: 0.5rem;
        background-color: #f9f9f9;
        box-shadow: 0 0.15rem 0.5rem rgba(0, 0, 0, 0.1);
        margin-bottom: 1.5rem;
    }
    
    /* Metric label */
    .metric-label {
        font-size: 1rem;
        color: #555;
        font-weight: 400;
    }
    
    /* Metric value */
    .metric-value {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1E88E5;
    }
    
    /* Data table styling */
    .dataframe-container {
        padding: 0.5rem;
        border-radius: 0.5rem;
        background-color: #ffffff;
        box-shadow: 0 0.15rem 0.5rem rgba(0, 0, 0, 0.05);
    }
    
    /* Status indicators */
    .status-success {
        color: #4CAF50;
        font-weight: 500;
    }
    
    .status-warning {
        color: #FF9800;
        font-weight: 500;
    }
    
    .status-error {
        color: #F44336;
        font-weight: 500;
    }
    
    /* Sidebar styling */
    .sidebar .sidebar-content {
        background-color: #f5f5f5;
    }
    
    /* Custom button styling */
    .stButton > button {
        background-color: #1976D2;
        color: white;
        border-radius: 0.3rem;
        border: none;
        padding: 0.5rem 1rem;
        font-weight: 600;
    }
    
    .stButton > button:hover {
        background-color: #1565C0;
    }
    
    /* Footer styling */
    .footer {
        text-align: center;
        margin-top: 3rem;
        padding-top: 1rem;
        border-top: 1px solid #e0e0e0;
        color: #9e9e9e;
        font-size: 0.8rem;
    }
</style>
""", unsafe_allow_html=True)

# ---- HELPER FUNCTIONS ----

# Function to create a base64 encoded string for download links
def get_download_link(df, filename, text):
    csv = df.to_csv(index=False)
    b64 = base64.b64encode(csv.encode()).decode()
    href = f'<a href="data:file/csv;base64,{b64}" download="{filename}" class="custom-button">{text}</a>'
    return href

# Function for animated progress tracking
def progress_tracker(task_name):
    progress_bar = st.progress(0)
    status_text = st.empty()
    for i in range(101):
        progress_bar.progress(i)
        if i < 70:
            status_text.text(f"{task_name}... ({i}%)")
        elif i < 90:
            status_text.text(f"{task_name}... Processing data ({i}%)")
        else:
            status_text.text(f"{task_name}... Finalizing ({i}%)")
        time.sleep(0.01)
    status_text.empty()
    progress_bar.empty()

# Function to load trials with robust error handling
@st.cache_data
def load_trials():
    with st.spinner("Loading clinical trial data..."):
        try:
            # First check if API is available
            try:
                health_response = requests.get(f"{API_URL}/health", timeout=5)
                health_response.raise_for_status()
                st.success(f"✅ API connected successfully: {health_response.json().get('status', 'healthy')}")
            except:
                st.warning("⚠️ API health check failed - using fallback data")
            
            # Try to get trial data
            response = requests.get(f"{API_URL}/trials", timeout=10)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            st.error(f"❌ Cannot connect to API at {API_URL}. Make sure the FastAPI server is running.")
            return load_fallback_trials()
        except requests.exceptions.HTTPError as e:
            st.error(f"❌ HTTP error: {e}")
            return load_fallback_trials()
        except Exception as e:
            st.error(f"❌ Error loading trials: {str(e)}")
            return load_fallback_trials()

# Fallback function to load trial data from JSON files
def load_fallback_trials():
    st.info("ℹ️ Loading data directly from JSON files...")
    try:
        json_dir = os.path.join(project_root, "data", "outputs", "json")
        trials = []
        
        # Get NCT files
        json_files = [f for f in os.listdir(json_dir) if f.endswith('.json') and f.startswith('NCT')]
        
        progress_tracker("Reading JSON files")
        
        # Extract basic trial info from each file
        for json_file in json_files[:10]:  # Limit to 10 for performance
            file_path = os.path.join(json_dir, json_file)
            with open(file_path, 'r') as f:
                data = json.load(f)
                study_info = data.get("clinical_study", {})
                
                trials.append({
                    "id": len(trials) + 1,
                    "title": study_info.get("title", "Unknown"),
                    "nct_identifier": study_info.get("nct_identifier", "Unknown"),
                    "indication": study_info.get("indication", "Unknown"),
                    "intervention": study_info.get("intervention", "Unknown"),
                    "phase": study_info.get("phase", "Unknown"),
                    "sponsor": study_info.get("sponsor", "Unknown"),
                    "number_of_participants": study_info.get("number_of_participants", 0),
                    "average_age": study_info.get("average_age", 0)
                })
        
        return trials
    except Exception as e:
        st.error(f"❌ Failed to load fallback data: {str(e)}")
        return []

# Function to load specific trial with fallback
@st.cache_data
def load_trial(nct_id):
    with st.spinner(f"Loading details for trial {nct_id}..."):
        try:
            response = requests.get(f"{API_URL}/trials/{nct_id}", timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.warning(f"⚠️ API error: {str(e)}. Loading from JSON file.")
            try:
                # Try loading from JSON
                json_path = os.path.join(project_root, "data", "outputs", "json", f"{nct_id}.json")
                with open(json_path, 'r') as f:
                    return json.load(f)
            except Exception as file_e:
                st.error(f"❌ Failed to load trial data: {str(file_e)}")
                return None

# Function to compare endpoints with fallback
@st.cache_data
def compare_endpoint(endpoint_name, include_placebo=True):
    with st.spinner(f"Analyzing {endpoint_name} across trials..."):
        try:
            response = requests.get(
                f"{API_URL}/endpoints/{endpoint_name}",
                params={"include_placebo": include_placebo},
                timeout=10
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            st.warning(f"⚠️ API error: {str(e)}. Loading endpoint data from JSON files.")
            try:
                progress_tracker("Extracting endpoint data")
                # Load from JSON files
                json_dir = os.path.join(project_root, "data", "outputs", "json")
                json_files = [f for f in os.listdir(json_dir) if f.endswith('.json') and f.startswith('NCT')]
                
                endpoint_data = []
                for json_file in json_files:
                    file_path = os.path.join(json_dir, json_file)
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    study_info = data.get("clinical_study", {})
                    nct_id = study_info.get("nct_identifier", "")
                    title = study_info.get("title", "")
                    sponsor = study_info.get("sponsor", "")
                    
                    for endpoint in data.get("endpoints", []):
                        if endpoint_name.lower() in endpoint.get("name", "").lower():
                            # Skip if placebo not included
                            if not include_placebo and endpoint.get("arm") == "placebo":
                                continue
                            
                            endpoint_data.append({
                                "nct_id": nct_id,
                                "study_title": title,
                                "sponsor": sponsor,
                                "endpoint_name": endpoint.get("name", ""),
                                "arm": endpoint.get("arm", ""),
                                "timepoint": endpoint.get("timepoint", ""),
                                "value": endpoint.get("average_value"),
                                "upper_end": endpoint.get("upper_end"),
                                "lower_end": endpoint.get("lower_end"),
                                "p_value": endpoint.get("statistical_significance", "")
                            })
                
                return endpoint_data
            except Exception as file_e:
                st.error(f"❌ Failed to load endpoint data: {str(file_e)}")
                return []

# ---- SIDEBAR & NAVIGATION ----
with st.sidebar:
    st.image("https://img.icons8.com/?size=100&id=ZJZP37RNt9kj&format=png", width=100)
    st.markdown("<h1 style='text-align: center;'>PAH Trials Analytics</h1>", unsafe_allow_html=True)
    st.markdown("---")
    
    page = st.radio(
        "Select a page",
        ["Trials Overview", "Trial Details", "Endpoint Comparison", "About"],
        index=0
    )
    
    st.markdown("---")
    with st.expander("⚙️ Advanced Settings"):
        cache_option = st.checkbox("Use Cache", value=True, help="Cache data for faster loading")
        theme = st.selectbox("Color Theme", ["Blue", "Green", "Purple", "Orange"], index=0)
        display_limit = st.slider("Display Limit", min_value=5, max_value=50, value=10, help="Maximum number of items to display")
    
    st.markdown("---")
    st.markdown("<div class='footer'>Developed for Clinical Trials & Corporate Disclosure Extraction Pipeline</div>", unsafe_allow_html=True)

# ---- LOAD TRIALS DATA ----
trials = load_trials()

# ---- MAIN CONTENT ----
# Trials Overview Page
if page == "Trials Overview":
    # Main title
    st.markdown("<h1 class='main-header'>Clinical Trials Overview</h1>", unsafe_allow_html=True)
    st.markdown("<p>Comprehensive analysis of PAH clinical trials with their key metrics and distributions.</p>", unsafe_allow_html=True)
    
    if trials:
        # Convert to DataFrame for display
        df_trials = pd.DataFrame(trials)
        
        # Key metrics section
        st.markdown("<h2 class='section-header'>Key Metrics</h2>", unsafe_allow_html=True)
        
        # Create three metric cards in columns
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-label'>Total Trials</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{len(df_trials)}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col2:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-label'>Average Participants</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{round(df_trials['number_of_participants'].mean())}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
        
        with col3:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-label'>Average Age</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{round(df_trials['average_age'].mean(), 1)}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        with col4:
            st.markdown("<div class='card'>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-label'>Unique Sponsors</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='metric-value'>{df_trials['sponsor'].nunique()}</div>", unsafe_allow_html=True)
            st.markdown("</div>", unsafe_allow_html=True)
            
        # Interactive plots section
        st.markdown("<h2 class='section-header'>Trial Distribution Analysis</h2>", unsafe_allow_html=True)
        
        col1, col2 = st.columns(2)
        
        with col1:
            # Interactive sponsor bar chart
            sponsor_counts = df_trials["sponsor"].value_counts().reset_index()
            sponsor_counts.columns = ["Sponsor", "Count"]
            
            # Improved bar chart
            fig = px.bar(
                sponsor_counts,
                x="Count",
                y="Sponsor",
                title="Trials by Sponsor",
                color="Count",
                color_continuous_scale="Blues",
                orientation='h'
            )
            
            fig.update_layout(
                height=400,
                yaxis_title="",
                xaxis_title="Number of Trials",
                coloraxis_showscale=False,
                title_font_size=18,
                font=dict(family="Arial", size=12),
                title_font_family="Arial",
                title_x=0.5,
                margin=dict(l=20, r=20, t=50, b=20),
                plot_bgcolor='white'
            )
            
            st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            # Phase distribution pie chart with better colors
            phase_counts = df_trials["phase"].value_counts().reset_index()
            phase_counts.columns = ["Phase", "Count"]
            
            # Custom color sequence
            color_sequence = ['#1f77b4', '#2ca02c', '#d62728', '#9467bd', '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22']
            
            fig = px.pie(
                phase_counts,
                names="Phase",
                values="Count",
                title="Trial Phase Distribution",
                color_discrete_sequence=color_sequence,
                hole=0.4
            )
            
            fig.update_layout(
                height=400,
                legend_title="",
                title_font_size=18,
                font=dict(family="Arial", size=12),
                title_font_family="Arial",
                title_x=0.5,
                margin=dict(l=20, r=20, t=50, b=20)
            )
            
            # Add percentage labels
            fig.update_traces(textposition='inside', textinfo='percent+label')
            
            st.plotly_chart(fig, use_container_width=True)
        
        # Participants by trial chart
        st.markdown("<h2 class='section-header'>Participant Analysis</h2>", unsafe_allow_html=True)
        
        # Sort trials by number of participants
        df_participants = df_trials.sort_values(by="number_of_participants", ascending=False)
        df_participants = df_participants.head(10)  # Top 10 by participants
        
        # Create bar chart with enhanced styling
        fig = px.bar(
            df_participants,
            x="nct_identifier",
            y="number_of_participants",
            title="Number of Participants by Trial (Top 10)",
            color="number_of_participants",
            color_continuous_scale="Viridis",
            labels={"nct_identifier": "Trial ID", "number_of_participants": "Number of Participants"}
        )
        
        # Add trial titles as hover text
        fig.update_traces(
            hovertemplate="<b>%{x}</b><br>" +
                         "Trial: %{customdata}<br>" +
                         "Participants: %{y}<extra></extra>",
            customdata=df_participants["title"].tolist()
        )
        
        fig.update_layout(
            height=500,
            xaxis_title="Clinical Trial",
            yaxis_title="Number of Participants",
            coloraxis_showscale=False,
            title_font_size=18,
            font=dict(family="Arial", size=12),
            title_font_family="Arial",
            title_x=0.5,
            xaxis_tickangle=-45,
            margin=dict(l=20, r=20, t=50, b=100),
            plot_bgcolor='white'
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Detailed trial data with filtering
        st.markdown("<h2 class='section-header'>Trial Data Explorer</h2>", unsafe_allow_html=True)
        
        # Add filters
        col1, col2, col3 = st.columns(3)
        with col1:
            selected_sponsors = st.multiselect("Filter by Sponsor", options=sorted(df_trials["sponsor"].unique()), default=[])
        with col2:
            selected_phases = st.multiselect("Filter by Phase", options=sorted(df_trials["phase"].unique()), default=[])
        with col3:
            search_term = st.text_input("Search Trials", "")
        
        # Apply filters
        filtered_df = df_trials.copy()
        
        if selected_sponsors:
            filtered_df = filtered_df[filtered_df["sponsor"].isin(selected_sponsors)]
            
        if selected_phases:
            filtered_df = filtered_df[filtered_df["phase"].isin(selected_phases)]
            
        if search_term:
            search_mask = (
                filtered_df["title"].str.contains(search_term, case=False) | 
                filtered_df["nct_identifier"].str.contains(search_term, case=False) |
                filtered_df["indication"].str.contains(search_term, case=False)
            )
            filtered_df = filtered_df[search_mask]
        
        # Display filtered dataframe
        st.markdown("<div class='dataframe-container'>", unsafe_allow_html=True)
        st.dataframe(
            filtered_df[["nct_identifier", "title", "sponsor", "phase", "indication", "number_of_participants"]],
            use_container_width=True,
            column_config={
                "nct_identifier": "NCT ID",
                "title": "Trial Title",
                "sponsor": "Sponsor",
                "phase": "Phase",
                "indication": "Indication",
                "number_of_participants": "Participants"
            },
            height=400
        )
        st.markdown("</div>", unsafe_allow_html=True)
        
        # Export data option
        st.download_button(
            label="📊 Export Data as CSV",
            data=filtered_df.to_csv(index=False).encode('utf-8'),
            file_name="pah_trials_data.csv",
            mime='text/csv'
        )
        
    else:
        st.error("❌ No trials data available. Please check API connection.")

# Trial Details Page  
elif page == "Trial Details":
    # Main title with styling
    st.markdown("<h1 class='main-header'>Trial Details</h1>", unsafe_allow_html=True)
    st.markdown("<p>Explore comprehensive information about individual clinical trials.</p>", unsafe_allow_html=True)
    
    if trials:
        # Create a more attractive selection box for trials
        st.markdown("<h2 class='section-header'>Select a Trial</h2>", unsafe_allow_html=True)
        
        # Format options to show more information
        trial_options = {
            f"{t['nct_identifier']} - {t['sponsor']} - {t['phase']}": 
            t['nct_identifier'] for t in trials
        }
        
        # Use a selectbox with a more detailed format
        selected_trial = st.selectbox(
            "Choose a clinical trial to view details",
            list(trial_options.keys()),
            format_func=lambda x: x
        )
        
        if selected_trial:
            with st.spinner("Loading trial details..."):
                nct_id = trial_options[selected_trial]
                trial_data = load_trial(nct_id)
                
                if trial_data:
                    # Get main trial info
                    study = trial_data["clinical_study"]
                    
                    # Create two columns layout
                    col1, col2 = st.columns([2, 1])
                    
                    with col1:
                        # Main title and basic info
                        st.markdown(f"<h2 class='sub-header'>{study['title']}</h2>", unsafe_allow_html=True)
                        
                        # Information card
                        st.markdown("<div class='card'>", unsafe_allow_html=True)
                        st.markdown(f"<p><strong>NCT ID:</strong> {study['nct_identifier']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p><strong>Indication:</strong> {study['indication']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p><strong>Sponsor:</strong> {study['sponsor']}</p>", unsafe_allow_html=True)
                        st.markdown(f"<p><strong>Phase:</strong> {study['phase']}</p>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    with col2:
                        # Participant metrics with visuals
                        st.markdown("<div class='card'>", unsafe_allow_html=True)
                        
                        # Trial size visualization
                        labels = ["Participants"]
                        values = [study["number_of_participants"]]
                        
                        fig = go.Figure()
                        fig.add_trace(go.Bar(
                            x=labels,
                            y=values,
                            marker_color='#1E88E5',
                            text=values,
                            textposition='auto',
                            width=0.5
                        ))
                        
                        fig.update_layout(
                            title="Trial Size",
                            height=200,
                            margin=dict(l=20, r=20, t=40, b=20),
                            yaxis_title="Count",
                            xaxis_title="",
                            showlegend=False,
                            plot_bgcolor='white'
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        # Arms distribution
                        arms_data = {
                            "Arm Type": ["Intervention", "Placebo"],
                            "Count": [study["study_arms"]["intervention"], study["study_arms"]["placebo"]]
                        }
                        arms_df = pd.DataFrame(arms_data)
                        
                        fig = px.pie(
                            arms_df,
                            names="Arm Type",
                            values="Count",
                            color_discrete_sequence=['#1976D2', '#90CAF9'],
                            hole=0.4
                        )
                        
                        fig.update_layout(
                            title="Arms Distribution",
                            height=200,
                            margin=dict(l=20, r=20, t=40, b=0),
                            showlegend=True,
                            legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5)
                        )
                        
                        st.plotly_chart(fig, use_container_width=True)
                        
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Intervention details
                    st.markdown("<h2 class='section-header'>Intervention Details</h2>", unsafe_allow_html=True)
                    
                    drug = study["interventional_drug"]
                    
                    # Create a more visually appealing card for drug info
                    cols = st.columns(4)
                    
                    with cols[0]:
                        st.markdown("<div class='card' style='height: 150px;'>", unsafe_allow_html=True)
                        st.markdown("<p style='color: #757575; font-size: 0.9rem;'>DRUG NAME</p>", unsafe_allow_html=True)
                        st.markdown(f"<p style='font-size: 1.2rem; font-weight: 600;'>{drug['name']}</p>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                    with cols[1]:
                        st.markdown("<div class='card' style='height: 150px;'>", unsafe_allow_html=True)
                        st.markdown("<p style='color: #757575; font-size: 0.9rem;'>DOSAGE</p>", unsafe_allow_html=True)
                        st.markdown(f"<p style='font-size: 1.2rem; font-weight: 600;'>{drug['dose']}</p>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                    with cols[2]:
                        st.markdown("<div class='card' style='height: 150px;'>", unsafe_allow_html=True)
                        st.markdown("<p style='color: #757575; font-size: 0.9rem;'>FREQUENCY</p>", unsafe_allow_html=True)
                        st.markdown(f"<p style='font-size: 1.2rem; font-weight: 600;'>{drug['frequency']}</p>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                        
                    with cols[3]:
                        st.markdown("<div class='card' style='height: 150px;'>", unsafe_allow_html=True)
                        st.markdown("<p style='color: #757575; font-size: 0.9rem;'>FORMULATION</p>", unsafe_allow_html=True)
                        st.markdown(f"<p style='font-size: 1.2rem; font-weight: 600;'>{drug['formulation']}</p>", unsafe_allow_html=True)
                        st.markdown("</div>", unsafe_allow_html=True)
                    
                    # Endpoints and baseline measures with tabs
                    st.markdown("<h2 class='section-header'>Trial Outcomes</h2>", unsafe_allow_html=True)
                    
                    # Use tabs for endpoints and baseline
                    endpoint_tab, baseline_tab = st.tabs(["📊 Endpoints", "📈 Baseline Measures"])
                    
                    with endpoint_tab:
                        if trial_data["endpoints"]:
                            endpoints_df = pd.DataFrame(trial_data["endpoints"])
                            
                            # Display endpoints table with improved styling
                            st.markdown("<div class='dataframe-container'>", unsafe_allow_html=True)
                            st.dataframe(
                                endpoints_df,
                                use_container_width=True,
                                column_config={
                                    "name": "Endpoint",
                                    "arm": "Treatment Arm",
                                    "timepoint": "Timepoint",
                                    "average_value": "Value",
                                    "statistical_significance": "P-value",
                                    "description": None  # Hide description column
                                }
                            )
                            st.markdown("</div>", unsafe_allow_html=True)
                            
                            # Create endpoint visualization
                            st.markdown("<h3>Endpoint Visualization</h3>", unsafe_allow_html=True)
                            
                            # Group by name and arm
                            endpoint_groups = {}
                            for endpoint in trial_data["endpoints"]:
                                name = endpoint["name"]
                                if name not in endpoint_groups:
                                    endpoint_groups[name] = {"intervention": None, "placebo": None}
                                
                                if endpoint["arm"] == "intervention":
                                    endpoint_groups[name]["intervention"] = endpoint
                                elif endpoint["arm"] == "placebo":
                                    endpoint_groups[name]["placebo"] = endpoint
                            
                            # Create comparison plot for endpoints with both arms
                            valid_endpoints = [name for name, data in endpoint_groups.items() 
                                             if data["intervention"] and data["placebo"] and 
                                             data["intervention"]["average_value"] is not None and 
                                             data["placebo"]["average_value"] is not None]
                            
                            if valid_endpoints:
                                selected_endpoint = st.selectbox(
                                    "Select endpoint to visualize",
                                    valid_endpoints,
                                    key="endpoint_select"
                                )
                                
                                if selected_endpoint:
                                    endpoint_data = endpoint_groups[selected_endpoint]
                                    
                                    # Create comparison bar chart with improved styling
                                    fig = go.Figure()
                                    
                                    # Add intervention bar
                                    fig.add_trace(go.Bar(
                                        x=["Intervention"],
                                        y=[endpoint_data["intervention"]["average_value"]],
                                        error_y=dict(
                                            type='data',
                                            symmetric=False,
                                            array=[endpoint_data["intervention"]["upper_end"] - endpoint_data["intervention"]["average_value"] 
                                                  if endpoint_data["intervention"]["upper_end"] is not None else 0],
                                            arrayminus=[endpoint_data["intervention"]["average_value"] - endpoint_data["intervention"]["lower_end"]
                                                      if endpoint_data["intervention"]["lower_end"] is not None else 0]
                                        ) if endpoint_data["intervention"]["upper_end"] is not None or endpoint_data["intervention"]["lower_end"] is not None else None,
                                        name="Intervention",
                                        marker_color='#1976D2',
                                        text=[f"{endpoint_data['intervention']['average_value']}"],
                                        textposition="outside"
                                    ))
                                    
                                    # Add placebo bar
                                    fig.add_trace(go.Bar(
                                        x=["Placebo"],
                                        y=[endpoint_data["placebo"]["average_value"]],
                                        error_y=dict(
                                            type='data',
                                            symmetric=False,
                                            array=[endpoint_data["placebo"]["upper_end"] - endpoint_data["placebo"]["average_value"]
                                                  if endpoint_data["placebo"]["upper_end"] is not None else 0],
                                            arrayminus=[endpoint_data["placebo"]["average_value"] - endpoint_data["placebo"]["lower_end"]
                                                      if endpoint_data["placebo"]["lower_end"] is not None else 0]
                                        ) if endpoint_data["placebo"]["upper_end"] is not None or endpoint_data["placebo"]["lower_end"] is not None else None,
                                        name="Placebo",
                                        marker_color='#90CAF9',
                                        text=[f"{endpoint_data['placebo']['average_value']}"],
                                        textposition="outside"
                                    ))
                                    
                                    # Calculate difference for treatment effect
                                    int_value = endpoint_data["intervention"]["average_value"]
                                    pla_value = endpoint_data["placebo"]["average_value"]
                                    diff = int_value - pla_value
                                    
                                    # Update layout with improved styling
                                    fig.update_layout(
                                        title=f"{selected_endpoint} Comparison",
                                        xaxis_title="Arm",
                                        yaxis_title=f"{selected_endpoint} Value",
                                        barmode='group',
                                        height=450,
                                        plot_bgcolor='white',
                                        font=dict(family="Arial", size=12),
                                        shapes=[
                                            # Line connecting bars for effect visualization
                                            dict(
                                                type='line',
                                                x0=0, y0=int_value,
                                                x1=1, y1=pla_value,
                                                line=dict(color='#616161', width=1, dash='dot')
                                            )
                                        ]
                                    )
                                    
                                    # Add p-value annotation
                                    p_value = endpoint_data["intervention"]["statistical_significance"]
                                    effect_text = f"Effect: {diff:.2f}"
                                    
                                    if p_value:
                                        p_color = "#4CAF50" if "p<0.05" in p_value or "p=0.05" in p_value else "#F44336"
                                        fig.add_annotation(
                                            x=0.5,
                                            y=max(int_value, pla_value) * 1.1,
                                            text=f"{effect_text} | {p_value}",
                                            showarrow=False,
                                            font=dict(color=p_color, size=14)
                                        )
                                    
                                    st.plotly_chart(fig, use_container_width=True)
                                    
                                    # Add p-value interpretation
                                    if p_value:
                                        if "p<0.05" in p_value or "p=0.05" in p_value:
                                            st.success("✅ This endpoint shows a statistically significant difference between intervention and placebo.")
                                        else:
                                            st.info("ℹ️ This endpoint does not show a statistically significant difference.")
                                else:
                                    st.info("Please select an endpoint to visualize")
                            else:
                                st.info("No endpoints available with data for both arms")
                        else:
                            st.info("No endpoint data available for this trial")
                    
                    with baseline_tab:
                        if trial_data["baseline_measures"]:
                            baseline_df = pd.DataFrame(trial_data["baseline_measures"])
                            
                            # Display baseline measures table with improved styling
                            st.markdown("<div class='dataframe-container'>", unsafe_allow_html=True)
                            st.dataframe(
                                baseline_df,
                                use_container_width=True,
                                column_config={
                                    "name": "Baseline Measure",
                                    "arm": "Treatment Arm",
                                    "average_value": "Value",
                                    "description": None  # Hide description column
                                }
                            )
                            st.markdown("</div>", unsafe_allow_html=True)
                            
                            # Create baseline visualization if data is available
                            if not baseline_df.empty:
                                st.markdown("<h3>Baseline Comparison</h3>", unsafe_allow_html=True)
                                
                                # Get unique measures
                                measures = baseline_df["name"].unique()
                                
                                if len(measures) > 0:
                                    selected_measure = st.selectbox(
                                        "Select baseline measure to visualize",
                                        measures,
                                        key="baseline_select"
                                    )
                                    
                                    # Filter for selected measure
                                    measure_data = baseline_df[baseline_df["name"] == selected_measure]
                                    
                                    # Check if we have data for both arms
                                    if "intervention" in measure_data["arm"].values and "placebo" in measure_data["arm"].values:
                                        # Create comparison chart
                                        fig = go.Figure()
                                        
                                        for arm in ["intervention", "placebo"]:
                                            arm_data = measure_data[measure_data["arm"] == arm].iloc[0]
                                            
                                            fig.add_trace(go.Bar(
                                                x=[arm.capitalize()],
                                                y=[arm_data["average_value"]],
                                                name=arm.capitalize(),
                                                marker_color='#1976D2' if arm == "intervention" else '#90CAF9',
                                                text=[f"{arm_data['average_value']}"],
                                                textposition="outside",
                                                error_y=dict(
                                                    type='data',
                                                    symmetric=False,
                                                    array=[arm_data["upper_end"] - arm_data["average_value"] 
                                                          if arm_data["upper_end"] is not None else 0],
                                                    arrayminus=[arm_data["average_value"] - arm_data["lower_end"]
                                                              if arm_data["lower_end"] is not None else 0]
                                                ) if arm_data["upper_end"] is not None or arm_data["lower_end"] is not None else None
                                            ))
                                        
                                        fig.update_layout(
                                            title=f"Baseline {selected_measure} Comparison",
                                            xaxis_title="Arm",
                                            yaxis_title=f"{selected_measure} Value",
                                            barmode='group',
                                            height=400,
                                            plot_bgcolor='white',
                                            font=dict(family="Arial", size=12)
                                        )
                                        
                                        st.plotly_chart(fig, use_container_width=True)
                                        
                                        # Add balancing assessment
                                        int_value = measure_data[measure_data["arm"] == "intervention"]["average_value"].values[0]
                                        pla_value = measure_data[measure_data["arm"] == "placebo"]["average_value"].values[0]
                                        pct_diff = abs(int_value - pla_value) / ((int_value + pla_value) / 2) * 100
                                        
                                        if pct_diff < 5:
                                            st.success(f"✅ Arms are well balanced for this measure (Difference: {pct_diff:.1f}%)")
                                        elif pct_diff < 10:
                                            st.warning(f"⚠️ Arms show some imbalance for this measure (Difference: {pct_diff:.1f}%)")
                                        else:
                                            st.error(f"❌ Arms are notably imbalanced for this measure (Difference: {pct_diff:.1f}%)")
                                    else:
                                        st.info("Baseline data not available for both arms")
                        else:
                            st.info("No baseline data available for this trial")
                else:
                    st.error(f"❌ Could not load details for trial {nct_id}")
    else:
        st.error("❌ No trials data available. Please check API connection.")

# Endpoint Comparison Page
elif page == "Endpoint Comparison":
    # Main title with styling
    st.markdown("<h1 class='main-header'>Endpoint Comparison</h1>", unsafe_allow_html=True)
    st.markdown("<p>Compare endpoint outcomes across multiple PAH clinical trials to identify trends and differences in treatment effects.</p>", unsafe_allow_html=True)
    
    # Analysis controls in a cleaner layout
    st.markdown("<h2 class='section-header'>Analysis Controls</h2>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Common endpoints for PAH trials with icons
        endpoint_options = {
            "PVR": "Pulmonary Vascular Resistance",
            "6MWD": "6-Minute Walk Distance",
            "NT-proBNP": "NT-proBNP Levels", 
            "WHO FC": "WHO Functional Class", 
            "CARDIAC OUTPUT": "Cardiac Output"
        }
        
        # Create a more visually appealing endpoint selector
        endpoint_name = st.selectbox(
            "Select an endpoint to analyze",
            list(endpoint_options.keys()),
            format_func=lambda x: f"{x} - {endpoint_options[x]}"
        )
    
    with col2:
        # Options
        include_placebo = st.checkbox("Include placebo arms", value=True)
        
        # Add visualization options
        chart_type = st.radio(
            "Chart Type",
            ["Bar Chart", "Treatment Effect"],
            horizontal=True
        )
    
    if endpoint_name:
        # Add description of the selected endpoint
        endpoint_descriptions = {
            "PVR": "Pulmonary Vascular Resistance (PVR) measures the resistance to blood flow through the pulmonary circulation. A decrease indicates improved blood flow.",
            "6MWD": "6-Minute Walk Distance (6MWD) measures the distance a patient can walk in 6 minutes, indicating exercise capacity and functional status.",
            "NT-proBNP": "N-terminal pro-brain natriuretic peptide (NT-proBNP) is a biomarker of heart failure and right ventricular dysfunction. Lower values indicate improved heart function.",
            "WHO FC": "WHO Functional Class (WHO FC) classifies the severity of symptoms and functional limitations in patients with pulmonary hypertension.",
            "CARDIAC OUTPUT": "Cardiac Output measures the volume of blood pumped by the heart per minute, reflecting heart function."
        }
        
        st.markdown(f"<div class='card'><p>{endpoint_descriptions.get(endpoint_name, '')}</p></div>", unsafe_allow_html=True)
        
        # Load and process endpoint data
        endpoint_data = compare_endpoint(endpoint_name, include_placebo)
        
        if endpoint_data:
            # Convert to DataFrame
            df = pd.DataFrame(endpoint_data)
            
            # Display results header
            st.markdown(f"<h2 class='section-header'>Results for {endpoint_name}</h2>", unsafe_allow_html=True)
            
            # Enhanced data table
            st.markdown("<h3>Data Summary</h3>", unsafe_allow_html=True)
            st.markdown("<div class='dataframe-container'>", unsafe_allow_html=True)
            
            # Format p-values and show statistical significance
            def format_p_value(p_val):
                if pd.isna(p_val) or p_val == "":
                    return ""
                
                if "p<0.05" in str(p_val).lower() or "p=0.05" in str(p_val).lower() or "p<0.001" in str(p_val).lower():
                    return f"<span style='color: #4CAF50; font-weight: 600;'>{p_val} ✓</span>"
                else:
                    return f"<span style='color: #F44336;'>{p_val}</span>"
            
            summary_df = df[["nct_id", "sponsor", "arm", "value", "p_value"]].copy()
            
            st.dataframe(
                summary_df,
                use_container_width=True,
                column_config={
                    "nct_id": "Trial ID",
                    "sponsor": "Sponsor",
                    "arm": "Treatment Arm",
                    "value": f"{endpoint_name} Value",
                    "p_value": st.column_config.Column(
                        "Statistical Significance",
                        help="P-values for statistical significance",
                        width="medium"
                    )
                },
                hide_index=True
            )
            st.markdown("</div>", unsafe_allow_html=True)
            
            # Download option
            col1, col2 = st.columns([1, 5])
            with col1:
                st.download_button(
                    label="📊 Export Data",
                    data=df.to_csv(index=False).encode('utf-8'),
                    file_name=f"{endpoint_name}_comparison.csv",
                    mime='text/csv'
                )
            
            # Create visualization based on selected chart type
            st.markdown("<h3>Visualization</h3>", unsafe_allow_html=True)
            
            # Filter for valid numeric values
            df_plot = df[pd.notnull(df["value"])].copy()
            
            if not df_plot.empty:
                if chart_type == "Bar Chart":
                    # Improved bar chart visualization
                    fig = px.bar(
                        df_plot,
                        x="nct_id",
                        y="value",
                        color="arm",
                        barmode="group",
                        color_discrete_map={"intervention": "#1976D2", "placebo": "#90CAF9"},
                        error_y="upper_end" if "upper_end" in df_plot.columns and not df_plot["upper_end"].isna().all() else None,
                        error_y_minus="lower_end" if "lower_end" in df_plot.columns and not df_plot["lower_end"].isna().all() else None,
                        labels={
                            "nct_id": "Clinical Trial",
                            "value": f"{endpoint_name} Value",
                            "arm": "Treatment Arm"
                        },
                        title=f"Comparison of {endpoint_name} Across PAH Clinical Trials",
                        hover_data=["study_title", "sponsor", "timepoint", "p_value"]
                    )
                    
                    # Customize layout
                    fig.update_layout(
                        xaxis_tickangle=-45,
                        legend_title="Treatment Arm",
                        height=500,
                        font=dict(family="Arial", size=12),
                        plot_bgcolor='white',
                        margin=dict(l=20, r=20, t=50, b=80)
                    )
                    
                    st.plotly_chart(fig, use_container_width=True)
                    
                else:  # Treatment Effect
                    if include_placebo and "placebo" in df_plot["arm"].values and "intervention" in df_plot["arm"].values:
                        st.markdown("<h3>Treatment Effect Analysis</h3>", unsafe_allow_html=True)
                        
                        # Calculate treatment effect
                        trial_effects = []
                        for nct_id in df_plot["nct_id"].unique():
                            trial_data = df_plot[df_plot["nct_id"] == nct_id]
                            
                            intervention_rows = trial_data[trial_data["arm"] == "intervention"]
                            placebo_rows = trial_data[trial_data["arm"] == "placebo"]
                            
                            if not intervention_rows.empty and not placebo_rows.empty:
                                intervention_value = intervention_rows["value"].values[0]
                                placebo_value = placebo_rows["value"].values[0]
                                
                                effect = intervention_value - placebo_value
                                p_value = intervention_rows["p_value"].values[0] if not intervention_rows.empty else "Unknown"
                                
                                is_significant = False
                                if isinstance(p_value, str) and ("p<0.05" in p_value.lower() or 
                                                               "p = 0.05" in p_value.lower() or 
                                                               "p<.05" in p_value.lower()):
                                    is_significant = True
                                
                                trial_effects.append({
                                    "nct_id": nct_id,
                                    "study_title": intervention_rows["study_title"].values[0] if not intervention_rows.empty else "",
                                    "sponsor": intervention_rows["sponsor"].values[0] if not intervention_rows.empty else "",
                                    "effect": effect,
                                    "p_value": p_value,
                                    "is_significant": is_significant,
                                    "intervention_value": intervention_value,
                                    "placebo_value": placebo_value
                                })
                        
                        if trial_effects:
                            df_effects = pd.DataFrame(trial_effects)
                            
                            # Create enhanced horizontal bar chart
                            fig = px.bar(
                                df_effects,
                                y="nct_id",
                                x="effect",
                                orientation="h",
                                color="is_significant",
                                color_discrete_map={True: "#4CAF50", False: "#F44336"},
                                labels={
                                    "nct_id": "Clinical Trial",
                                    "effect": f"Effect Size (Intervention - Placebo)",
                                    "is_significant": "Statistically Significant"
                                },
                                title=f"Treatment Effect for {endpoint_name} Across PAH Clinical Trials",
                                hover_data=["study_title", "sponsor", "p_value", "intervention_value", "placebo_value"]
                            )
                            
                            # Improve the visualization
                            fig.update_layout(
                                height=500,
                                font=dict(family="Arial", size=12),
                                plot_bgcolor='white',
                                margin=dict(l=20, r=20, t=50, b=20)
                            )
                            
                            # Add vertical line at x=0
                            fig.add_shape(
                                type="line",
                                x0=0, y0=-0.5,
                                x1=0, y1=len(df_effects) - 0.5,
                                line=dict(color="gray", width=2, dash="dash")
                            )
                            
                            # Add p-values as annotations
                            for i, row in df_effects.iterrows():
                                fig.add_annotation(
                                    x=row["effect"] + (0.1 if row["effect"] >= 0 else -0.1),
                                    y=i,
                                    text=f"{row['p_value']}",
                                    showarrow=False,
                                    font=dict(
                                        size=10,
                                        color="#4CAF50" if row['is_significant'] else "#F44336"
                                    )
                                )
                            
                            st.plotly_chart(fig, use_container_width=True)
                            
                            # Add interpretation
                            positive_effects = sum(df_effects["effect"] > 0)
                            significant_effects = sum(df_effects["is_significant"])
                            
                            st.markdown("<div class='card'>", unsafe_allow_html=True)
                            st.markdown("<h3>Analysis Summary</h3>", unsafe_allow_html=True)
                            st.markdown(f"<p>{positive_effects} out of {len(df_effects)} trials ({positive_effects/len(df_effects)*100:.0f}%) show positive treatment effect for {endpoint_name}.</p>", unsafe_allow_html=True)
                            st.markdown(f"<p>{significant_effects} out of {len(df_effects)} trials ({significant_effects/len(df_effects)*100:.0f}%) show statistically significant results.</p>", unsafe_allow_html=True)
                            
                            if positive_effects > len(df_effects) / 2:
                                st.markdown("<p class='status-success'>✅ Majority of trials show positive treatment effect</p>", unsafe_allow_html=True)
                            else:
                                st.markdown("<p class='status-warning'>⚠️ Less than half of trials show positive treatment effect</p>", unsafe_allow_html=True)
                                
                            st.markdown("</div>", unsafe_allow_html=True)
                            
                    else:
                        st.warning("Treatment effect comparison requires both intervention and placebo arm data.")
            else:
                st.info(f"No numeric data available for {endpoint_name}")
        else:
            st.warning(f"No data found for endpoint: {endpoint_name}")

# About page
elif page == "About":
    st.markdown("<h1 class='main-header'>About This Dashboard</h1>", unsafe_allow_html=True)
    
    # Create a card layout
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("""
    <h2>Clinical Trial & Corporate Disclosure Extraction Pipeline</h2>
    
    <p>This interactive dashboard visualizes data from industry-sponsored interventional clinical trials
    for Pulmonary Arterial Hypertension (PAH) extracted from ClinicalTrials.gov, 
    corporate filings (SEC), and scientific publications.</p>
    
    <h3>Pipeline Architecture</h3>
    <ol>
        <li><strong>Data Extraction</strong> - Raw data is fetched from ClinicalTrials.gov API</li>
        <li><strong>Data Enrichment</strong> - Trial data is enriched with SEC filings and publication data</li>
        <li><strong>Data Processing</strong> - Information is structured into PostgreSQL-compatible objects</li>
        <li><strong>Data Analysis</strong> - Rich metadata on endpoints, arms, drug regimens, and baseline characteristics is analyzed</li>
        <li><strong>Visualization</strong> - Interactive visualizations provide insights across multiple trials</li>
    </ol>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Create two column layout for additional information
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("""
        <h3>Data Sources</h3>
        <ul>
            <li><strong>ClinicalTrials.gov API</strong> - Primary source for trial data</li>
            <li><strong>Financial Modeling Prep API</strong> - For SEC filings analysis</li>
            <li><strong>Google Custom Search API</strong> - For scientific publication discovery</li>
        </ul>
        
        <h3>Key Features</h3>
        <ul>
            <li>Cross-trial endpoint comparison</li>
            <li>Treatment effect analysis</li>
            <li>Baseline characteristics assessment</li>
            <li>Trial metadata exploration</li>
        </ul>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    with col2:
        st.markdown("<div class='card'>", unsafe_allow_html=True)
        st.markdown("""
        <h3>Technologies Used</h3>
        <ul>
            <li><strong>Backend</strong>: FastAPI, SQLAlchemy, PostgreSQL</li>
            <li><strong>Frontend</strong>: Streamlit, Plotly</li>
            <li><strong>Data Processing</strong>: Pandas, Matplotlib, PyPDF2</li>
            <li><strong>API Integration</strong>: ClinicalTrials.gov, FMP, Google Search</li>
        </ul>
        
        <h3>Future Enhancements</h3>
        <ul>
            <li>Meta-analysis of treatment effects</li>
            <li>Predictive modeling of treatment outcomes</li>
            <li>Integration with additional data sources</li>
            <li>Enhanced natural language processing for publication data extraction</li>
        </ul>
        """, unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)
    
    # Add project information and acknowledgements
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.markdown("""
    <h3>Project Implementation</h3>
    <p>This project was implemented as part of a technical assignment to demonstrate capabilities
    in data extraction, processing, and visualization. The pipeline is designed to be modular,
    extensible, and focused on real-world data.</p>
    
    <p>The dashboard provides an intuitive interface for researchers and analysts to compare
    clinical trial outcomes, identify trends, and assess treatment efficacy across multiple studies.</p>
    """, unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)
    
    # Add contact information in footer
    st.markdown("<div class='footer'>", unsafe_allow_html=True)
    st.markdown("© 2025 Clinical Trial Analytics | All data sourced from ClinicalTrials.gov and public sources", unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)

# Run with: streamlit run src/streamlit/app.py