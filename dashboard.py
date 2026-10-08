"""dashboard.py - KPI cards, Plotly charts and recent records (all calculated from SQLite)."""
import pandas as pd
import plotly.express as px
import streamlit as st
from database import get_rooms, get_students, get_fees, seed_sample_data
from utils import YEARS, pretty, flash, show_flash


def show_dashboard():
    st.title("🏠 Dashboard")
    show_flash()
    rooms, students, fees = get_rooms(), get_students(), get_fees()

    total_beds = int(rooms["capacity"].sum())
    occupied = int(rooms["occupied_beds"].sum())
    total_fee = float(fees["total_fee"].sum())
    collected = float(fees["amount_paid"].sum())

    c = st.columns(4)
    c[0].metric("👨‍🎓 Total Students", len(students))
    c[1].metric("🚪 Total Rooms", len(rooms))
    c[2].metric("🛏️ Total Beds", total_beds)
    c[3].metric("✅ Occupied Beds", occupied)
    c = st.columns(4)
    c[0].metric("🟢 Available Beds", total_beds - occupied)
    c[1].metric("💵 Total Hostel Fees", f"₹{total_fee:,.0f}")
    c[2].metric("💰 Fees Collected", f"₹{collected:,.0f}")
    c[3].metric("⏳ Pending Fees", f"₹{total_fee - collected:,.0f}")

    st.divider()
    if students.empty and rooms.empty:
        st.info("The database is empty. Add records or load demo data below.")
    else:
        col1, col2 = st.columns(2)
        occ = pd.DataFrame({"Bed Status": ["Occupied", "Available"], "Beds": [occupied, total_beds - occupied]})
        col1.plotly_chart(px.pie(occ, names="Bed Status", values="Beds", hole=0.45, title="Room Occupancy",
                                 color="Bed Status", color_discrete_map={"Occupied": "#EF553B", "Available": "#00CC96"}))
        if fees.empty:
            col2.info("No fee records yet.")
        else:
            fs = fees["payment_status"].value_counts().reindex(["Paid", "Partial", "Pending"], fill_value=0)
            fs = fs.rename_axis("Status").reset_index(name="Records")
            col2.plotly_chart(px.pie(fs, names="Status", values="Records", hole=0.45, title="Fee Status",
                                     color="Status", color_discrete_map={"Paid": "#00CC96", "Partial": "#FFA15A", "Pending": "#EF553B"}))
        col3, col4 = st.columns(2)
        if not students.empty:
            br = students["branch"].value_counts().rename_axis("Branch").reset_index(name="Students")
            col3.plotly_chart(px.bar(br, x="Branch", y="Students", title="Students by Branch", color="Branch", text="Students"))
            yr = students["year"].value_counts().reindex(YEARS, fill_value=0).rename_axis("Year").reset_index(name="Students")
            col4.plotly_chart(px.bar(yr, x="Year", y="Students", title="Students by Year", color="Year", text="Students"))

    st.subheader("🕒 Recent Records")
    t1, t2 = st.tabs(["Recently Added Students", "Recent Fee Payments"])
    with t1:
        if students.empty:
            st.info("No students yet.")
        else:
            st.dataframe(pretty(students.head(5)[["student_id", "full_name", "branch", "year", "room_number", "admission_date"]]),
                         hide_index=True)
    with t2:
        paid = fees[fees["payment_date"].notna()].sort_values(["payment_date", "id"], ascending=False).head(5)
        if paid.empty:
            st.info("No payments yet.")
        else:
            st.dataframe(pretty(paid[["student_id", "full_name", "amount_paid", "remaining", "payment_status", "payment_date"]]),
                         hide_index=True)

    with st.expander("🧪 Demo data"):
        st.write("Load about 18 students, 10 rooms and fee records to populate the dashboard.")
        if st.button("Load Sample Data"):
            if seed_sample_data():
                flash("Sample data loaded successfully.")
                st.rerun()
            else:
                st.warning("Sample data can only be loaded into an empty database.")
