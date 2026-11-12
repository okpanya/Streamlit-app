
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import hashlib
from datetime import datetime, timedelta, date
import calendar

DB_NAME = "student_attendance.db"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


# ================= DATABASE =================

def connect_db():
    return sqlite3.connect(DB_NAME)


def setup_database():
    with connect_db() as db:
        db.execute("""
            CREATE TABLE IF NOT EXISTS students (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                department TEXT,
                class_name TEXT
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS visits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                student_id TEXT NOT NULL,
                check_in TEXT NOT NULL,
                check_out TEXT,
                FOREIGN KEY(student_id)
                    REFERENCES students(student_id)
                    ON DELETE CASCADE
            )
        """)

        db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                username TEXT PRIMARY KEY,
                password TEXT NOT NULL
            )
        """)

        # Default administrator
        db.execute("""
            INSERT OR IGNORE INTO admins(username, password)
            VALUES (?, ?)
        """, ("admin", hashlib.sha256(
            "admin123".encode()
        ).hexdigest()))


def get_now():
    return datetime.now()


def format_duration(seconds):
    seconds = max(0, int(seconds))
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    return f"{hours} hours, {minutes} minutes"


# ================= LOGIN =================

class LoginWindow:

    def __init__(self, root):
        self.root = root
        self.root.title("Administrator Login")
        self.root.geometry("420x350")
        self.root.resizable(False, False)
        self.root.configure(bg="#edf2f7")

        tk.Label(
            root,
            text="STUDENT ATTENDANCE SYSTEM",
            font=("Arial", 16, "bold"),
            bg="#edf2f7",
            fg="#17365d"
        ).pack(pady=30)

        tk.Label(root, text="Username",
                 bg="#edf2f7").pack()

        self.username = tk.Entry(root, width=32)
        self.username.pack(pady=7)

        tk.Label(root, text="Password",
                 bg="#edf2f7").pack()

        self.password = tk.Entry(
            root, width=32, show="*"
        )
        self.password.pack(pady=7)

        tk.Button(
            root,
            text="LOGIN",
            width=22,
            bg="#17365d",
            fg="white",
            command=self.login
        ).pack(pady=25)

        root.bind("<Return>", lambda event: self.login())

    def login(self):
        username = self.username.get().strip()
        password = hashlib.sha256(
            self.password.get().encode()
        ).hexdigest()

        with connect_db() as db:
            result = db.execute("""
                SELECT username FROM admins
                WHERE username=? AND password=?
            """, (username, password)).fetchone()

        if result:
            self.root.destroy()
            main = tk.Tk()
            AttendanceSystem(main)
            main.mainloop()
        else:
            messagebox.showerror(
                "Login Failed",
                "Incorrect username or password."
            )


# ================= MAIN APPLICATION =================

class AttendanceSystem:

    def __init__(self, root):
        self.root = root
        self.root.title("Student Attendance Management System")
        self.root.geometry("1150x680")
        self.root.minsize(950, 550)

        self.details_window = None
        self.details_tree = None

        self.build_interface()
        self.refresh_students()

    def build_interface(self):

        header = tk.Frame(
            self.root, bg="#17365d", height=85
        )
        header.pack(fill="x")

        tk.Label(
            header,
            text="STUDENT ATTENDANCE MANAGEMENT SYSTEM",
            font=("Arial", 20, "bold"),
            fg="white",
            bg="#17365d"
        ).pack(pady=22)

        toolbar = tk.Frame(self.root, pady=12)
        toolbar.pack(fill="x")

        buttons = [
            ("Add Student", self.add_student),
            ("Delete Student", self.delete_student),
            ("Check In", self.check_in),
            ("Check Out", self.check_out),
            ("Student Details", self.open_details),
            ("Refresh Database", self.refresh_all),
            ("Reports", self.open_reports)
        ]

        for title, action in buttons:
            tk.Button(
                toolbar,
                text=title,
                command=action,
                bg="#17365d",
                fg="white",
                padx=9,
                pady=7
            ).pack(side="left", padx=5)

        self.clock_label = tk.Label(
            self.root,
            font=("Arial", 11, "bold"),
            fg="#17365d"
        )
        self.clock_label.pack(anchor="e", padx=20)

        self.update_clock()

        columns = (
            "ID", "Name", "Department",
            "Class", "Status", "Last Entry"
        )

        self.tree = ttk.Treeview(
            self.root,
            columns=columns,
            show="headings",
            height=18
        )

        for column in columns:
            self.tree.heading(column, text=column)
            self.tree.column(column, width=155)

        self.tree.pack(
            fill="both", expand=True, padx=15, pady=15
        )

        self.tree.bind(
            "<Double-1>",
            lambda event: self.open_details()
        )

        self.status_label = tk.Label(
            self.root,
            text="Database connected",
            bg="#17365d",
            fg="white",
            anchor="w",
            padx=10
        )
        self.status_label.pack(fill="x", side="bottom")

    def update_clock(self):
        self.clock_label.config(
            text=get_now().strftime("%A, %d %B %Y  %H:%M:%S")
        )
        self.root.after(1000, self.update_clock)

    def selected_student(self):
        selected = self.tree.selection()

        if not selected:
            messagebox.showwarning(
                "Selection Required",
                "Please select a student first."
            )
            return None

        return self.tree.item(selected[0])["values"][0]

    # ================= STUDENT MANAGEMENT =================

    def add_student(self):

        window = tk.Toplevel(self.root)
        window.title("Register Student")
        window.geometry("380x340")
        window.transient(self.root)

        fields = [
            "Student ID",
            "Full Name",
            "Department",
            "Class"
        ]

        entries = {}

        for field in fields:
            tk.Label(window, text=field).pack(pady=(10, 2))
            entry = tk.Entry(window, width=35)
            entry.pack()
            entries[field] = entry

        def save_student():
            student_id = entries["Student ID"].get().strip()
            name = entries["Full Name"].get().strip()
            department = entries["Department"].get().strip()
            class_name = entries["Class"].get().strip()

            if not student_id or not name:
                messagebox.showerror(
                    "Error",
                    "Student ID and Name are required."
                )
                return

            try:
                with connect_db() as db:
                    db.execute("""
                        INSERT INTO students
                        (student_id, name, department, class_name)
                        VALUES (?, ?, ?, ?)
                    """, (
                        student_id, name,
                        department, class_name
                    ))

                messagebox.showinfo(
                    "Success", "Student registered successfully."
                )
                window.destroy()
                self.refresh_all()

            except sqlite3.IntegrityError:
                messagebox.showerror(
                    "Error",
                    "This Student ID already exists."
                )

        tk.Button(
            window,
            text="SAVE STUDENT",
            bg="#17365d",
            fg="white",
            command=save_student
        ).pack(pady=20)

    def delete_student(self):
        student_id = self.selected_student()

        if not student_id:
            return

        answer = messagebox.askyesno(
            "Confirm Delete",
            "Delete this student and ALL their attendance records?"
        )

        if answer:
            with connect_db() as db:
                db.execute("PRAGMA foreign_keys = ON")
                db.execute(
                    "DELETE FROM visits WHERE student_id=?",
                    (student_id,)
                )
                db.execute(
                    "DELETE FROM students WHERE student_id=?",
                    (student_id,)
                )

            self.refresh_all()
            messagebox.showinfo(
                "Deleted",
                "Student and attendance records deleted."
            )

    # ================= ATTENDANCE =================

    def check_in(self):
        student_id = self.selected_student()

        if not student_id:
            return

        now = get_now().strftime(TIME_FORMAT)

        with connect_db() as db:

            student = db.execute(
                "SELECT name FROM students WHERE student_id=?",
                (student_id,)
            ).fetchone()

            active = db.execute("""
                SELECT id FROM visits
                WHERE student_id=? AND check_out IS NULL
            """, (student_id,)).fetchone()

            if active:
                messagebox.showwarning(
                    "Already Inside",
                    "This student has already checked in."
                )
                return

            db.execute("""
                INSERT INTO visits(student_id, check_in)
                VALUES (?, ?)
            """, (student_id, now))

        messagebox.showinfo(
            "Check In",
            f"{student[0]} entered school at {now}"
        )

        self.refresh_all()

    def check_out(self):
        student_id = self.selected_student()

        if not student_id:
            return

        now = get_now().strftime(TIME_FORMAT)

        with connect_db() as db:

            active = db.execute("""
                SELECT id, check_in FROM visits
                WHERE student_id=? AND check_out IS NULL
                ORDER BY id DESC LIMIT 1
            """, (student_id,)).fetchone()

            if not active:
                messagebox.showwarning(
                    "Not Inside",
                    "This student has not checked in."
                )
                return

            db.execute("""
                UPDATE visits
                SET check_out=?
                WHERE id=?
            """, (now, active[0]))

            duration = (
                get_now() -
                datetime.strptime(active[1], TIME_FORMAT)
            ).total_seconds()

        messagebox.showinfo(
            "Check Out",
            "Student checked out successfully.\n"
            f"Time spent: {format_duration(duration)}"
        )

        self.refresh_all()

    # ================= REFRESH DATABASE =================

    def refresh_students(self):

        for item in self.tree.get_children():
            self.tree.delete(item)

        with connect_db() as db:

            students = db.execute("""
                SELECT student_id, name, department, class_name
                FROM students ORDER BY name
            """).fetchall()

            for student in students:

                last = db.execute("""
                    SELECT check_in, check_out
                    FROM visits
                    WHERE student_id=?
                    ORDER BY id DESC LIMIT 1
                """, (student[0],)).fetchone()

                if last and last[1] is None:
                    status = "INSIDE"
                elif last:
                    status = "OUTSIDE"
                else:
                    status = "NOT RECORDED"

                last_entry = last[0] if last else "-"

                self.tree.insert(
                    "",
                    "end",
                    values=(
                        student[0], student[1],
                        student[2], student[3],
                        status, last_entry
                    )
                )

        self.status_label.config(
            text=f"Database refreshed | Total students: {len(students)}"
        )

    def refresh_all(self):
        self.refresh_students()

        # Refresh the existing details window without closing it.
        if self.details_window and self.details_window.winfo_exists():
            self.refresh_details()

    # ================= STUDENT DETAILS WINDOW =================

    def open_details(self):

        if self.details_window and self.details_window.winfo_exists():
            self.details_window.lift()
            self.refresh_details()
            return

        self.details_window = tk.Toplevel(self.root)
        self.details_window.title("Student Attendance Details")
        self.details_window.geometry("1050x480")

        tk.Label(
            self.details_window,
            text="STUDENT ATTENDANCE RECORDS",
            font=("Arial", 16, "bold"),
            fg="#17365d"
        ).pack(pady=12)

        columns = (
            "Student ID", "Check In", "Check Out",
            "Time Spent", "Off-Campus Period"
        )

        self.details_tree = ttk.Treeview(
            self.details_window,
            columns=columns,
            show="headings"
        )

        for column in columns:
            self.details_tree.heading(column, text=column)
            self.details_tree.column(column, width=190)

        self.details_tree.pack(
            fill="both", expand=True, padx=10, pady=10
        )

        tk.Button(
            self.details_window,
            text="REFRESH FROM DATABASE",
            command=self.refresh_details,
            bg="#17365d",
            fg="white"
        ).pack(pady=12)

        self.details_window.protocol(
            "WM_DELETE_WINDOW",
            self.close_details
        )

        self.refresh_details()

    def close_details(self):
        if self.details_window:
            self.details_window.destroy()

        self.details_window = None
        self.details_tree = None

    def refresh_details(self):

        if not self.details_tree:
            return

        for item in self.details_tree.get_children():
            self.details_tree.delete(item)

        with connect_db() as db:
            records = db.execute("""
                SELECT student_id, check_in, check_out
                FROM visits
                ORDER BY check_in DESC
            """).fetchall()

        for student_id, check_in, check_out in records:

            start = datetime.strptime(check_in, TIME_FORMAT)
            end = (
                datetime.strptime(check_out, TIME_FORMAT)
                if check_out else get_now()
            )

            spent = format_duration(
                (end - start).total_seconds()
            )

            off_campus = self.calculate_gap(
                student_id, check_in
            )

            self.details_tree.insert(
                "",
                "end",
                values=(
                    student_id,
                    check_in,
                    check_out or "Still Inside",
                    spent,
                    off_campus
                )
            )

    def calculate_gap(self, student_id, check_in):

        with connect_db() as db:
            next_visit = db.execute("""
                SELECT check_in FROM visits
                WHERE student_id=? AND check_in>?
                ORDER BY check_in LIMIT 1
            """, (student_id, check_in)).fetchone()

            current = db.execute("""
                SELECT check_out FROM visits
                WHERE student_id=? AND check_in=?
            """, (student_id, check_in)).fetchone()

        if not current or not current[0]:
            return "Currently Inside"

        start = datetime.strptime(current[0], TIME_FORMAT)

        end = (
            datetime.strptime(next_visit[0], TIME_FORMAT)
            if next_visit else get_now()
        )

        return format_duration(
            (end - start).total_seconds()
        )

    # ================= WEEKLY AND MONTHLY REPORTS =================

    def open_reports(self):

        student_id = self.selected_student()

        if not student_id:
            return

        with connect_db() as db:
            student = db.execute("""
                SELECT name FROM students WHERE student_id=?
            """, (student_id,)).fetchone()

        if not student:
            return

        window = tk.Toplevel(self.root)
        window.title("Weekly and Monthly Reports")
        window.geometry("650x510")

        tk.Label(
            window,
            text=f"ATTENDANCE REPORT: {student[0]}",
            font=("Arial", 15, "bold"),
            fg="#17365d"
        ).pack(pady=15)

        today = date.today()

        def get_period(kind):
            if kind == "Weekly":
                start = today - timedelta(days=today.weekday())
                end = start + timedelta(days=7)
            else:
                start = today.replace(day=1)

                if today.month == 12:
                    next_month = date(today.year + 1, 1, 1)
                else:
                    next_month = date(
                        today.year, today.month + 1, 1
                    )

                end = next_month

            return (
                datetime.combine(start, datetime.min.time()),
                datetime.combine(end, datetime.min.time())
            )

        def report(kind):

            start, end = get_period(kind)
            now = get_now()

            with connect_db() as db:
                visits = db.execute("""
                    SELECT check_in, check_out
                    FROM visits
                    WHERE student_id=?
                    ORDER BY check_in
                """, (student_id,)).fetchall()

            time_spent = 0
            off_campus = 0
            sessions = 0
            current = None

            for check_in, check_out in visits:

                entry = datetime.strptime(
                    check_in, TIME_FORMAT
                )

                exit_time = (
                    datetime.strptime(check_out, TIME_FORMAT)
                    if check_out else now
                )

                # Count only the part inside the report period.
                overlap_start = max(entry, start)
                overlap_end = min(exit_time, end, now)

                if overlap_end > overlap_start:
                    time_spent += (
                        overlap_end - overlap_start
                    ).total_seconds()
                    sessions += 1

                if check_out:
                    current = datetime.strptime(
                        check_out, TIME_FORMAT
                    )
                else:
                    current = None

            # Calculate gaps between consecutive visits.
            for i in range(len(visits) - 1):

                if not visits[i][1]:
                    continue

                exit_time = datetime.strptime(
                    visits[i][1], TIME_FORMAT
                )

                next_entry = datetime.strptime(
                    visits[i + 1][0], TIME_FORMAT
                )

                gap_start = max(exit_time, start)
                gap_end = min(next_entry, end, now)

                if gap_end > gap_start:
                    off_campus += (
                        gap_end - gap_start
                    ).total_seconds()

            # Include an ongoing absence after the latest checkout.
            if visits and visits[-1][1]:
                last_exit = datetime.strptime(
                    visits[-1][1], TIME_FORMAT
                )

                if last_exit < now:
                    gap_start = max(last_exit, start)
                    gap_end = min(now, end)

                    if gap_end > gap_start:
                        off_campus += (
                            gap_end - gap_start
                        ).total_seconds()

            result = (
                f"{kind.upper()} ATTENDANCE REPORT\n\n"
                f"Student: {student[0]}\n"
                f"Student ID: {student_id}\n"
                f"Period: {start.date()} to "
                f"{(end - timedelta(days=1)).date()}\n\n"
                f"Attendance sessions: {sessions}\n"
                f"Total time spent in school:\n"
                f"{format_duration(time_spent)}\n\n"
                f"Total off-campus period:\n"
                f"{format_duration(off_campus)}"
            )

            output.config(state="normal")
            output.delete("1.0", "end")
            output.insert("1.0", result)
            output.config(state="disabled")

        tk.Button(
            window,
            text="WEEKLY REPORT",
            command=lambda: report("Weekly"),
            bg="#17365d",
            fg="white",
            width=20
        ).pack(pady=8)

        tk.Button(
            window,
            text="MONTHLY REPORT",
            command=lambda: report("Monthly"),
            bg="#17365d",
            fg="white",
            width=20
        ).pack(pady=8)

        output = tk.Text(
            window,
            height=14,
            width=65,
            font=("Consolas", 11),
            state="disabled"
        )
        output.pack(padx=15, pady=15)


# ================= START PROGRAM =================

if __name__ == "__main__":
    setup_database()

    root = tk.Tk()
    LoginWindow(root)
    root.mainloop()
