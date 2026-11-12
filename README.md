# Student Attendance Management System (Streamlit)

## Run locally
```bash
python -m pip install -r requirements.txt
streamlit run attendance_system.py
```

## Streamlit Community Cloud
1. Upload `attendance_system.py` and `requirements.txt` to your GitHub repository.
2. In Streamlit Community Cloud, create/redeploy the app.
3. Set **Main file path** to `attendance_system.py`.
4. Optional but strongly recommended: add these secrets in the app settings:

```toml
ADMIN_USERNAME = "your_admin_username"
ADMIN_PASSWORD = "choose_a_strong_password"
```

The original default login is retained if secrets are not configured:
- Username: `admin`
- Password: `admin123`

## Database note
The app creates/uses `student_attendance.db` in its working directory. SQLite files on Streamlit Community Cloud are not durable storage: the database may be lost when the app is restarted, redeployed, or its container is replaced. For a production school system, use persistent external storage or a managed database, and keep backups. Do not rely on a local SQLite file as the only copy of attendance records.
