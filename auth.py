import streamlit as st

def login():
    """
    Display a login form and handle user authentication.

    This function:
    - Displays a login form with fields for username and password.
    - Handles the form submission and authenticates the user based on credentials stored in Streamlit secrets.
    - Updates session state upon successful login and triggers a rerun with the user logged in.
    - Shows appropriate error messages for invalid login attempts.
    """
    st.title("🔒 Login Required")

    # Only show input fields if not logged in
    if "login_submitted" not in st.session_state:
        st.session_state.login_submitted = False

    # Get or initialize username/password in session state to preserve values
    if "username" not in st.session_state:
        st.session_state.username = ""
    if "password" not in st.session_state:
        st.session_state.password = ""

    # Function to handle login form submission
    def handle_login():
        st.session_state.login_submitted = True

    username = st.text_input("Username", value=st.session_state.username, key="username_input")
    password = st.text_input("Password", type="password", value=st.session_state.password, key="password_input")
    
    # Update session state with current input values
    st.session_state.username = username
    st.session_state.password = password
    
    # Login button
    login_btn = st.button("Login", on_click=handle_login)

    # Process login after submission
    if st.session_state.login_submitted:
        credentials = st.secrets["credentials"]
        if username in credentials and password == credentials[username]["password"]:
            st.session_state['logged_in'] = True
            st.session_state['username'] = username
            st.session_state['role'] = credentials[username]["role"]
            st.success(f"Welcome, {username} ({st.session_state['role']})!")
            # Reset login_submitted to avoid reprocessing on page rerun
            st.session_state.login_submitted = False
            # This will trigger a rerun with logged_in=True
            st.rerun()
        else:
            st.error("Invalid username or password.")
            # Reset login_submitted if login failed
            st.session_state.login_submitted = False

def logout():
    """
    Handle the logout process.

    This function:
    - Resets the session state related to login.
    - Triggers a rerun to show the login form.
    """
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.session_state["logged_in"] = False
    st.rerun()