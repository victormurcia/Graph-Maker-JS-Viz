import streamlit as st
from sidebar_utils import (
    render_window_controls,
    render_dicom_metadata,
    render_clinical_info_placeholder,
    reinitialize_window_state,
)
from dicom_utils import display_dicom
from annotation_utils import render_radio_fields, CLINICIAN_RADIOS, DATA_SCIENTIST_RADIOS,all_annotations_filled, refresh_form_complete
from navigation import previous_view, next_view, on_prev_click, on_next_click, previous_study, next_study
from datetime import datetime

def render_role_interface(role, dicom_df, selected_row, username):
    """
    Render the user interface based on the user's role, DICOM data, and selected row.

    This function:
    - Displays the DICOM navigator, header, window controls, and metadata.
    - Provides navigation controls for Clinicians and Data Scientists.
    - Displays the DICOM image with windowing controls.
    - Renders annotation fields based on the user's role.
    
    Parameters:
    - role: User's role ("Clinician" or "Data Scientist").
    - dicom_df: DataFrame containing DICOM information.
    - selected_row: The currently selected row in the DICOM data.
    """

    if st.session_state.get("trigger_rerun", False):
        st.session_state.trigger_rerun = False
        st.rerun()

    if "form_complete" not in st.session_state:
        refresh_form_complete()
    
    if role == "Data Scientist":
        ds_idx = st.session_state.get("ds_idx", 0)
        selected_row = dicom_df.iloc[ds_idx]
    # Columns layout
    dicom_navigator, annotations = st.columns([5, 2])

    with dicom_navigator:
        st.title(f"DICOM Navigator ({role})[{username}]")
        display_dicom_header(selected_row)

        reinitialize_window_state(selected_row["image_path"])

        with st.sidebar:
            render_window_controls()

            tabs = st.tabs(["Clinical Info", "DICOM Metadata"])
            with tabs[0]:
                render_clinical_info_placeholder()

            with tabs[1]:
                render_dicom_metadata(selected_row)
            
        if role == "Clinician":
            study_idx = st.session_state.get("study_idx", 0)
            study_keys = list(st.session_state.study_groups.keys())
            total_studies = len(study_keys)
            saving_study = st.session_state.get("saving_study_annotation", False)
            complete = st.session_state.get("form_complete", False)

            col8, col9, col10 = st.columns([1, 3, 1])
            with col8:
                st.button("⬅️ Previous Study", on_click=previous_study, disabled=saving_study or not complete or study_idx == 0)
            with col9:
                st.markdown(f"<div style='text-align:center; font-weight:bold;'>Study {study_idx+1} / {total_studies}</div>", unsafe_allow_html=True)
            with col10:
                st.button("➡️ Next Study", on_click=next_study, disabled=saving_study or not complete or study_idx >= total_studies - 1)

        if role == "Data Scientist":
            saving_ds = st.session_state.get("saving_ds_annotation", False)
            ds_idx = st.session_state.get("ds_idx", 0)
            total_images = len(dicom_df)

            complete = st.session_state.get("form_complete", False)
            
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                st.button("⬅️ Previous Image", on_click=on_prev_click, disabled=saving_ds or not complete or ds_idx == 0)
            with col2:
                st.markdown(f"<div style='text-align:center; font-weight:bold;'>Image {ds_idx+1} / {total_images}</div>", unsafe_allow_html=True)
            with col3:
                st.button("➡️ Next Image", on_click=on_next_click, disabled=saving_ds or not complete or ds_idx >= total_images - 1)

        # Display DICOM (shared)
        display_dicom(
            selected_row["image_path"],
            downsample_factor=4,
            window_center=st.session_state.wc_val,
            window_width=st.session_state.ww_val,
        )

        if "form_complete" not in st.session_state:
            refresh_form_complete()
            
        if role == "Clinician":
            current_study = study_keys[study_idx]
            df_views = dicom_df[dicom_df['study_icn'] == current_study]
            view_idx = st.session_state.get("view_idx", 0)
            total_views = len(df_views)

            saving_view = st.session_state.get("saving_view_annotation", False)
            complete = st.session_state.get("form_complete", False)

            col5, col6, col7 = st.columns([1, 3, 1])
            with col5:
                st.button("⬅️ Previous View", on_click=previous_view, disabled=saving_view or not complete or view_idx == 0)
            with col6:
                st.markdown(f"<div style='text-align:center; font-weight:bold;'>View {view_idx+1} / {total_views}</div>", unsafe_allow_html=True)
            with col7:
                st.button("➡️ Next View", on_click=next_view, disabled=saving_view or not complete or view_idx >= total_views - 1)

    with annotations:
        st.title("Annotations")

        if role == "Clinician":
            render_radio_fields(CLINICIAN_RADIOS, selected_row["image_path"], role, username)
        elif role == "Data Scientist":
            render_radio_fields(DATA_SCIENTIST_RADIOS, selected_row["image_path"], role, username)

        render_annotation_feedback()

def display_dicom_header(row):
    """
    Display the header information of the currently selected DICOM file.

    This function shows the patient information, view folder, and file information in a centered format.

    Parameters:
    - row: The currently selected row in the DICOM data containing header information.
    """
    st.markdown(
        f"""
        <div style='text-align:center; font-size:14px;'>
            <strong>Study:</strong> {row.get('study_icn')} &nbsp; | &nbsp;
            <strong>View folder:</strong> {row.get('study_icn')} &nbsp; | &nbsp;
            <strong>File:</strong> {row.get('dicom_id')}
        </div>
        """,
        unsafe_allow_html=True
    )

def render_annotation_feedback():
    """
    Render feedback messages based on the current annotation status.

    This function displays warnings if not all annotation fields are filled and 
    shows success messages if annotations are saved.
    """
    if st.session_state.get("annotation_warning"):
        st.warning("⚠️ Please complete **all annotation fields** before navigating to another patient.")
    if st.session_state.get("annotation_saved"):
        st.success("✅ Annotation Saved!")
        st.session_state.annotation_saved = False
    st.session_state.annotation_warning = False