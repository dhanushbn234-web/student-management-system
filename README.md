# 🎓 EduManager Pro — Student Management System

A full-featured **Student Management Web Application** built with **Python (Flask)** and **SQLite**. It provides a clean web dashboard for managing students, attendance, grades, and more — all running locally in your browser.

---

## ✨ Features

- 🔐 **Admin Authentication** — Secure login with SHA-256 hashed passwords
- 👩‍🎓 **Student Management** — Add, update, delete, and search student records
- 📋 **Attendance Tracking** — Mark and view attendance per student
- 📊 **Grade Management** — Record and review grades by subject
- 🧾 **Dashboard Analytics** — Overview of total students, classes, and attendance stats
- 🗄️ **SQLite Database** — Lightweight, file-based database (no server needed)
- 🌐 **Web Interface** — Responsive browser-based UI served by Flask

---

## 🛠️ Tech Stack

| Layer      | Technology        |
|------------|-------------------|
| Backend    | Python 3, Flask   |
| Database   | SQLite3           |
| Frontend   | HTML/CSS/JS (via Flask render_template_string) |

---

## 🚀 Getting Started

### 1. Clone the repository
```bash
git clone https://github.com/<your-username>/student-management-system.git
cd student-management-system
```

### 2. Install dependencies
```bash
pip install flask
```

### 3. Run the application
```bash
python web_app.py
```

### 4. Open in your browser
```
http://127.0.0.1:5000
```

### 5. Default Login Credentials
| Field    | Value     |
|----------|-----------|
| Username | `admin`   |
| Password | `admin123` |

> ⚠️ **Change the default password after first login for security.**

---

## 📁 Project Structure

```
mini project/
├── web_app.py          # Main Flask web application (routes, UI, API)
├── student_system.py   # Core student CRUD logic and database helpers
├── .gitignore          # Git ignore rules
├── README.md           # Project documentation
└── student_records.db  # SQLite database (auto-created on first run, not tracked by git)
```

---

## 📌 Notes

- The `student_records.db` database file is excluded from version control (`.gitignore`). It is auto-generated when you run the app for the first time.
- The app runs in debug mode by default on port `5000`. Disable `debug=True` in production.

---

## 📄 License

This project is open-source. Feel free to use and modify it for educational purposes.
