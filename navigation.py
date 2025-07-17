import streamlit as st
from datetime import datetime, timedelta
import pandas as pd
import time
# --- Annotation utilities ---
from annotation_utils import (
    reset_annotation_fields,
    all_annotations_filled,
    save_all_views_for_patient,
    refresh_form_complete,
    load_annotations_for_image
)

_MIN_NAV_INTERVAL = 1.0          # seconds

def _too_soon(flag_name):
    now = time.time()
    last = st.session_state.get(flag_name, 0)
    if isinstance(last, datetime):
        last = last.timestamp()  # convert datetime to float
    st.session_state[flag_name] = now
    return (now - last) < _MIN_NAV_INTERVAL

def navigate_study(direction):
    """
    Save annotations for the current patient and switch to the previous or next patient in the list.
    
    direction: int, either -1 for previous patient or 1 for next patient
    """
    # Prevent rapid navigation
    if st.session_state.get("saving_annotation", False) or _too_soon("last_clinician_nav"):
        return

    # Refuse to move forward if annotations are incomplete
    if not all_annotations_filled():
        st.session_state.annotation_warning = True
        refresh_form_complete()  # Ensure form_complete is updated
        return

    # Set saving flag
    st.session_state.saving_annotation = True

    try:
        patient_df = st.session_state.dicom_df[
            st.session_state.dicom_df["study_icn"] == st.session_state.current_patient_group
        ]
        save_all_views_for_patient(
            patient_df,
            username=st.session_state.get("username", "unknown"),
            role=st.session_state.get("role", "Unknown"),
        )
        
        patients = st.session_state.dicom_df["study_icn"].unique()
        current_idx = list(patients).index(st.session_state.current_patient_group)
        new_idx = current_idx + direction
        
        if 0 <= new_idx < len(patients):
            st.session_state.current_patient_group = patients[new_idx]
            st.session_state.view_idx = 0
            reset_annotation_fields()
            
            # Load annotations for the new patient's first view
            new_patient_df = st.session_state.dicom_df[
                st.session_state.dicom_df['study_icn'] == st.session_state.current_patient_group
            ]
            if not new_patient_df.empty:
                first_row = new_patient_df.iloc[0]
                load_annotations_for_image(first_row["image_path"], "Clinician", st.session_state.get("username"))
            
            st.session_state.annotation_start_time = datetime.now()
            refresh_form_complete()  # Refresh form completion status

    finally:
        st.session_state.saving_annotation = False

# Example usage:
def previous_study():
    navigate_study(direction=-1)

def next_study():
    navigate_study(direction=1)

def previous_view():
    """
    Switch to the previous view of the current patient if it exists.
    """
    # Prevent rapid navigation
    if st.session_state.get("saving_annotation", False):
        return

    if st.session_state.view_idx > 0:
        # Save current annotations before switching if any are filled
        current_patient_df = st.session_state.dicom_df[st.session_state.dicom_df['study_icn'] == st.session_state.current_patient_group]
        current_row = current_patient_df.iloc[st.session_state.view_idx]
        
        # Save partial annotations if any fields are filled
        if any(st.session_state.get(key) is not None for key in [
            "ards_likelihood", "diffuse_damage", "pleural_lesion", "pulmonary_edema",
            "consolidation", "atelectasis", "mediastinum_findings", "sufficient_quality", "global_criteria"
        ]):
            save_all_views_for_patient(
                current_patient_df,
                username=st.session_state.get("username", "unknown"),
                role=st.session_state.get("role", "Unknown"),
            )
        
        # Switch to previous view
        st.session_state.view_idx -= 1
        
        # Load annotations for the new view
        new_patient_df = st.session_state.dicom_df[st.session_state.dicom_df['study_icn'] == st.session_state.current_patient_group]
        new_row = new_patient_df.iloc[st.session_state.view_idx]
        load_annotations_for_image(new_row["image_path"], "Clinician", st.session_state.get("username"))
        
        refresh_form_complete()

def next_view():
    """
    Switch to the next view of the current patient if it exists.
    """
    # Prevent rapid navigation
    if st.session_state.get("saving_annotation", False):
        return
        
    # Get the current patient's data
    patient_df = st.session_state.dicom_df[st.session_state.dicom_df['study_icn'] == st.session_state.current_patient_group]
    
    if st.session_state.view_idx < len(patient_df) - 1:
        # Save current annotations before switching if any are filled
        current_row = patient_df.iloc[st.session_state.view_idx]
        
        # Save partial annotations if any fields are filled
        if any(st.session_state.get(key) is not None for key in [
            "ards_likelihood", "diffuse_damage", "pleural_lesion", "pulmonary_edema",
            "consolidation", "atelectasis", "mediastinum_findings", "sufficient_quality", "global_criteria"
        ]):
            save_all_views_for_patient(
                patient_df,
                username=st.session_state.get("username", "unknown"),
                role=st.session_state.get("role", "Unknown"),
            )
        
        # Switch to next view
        st.session_state.view_idx += 1
        
        # Load annotations for the new view
        new_row = patient_df.iloc[st.session_state.view_idx]
        load_annotations_for_image(new_row["image_path"], "Clinician", st.session_state.get("username"))
        
        refresh_form_complete()

# Define button click handlers
def on_prev_click():
    """Handle previous button click for Data Scientist navigation"""
    # IMMEDIATELY disable buttons on first click to prevent rapid clicking
    st.session_state.navigating_annotation = True
    navigate_ds("prev")
    
def on_next_click():
    """Handle next button click for Data Scientist navigation"""
    # IMMEDIATELY disable buttons on first click to prevent rapid clicking
    st.session_state.navigating_annotation = True
    navigate_ds("next")

def navigate_ds(direction):
    """
    Navigate Data Scientist's annotations in the specified direction.
    Fixed version with immediate button disabling and proper state management.
    """
    try:
        # Prevent rapid navigation with time-based throttling
        if st.session_state.get("saving_annotation", False) or _too_soon("last_ds_nav"):
            return
            
        # Set flag to indicate navigation is in progress
        st.session_state.navigation_in_progress = True

        idx = st.session_state.get("ds_idx", 0)
        total = len(st.session_state.dicom_df)

        # Check bounds
        if (direction == "prev" and idx == 0) or (direction == "next" and idx == total - 1):
            return

        # Get current image path before navigation for saving
        current_selected_row = st.session_state.dicom_df.iloc[idx]
        current_image_path = current_selected_row["image_path"]

        # Save current annotations if they're all filled
        if all_annotations_filled():
            st.session_state.saving_annotation = True
            try:
                save_all_views_for_patient(
                    patient_df=None,
                    username=st.session_state.get("username"),
                    role=st.session_state.get("role", "Unknown"),
                    selected_row=current_selected_row
                )
            finally:
                st.session_state.saving_annotation = False

        # Navigate to new index
        if direction == "next":
            st.session_state.ds_idx = min(idx + 1, total - 1)
        else:  # "prev"
            st.session_state.ds_idx = max(idx - 1, 0)

        # Load annotations for the new image
        new_idx = st.session_state.ds_idx
        new_selected_row = st.session_state.dicom_df.iloc[new_idx]
        
        # Reset annotation fields first to prevent contamination
        reset_annotation_fields()
        
        # Load existing annotations for the new image
        load_annotations_for_image(
            new_selected_row["image_path"], 
            "Data Scientist", 
            st.session_state.get("username")
        )
        
        # Refresh form completion state
        refresh_form_complete()
        
        # Reset annotation start time
        st.session_state.annotation_start_time = datetime.now()

    finally:
        # Clear navigation flags to re-enable buttons if conditions are met
        st.session_state.navigation_in_progress = False
        # Only clear navigating_annotation if no saving is happening and form is complete
        if not st.session_state.get("saving_annotation", False) and st.session_state.get("form_complete", False):
            st.session_state.navigating_annotation = False