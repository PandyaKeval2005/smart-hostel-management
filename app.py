"""app.py - entry point. Run with:  streamlit run app.py"""
import streamlit as st
from database import init_db
from auth import login_page, logout
from dashboard import show_dashboard
from student_management import show_student_management
from room_management import show_room_management
from fee_management import show_fee_management

st.set_page_config(page_title="Smart Hostel Management", page_icon="🏨", layout="wide")
st.markdown("""
<style>
[data-testid="stMetric"] {background: rgba(128,128,128,0.08); border: 1px solid rgba(128,128,128,0.25);
                          border-radius: 12px; padding: 14px 16px;}
.block-container {padding-top: 2rem;}
</style>""", unsafe_allow_html=True)

init_db()   # creates database, tables and default admin automatically

if not st.session_state.get("logged_in", False):
    login_page()
    st.stop()  # nothing below is reachable without logging in

MENU = ["🏠 Dashboard", "👨‍🎓 Student Management", "🛏️ Room Management", "💰 Fee Management", "🚪 Logout"]
st.sidebar.title("🏨 Smart Hostel")
st.sidebar.caption(f"Logged in as **{st.session_state.get('username', 'admin')}**")
choice = st.sidebar.radio("Navigation", MENU)

if choice == MENU[0]:
    show_dashboard()
elif choice == MENU[1]:
    show_student_management()
elif choice == MENU[2]:
    show_room_management()
elif choice == MENU[3]:
    show_fee_management()
else:
    logout()
    st.rerun()
