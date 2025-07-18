"""
Author: Victor M. Murcia Ruiz, PhD
Date: 5/5/2025

DICOM Viewer Streamlit Application

This script sets up and runs a Streamlit web application for viewing and annotating DICOM images. 
The application was designed to handle the VACXR dataset structure, however, it can be readily adapted
to handle similar imaging datasets.
The application supports user authentication, role-based access control, and provides tools for 
interacting with DICOM metadata, windowing controls, and image annotations.

Key Features:
- User Authentication: Secure login mechanism that verifies user credentials stored in Streamlit secrets.
- Role-Based Interface: Different user interfaces and functionalities for Clinicians and Data Scientists.
- DICOM Image Viewing: Display and interact with DICOM images using window level and width adjustments.
- Annotations: Save, load, and reset annotation fields with role-specific options.
- Navigation: Navigate through patients and views for Clinicians, and through individual images for Data Scientists.
- Custom Styling: Inject custom CSS to enhance the appearance and usability of the Streamlit application.

Modules:
- auth: Handles user authentication.
- config: Configuration file containing paths to various datasets.
- dicom_utils: Utilities for processing and displaying DICOM images.
- annotation_utils: Functions to manage annotation fields and save annotation data.
- sidebar_utils: Functions to render various sidebar components such as window controls and metadata.
- navigation: Functions to navigate between patients, views, and images.
- role_interface: Functions to render the interface based on the user's role.

Usage:
To run the application, simply execute this script using Streamlit:
    streamlit run ards_quest_vacxr_annotation.py

The GitHub repo for this application at the time of writing can be found here: 
https://github.ec.va.gov/Victor-MurciaRuiz/ARDS_VACXR_Annotation_App
"""
import streamlit as st
import pandas as pd
import os
from datetime import datetime
from glob import glob
from role_interface import render_role_interface
from auth import login,logout
from config import PARQUET_PATH, ANNOTATION_DIR
 
# --- Load DICOM Index ---
@st.cache_data
def load_dicom_index(parquet_path):
    """
    Load DICOM index from a parquet file, with caching to improve performance.

    Parameters:
    - parquet_path: Path to the parquet file containing the DICOM index.

    Returns:
    A pandas DataFrame containing the DICOM index.
    """
    return pd.read_parquet(parquet_path)

def inject_custom_css():
    """
    Inject custom CSS to style the Streamlit application.
    
    This function customizes the padding, margins, layout, and appearance of various elements within the Streamlit app.
    """
    st.markdown(
        """
        <style>
        .block-container {
            padding-top: 1rem;
            padding-bottom: 1rem;
        }
        .stRadio > div {
            margin-bottom: -10px;
        }
        .main .block-container {
            max-width: 100%;
            padding-right: 1rem;
        }
        .stSlider {
            padding-bottom: 0.5rem;
            padding-right: 1.5rem;
        }
        .element-container:has(.js-plotly-plot) {
            display: flex;
            justify-content: center;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

def load_annotation_df(username, role, annotation_dir):
    today = datetime.now().strftime("%Y%m%d")
    pattern = os.path.join(annotation_dir, f"ardsquest_annotations_{username}_{role}_{today}.parquet")
    matches = glob(pattern)
    if matches:
        return pd.read_parquet(matches[0])
    else:
        return pd.DataFrame()
    
# --- Main Streamlit App ---
def main():
    """
    Main function to run the Streamlit application.

    This function:
    - Sets up the page configuration and custom CSS.
    - Checks if the user is logged in and initiates the login process if not.
    - Loads DICOM index and annotation DataFrames.
    - Filters the DICOM data based on the user's role.
    - Determines the current image selection based on the role (Clinician or Data Scientist).
    - Renders the appropriate role interface.
    """
    st.set_page_config(page_title="DICOM Viewer", layout="wide")
    inject_custom_css()
    # --- First, check login ---
    if not st.session_state.get("logged_in", False):
        login()
        return
    
    # --- Add a logout button ---
    with st.sidebar:
        if st.button("Logout", use_container_width=True):
            logout()

    username = st.session_state.get("username")
    role = st.session_state.get('role', 'Unknown')

    dicom_df = load_dicom_index(PARQUET_PATH)

    st.session_state.df_ds = load_annotation_df(username, "Data Scientist", ANNOTATION_DIR)
    st.session_state.df_cl = load_annotation_df(username, "Clinician", ANNOTATION_DIR)
    # Filter dicom_df by AssignedClinician or AssignedDS depending on role
    #if username not in {"TEST_DS", "TEST_CL"}:
    #    if role == "Clinician" and "AssignedClinician" in dicom_df.columns:
    #        dicom_df = dicom_df[dicom_df["AssignedClinician"] == username].reset_index(drop=True)
    #    elif role == "Data Scientist" and "AssignedDS" in dicom_df.columns:
    #        dicom_df = dicom_df[dicom_df["AssignedDS"] == username].reset_index(drop=True)

    st.session_state.dicom_df = dicom_df

    if 'study_groups' not in st.session_state:
        st.session_state.study_groups = {k: v for k, v in dicom_df.groupby("study_icn")}

    if "study_index" not in st.session_state:
        st.session_state.study_idx = 0 

    if "view_index" not in st.session_state:
        st.session_state.view_index = 0 

    # --- Determine current image selection ---
    if role == "Clinician":
        if "current_patient_group" not in st.session_state:
            st.session_state.current_patient_group = dicom_df["study_icn"].unique()[0]

        patient_df = dicom_df[dicom_df["study_icn"] == st.session_state.current_patient_group]
        patient_df = patient_df.reset_index(drop=True)

        if "view_idx" not in st.session_state:
            st.session_state.view_idx = 0

        if st.session_state.view_idx >= len(patient_df):
            st.session_state.view_idx = 0

        selected_row = patient_df.iloc[st.session_state.view_idx]
        st.session_state.selected_row = selected_row

    elif role == "Data Scientist":
        if "ds_idx" not in st.session_state:
            st.session_state.ds_idx = 0
            st.session_state.annotation_start_time = datetime.now()

        if st.session_state.ds_idx >= len(dicom_df):
            st.session_state.ds_idx = 0

        selected_row = dicom_df.iloc[st.session_state.ds_idx]
        st.session_state.selected_row = selected_row

    else:
        st.warning("Invalid role: access denied.")
        return
    
    render_role_interface(role, dicom_df, selected_row, username)

if __name__ == "__main__":
    main()