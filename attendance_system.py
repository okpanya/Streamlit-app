import os
import hashlib
import sqlite3
from pathlib import Path
from datetime import date, datetime, time, timedelta
from calendar import monthrange

import pandas as pd
import streamlit as st

# ------------------------------------------------------------
# SCHOOL SETTINGS
# ------------------------------------------------------------
DB_NAME = os.environ.get(
    "ATTENDANCE_DB",
    str(Path(__file__).resolve().parent / "student_attendance.db")
)

SCHOOL_START = time(8, 0)
SCHOOL_END = time(15, 0)

# Change these in Streamlit Cloud -> App -> Settings -> Secrets.
# Defaults are retained from the original desktop application.
ADMIN_USERNAME = st.secrets.get("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "admin123")


# ------------------------------------------------------------
# DATABASE
# ------------------------------------------------------------
def connect_db():
    conn = sqlite3.connect(DB_NAME, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def setup_database():
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS students (
                student_id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                class_name TEXT NOT NULL
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS attendance (
                record_id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                check_in TEXT NOT NULL,
                check_out TEXT,
                FOREIGN KEY(student_id)
                    REFERENCES students(student_id)
                    ON DELETE CASCADE
            )
        """)


def parse_dt(value):
    return datetime.fromisoformat(value)


def format_duration(minutes):
    minutes = max(0, int(round(minutes)))
    hours, mins = divmod(minutes, 60)
    return f"{hours}h {mins}m"


def get_students():
    with connect_db() as conn:
        return conn.execute("""
            SELECT student_id, full_name, class_name
            FROM students
            ORDER BY full_name
        """).fetchall()


def get_student_status(student_id):
    with connect_db() as conn:
        row = conn.execute("""
            SELECT 1 FROM attendance
            WHERE student_id = ? AND check_out IS NULL
            LIMIT 1
        """, (student_id,)).fetchone()
    return "INSIDE" if row else "OUTSIDE"


# ------------------------------------------------------------
# ATTENDANCE AND REPORT CALCULATIONS (retained from original)
# ------------------------------------------------------------
def school_minutes_for_day(student_id, day):
    if day.weekday() >= 5:
        return 0, 0

    opening = datetime.combine(day, SCHOOL_START)
    closing = datetime.combine(day, SCHOOL_END)
    scheduled = int((closing - opening).total_seconds() / 60)
    present = 0

    with connect_db() as conn:
        records = conn.execute("""
            SELECT check_in, check_out
            FROM attendance
            WHERE student_id = ? AND date(check_in) = ?
        """, (student_id, day.isoformat())).fetchall()

    for check_in, check_out in records:
        start = max(parse_dt(check_in), opening)
        end = (
            min(parse_dt(check_out), closing)
            if check_out
            else min(datetime.now(), closing)
        )
        if end > start:
            present += int((end - start).total_seconds() / 60)

    present = min(scheduled, present)
    absent = max(0, scheduled - present)
    return present, absent


def report_for_period(student_id, start_day, end_day):
    total_present = 0
    total_absent = 0
    current = start_day
    while current <= end_day:
        present, absent = school_minutes_for_day(student_id, current)
        total_present += present
        total_absent += absent
        current += timedelta(days=1)
    return total_present, total_absent


def get_report(student_id, period):
    today = date.today()
    if period == "week":
        start_day = today - timedelta(days=today.weekday())
        end_day = start_day + timedelta(days=6)
        title = "Weekly Attendance Report"
    else:
        start_day = today.replace(day=1)
        end_day = today.replace(day=monthrange(today.year, today.month)[1])
        title = "Monthly Attendance Report"

    with connect_db() as conn:
        student = conn.execute("""
            SELECT full_name, class_name
            FROM students WHERE student_id = ?
        """, (student_id,)).fetchone()

    if not student:
        return None

    present, absent = report_for_period(student_id, start_day, end_day)
    scheduled_days = sum(
        1 for offset in range((end_day - start_day).days + 1)
        if (start_day + timedelta(days=offset)).weekday() < 5
    )
    daily_minutes = int(
        (datetime.combine(today, SCHOOL_END)
         - datetime.combine(today, SCHOOL_START)).total_seconds() / 60
    )
    return {
        "title": title,
        "student": student,
        "start": start_day,
        "end": end_day,
        "scheduled": scheduled_days * daily_minutes,
        "present": present,
        "absent": absent,
    }


# ------------------------------------------------------------
# STREAMLIT PAGE AND SESSION
# ------------------------------------------------------------
st.set_page_config(
    page_title="Student Attendance Management System",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    .block-container {padding-top: 1.7rem; padding-bottom: 2rem;}
    .main-title {font-size: 1.8rem; font-weight: 750; color: #17365d;}
    div[data-testid="stMetric"] {
        background: #f4f7fb; padding: 14px 16px;
        border-radius: 12px; border: 1px solid #e5ebf3;
    }
</style>
""", unsafe_allow_html=True)

setup_database()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False


def login_page():
    st.markdown("<div class='main-title'>📚 STUDENT ATTENDANCE</div>",
                unsafe_allow_html=True)
    st.caption("Administrator Login")
    left, center, right = st.columns([1, 1.2, 1])
    with center:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("LOGIN", type="primary",
                                              use_container_width=True)
        if submitted:
            if (username.strip() == ADMIN_USERNAME
                    and password == ADMIN_PASSWORD):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Incorrect username or password.")


def student_table():
    students = get_students()
    rows = [
        {
            "Student ID": sid,
            "Full Name": name,
            "Class / Department": class_name,
            "Current Status": get_student_status(sid),
        }
        for sid, name, class_name in students
    ]
    return pd.DataFrame(rows, columns=[
        "Student ID", "Full Name", "Class / Department", "Current Status"
    ])


def registration_page():
    st.subheader("Register a Student")
    with st.form("register_student", clear_on_submit=True):
        c1, c2, c3 = st.columns(3)
        sid = c1.text_input("Student ID")
        name = c2.text_input("Full Name")
        class_name = c3.text_input("Class / Department")
        submitted = st.form_submit_button("Add Student", type="primary")
    if submitted:
        sid, name, class_name = sid.strip(), name.strip(), class_name.strip()
        if not sid or not name or not class_name:
            st.warning("Complete all student fields.")
        else:
            try:
                with connect_db() as conn:
                    conn.execute("""
                        INSERT INTO students (student_id, full_name, class_name)
                        VALUES (?, ?, ?)
                    """, (sid, name, class_name))
                st.success("Student registered successfully.")
                st.rerun()
            except sqlite3.IntegrityError:
                st.error("That student ID already exists.")


def attendance_page():
    st.subheader("Student Entry and Exit")
    with st.form("attendance_form"):
        sid = st.text_input("Enter Student ID").strip()
        col1, col2 = st.columns(2)
        checkin = col1.form_submit_button("CHECK IN", type="primary",
                                          use_container_width=True)
        checkout = col2.form_submit_button("CHECK OUT",
                                           use_container_width=True)

    if checkin or checkout:
        if not sid:
            st.warning("Enter a student ID.")
            return
        with connect_db() as conn:
            student = conn.execute(
                "SELECT full_name FROM students WHERE student_id = ?", (sid,)
            ).fetchone()
            if not student:
                st.error("Student ID does not exist.")
                return

            if checkin:
                open_session = conn.execute("""
                    SELECT record_id FROM attendance
                    WHERE student_id = ? AND check_out IS NULL
                    LIMIT 1
                """, (sid,)).fetchone()
                if open_session:
                    st.warning("This student has already checked in.")
                    return
                conn.execute("""
                    INSERT INTO attendance (student_id, check_in)
                    VALUES (?, ?)
                """, (sid, datetime.now().isoformat(timespec="seconds")))
                st.success(f"{student[0]} checked in successfully.")

            if checkout:
                row = conn.execute("""
                    SELECT record_id, check_in FROM attendance
                    WHERE student_id = ? AND check_out IS NULL
                    ORDER BY check_in DESC LIMIT 1
                """, (sid,)).fetchone()
                if not row:
                    st.warning("This student has no open check-in record.")
                    return
                now = datetime.now()
                conn.execute(
                    "UPDATE attendance SET check_out = ? WHERE record_id = ?",
                    (now.isoformat(timespec="seconds"), row[0])
                )
                duration = now - parse_dt(row[1])
                st.success(
                    f"{student[0]} checked out. Time spent: "
                    f"{format_duration(duration.total_seconds() / 60)}"
                )

    st.divider()
    st.subheader("Current Student Status")
    st.dataframe(student_table(), use_container_width=True, hide_index=True)


def details_page():
    st.subheader("Student Details and Attendance History")
    students = get_students()
    if not students:
        st.info("No students have been registered yet.")
        return

    choices = {f"{name} ({sid})": sid for sid, name, _ in students}
    selected = st.selectbox("Select student", list(choices))
    sid = choices[selected]

    with connect_db() as conn:
        student = conn.execute("""
            SELECT full_name, class_name FROM students WHERE student_id = ?
        """, (sid,)).fetchone()
        records = conn.execute("""
            SELECT check_in, check_out FROM attendance
            WHERE student_id = ? ORDER BY check_in DESC
        """, (sid,)).fetchall()

    st.write(f"**Student:** {student[0]}  |  **ID:** {sid}  |  "
             f"**Class:** {student[1]}")

    history = []
    for check_in, check_out in records:
        start = parse_dt(check_in)
        end = parse_dt(check_out) if check_out else datetime.now()
        duration = max(0, (end - start).total_seconds() / 60)
        history.append({
            "Check-In": start.strftime("%d %b %Y, %I:%M %p"),
            "Check-Out": (
                parse_dt(check_out).strftime("%d %b %Y, %I:%M %p")
                if check_out else "Still inside"
            ),
            "Time Spent": format_duration(duration),
        })

    if history:
        st.dataframe(pd.DataFrame(history), use_container_width=True,
                     hide_index=True)
        st.download_button(
            "Download Attendance History (CSV)",
            pd.DataFrame(history).to_csv(index=False).encode("utf-8"),
            file_name=f"{sid}_attendance_history.csv",
            mime="text/csv",
        )
    else:
        st.info("No attendance records found for this student.")


def reports_page():
    st.subheader("Weekly and Monthly Attendance Reports")
    students = get_students()
    if not students:
        st.info("Register a student before generating a report.")
        return

    choices = {f"{name} ({sid})": sid for sid, name, _ in students}
    selected = st.selectbox("Select student for report", list(choices),
                            key="report_student")
    sid = choices[selected]
    period = st.radio("Report period", ["week", "month"],
                      format_func=lambda x: "Weekly" if x == "week" else "Monthly",
                      horizontal=True)
    report = get_report(sid, period)
    if report:
        st.markdown(f"### {report['title']}")
        st.write(f"**Student:** {report['student'][0]}  |  "
                 f"**Student ID:** {sid}  |  **Class:** {report['student'][1]}")
        st.write(f"**Period:** {report['start']:%d %b %Y} – "
                 f"{report['end']:%d %b %Y}")
        c1, c2, c3 = st.columns(3)
        c1.metric("Scheduled School Time", format_duration(report["scheduled"]))
        c2.metric("Total Time Present", format_duration(report["present"]))
        c3.metric("Total Absent Time", format_duration(report["absent"]))


def delete_page():
    st.subheader("Delete Student and Attendance Records")
    students = get_students()
    if not students:
        st.info("There are no students to delete.")
        return
    choices = {f"{name} ({sid})": sid for sid, name, _ in students}
    selected = st.selectbox("Select student", list(choices), key="delete_student")
    sid = choices[selected]
    st.warning("Deleting a student also deletes ALL their attendance records. "
               "This cannot be undone.")
    confirm = st.checkbox("I understand and want to delete this student.")
    if st.button("Delete Student and Records", type="primary",
                 disabled=not confirm):
        with connect_db() as conn:
            conn.execute("DELETE FROM students WHERE student_id = ?", (sid,))
        st.success(f"Student {sid} and associated records deleted.")
        st.rerun()


def dashboard_page():
    st.markdown("<div class='main-title'>STUDENT ATTENDANCE MANAGEMENT</div>",
                unsafe_allow_html=True)
    students = get_students()
    inside = sum(1 for sid, _, _ in students
                 if get_student_status(sid) == "INSIDE")
    c1, c2, c3 = st.columns(3)
    c1.metric("Registered Students", len(students))
    c2.metric("Currently Inside", inside)
    c3.metric("Currently Outside", len(students) - inside)

    st.subheader("Registered Students")
    st.dataframe(student_table(), use_container_width=True, hide_index=True)
    if st.button("Refresh from Database"):
        st.rerun()


if not st.session_state.authenticated:
    login_page()
else:
    with st.sidebar:
        st.title("📚 Attendance System")
        st.caption("Administrator panel")
        page = st.radio("Navigation", [
            "Dashboard",
            "Register Student",
            "Mark Attendance",
            "Student Details",
            "Attendance Reports",
            "Delete Student",
        ])
        st.divider()
        st.caption(f"School hours: {SCHOOL_START:%I:%M %p} – {SCHOOL_END:%I:%M %p}")
        if st.button("Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.rerun()

    if page == "Dashboard":
        dashboard_page()
    elif page == "Register Student":
        registration_page()
    elif page == "Mark Attendance":
        attendance_page()
    elif page == "Student Details":
        details_page()
    elif page == "Attendance Reports":
        reports_page()
    elif page == "Delete Student":
        delete_page()
