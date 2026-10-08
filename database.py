"""database.py - SQLite connection, table creation, shared queries and demo data."""
import os
import sqlite3
from datetime import date
import pandas as pd
from utils import hash_password, YEARS

DB_NAME = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hostel_management.db")

# Recalculates occupied beds of every room from the Active students living in it.
SYNC_SQL = """UPDATE rooms SET occupied_beds =
              (SELECT COUNT(*) FROM students
               WHERE students.room_id = rooms.id AND students.status = 'Active')"""


def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def run_query(sql, params=()):
    """SELECT query -> pandas DataFrame (parameterized)."""
    conn = get_connection()
    try:
        return pd.read_sql_query(sql, conn, params=params)
    finally:
        conn.close()


def execute(sql, params=()):
    """INSERT/UPDATE/DELETE (parameterized). Room occupancy is re-synced after every write."""
    conn = get_connection()
    try:
        cur = conn.execute(sql, params)
        conn.execute(SYNC_SQL)
        conn.commit()
        return cur.lastrowid
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db():
    """Create tables and the default admin account if they do not exist."""
    conn = get_connection()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS admins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL);

        CREATE TABLE IF NOT EXISTS rooms (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            room_number TEXT NOT NULL UNIQUE,
            block TEXT NOT NULL,
            floor INTEGER NOT NULL,
            room_type TEXT NOT NULL,
            capacity INTEGER NOT NULL CHECK (capacity > 0),
            occupied_beds INTEGER NOT NULL DEFAULT 0,
            fee REAL NOT NULL DEFAULT 0 CHECK (fee >= 0),
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);

        CREATE TABLE IF NOT EXISTS students (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL UNIQUE,
            enrollment_no TEXT NOT NULL UNIQUE,
            full_name TEXT NOT NULL,
            gender TEXT NOT NULL,
            branch TEXT NOT NULL,
            year TEXT NOT NULL,
            mobile TEXT NOT NULL,
            email TEXT NOT NULL,
            guardian_name TEXT NOT NULL,
            guardian_contact TEXT NOT NULL,
            room_id INTEGER REFERENCES rooms(id),
            admission_date TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Active',
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);

        CREATE TABLE IF NOT EXISTS fees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL REFERENCES students(id) ON DELETE CASCADE,
            total_fee REAL NOT NULL CHECK (total_fee >= 0),
            amount_paid REAL NOT NULL DEFAULT 0 CHECK (amount_paid >= 0 AND amount_paid <= total_fee),
            payment_date TEXT,
            due_date TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP);
    """)
    if conn.execute("SELECT COUNT(*) FROM admins WHERE username = ?", ("admin",)).fetchone()[0] == 0:
        conn.execute("INSERT INTO admins (username, password_hash) VALUES (?, ?)",
                     ("admin", hash_password("admin123")))
    conn.commit()
    conn.close()


# ---------- shared read queries (status / available beds / remaining are calculated here) ----------
def get_rooms():
    return run_query("""
        SELECT id, room_number, block, floor, room_type, capacity, occupied_beds,
               (capacity - occupied_beds) AS available_beds,
               CASE WHEN capacity - occupied_beds > 0 THEN 'Available' ELSE 'Full' END AS status,
               fee
        FROM rooms ORDER BY room_number""")


def get_students():
    return run_query("""
        SELECT s.id, s.student_id, s.enrollment_no, s.full_name, s.gender, s.branch, s.year,
               s.mobile, s.email, s.guardian_name, s.guardian_contact, s.room_id,
               r.room_number, r.fee AS room_fee, s.admission_date, s.status
        FROM students s LEFT JOIN rooms r ON s.room_id = r.id
        ORDER BY s.id DESC""")


def get_fees():
    return run_query("""
        SELECT f.id, f.student_id AS student_pk, s.student_id, s.enrollment_no, s.full_name,
               r.room_number, f.total_fee, f.amount_paid,
               (f.total_fee - f.amount_paid) AS remaining,
               CASE WHEN f.amount_paid <= 0 THEN 'Pending'
                    WHEN f.amount_paid < f.total_fee THEN 'Partial'
                    ELSE 'Paid' END AS payment_status,
               f.payment_date, f.due_date
        FROM fees f
        JOIN students s ON f.student_id = s.id
        LEFT JOIN rooms r ON s.room_id = r.id
        ORDER BY f.id DESC""")


# ---------- demo data ----------
def seed_sample_data():
    """Insert demo rooms, students and fee records. Only works on an empty database."""
    conn = get_connection()
    try:
        if conn.execute("SELECT COUNT(*) FROM students").fetchone()[0] or \
           conn.execute("SELECT COUNT(*) FROM rooms").fetchone()[0]:
            return False
        rooms = [("A-101", "A", 1, "Double", 2, 60000), ("A-102", "A", 1, "Double", 2, 60000),
                 ("A-103", "A", 1, "Single", 1, 80000), ("A-201", "A", 2, "Triple", 3, 50000),
                 ("A-202", "A", 2, "Triple", 3, 50000), ("B-101", "B", 1, "Four-Seater", 4, 40000),
                 ("B-102", "B", 1, "Four-Seater", 4, 40000), ("B-201", "B", 2, "Double", 2, 60000),
                 ("B-202", "B", 2, "Single", 1, 80000), ("B-203", "B", 2, "Triple", 3, 50000)]
        slots, room_fee = [], {}          # one slot per bed, so students fill rooms one after another
        for number, block, floor, rtype, cap, fee in rooms:
            rid = conn.execute("INSERT INTO rooms (room_number, block, floor, room_type, capacity, fee) "
                               "VALUES (?,?,?,?,?,?)", (number, block, floor, rtype, cap, fee)).lastrowid
            slots += [rid] * cap
            room_fee[rid] = fee
        people = [("Aarav Patel", "Male", "AIML"), ("Diya Shah", "Female", "Computer Engineering"),
                  ("Rohan Mehta", "Male", "IT"), ("Isha Joshi", "Female", "Civil"),
                  ("Karan Desai", "Male", "Mechanical"), ("Neha Trivedi", "Female", "Electrical"),
                  ("Vivek Solanki", "Male", "AIML"), ("Pooja Parmar", "Female", "IT"),
                  ("Harsh Vyas", "Male", "Computer Engineering"), ("Anjali Rathod", "Female", "AIML"),
                  ("Mehul Chauhan", "Male", "Mechanical"), ("Krishna Bhatt", "Male", "Civil"),
                  ("Riya Dave", "Female", "Electrical"), ("Jay Gohil", "Male", "IT"),
                  ("Sneha Jadeja", "Female", "Computer Engineering"), ("Dhruv Kansara", "Male", "AIML"),
                  ("Kavya Thakkar", "Female", "IT"), ("Yash Makwana", "Male", "Mechanical")]
        guardians = ["Suresh", "Ramesh", "Mahesh", "Dinesh", "Kiran"]
        for i, (name, gender, branch) in enumerate(people):
            year_no = i % 4 + 1
            surname = name.split()[1]
            room_id = slots[i]
            cur = conn.execute(
                "INSERT INTO students (student_id, enrollment_no, full_name, gender, branch, year, mobile, "
                "email, guardian_name, guardian_contact, room_id, admission_date, status) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?, 'Active')",
                (f"S{i+1:03d}", f"EN2024{i+1:03d}", name, gender, branch, YEARS[year_no - 1],
                 f"98765{10000 + i}", f"{name.split()[0].lower()}.{surname.lower()}@example.com",
                 f"Mr. {guardians[i % 5]} {surname}", f"97250{20000 + i}", room_id,
                 date(2027 - year_no, 7, 15).isoformat()))
            total = room_fee[room_id]
            paid = [total, total / 2, 0][i % 3]
            conn.execute("INSERT INTO fees (student_id, total_fee, amount_paid, payment_date, due_date) "
                         "VALUES (?,?,?,?,?)",
                         (cur.lastrowid, total, paid,
                          date(2026, 8, 1 + i).isoformat() if paid > 0 else None, "2026-12-31"))
        conn.execute(SYNC_SQL)
        conn.commit()
        return True
    finally:
        conn.close()
