import streamlit as st
import pydicom
import matplotlib.pyplot as plt
import plotly.express as px
import numpy as np
from pydicom.multival import MultiValue

def digital_xray_from_dicom(dcmf):
    """
    Convert a DICOM file to a digital X-ray image.

    Parameters:
    - dcmf: DICOM file object (pydicom.dataset.FileDataset).

    Returns:
    A processed numpy array representing the X-ray image.
    """
    im = dcmf.pixel_array.astype(np.float32)
    
    # Rescale using slope & intercept
    if hasattr(dcmf, 'RescaleSlope') and hasattr(dcmf, 'RescaleIntercept'):
        im = im * dcmf.RescaleSlope + dcmf.RescaleIntercept
        
    # Use the provided smallest and largest pixel values if available
    if hasattr(dcmf, 'SmallestImagePixelValue') and hasattr(dcmf, 'LargestImagePixelValue'):
        min_val = dcmf.SmallestImagePixelValue
        max_val = dcmf.LargestImagePixelValue
    else:
        # Otherwise, compute from the pixel data itself
        min_val = np.min(im)
        max_val = np.max(im)
    
    # Apply windowing
    if hasattr(dcmf, 'WindowCenter') and hasattr(dcmf, 'WindowWidth'):
        wc = dcmf.WindowCenter
        ww = dcmf.WindowWidth
    
        # Handle multiple values in Window Center/Window Width
        if isinstance(wc, pydicom.multival.MultiValue):
            wc = wc[0]
        if isinstance(ww, pydicom.multival.MultiValue):
            ww = ww[0]
    else:
        # Use dynamic range from smallest and largest pixel values
        wc = (min_val + max_val) / 2.0
        ww = (max_val - min_val)  
         
    lower = wc - (ww/2)
    upper = wc + (ww/2)
        
    im = np.clip(im, lower, upper)    

    if dcmf.PhotometricInterpretation == "MONOCHROME1":
        im = np.max(im) - im  # Invert image    
               
    return im, ww, wc, lower, upper

def get_first_element(value):
    """
    Extract the first element from a MultiValue object or convert a single value to float.

    Parameters:
    - value: A MultiValue or single value to convert.

    Returns:
    The first element as a float, or None if conversion fails.
    """
    if isinstance(value, MultiValue):
        return float(value[0])
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
    
def safe_float(val):
    """
    Safely convert a value to float, handling MultiValue and common containers.

    Parameters:
    - val: The value to convert, which may be a MultiValue, list, tuple, or single value.

    Returns:
    The converted float value, or None if conversion fails.
    """
    try:
        if isinstance(val, MultiValue):
            return float(val[0])
        elif isinstance(val, (list, tuple)):
            return float(val[0])
        else:
            return float(val)
    except (TypeError, ValueError, IndexError):
        return None
    
# --- Display a DICOM File ---
def display_dicom(
    filepath,
    downsample_factor: int = 4,
    window_center: float = None,
    window_width: float = None
):
    """
    Display a DICOM file in a Streamlit app, with optional downsampling and windowing.

    Parameters:
    - filepath: Path to the DICOM file.
    - downsample_factor: Factor by which to downsample the image (default is 4).
    - window_center: Custom window center for image display (default is None).
    - window_width: Custom window width for image display (default is None).
    """
    try:
        # 1. Read and rescale
        ds = pydicom.dcmread(filepath)
        arr, ww, wc, lower, upper = digital_xray_from_dicom(ds)

        # 2. Downsample (if desired)
        if downsample_factor > 1:
            arr = arr[::downsample_factor, ::downsample_factor]

        center = window_center or wc
        width = window_width or ww

        # 4. Compute zmin/zmax
        zmin = (center - width / 2.0) or lower
        zmax = (center + width / 2.0) or upper

        # 5. Plot with Plotly (zmin/zmax do the windowing)
        fig = px.imshow(
            arr,
            color_continuous_scale="gray",
            aspect="equal",
            zmin=zmin,
            zmax=zmax,
            origin="upper",
            x=np.arange(arr.shape[1]),
            y=np.arange(arr.shape[0])
        )
        fig.update_layout(
            coloraxis_showscale=False,
            margin=dict(l=0, r=0, t=0, b=0),
            dragmode="pan",
            autosize=True,
            height=600,
        )
        fig.update_xaxes(showticklabels=False)
        fig.update_yaxes(showticklabels=False)

        st.plotly_chart(
            fig, use_container_width=True, config={"displayModeBar": True, "modeBarButtonsToRemove": ["toImage"]}
        )
    except Exception as e:
        st.error(f"There was an error processing the DICOM file: {e}")