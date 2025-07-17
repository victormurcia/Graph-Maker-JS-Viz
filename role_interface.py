import streamlit as st
from sidebar_utils import (
    render_window_controls,
    render_dicom_metadata,
    render_clinical_info_placeholder,
    reinitialize_window_state,
)
from dicom_utils import display_dicom
from annotation_utils import render_radio_fields, CLINICIAN_RADIOS, DATA_SCIENTIST_RADIOS,all_annotations_filled, refresh_form_complete,load_annotations_for_image
from navigation import previous_view, next_view, previous_study, next_study, on_prev_click, on_next_click, _too_soon
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
        if "ds_idx" not in st.session_state:
            st.session_state.ds_idx = 0
        ds_idx = st.session_state.ds_idx
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
            # Patient navigation (ABOVE image)
            patients = dicom_df['study_icn'].unique()
            current_patient_index = list(patients).index(st.session_state.current_patient_group)
            num_patients = len(patients)

            saving = st.session_state.get("saving_annotation", False)
            complete = st.session_state.get("form_complete", False)
            
            col1, col2, col3 = st.columns([1, 3, 1])
            with col1:
                if st.button("⬅️ Previous Study", disabled=saving or not complete, on_click=previous_study):
                    st.rerun()

            with col2:
                st.markdown(
                    f"<div style='text-align:left; font-weight:bold;'>Study {current_patient_index + 1} / {num_patients}</div>",
                    unsafe_allow_html=True
                )

            with col3:
                if st.button("➡️ Next Study",disabled=saving or not complete, on_click=next_study, key="btn_next_study",):
                    if st.session_state.get("annotation_warning") or all_annotations_filled():
                        st.rerun()
                    else:
                        st.session_state.annotation_warning = True

        if role == "Data Scientist":
            # initialize and pick the current row
            if "ds_idx" not in st.session_state:
                st.session_state.ds_idx = 0
            ds_idx = st.session_state.ds_idx
            selected_row = dicom_df.iloc[ds_idx]

            # Load annotations for current image (this was missing!)
            load_annotations_for_image(
                selected_row["image_path"], 
                "Data Scientist", 
                st.session_state.get("username")
            )

            # immediately recompute form completeness for the current image
            refresh_form_complete()

            # navigation state - CRITICAL: buttons must be disabled immediately after click
            saving = st.session_state.get("saving_annotation", False)
            navigating = st.session_state.get("navigating_annotation", False)
            navigation_in_progress = st.session_state.get("navigation_in_progress", False)
            complete = st.session_state.get("form_complete", False)

            total = len(dicom_df)
            col1, col2, col3 = st.columns([1, 3, 1])

            with col1:
                # Disable if ANY of these conditions are true:
                # - Currently saving annotations
                # - Navigation flag is set (immediately after button click)
                # - Navigation is in progress
                # - Form is incomplete
                # - At beginning of dataset
                prev_disabled = (saving or navigating or navigation_in_progress or 
                               not complete or ds_idx == 0)
                st.button(
                    "⬅️ Previous Image",
                    disabled=prev_disabled,
                    on_click=on_prev_click,
                    key="btn_prev_ds"
                )

            with col2:
                st.markdown(
                    f"<div style='text-align:center;'><strong>Record {ds_idx+1} / {total}</strong></div>",
                    unsafe_allow_html=True
                )

            with col3:
                # Disable if ANY of these conditions are true:
                # - Currently saving annotations
                # - Navigation flag is set (immediately after button click)
                # - Navigation is in progress
                # - Form is incomplete
                # - At end of dataset
                next_disabled = (saving or navigating or navigation_in_progress or 
                               not complete or ds_idx >= total - 1)
                st.button(
                    "➡️ Next Image",
                    disabled=next_disabled,
                    on_click=on_next_click,
                    key="btn_next_ds"
                )

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
            # View navigation (BELOW image)
            num_views = len(dicom_df[dicom_df['study_icn'] == st.session_state.current_patient_group])
            view_idx = st.session_state.get("view_idx", 0)
            col5, col6, col7 = st.columns([1, 3, 1])
            with col5:
                if st.button("⬅️ Previous View"):
                    previous_view()
                    st.rerun()

            with col6:
                st.markdown(
                    f"<div style='text-align:center; font-weight:bold;'>View {view_idx + 1} / {num_views}</div>",
                    unsafe_allow_html=True
                )

            with col7:
                if st.button("➡️ Next View"):
                    next_view()
                    st.rerun()

    with annotations:
        st.title("Annotations")

        if role == "Clinician":
            render_radio_fields(CLINICIAN_RADIOS, selected_row["image_path"], role, username)
        elif role == "Data Scientist":
            render_radio_fields(DATA_SCIENTIST_RADIOS, selected_row["image_path"], role, username)

        # ✅ Trigger rerun if form just became complete
        if st.session_state.get("form_complete", False) and not st.session_state.get("trigger_rerun", False):
            st.session_state.trigger_rerun = True

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