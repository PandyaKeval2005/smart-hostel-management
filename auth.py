"""auth.py - admin login / logout using hashed passwords and Streamlit session state."""
import streamlit as st
from database import run_query
from utils import hash_password


def check_login(username, password):
    """Return (True, '') on success or (False, error message)."""
    df = run_query("SELECT password_hash FROM admins WHERE username = ?", (username,))
    if df.empty:
        return False, "Incorrect username."
    if df["password_hash"][0] != hash_password(password):
        return False, "Incorrect password."
    return True, ""


def login_page():
    _, col, _ = st.columns([1, 1.3, 1])
    with col:
        st.markdown("## 🏨 Smart Hostel Management System")
        st.caption("Please sign in as administrator to continue.")
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("🔐 Login")
        if submitted:
            username = username.strip()
            if not username or not password:
                st.error("Username and password cannot be empty.")
            else:
                ok, message = check_login(username, password)
                if ok:
                    st.session_state["logged_in"] = True
                    st.session_state["username"] = username
                    st.rerun()
                else:
                    st.error(message)
        st.info("Demo login → Username: **admin** | Password: **admin123**")


def logout():
    """Clear the whole session so the login page is shown again."""
    st.session_state.clear()
