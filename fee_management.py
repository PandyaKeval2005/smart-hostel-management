"""fee_management.py - fee records, payments, search and filters. Status/remaining are calculated."""
from datetime import date, timedelta
import pandas as pd
import streamlit as st
from database import get_students, get_fees, execute
from utils import (search_df, filter_isin, pretty, to_csv, flash, show_flash, next_form_key, reset_form)

HIDE = ["id", "student_pk"]


def validate_fee(total, paid, due, student_exists=True):
    errors = []
    if not student_exists:
        errors.append("Student does not exist.")
    if total < 0:
        errors.append("Total fee cannot be negative.")
    if paid < 0:
        errors.append("Amount paid cannot be negative.")
    if paid > total:
        errors.append("Amount paid cannot exceed the total fee.")
    if not isinstance(due, date):
        errors.append("Due date is invalid.")
    return errors


def fee_label(r):
    return f"Fee #{r.id} - {r.student_id} {r.full_name} (Remaining ₹{r.remaining:,.0f})"


def show_fee_management():
    st.title("💰 Fee Management")
    show_flash()
    tab_view, tab_add, tab_pay, tab_update, tab_delete = st.tabs(
        ["📋 View / Search", "➕ Add Fee Record", "💳 Record Payment", "✏️ Update Fee", "🗑️ Delete Fee"])
    fees, students = get_fees(), get_students()

    # ---- View / search / filter ----
    with tab_view:
        search = st.text_input("🔍 Search by Student ID, Enrollment No or Student Name")
        f = st.columns(3)
        status = f[0].multiselect("Payment Status", ["Paid", "Partial", "Pending"])
        rooms_f = f[1].multiselect("Room", sorted(fees["room_number"].dropna().unique()))
        students_f = f[2].multiselect("Student", sorted(fees["student_id"].unique()))
        date_range = st.date_input("Due date range (select start and end)", value=())
        df = search_df(fees, search, ["student_id", "enrollment_no", "full_name"])
        for col, sel in [("payment_status", status), ("room_number", rooms_f), ("student_id", students_f)]:
            df = filter_isin(df, col, sel)
        if len(date_range) == 2 and not df.empty:
            due = pd.to_datetime(df["due_date"]).dt.date
            df = df[(due >= date_range[0]) & (due <= date_range[1])]
        st.caption(f"Showing {len(df)} of {len(fees)} fee records")
        st.dataframe(pretty(df, drop=["student_pk"]).rename(columns={"ID": "Fee ID"}), hide_index=True)
        st.download_button("⬇️ Download Fee Report", to_csv(pretty(df, drop=["student_pk"])), "fee_report.csv", "text/csv")

    # ---- Add ----
    with tab_add:
        if students.empty:
            st.info("Add a student first.")
        else:
            choices = {f"{r.student_id} - {r.full_name}": r for r in students.itertuples()}
            s = choices[st.selectbox("Select student", list(choices), key="fee_add_student")]
            room = s.room_number if isinstance(s.room_number, str) else "Not assigned"
            st.info(f"**Name:** {s.full_name}  |  **Enrollment:** {s.enrollment_no}  |  **Room:** {room}")
            default_fee = float(s.room_fee) if s.room_fee == s.room_fee else 0.0   # NaN check
            key = next_form_key("add_fee")
            with st.form(key):
                c1, c2, c3 = st.columns(3)
                total = c1.number_input("Total Fee (₹)", 0.0, 10000000.0, default_fee, 500.0, key=f"{key}t{s.id}")
                paid = c2.number_input("Amount Paid (₹)", 0.0, 10000000.0, 0.0, 500.0, key=f"{key}p{s.id}")
                due = c3.date_input("Due Date", date.today() + timedelta(days=90), key=f"{key}d")
                submitted = st.form_submit_button("Add Fee Record")
            if submitted:
                errors = validate_fee(total, paid, due)
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    try:
                        execute("INSERT INTO fees (student_id, total_fee, amount_paid, payment_date, due_date) VALUES (?,?,?,?,?)",
                                (int(s.id), total, paid, date.today().isoformat() if paid > 0 else None, due.isoformat()))
                        reset_form("add_fee")
                        flash("Fee record added successfully.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Could not add fee record: {ex}")

    # ---- Record payment ----
    with tab_pay:
        due_fees = fees[fees["remaining"] > 0]
        if due_fees.empty:
            st.info("No pending dues. All fee records are fully paid.")
        else:
            choices = {fee_label(r): r for r in due_fees.itertuples()}
            r = choices[st.selectbox("Select fee record", list(choices), key="pay_pick")]
            st.info(f"Total: ₹{r.total_fee:,.0f}  |  Paid: ₹{r.amount_paid:,.0f}  |  Remaining: ₹{r.remaining:,.0f}  |  Status: {r.payment_status}")
            with st.form(f"pay_form_{r.id}"):
                amount = st.number_input("Payment Amount (₹)", 1.0, float(r.remaining), float(r.remaining), 500.0)
                submitted = st.form_submit_button("Record Payment")
            if submitted:
                if amount <= 0 or amount > r.remaining:
                    st.error("Payment must be positive and cannot exceed the remaining amount.")
                else:
                    try:
                        execute("UPDATE fees SET amount_paid = amount_paid + ?, payment_date = ? WHERE id = ?",
                                (amount, date.today().isoformat(), int(r.id)))
                        flash("Fee payment recorded successfully.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Could not record payment: {ex}")

    # ---- Update ----
    with tab_update:
        if fees.empty:
            st.info("No fee records to update.")
        else:
            choices = {fee_label(r): r for r in fees.itertuples()}
            r = choices[st.selectbox("Select fee record", list(choices), key="fee_upd_pick")]
            with st.form(f"fee_upd_{r.id}"):
                c1, c2, c3 = st.columns(3)
                total = c1.number_input("Total Fee (₹)", 0.0, 10000000.0, float(r.total_fee), 500.0)
                paid = c2.number_input("Amount Paid (₹)", 0.0, 10000000.0, float(r.amount_paid), 500.0)
                due = c3.date_input("Due Date", date.fromisoformat(r.due_date))
                submitted = st.form_submit_button("Update Fee Record")
            if submitted:
                errors = validate_fee(total, paid, due)
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    try:
                        pay_date = (r.payment_date or date.today().isoformat()) if paid > 0 else None
                        execute("UPDATE fees SET total_fee=?, amount_paid=?, payment_date=?, due_date=? WHERE id=?",
                                (total, paid, pay_date, due.isoformat(), int(r.id)))
                        flash("Fee record updated successfully.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Could not update fee record: {ex}")

    # ---- Delete ----
    with tab_delete:
        if fees.empty:
            st.info("No fee records to delete.")
        else:
            choices = {fee_label(r): int(r.id) for r in fees.itertuples()}
            label = st.selectbox("Select fee record to delete", list(choices), key="fee_del_pick")
            confirm = st.checkbox("I confirm that I want to delete this fee record")
            if st.button("🗑️ Delete Fee Record"):
                if not confirm:
                    st.error("Please tick the confirmation box first.")
                else:
                    try:
                        execute("DELETE FROM fees WHERE id = ?", (choices[label],))
                        flash("Fee record deleted successfully.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Could not delete fee record: {ex}")
