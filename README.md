# 🏨 Smart Hostel Management System Using Python and Streamlit

## Project Description
A small, focused hostel management web app for managing **students, rooms and fees**. Built as a Python Programming mini-project with a modular structure, SQLite storage and an interactive Streamlit dashboard.

## Features
- Admin login with hashed password (SHA-256) and session-state protection
- Dashboard: 8 KPI cards, 4 interactive Plotly charts, recent students and payments
- Student Management: add, view, update, delete, search, filter, CSV export
- Room Management: add, view, update, delete, search, filter, available/full views, CSV export
- Fee Management: add record, record payment, update, delete, search, filter (status, room, student, due-date range), CSV export
- Automatic room occupancy, available beds, room status, remaining fee and payment status
- Validation (unique IDs, mobile, email, capacity, fee limits) with friendly error messages
- One-click demo data (18 students, 10 rooms, fee records)

## Technologies Used
Python 3, Streamlit, SQLite (`sqlite3`), Pandas, Plotly, `hashlib`, `datetime`

## Project Structure
```
smart_hostel_management/
├── app.py                 # entry point, navigation
├── database.py            # connection, tables, shared queries, demo data
├── auth.py                # login / logout
├── student_management.py  # student CRUD + search/filter
├── room_management.py     # room CRUD + search/filter
├── fee_management.py      # fee CRUD + payments + search/filter
├── dashboard.py           # KPIs, charts, recent records
├── utils.py               # constants, validators, hashing, CSV helper
├── requirements.txt
├── README.md
└── hostel_management.db   # created automatically on first run
```

## Installation
```
pip install -r requirements.txt
```

## How to Run
```
streamlit run app.py
```

## Default Admin Credentials
- Username: `admin`
- Password: `admin123`

## Database Information
SQLite file `hostel_management.db` with tables `admins`, `rooms`, `students`, `fees`.
Foreign keys are enabled (`PRAGMA foreign_keys = ON`) and all queries are parameterized.
`rooms.occupied_beds` is recalculated from Active students after every write.
To reset the project, delete `hostel_management.db` and restart the app.

## Screenshots
_Add screenshots here (Login, Dashboard, Students, Rooms, Fees)._

## Future Scope
- Salted password hashing (bcrypt) and multiple admin roles
- PDF receipts for fee payments
- Room-change history
- Deployment on Streamlit Community Cloud
