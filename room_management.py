"""room_management.py - CRUD, search and filters for rooms. Available beds and status are calculated."""
import streamlit as st
from database import get_rooms, run_query, execute
from utils import ROOM_TYPES, search_df, filter_isin, pretty, to_csv, flash, show_flash, next_form_key, reset_form

EMPTY = {"room_number": "", "block": "A", "floor": 1, "room_type": ROOM_TYPES[0], "capacity": 1, "fee": 0.0}


def validate_room(d, edit_pk=None, occupied=0):
    errors = []
    if not d["room_number"]:
        errors.append("Room number is required.")
    if not d["block"]:
        errors.append("Block is required.")
    if d["capacity"] <= 0:
        errors.append("Capacity must be greater than 0.")
    if d["capacity"] < occupied:
        errors.append(f"Capacity cannot be less than the currently occupied beds ({occupied}).")
    if d["fee"] < 0:
        errors.append("Fee cannot be negative.")
    if d["room_number"] and not run_query("SELECT id FROM rooms WHERE room_number = ? AND id != ?",
                                          (d["room_number"], edit_pk or -1)).empty:
        errors.append("Room number already exists.")
    return errors


def room_form(key, d, button):
    with st.form(key):
        c1, c2 = st.columns(2)
        number = c1.text_input("Room Number *", d["room_number"], key=key + "a")
        block = c2.text_input("Block *", d["block"], key=key + "b")
        floor = c1.number_input("Floor", 0, 50, int(d["floor"]), 1, key=key + "c")
        rtype = c2.selectbox("Room Type", ROOM_TYPES, ROOM_TYPES.index(d["room_type"]), key=key + "d")
        cap = c1.number_input("Capacity (beds)", 1, 20, int(d["capacity"]), 1, key=key + "e")
        fee = c2.number_input("Yearly Fee (₹)", 0.0, 1000000.0, float(d["fee"]), 500.0, key=key + "f")
        st.caption("Occupied beds, available beds and status are calculated automatically.")
        submitted = st.form_submit_button(button)
    return submitted, {"room_number": number.strip(), "block": block.strip(), "floor": int(floor),
                       "room_type": rtype, "capacity": int(cap), "fee": float(fee)}


def show_room_management():
    st.title("🛏️ Room Management")
    show_flash()
    tab_view, tab_add, tab_update, tab_delete = st.tabs(["📋 View / Search", "➕ Add Room", "✏️ Update Room", "🗑️ Delete Room"])
    rooms = get_rooms()

    with tab_view:
        search = st.text_input("🔍 Search by Room Number or Block")
        show = st.radio("Show", ["All Rooms", "Available Rooms", "Full Rooms"], horizontal=True)
        f = st.columns(3)
        types = f[0].multiselect("Room Type", ROOM_TYPES)
        floors = f[1].multiselect("Floor", sorted(rooms["floor"].unique()))
        blocks = f[2].multiselect("Block", sorted(rooms["block"].unique()))
        df = search_df(rooms, search, ["room_number", "block"])
        df = filter_isin(filter_isin(filter_isin(df, "room_type", types), "floor", floors), "block", blocks)
        if show == "Available Rooms":
            df = df[df["status"] == "Available"]
        elif show == "Full Rooms":
            df = df[df["status"] == "Full"]
        st.caption(f"Showing {len(df)} of {len(rooms)} rooms")
        st.dataframe(pretty(df, drop=["id"]), hide_index=True)
        st.download_button("⬇️ Download Room Report", to_csv(pretty(df, drop=["id"])), "room_report.csv", "text/csv")

    with tab_add:
        key = next_form_key("add_room")
        submitted, data = room_form(key, EMPTY, "Add Room")
        if submitted:
            errors = validate_room(data)
            if errors:
                for e in errors:
                    st.error(e)
            else:
                try:
                    execute("INSERT INTO rooms (room_number, block, floor, room_type, capacity, fee) VALUES (?,?,?,?,?,?)",
                            (data["room_number"], data["block"], data["floor"], data["room_type"], data["capacity"], data["fee"]))
                    reset_form("add_room")
                    flash("Room added successfully.")
                    st.rerun()
                except Exception as ex:
                    st.error(f"Could not add room: {ex}")

    with tab_update:
        if rooms.empty:
            st.info("No rooms to update.")
        else:
            choices = {f"{r.room_number} (Block {r.block})": r for r in rooms.itertuples()}
            r = choices[st.selectbox("Select room", list(choices), key="upd_room_pick")]
            current = {"room_number": r.room_number, "block": r.block, "floor": r.floor, "room_type": r.room_type,
                       "capacity": r.capacity, "fee": r.fee}
            st.caption(f"Currently occupied beds: {r.occupied_beds}")
            submitted, data = room_form(f"upd_room_{r.id}", current, "Update Room")
            if submitted:
                errors = validate_room(data, int(r.id), int(r.occupied_beds))
                if errors:
                    for e in errors:
                        st.error(e)
                else:
                    try:
                        execute("UPDATE rooms SET room_number=?, block=?, floor=?, room_type=?, capacity=?, fee=? WHERE id=?",
                                (data["room_number"], data["block"], data["floor"], data["room_type"],
                                 data["capacity"], data["fee"], int(r.id)))
                        flash("Room updated successfully.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Could not update room: {ex}")

    with tab_delete:
        if rooms.empty:
            st.info("No rooms to delete.")
        else:
            choices = {f"{r.room_number} (Block {r.block})": int(r.id) for r in rooms.itertuples()}
            label = st.selectbox("Select room to delete", list(choices), key="del_room_pick")
            if st.button("🗑️ Delete Room"):
                assigned = run_query("SELECT COUNT(*) AS c FROM students WHERE room_id = ?", (choices[label],))["c"][0]
                if assigned > 0:
                    st.warning("Cannot delete this room because students are currently assigned to it.")
                else:
                    try:
                        execute("DELETE FROM rooms WHERE id = ?", (choices[label],))
                        flash("Room deleted successfully.")
                        st.rerun()
                    except Exception as ex:
                        st.error(f"Could not delete room: {ex}")
