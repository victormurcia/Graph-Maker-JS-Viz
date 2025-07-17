import streamlit as st
import pandas as pd
from dicom_utils import safe_float, digital_xray_from_dicom
from callbacks import update_window_range, reset_windowing
import pydicom
from pydicom.valuerep import PersonName

def reinitialize_window_state(image_path):
    if (
        "native_center" not in st.session_state
        or "native_width" not in st.session_state
        or st.session_state.get("last_loaded_image") != image_path
    ):
        ds = pydicom.dcmread(image_path)
        _, ww, wc, lower, upper = digital_xray_from_dicom(ds)

        # Calculate theoretical min/max
        bits_stored = ds.get("BitsStored", 12)
        is_signed = ds.get("PixelRepresentation", 0) == 1
        if is_signed:
            intensity_min = -2 ** (bits_stored - 1)
            intensity_max = 2 ** (bits_stored - 1) - 1
        else:
            intensity_min = 0
            intensity_max = 2 ** bits_stored - 1

        st.session_state.native_center = int(wc)
        st.session_state.native_width = int(ww)
        st.session_state.wc_val = int(wc)
        st.session_state.ww_val = int(ww)
        st.session_state.intensity_min = intensity_min
        st.session_state.intensity_max = intensity_max
        st.session_state.window_range_slider = (int(wc - ww // 2), int(wc + ww // 2))
        st.session_state.last_loaded_image = image_path

def render_window_controls():
    st.markdown("### 🖼 Windowing Controls")

    min_possible = int(st.session_state.get("intensity_min", 0))  # fallback to 0
    max_possible = int(st.session_state.get("intensity_max", 4095))  # fallback to 12-bit

    col1, col2 = st.columns([3, 1.3])
    with col1:
        st.slider(
            "Windowing Range (min/max)",
            min_value=min_possible,
            max_value=max_possible,
            value=st.session_state.get("window_range_slider", (
                st.session_state.wc_val - st.session_state.ww_val // 2,
                st.session_state.wc_val + st.session_state.ww_val // 2
            )),
            step=1,
            key="window_range_slider",
            on_change=update_window_range
        )
    with col2:
        st.button("🔄 Reset", on_click=reset_windowing)

def render_dicom_metadata(row):
    """
    Render the DICOM metadata by reading the DICOM header.

    Parameters:
    - row: A dictionary or pandas Series containing at least the 'image_path'.
    """
    st.markdown("### 📋 DICOM Metadata")

    metadata_fields = [
        "PatientName", "PatientID", "PatientSex", "PatientAge",
        "PatientBirthDate", "StudyDate", "StudyTime",
        "BodyPartExamined", "PatientPosition"
    ]

    try:
        ds = pydicom.dcmread(row["image_path"], stop_before_pixels=True)

        def normalize(val):
            if isinstance(val, PersonName):
                return str(val).replace("^", " ")
            return str(val) if val is not None else None

        metadata_values = [normalize(getattr(ds, field, None)) for field in metadata_fields]

    except Exception as e:
        st.error(f"Error reading DICOM metadata: {e}")
        metadata_values = [None] * len(metadata_fields)

    metadata_df = pd.DataFrame({
        "Field": metadata_fields,
        "Value": metadata_values
    })

    st.markdown(
                """
                <style>
                [data-testid="stElementToolbar"] {
                    display: none;
                }
                </style>
                """,
                unsafe_allow_html=True
            )
    
    st.dataframe(metadata_df, use_container_width=True)

def render_clinical_info_placeholder():
    """
    Render a placeholder for clinical values.

    This function displays a title and an "info" message indicating that clinical values are coming soon.
    """
    st.title("Clinical Values")
    st.info("Coming soon...")
