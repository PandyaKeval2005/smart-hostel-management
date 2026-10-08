"""student_management.py - CRUD, search and filters for students (linked to rooms)."""
import sqlite3
from datetime import date
import streamlit as st
from database import get_students, get_rooms, run_query, execute
from utils import (BRANCHES, YEARS, GENDERS, STATUSES, is_valid_email, is_valid_mobile, search_df,
                   filter_isin, pretty, to_csv, flash, show_flash, next_form_key, reset_form)

EMPTY = {"student_id": "", "enrollment_no": "", "full_name": "", "gender": GENDERS[0], "branch": BRANCHES[0],
         "year": YEARS[0], "mobile": "", "email": "", "guardian_name": "", "guardian_contact": "",
         "room_id": None, "admission_date": date.today(), "status": "Active"}


def room_options(current_room_id=None):
    """Dictionary {label: room_id} of rooms that still have a free bed (plus the student's current room)."""
    rooms = get_rooms()
    rooms = rooms[(rooms["available_beds"] > 0) | (rooms["id"] == current_room_id)]
    options = {"No room (unassigned)": None}
    for r in rooms.itertuples():
        tag = "current room" if r.id == current_room_id else f"{r.available_beds} bed(s) free"
        options[f"{r.room_number} - Block {r.block}, {tag}"] = int(r.id)
    return options


def validate_student(d, edit_pk=None):
    """Return a list of error messages (empty list = valid)."""
    errors = []
    required = {"Student ID": d["student_id"], "Enrollment Number": d["enrollment_no"], "Full Name": d["full_name"],
                "Mobile": d["mobile"], "Email": d["email"], "Guardian Name": d["guardian_name"],
                "Guardian Contact": d["guardian_contact"]}
    for label, value in required.items():
        if not value.strip():
            errors.append(f"{label} is required.")
    if errors:
        return errors
    pk = edit_pk or -1
    if not run_query("SELECT id FROM students WHERE student_id = ? AND id != ?", (d["student_id"], pk)).empty:
        errors.append("Student ID already exists.")
    if not run_query("SELECT id FROM students WHERE enrollment_no = ? AND id != ?", (d["enrollment_no"], pk)).empty:
        errors.append("Enrollment Number already exists.")
    if not is_valid_mobile(d["mobile"]):
        errors.append("Mobile must be a valid 10-digit number.")
    if not is_valid_mobile(d["guardian_contact"]):
        errors.append("Guardian contact must be a valid 10-digit number.")
    if not is_valid_email(d["email"]):
        errors.append("Email format is invalid.")
    if d["year"] not in YEARS:
        errors.append("Year is invalid.")
    if d["status"] == "Active" and d["room_id"] is not None:
        room = run_query("SELECT capacity FROM rooms WHERE id = ?", (d["room_id"],))
        if room.empty:
            errors.append("Selected room does not exist.")
        else:
            used = run_query("SELECT COUNT(*) AS c FROM students WHERE room_id = ? AND status = 'Active' AND id != ?",
                             (d["room_id"], pk))["c"][0]
            if used >= room["capacity"][0]:
                errors.append("Student cannot be assigned because no bed is available. Room is already full.")
    return errors


def student_form(key, d, room_opts, button):
    """Draws the student form and returns (submitted, data)."""
    with st.form(key):
        c1, c2 = st.columns(2)
        sid = c1.text_input("Student ID *", d["student_id"], key=key + "a")
        enr = c2.text_input("Enrollment Number *", d["enrollment_no"], key=key + "b")
        name = c1.text_input("Full Name *", d["full_name"], key=key + "c")
        gender = c2.selectbox("Gender", GENDERS, GENDERS.index(d["gender"]), key=key + "d")
        branch = c1.selectbox("Branch", BRANCHES, BRANCHES.index(d["branch"]) if d["branch"] in BRANCHES else 0, key=key + "e")
        year = c2.selectbox("Year", YEARS, YEARS.index(d["year"]), key=key + "f")
        mobile = c1.text_input("Mobile Number *", d["mobile"], key=key + "g")
        email = c2.text_input("Email *", d["email"], key=key + "h")
        gname = c1.text_input("Parent/Guardian Name *", d["guardian_name"], key=key + "i")
        gcontact = c2.text_input("Parent/Guardian Contact *", d["guardian_contact"], key=key + "j")
        labels = list(room_opts)
        idx = next((i for i, l in enumerate(labels) if room_opts[l] == d["room_id"]), 0)
        room_label = c1.selectbox("Room", labels, idx, key=key + "k")
        adm = c2.date_input("Admission Date", d["admission_date"], key=key + "l")
        status = c1.selectbox("Status", STATUSES, STATUSES.index(d["status"]), key=key + "m")
        submitted = st.form_submit_button(button)
    data = {"student_id": sid.strip(), "enrollment_no": enr.strip(), "full_name": name.strip(), "gender": gender,
            "branch": branch, "year": year, "mobile": mobile.strip(), "email": email.strip(),
            "guardian_name": gname.strip(), "guardian_contact": gcontact.strip(),
            "room_id": room_opts[room_label], "admission_date": adm, "status": status}
    return submitted, data


def show_student_management():
    st.title("👨‍🎓 Student Management")
    show_flash()
    tab_view, tab_add, tab_update, tab_delete = st.tabs(["📋 View / Search", "➕ Add Student", "✏️ Update Student", "🗑️ Delete Student"])
    students = get_students()

    # ---- View, search, filter, export ----
    with tab_view:
        search = st.text_input("🔍 Search by Student ID, Enrollment No, Name or Mobile")
        f = st.columns(5)
        branches = f[0].multiselect("Branch", BRANCHES)
        years = f[1].multiselect("Year", YEARS)
        genders = f[2].multiselect("Gender", GENDERS)
        rooms_f = f[3].multiselect("Room", sorted(students["room_number"].dropna().unique()))
        statuses = f[4].multiselect("Status", STATUSES)
        df = search_df(students, search, ["student_id", "enrollment_no", "full_name", "mobile"])
        for col, sel in [("branch", branches), ("year", years), ("gender", genders), ("room_number", rooms_f), ("status", statuses)]:
            df = filter_isin(df, col, sel)
        st.caption(f"Showing {len(df)} of {len(students)} students")
        st.dataframe(pretty(df, drop=["id", "room_id", "room_fee"]), hide_index=True)
        st.download_button("⬇️ Download Student Report", to_csv(pretty(df, drop=["id", "room_id", "room_fee"])),
                           "student_report.csv", "text/csv")

    # ---- Add ----
    with tab_add:
        key = next_form_key("add_student")
        submitted, data = student_form(key, EMPTY, room_options(), "Add Student")
        if submitted:
            errors = validate_student(data)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    if data["status"] == "Inactive":
                        data["room_id"] = None     # inactive students do not hold a bed
                    execute("INSERT INTO students (student_id, enrollment_no, full_name, gender, branch, year, mobile, "
                            "email, guardian_name, guardian_contact, room_id, admission_date, status) "
                            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                            (data["student_id"], data["enrollment_no"], data["full_name"], data["gender"], data["branch"],
                             data["year"], data["mobile"], data["email"], data["guardian_name"], data["guardian_contact"],
                             data["room_id"], data["admission_date"].isoformat(), data["status"]))
                    reset_form("add_student")
                    flash("Student added successfully.")
                    st.rerun()
                except sqlite3.IntegrityError:
                    st.error("Student ID or Enrollment Number already exists.")
                except Exception as ex:
                    st.error(f"Could not add student: {ex}")

    # ---- Update ----
    with tab_update:
        if students.empty:
            st.info("No students to update.")
        else:
            choices = {f"{r.student_id} - {r.full_name}": r for r in students.itertuples()}
            r = choices[st.selectbox("Select student", list(choices), key="upd_pick")]
            current = {"student_id": r.student_id, "enrollment_no": r.enrollment_no, "full_name": r.full_name,
                       "gender": r.gender, "branch": r.branch, "year": r.year, "mobile": r.mobile, "email": r.email,
                       "guardian_name": r.guardian_name, "guardian_contact": r.guardian_contact,
                       "room_id": None if r.room_id != r.room_id else int(r.room_id),   # NaN -> None
                       "admission_date": date.fromisoformat(r.admission_date), "status": r.status}
            st.caption("Changing the room automatically frees the old bed and occupies the new one.")
            submitted, data = student_form(f"upd_student_{r.id}", current, room_options(current["room_id"]), "Update Student")
            if submitted:
                errors = validate_student(data, edit_pk=int(r.id))
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    try:
                        if data["status"] == "Inactive":
                            data["room_id"] = None
                        execute("UPDATE students SET student_id=?, enrollment_no=?, full_name=?, gender=?, branch=?, year=?, "
                                "mobile=?, email=?, guardian_name=?, guardian_contact=?, room_id=?, admission_date=?, status=? "
                                "WHERE id=?",
                                (data["student_id"], data["enrollment_no"], data["full_name"], data["gender"], data["branch"],
                                 data["year"], data["mobile"], data["email"], data["guardian_name"], data["guardian_contact"],
                                 data["room_id"], data["admission_date"].isoformat(), data["status"], int(r.id)))
                        flash("Student updated successfully.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Could not update student: {ex}")

    # ---- Delete ----
    with tab_delete:
        if students.empty:
            st.info("No students to delete.")
        else:
            choices = {f"{r.student_id} - {r.full_name}": int(r.id) for r in students.itertuples()}
            label = st.selectbox("Select student to delete", list(choices), key="del_pick")
            st.warning("Deleting a student also deletes their fee records and frees their bed.")
            confirm = st.checkbox("I confirm that I want to delete this student")
            if st.button("🗑️ Delete Student"):
                if not confirm:
                    st.error("Please tick the confirmation box first.")
                else:
                    try:
                        execute("DELETE FROM students WHERE id = ?", (choices[label],))
                        flash("Student deleted successfully.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Could not delete student: {ex}")
