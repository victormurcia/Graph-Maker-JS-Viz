import streamlit as st
from datetime import datetime
from annotation_utils import (
    reset_annotation_fields,
    all_annotations_filled,
    save_all_views_for_patient,
    refresh_form_complete,
    load_annotations_for_image
)

_MIN_NAV_INTERVAL = 1.0 # seconds

def _too_soon(flag, cooldown=_MIN_NAV_INTERVAL):
    now = datetime.now().timestamp()
    last = st.session_state.get(flag, 0)
    st.session_state[flag] = now
    return now - last < cooldown

# --- Clinician Study Navigation ---
def navigate_study_group(direction):
    if st.session_state.get("saving_study_annotation", False) or _too_soon("last_study_nav"):
        return

    if not all_annotations_filled():
        st.session_state.annotation_warning = True
        refresh_form_complete()
        return

    st.session_state["saving_study_annotation"] = True
    try:
        study_idx = st.session_state.get("study_idx", 0)
        keys = list(st.session_state.study_groups.keys())
        total = len(keys)

        if (direction == "prev" and study_idx == 0) or (direction == "next" and study_idx >= total - 1):
            return

        current_key = keys[study_idx]
        df = st.session_state.dicom_df[st.session_state.dicom_df['study_icn'] == current_key]
        save_all_views_for_patient(df, st.session_state.username, st.session_state.role)

        st.session_state.study_idx = study_idx + (1 if direction == "next" else -1)
        st.session_state.view_idx = 0

        new_key = keys[st.session_state.study_idx]
        df_new = st.session_state.dicom_df[st.session_state.dicom_df['study_icn'] == new_key]
        load_annotations_for_image(df_new.iloc[0]["image_path"], "Clinician", st.session_state.username)
        refresh_form_complete()
        st.session_state.annotation_start_time = datetime.now()
    finally:
        st.session_state["saving_study_annotation"] = False

def previous_study():
    navigate_study_group("prev")
    st.rerun()

def next_study():
    navigate_study_group("next")
    st.rerun()

# --- Clinician View Navigation ---
def navigate_view(direction):
    if st.session_state.get("saving_view_annotation", False) or _too_soon("last_view_nav"):
        return

    if not all_annotations_filled():
        st.session_state.annotation_warning = True
        refresh_form_complete()
        return

    st.session_state["saving_view_annotation"] = True
    try:
        view_idx = st.session_state.get("view_idx", 0)
        keys = list(st.session_state.study_groups.keys())
        current_key = keys[st.session_state.study_idx]
        df = st.session_state.dicom_df[st.session_state.dicom_df['study_icn'] == current_key]
        total = len(df)

        if (direction == "prev" and view_idx == 0) or (direction == "next" and view_idx >= total - 1):
            return

        current = df.iloc[view_idx]
        save_all_views_for_patient(df, st.session_state.username, st.session_state.role)

        st.session_state.view_idx = view_idx + (1 if direction == "next" else -1)
        reset_annotation_fields()
        new = df.iloc[st.session_state.view_idx]
        load_annotations_for_image(new["image_path"], "Clinician", st.session_state.username)
        refresh_form_complete()
        st.session_state.annotation_start_time = datetime.now()
    finally:
        st.session_state["saving_view_annotation"] = False

def previous_view():
    navigate_view("prev")
    st.rerun()

def next_view():
    navigate_view("next")
    st.rerun()

# --- Data Scientist Navigation ---
def navigate_ds(direction):
    if st.session_state.get("saving_ds_annotation", False) or _too_soon("last_ds_nav"):
        return

    if not all_annotations_filled():
        st.session_state.annotation_warning = True
        refresh_form_complete()
        return

    st.session_state["saving_ds_annotation"] = True
    try:
        idx = st.session_state.get("ds_idx", 0)
        total = len(st.session_state.dicom_df)

        if (direction == "prev" and idx == 0) or (direction == "next" and idx >= total - 1):
            return

        current = st.session_state.dicom_df.iloc[idx]
        save_all_views_for_patient(None, st.session_state.username, st.session_state.role, current)

        st.session_state.ds_idx = idx + (1 if direction == "next" else -1)
        reset_annotation_fields()
        new = st.session_state.dicom_df.iloc[st.session_state.ds_idx]
        load_annotations_for_image(new["image_path"], "Data Scientist", st.session_state.username)
        refresh_form_complete()
        st.session_state.annotation_start_time = datetime.now()
    finally:
        st.session_state["saving_ds_annotation"] = False

def on_prev_click():
    navigate_ds("prev")
    st.experimental_rerun()

def on_next_click():
    navigate_ds("next")
    st.experimental_rerun()
