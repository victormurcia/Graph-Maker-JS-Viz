import streamlit as st
import pandas as pd
import os
from datetime import datetime
import msvcrt
import tempfile
from contextlib import contextmanager
import time
import shutil
import uuid
from config import ANNOTATION_DIR


LOCK_SUFFIX = ".lock"          # simple sentinel file for fcntl/msvcrt locking
BACKUP_KEEP = 3                # keep N most-recent backups

# Define the radio button fields as tuples: (label, field_name, options, horizontal)
CLINICIAN_RADIOS = [
    (
        "Select consistency:",
        "ards_likelihood",
        "ARDS_Likelihood_Score",
        [
            "1 - Highly inconsistent",
            "2 - Somewhat inconsistent",
            "3 - Somewhat consistent",
            "4 - Highly consistent"
        ],
        False
    ),
    (
        "Diffuse alveolar damage:",
        "diffuse_damage",
        "DiffuseAlveolarDamage",
        ["Left", "Right", "Bilateral", "None"],
        True
    ),
    (
        "Pleural space occupying lesion (e.g., PEFF, PTX):",
        "pleural_lesion",
        "PleuralSpaceOccupyingLesion",
        ["Left", "Right", "Bilateral", "None"],
        True
    ),
    (
        "Pulmonary edema:",
        "pulmonary_edema",
        "PulmonaryEdema",
        ["Left", "Right", "Bilateral", "None"],
        True
    ),
    (
        "Consolidation:",
        "consolidation",
        "Consolidation",
        ["Left", "Right", "Bilateral", "None"],
        True
    ),
    (
        "Atelectasis:",
        "atelectasis",
        "Atelectasis",
        ["Left", "Right", "Bilateral", "None"],
        True
    ),
    (
        "Normal Appearing Mediastinum?:",
        "mediastinum_findings",
        "FindingsMediastinum",
        ["Yes", "No"],
        True
    ),
    (
        "Sufficient quality for clinical analysis:",
        "sufficient_quality",
        "SufficientQuality",
        ["Yes", "No"],
        True
    ),
    (
        "Global ARDS Criteria:",
        "global_criteria",
        "GlobalARDSCriteria",
        ["Yes", "No"],
        True
    ),
]

DATA_SCIENTIST_RADIOS = [
    (
        "Intubated (OETT or tracheostomy):",
        "intubated",
        "Intubated",
        ["Yes", "No"],
        True
    ),
    (
        "External support devices visible (e.g., ECG leads, brace):",
        "external_support_devices",
        "ExternalSupportDevices",
        ["Yes", "No"],
        True
    ),
    (
        "Implanted medical device visible (e.g., pacemaker, prosthetic):",
        "implanted_device",
        "ImplantedDevice",
        ["Yes", "No"],
        True
    ),
    (
        "Other foreign bodies present (e.g., shrapnel):",
        "foreign_bodies",
        "ForeignBodies",
        ["Yes", "No"],
        True
    ),
    (
        "Image artifacts/quality issues present:",
        "image_artifacts",
        "ImageArtifacts",
        ["Yes", "No"],
        True
    ),
    (
        "Annotations or text present:",
        "annotations_text_present",
        "AnnotationsTextPresent",
        ["No", "Few characters", "Complete words"],
        True
    ),
    (
        "PHI present?",
        "phi_present",
        "PhiPresent",
        ["Yes", "No"],
        True
    ),
    (
        "Post-processing image present?",
        "post_processing",
        "PostProcessing",
        ["Yes", "No"],
        True
    ),
    (
        "View present?",
        "view_present",
        "ViewPresent",
        ["Frontal", "Lateral", 'Other'],
        True
    ),
]

def load_annotations_for_image(image_path, role, username):
    """
    Load annotations for a specific image and populate session state.
    """
    if role == "Clinician":
        df = st.session_state.get("df_cl", pd.DataFrame())
        timestamp_col = "Timestamp_cl"
        username_col = "Username_cl"
        field_mapping = {
            "ards_likelihood": "ARDS_Likelihood_Score",
            "diffuse_damage": "DiffuseAlveolarDamage",
            "pleural_lesion": "PleuralSpaceOccupyingLesion",
            "pulmonary_edema": "PulmonaryEdema",
            "consolidation": "Consolidation",
            "atelectasis": "Atelectasis",
            "mediastinum_findings": "FindingsMediastinum",
            "sufficient_quality": "SufficientQuality",
            "global_criteria": "GlobalARDSCriteria",
        }
    elif role == "Data Scientist":
        df = st.session_state.get("df_ds", pd.DataFrame())
        timestamp_col = "Timestamp_ds"
        username_col = "Username_ds"
        field_mapping = {
            "intubated": "Intubated",
            "external_support_devices": "ExternalSupportDevices",
            "implanted_device": "ImplantedDevice",
            "foreign_bodies": "ForeignBodies",
            "image_artifacts": "ImageArtifacts",
            "annotations_text_present": "AnnotationsTextPresent",
            "phi_present": "PhiPresent",
            "post_processing": "PostProcessing",
            "view_present": "ViewPresent",
        }
    else:
        return

    # Reset all annotation fields first
    for session_key in field_mapping.keys():
        st.session_state[session_key] = None

    if not df.empty:
        # Filter for the specific image and username
        matches = df[(df["image_path"] == image_path) & (df[username_col] == username)]
        
        if not matches.empty:
            # Get the most recent annotation
            latest_annotation = matches.sort_values(by=timestamp_col, ascending=False).iloc[0]
            
            # Load values into session state
            for session_key, db_field in field_mapping.items():
                if db_field in latest_annotation and pd.notna(latest_annotation[db_field]):
                    st.session_state[session_key] = latest_annotation[db_field]
                    
def refresh_form_complete():
    """Re-compute 'are all radios filled?' and cache the result."""
    st.session_state.form_complete = all_annotations_filled()

def _radio_changed(image_path, role, username):
    """Called when any radio button changes - save partial annotation and refresh form state"""
    # Save partial annotation
    save_partial_annotation(image_path, role, username)
    # Immediately refresh form completion state
    refresh_form_complete()
    # Only clear navigation flags if no saving is happening and form is complete
    # This allows buttons to be re-enabled when all fields are filled
    if not st.session_state.get("saving_annotation", False) and st.session_state.get("form_complete", False):
        st.session_state.navigating_annotation = False

def render_radio_fields(fields, image_path, role, username):
    """
    Render radio button fields based on the provided fields, image path, and user role.
    """
    for label, session_key, annotation_field, options, horizontal in fields:
        st.radio(
            label,
            options=options,
            index=get_radio_index(options, st.session_state.get(session_key)),
            key=session_key,
            horizontal=horizontal,
            on_change=_radio_changed,
            args=(image_path, role, username),
        )

def get_radio_index(options, value):
    """
    Get the index of the current value in the provided options.
    """
    try:
        if isinstance(value, str):
            value = value.strip()
        return options.index(value) if pd.notna(value) and value is not None else None
    except (ValueError, TypeError):
        return None
    
def get_annotation_value(field, image_path, role, username):
    """
    Get the most recent annotation value for a given field, image path, and user role.
    """
    if role == "Clinician":
        df = st.session_state.get("df_cl", pd.DataFrame())
        timestamp_col = "Timestamp_cl"
        username_col = "Username_cl"
    elif role == "Data Scientist":
        df = st.session_state.get("df_ds", pd.DataFrame())
        timestamp_col = "Timestamp_ds"
        username_col = "Username_ds"
    else:
        return None

    if df.empty:
        return None

    row = df[(df["image_path"] == image_path) & (df[username_col] == username)]

    if not row.empty and field in row.columns:
        # Sort by timestamp and take the most recent if duplicates exist
        row = row.sort_values(by=timestamp_col, ascending=False).iloc[0]
        return row[field]
    return None

def reset_annotation_fields():
    """
    Reset all annotation fields in the session state to None.
    """
    annotation_keys = [
        # Clinician fields
        "ards_likelihood",
        "diffuse_damage",
        "pleural_lesion",
        "pulmonary_edema",
        "consolidation",
        "atelectasis",
        "mediastinum_findings",
        "sufficient_quality",
        "global_criteria",
        # Data Scientist fields
        "intubated",
        "external_support_devices",
        "implanted_device",
        "foreign_bodies",
        "image_artifacts",
        "annotations_text_present",
        "phi_present",
        "post_processing",
        "view_present",
    ]
    
    # Set each key to None
    for key in annotation_keys:
        st.session_state[key] = None

# Sample function to update: now explicitly passes selected_row
def save_all_views_for_patient(patient_df, username, role, annotation_dir=ANNOTATION_DIR, selected_row=None, max_retries=3, backoff=0.4):
    """
    Save annotations to separate files based on user role.
    Enhanced version with better error handling and data integrity.
    """
    os.makedirs(annotation_dir, exist_ok=True)
    role = st.session_state.get("role", "Unknown")
    elapsed_time = (
        datetime.now() - st.session_state.get("annotation_start_time")
    ).total_seconds() if st.session_state.get("annotation_start_time") else None

    timestamp = datetime.now().isoformat(timespec="seconds")
    today = datetime.now().strftime("%Y%m%d")

    filename = f"ardsquest_annotations_{username}_{role}_{today}.parquet"
    out_path = os.path.join(annotation_dir, filename)

    if role == "Clinician":
        # For clinicians, save all views for the current patient
        if patient_df is None or patient_df.empty:
            return
            
        rows = []
        for _, row in patient_df.iterrows():
            entry = {
                "AnnotationID": str(uuid.uuid4()),
                "Timestamp_cl": timestamp,
                "Username_cl": username,
                "UserRole_cl": role,
                "AnnotationElapsedTime_sec_cl": elapsed_time,
                "study_icn": str(row["study_icn"]),
                "dicom_id": row["dicom_id"],
                "image_path": row["image_path"],
                "ARDS_Likelihood_Score": st.session_state.get("ards_likelihood"),
                "DiffuseAlveolarDamage": st.session_state.get("diffuse_damage"),
                "PleuralSpaceOccupyingLesion": st.session_state.get("pleural_lesion"),
                "PulmonaryEdema": st.session_state.get("pulmonary_edema"),
                "Consolidation": st.session_state.get("consolidation"),
                "Atelectasis": st.session_state.get("atelectasis"),
                "FindingsMediastinum": st.session_state.get("mediastinum_findings"),
                "SufficientQuality": st.session_state.get("sufficient_quality"),
                "GlobalARDSCriteria": st.session_state.get("global_criteria"),
            }
            rows.append(entry)
        df_new = pd.DataFrame(rows)

    elif role == "Data Scientist" and selected_row is not None:
        df_new = pd.DataFrame([{
            "AnnotationID": str(uuid.uuid4()),
            "Timestamp_ds": timestamp,
            "Username_ds": username,
            "UserRole_ds": role,
            "AnnotationElapsedTime_sec_ds": elapsed_time,
            "study_icn": str(selected_row["study_icn"]),
            "dicom_id": selected_row["dicom_id"],
            "image_path": selected_row["image_path"],
            "Intubated": st.session_state.get("intubated"),
            "ExternalSupportDevices": st.session_state.get("external_support_devices"),
            "ImplantedDevice": st.session_state.get("implanted_device"),
            "ForeignBodies": st.session_state.get("foreign_bodies"),
            "ImageArtifacts": st.session_state.get("image_artifacts"),
            "AnnotationsTextPresent": st.session_state.get("annotations_text_present"),
            "PhiPresent": st.session_state.get("phi_present"),
            "PostProcessing": st.session_state.get("post_processing"),
            "ViewPresent": st.session_state.get("view_present"),
        }])
    else:
        return  # Invalid role or missing selected_row

    # Safe concurrent save with retry logic
    for attempt in range(max_retries):
        try:
            # Read existing data
            try:
                df_existing = pd.read_parquet(out_path)
            except (FileNotFoundError, Exception):
                df_existing = pd.DataFrame()

            # Remove any existing annotations for the same image_path and username
            # to avoid duplicates when saving partial annotations
            if not df_existing.empty:
                if role == "Clinician":
                    username_col = "Username_cl"
                else:
                    username_col = "Username_ds"
                
                # Remove existing entries for the same images
                image_paths_to_remove = df_new["image_path"].unique()
                df_existing = df_existing[
                    ~((df_existing["image_path"].isin(image_paths_to_remove)) & 
                      (df_existing[username_col] == username))
                ]

            # Combine existing and new data
            df_to_save = pd.concat([df_existing, df_new], ignore_index=True)
            
            # Save to temporary file first, then move to final location
            with tempfile.NamedTemporaryFile(delete=False, suffix=".parquet") as tmp:
                df_to_save.to_parquet(tmp.name, index=False)
                
            # Atomic move
            shutil.move(tmp.name, out_path)
            
            # Update session state with new data
            if role == "Clinician":
                st.session_state.df_cl = df_to_save
            else:
                st.session_state.df_ds = df_to_save
            
            st.session_state.annotation_saved = True
            break
            
        except (PermissionError, OSError) as e:
            if attempt < max_retries - 1:
                time.sleep(backoff * (2 ** attempt))  # Exponential backoff
            else:
                st.error(f"Failed to save annotations after {max_retries} attempts: {str(e)}")

@contextmanager
def locked_file(file_path):
    if not os.path.exists(file_path):
        open(file_path, 'wb').close()
    with open(file_path, 'r+b') as f:
        try:
            msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, os.path.getsize(file_path))
        finally:
            f.seek(0)
            msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, os.path.getsize(file_path))
    yield

def all_annotations_filled():
    """
    Check if all required annotations are filled based on user role.
    """
    role = st.session_state.get("role", "Unknown")

    clinician_keys = [
        "ards_likelihood",
        "diffuse_damage",
        "pleural_lesion",
        "pulmonary_edema",
        "consolidation",
        "atelectasis",
        "mediastinum_findings",
        "sufficient_quality",
        "global_criteria",
    ]

    data_scientist_keys = [
        "intubated",
        "external_support_devices",
        "implanted_device",
        "foreign_bodies",
        "image_artifacts",
        "annotations_text_present",
        "phi_present",
        "post_processing",
        "view_present",
    ]

    if role == "Clinician":
        keys_to_check = clinician_keys
    elif role == "Data Scientist":
        keys_to_check = data_scientist_keys
    else:
        return False

    return all(st.session_state.get(key) is not None for key in keys_to_check)

def save_partial_annotation(image_path, role, username):
    """Save partial annotation immediately when radio buttons change"""
    if role == "Data Scientist":
        idx = st.session_state.get("ds_idx")
        if idx is not None:
            selected_row = st.session_state.dicom_df.iloc[idx]
            save_all_views_for_patient(
                patient_df=None,
                username=username,
                role=role,
                selected_row=selected_row
            )
    elif role == "Clinician":
        current_group = st.session_state.get("current_patient_group")
        if current_group:
            patient_df = st.session_state.dicom_df[
                st.session_state.dicom_df["study_icn"] == current_group
            ]
            save_all_views_for_patient(
                patient_df=patient_df,
                username=username,
                role=role
            )