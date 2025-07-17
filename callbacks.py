import streamlit as st

def update_wc_slider():
    st.session_state.wc_val = st.session_state.wc_slider_val

def update_ww_slider():
    st.session_state.ww_val = st.session_state.ww_slider_val

def reset_wc():
    st.session_state.wc_val = st.session_state.native_center
    st.session_state.wc_slider_val = st.session_state.native_center

def reset_ww():
    st.session_state.ww_val = st.session_state.native_width
    st.session_state.ww_slider_val = st.session_state.native_width

def update_window_range():
    lower, upper = st.session_state.window_range_slider
    st.session_state.wc_val = int((lower + upper) / 2)
    st.session_state.ww_val = int(upper - lower)

def reset_windowing():
    center = st.session_state.native_center
    width = st.session_state.native_width
    lower = center - width // 2
    upper = center + width // 2

    st.session_state.window_range_slider = (lower, upper)
    st.session_state.wc_val = center
    st.session_state.ww_val = width