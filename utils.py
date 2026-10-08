"""utils.py - constants, validation helpers, password hashing, CSV export and small UI helpers."""
import hashlib
import re
import pandas as pd
import streamlit as st

BRANCHES = ["AIML", "Computer Engineering", "IT", "Mechanical", "Electrical", "Civil"]
YEARS = ["1st Year", "2nd Year", "3rd Year", "4th Year"]
GENDERS = ["Male", "Female", "Other"]
ROOM_TYPES = ["Single", "Double", "Triple", "Four-Seater"]
STATUSES = ["Active", "Inactive"]

LABELS = {"student_id": "Student ID", "enrollment_no": "Enrollment No", "id": "ID",
          "mobile": "Mobile", "guardian_name": "Guardian Name", "guardian_contact": "Guardian Contact",
          "available_beds": "Available Beds", "fee": "Fee (Rs)", "total_fee": "Total Fee (Rs)",
          "amount_paid": "Amount Paid (Rs)", "remaining": "Remaining (Rs)", "room_fee": "Room Fee (Rs)"}


def hash_password(password):
    """Return the SHA-256 hash of a password (plain passwords are never stored)."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def is_valid_email(email):
    return re.fullmatch(r"[\w.+-]+@[\w-]+(\.[\w-]+)+", email.strip()) is not None


def is_valid_mobile(mobile):
    """10-digit Indian mobile number starting with 6-9."""
    return re.fullmatch(r"[6-9]\d{9}", mobile.strip()) is not None


def calc_fee_status(total, paid):
    if paid <= 0:
        return "Pending"
    if paid < total:
        return "Partial"
    return "Paid"


def to_csv(df):
    """Convert a DataFrame to CSV bytes for st.download_button."""
    return df.to_csv(index=False).encode("utf-8")


def search_df(df, text, columns):
    """Keep rows where any of the given columns contains the text (case-insensitive)."""
    text = text.strip()
    if not text:
        return df
    mask = pd.Series(False, index=df.index)
    for col in columns:
        mask |= df[col].astype(str).str.contains(text, case=False, regex=False, na=False)
    return df[mask]


def filter_isin(df, column, selected):
    """Apply a multiselect filter; an empty selection means 'no filter'."""
    if selected:
        return df[df[column].isin(selected)]
    return df


def pretty(df, drop=()):
    """Prepare a DataFrame for display: drop internal columns and make headings readable."""
    out = df.drop(columns=list(drop), errors="ignore").copy()
    out.columns = [LABELS.get(c, c.replace("_", " ").title()) for c in out.columns]
    return out


def flash(message, kind="success"):
    """Store a message that will be shown after the next rerun."""
    st.session_state["flash"] = (kind, message)


def show_flash():
    if "flash" in st.session_state:
        kind, message = st.session_state.pop("flash")
        getattr(st, kind)(message)


def next_form_key(name):
    """Counter used to reset (clear) a form after a successful submit."""
    return f"{name}_{st.session_state.get(name + '_ctr', 0)}"


def reset_form(name):
    st.session_state[name + "_ctr"] = st.session_state.get(name + "_ctr", 0) + 1
