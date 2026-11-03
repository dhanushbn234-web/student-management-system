import os
import sqlite3
import hashlib
from functools import wraps
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for  # type: ignore

try:
    from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for  # type: ignore
except Exception:
    from types import SimpleNamespace

    class _FakeFlask:
        def __init__(self, *args, **kwargs):
            self._routes = []

        def route(self, rule, **options):
            def decorator(f):
                self._routes.append((rule, options, f.__name__))
                return f
            return decorator

        def run(self, *args, **kwargs):
            print("[FakeFlask] run called with:", args, kwargs)

    Flask = _FakeFlask
    request = SimpleNamespace(args={}, json={}, path="")
    session = {}
    jsonify = lambda x: x
    render_template_string = lambda s, **kw: s
    redirect = lambda url: url
    url_for = lambda endpoint: f"/{endpoint}"

# Initialize Flask Application
app = Flask(__name__)
app.secret_key = "edumanager-super-secret-key-2026-auth"
DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "student_records.db")

def hash_password(password: str) -> str:
    """Computes SHA-256 hash for secure password storage."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

def init_db():
    """Initializes the SQLite database tables, attendance tracking, and default admin account."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Students Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            age INTEGER,
            grade TEXT,
            email TEXT
        );
    """)

    # Users / Admin Auth Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT DEFAULT 'System Admin',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)

    # Attendance Table with Strict Duplicate Prevention
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS attendance (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id TEXT NOT NULL,
            class_id TEXT NOT NULL,
            attendance_date TEXT NOT NULL,
            status TEXT NOT NULL CHECK(status IN ('present', 'absent', 'late', 'excused')),
            notes TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(student_id, attendance_date, class_id),
            FOREIGN KEY(student_id) REFERENCES students(id) ON DELETE CASCADE
        );
    """)
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_date_class ON attendance(attendance_date, class_id);")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_att_student ON attendance(student_id);")

    # Seed Default Administrator account if not exists
    cursor.execute("SELECT id FROM users WHERE username = 'admin'")
    if not cursor.fetchone():
        cursor.execute("""
            INSERT INTO users (username, password_hash, role)
            VALUES (?, ?, ?)
        """, ("admin", hash_password("admin123"), "System Administrator"))

    conn.commit()
    conn.close()

def get_db_connection():
    """Establishes connection to sqlite database."""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def login_required(f):
    """Decorator to enforce session authentication on protected routes."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user" not in session:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized. Please log in first."}), 401
            return redirect(url_for("login_page"))
        return f(*args, **kwargs)
    return decorated_function

# ==============================================================================
# HTML TEMPLATES: LOGIN & DASHBOARD
# ==============================================================================

LOGIN_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" class="h-full">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>EduManager Pro - Sign In</title>
    <!-- Google Fonts -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['"Inter"', 'sans-serif'],
                        mono: ['"JetBrains Mono"', 'monospace'],
                    },
                    colors: {
                        brand: {
                            50: '#eef2ff',
                            100: '#e0e7ff',
                            200: '#c7d2fe',
                            300: '#a5b4fc',
                            400: '#818cf8',
                            500: '#6366f1',
                            600: '#4f46e5',
                            700: '#4338ca',
                            800: '#3730a3',
                            900: '#312e81',
                        }
                    }
                }
            }
        }
    </script>
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #0b0f19;
        }
        .mesh-bg {
            background-image: 
                radial-gradient(at 0% 0%, rgba(79, 70, 229, 0.15) 0px, transparent 50%),
                radial-gradient(at 100% 0%, rgba(147, 51, 234, 0.12) 0px, transparent 50%),
                radial-gradient(at 50% 100%, rgba(59, 130, 246, 0.1) 0px, transparent 50%);
        }
    </style>
</head>
<body class="h-full flex items-center justify-center p-4 sm:p-6 text-slate-100 selection:bg-indigo-500 selection:text-white mesh-bg antialiased">

    <div class="w-full max-w-[420px] space-y-6">
        <!-- Logo & Header -->
        <div class="text-center space-y-3">
            <div class="inline-flex items-center justify-center w-12 h-12 rounded-2xl bg-gradient-to-br from-indigo-500 to-indigo-700 shadow-xl shadow-indigo-500/25 border border-indigo-400/30">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 14l9-5-9-5-9 5 9 5z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z"/>
                </svg>
            </div>
            <div>
                <div class="flex items-center justify-center space-x-2">
                    <h1 class="text-2xl font-bold tracking-tight text-white">EduManager Pro</h1>
                    <span class="px-1.5 py-0.5 text-[10px] font-semibold tracking-wide uppercase bg-indigo-500/20 text-indigo-300 border border-indigo-500/30 rounded-md">2026 SaaS</span>
                </div>
                <p class="text-xs text-slate-400 mt-1">Student Management & Records Intelligence</p>
            </div>
        </div>

        <!-- Auth Card -->
        <div class="bg-slate-900/90 backdrop-blur-xl border border-slate-800/90 rounded-2xl p-6 sm:p-8 shadow-2xl shadow-black/40 space-y-5">
            <!-- Header Text -->
            <div class="border-b border-slate-800/80 pb-4">
                <h2 class="text-base font-semibold text-white">Welcome back</h2>
                <p class="text-xs text-slate-400 mt-0.5">Enter administrator credentials to access dashboard</p>
            </div>

            <!-- Error Banner -->
            <div id="error-banner" class="hidden p-3 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs font-medium flex items-center space-x-2">
                <svg class="w-4 h-4 flex-shrink-0 text-rose-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                </svg>
                <span id="error-message">Invalid username or password.</span>
            </div>

            <!-- Form -->
            <form id="login-form" onsubmit="handleLogin(event)" class="space-y-4">
                <!-- Username -->
                <div class="space-y-1.5">
                    <label class="block text-xs font-medium text-slate-300">Username</label>
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                            </svg>
                        </div>
                        <input type="text" id="username" required placeholder="admin" autocomplete="username"
                               class="w-full pl-10 pr-4 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500 transition duration-150">
                    </div>
                </div>

                <!-- Password -->
                <div class="space-y-1.5">
                    <div class="flex items-center justify-between">
                        <label class="block text-xs font-medium text-slate-300">Password</label>
                    </div>
                    <div class="relative">
                        <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-500">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"/>
                            </svg>
                        </div>
                        <input type="password" id="password" required placeholder="••••••••" autocomplete="current-password"
                               class="w-full pl-10 pr-10 py-2.5 bg-slate-950/70 border border-slate-800 rounded-xl text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-indigo-500/60 focus:border-indigo-500 transition duration-150">
                        <button type="button" onclick="togglePasswordVisibility()" class="absolute inset-y-0 right-0 pr-3 flex items-center text-slate-500 hover:text-slate-300">
                            <svg id="eye-icon" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                            </svg>
                        </button>
                    </div>
                </div>

                <!-- Auto-fill Demo -->
                <div class="pt-1">
                    <button type="button" onclick="fillDemoCredentials()" class="w-full py-2 px-3 bg-indigo-950/40 hover:bg-indigo-900/50 text-indigo-300 text-xs font-medium rounded-xl transition duration-150 flex items-center justify-center space-x-1.5 border border-indigo-800/40">
                        <svg class="w-3.5 h-3.5 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"/>
                        </svg>
                        <span>Demo Quick Fill (admin / admin123)</span>
                    </button>
                </div>

                <!-- Submit Button -->
                <div class="pt-2">
                    <button type="submit" id="login-btn" class="w-full inline-flex items-center justify-center space-x-2 py-2.5 px-4 bg-indigo-600 hover:bg-indigo-500 active:bg-indigo-700 text-white rounded-xl text-sm font-semibold shadow-lg shadow-indigo-600/30 transition duration-150">
                        <svg id="login-spinner" class="hidden animate-spin w-4 h-4 text-white" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span id="login-btn-text">Sign In</span>
                    </button>
                </div>
            </form>
        </div>

        <!-- Footer -->
        <p class="text-center text-xs text-slate-500 font-medium">
            EduManager Pro &copy; 2026 &bull; Protected with SQLite &amp; SHA-256 Auth
        </p>
    </div>

    <script>
        function togglePasswordVisibility() {
            const pwdInput = document.getElementById("password");
            const eyeIcon = document.getElementById("eye-icon");
            if (pwdInput.type === "password") {
                pwdInput.type = "text";
                eyeIcon.innerHTML = `
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l18 18"/>
                `;
            } else {
                pwdInput.type = "password";
                eyeIcon.innerHTML = `
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                `;
            }
        }

        function fillDemoCredentials() {
            document.getElementById("username").value = "admin";
            document.getElementById("password").value = "admin123";
            hideError();
        }

        function showError(msg) {
            const banner = document.getElementById("error-banner");
            document.getElementById("error-message").innerText = msg;
            banner.classList.remove("hidden");
        }

        function hideError() {
            document.getElementById("error-banner").classList.add("hidden");
        }

        function handleLogin(event) {
            event.preventDefault();
            hideError();

            const username = document.getElementById("username").value.trim();
            const password = document.getElementById("password").value;

            if (!username || !password) {
                showError("Please enter both username and password.");
                return;
            }

            const btn = document.getElementById("login-btn");
            const spinner = document.getElementById("login-spinner");
            const btnText = document.getElementById("login-btn-text");

            btn.disabled = true;
            spinner.classList.remove("hidden");
            btnText.innerText = "Authenticating...";

            fetch('/api/login', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ username, password })
            })
            .then(async response => {
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || "Authentication failed");
                }
                return data;
            })
            .then(data => {
                btnText.innerText = "Redirecting...";
                window.location.href = "/";
            })
            .catch(err => {
                showError(err.message);
                btn.disabled = false;
                spinner.classList.add("hidden");
                btnText.innerText = "Sign In";
            });
        }
    </script>
</body>
</html>
"""

DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html lang="en" class="h-full bg-slate-50">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Dashboard - EduManager Pro</title>
    <!-- Google Fonts: Inter & JetBrains Mono -->
    <link rel="preconnect" href="https://fonts.googleapis.com">
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
    <!-- Tailwind CSS CDN -->
    <script src="https://cdn.tailwindcss.com"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    fontFamily: {
                        sans: ['"Inter"', 'system-ui', '-apple-system', 'sans-serif'],
                        mono: ['"JetBrains Mono"', 'monospace'],
                    },
                    colors: {
                        brand: {
                            50: '#eef2ff',
                            100: '#e0e7ff',
                            200: '#c7d2fe',
                            300: '#a5b4fc',
                            400: '#818cf8',
                            500: '#6366f1',
                            600: '#4f46e5',
                            700: '#4338ca',
                            800: '#3730a3',
                            900: '#312e81',
                        }
                    }
                }
            }
        }
    </script>
    <style>
        body {
            font-family: 'Inter', sans-serif;
            background-color: #f8fafc;
            color: #0f172a;
        }
        .sidebar-nav-item {
            transition: all 0.15s ease-in-out;
        }
        .sidebar-nav-item.active {
            background-color: #eef2ff;
            color: #4f46e5;
            font-weight: 600;
        }
        .sidebar-nav-item:not(.active):hover {
            background-color: #f1f5f9;
            color: #1e293b;
        }
        .custom-scrollbar::-webkit-scrollbar {
            height: 6px;
            width: 6px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
            background: #cbd5e1;
            border-radius: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
            background: #94a3b8;
        }
        .badge-pulse {
            animation: pulse-dot 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }
        @keyframes pulse-dot {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.4; transform: scale(1.15); }
        }
        .chart-tooltip {
            pointer-events: none;
            transition: opacity 0.15s ease, transform 0.15s ease;
        }
    </style>
</head>
<body class="h-full flex flex-col antialiased selection:bg-indigo-500 selection:text-white">

    <!-- Mobile Navigation Drawer Overlay -->
    <div id="mobile-sidebar-backdrop" onclick="toggleMobileSidebar()" class="fixed inset-0 z-40 bg-slate-900/50 backdrop-blur-sm hidden md:hidden transition-opacity"></div>

    <div class="flex-1 flex overflow-hidden">

        <!-- ============================================================================== -->
        <!-- 1. LEFT SIDEBAR (256px wide, Fixed/Sticky SaaS layout) -->
        <!-- ============================================================================== -->
        <aside id="app-sidebar" class="fixed inset-y-0 left-0 z-50 w-64 bg-white border-r border-slate-200/90 flex flex-col justify-between transform -translate-x-full md:translate-x-0 md:static transition-transform duration-200 ease-in-out">
            
            <!-- Sidebar Top: Brand & Navigation -->
            <div class="flex flex-col flex-1 overflow-y-auto custom-scrollbar">
                
                <!-- Brand Header -->
                <div class="h-16 px-6 flex items-center justify-between border-b border-slate-100">
                    <div class="flex items-center space-x-3">
                        <div class="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-md shadow-indigo-500/20">
                            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 14l9-5-9-5-9 5 9 5z"/>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 14l6.16-3.422a12.083 12.083 0 01.665 6.479A11.952 11.952 0 0012 20.055a11.952 11.952 0 00-6.824-2.998 12.078 12.078 0 01.665-6.479L12 14z"/>
                            </svg>
                        </div>
                        <div>
                            <span class="text-sm font-bold text-slate-900 tracking-tight block">EduManager</span>
                            <span class="text-[10px] font-semibold text-indigo-600 tracking-wide uppercase">Pro Edition</span>
                        </div>
                    </div>

                    <!-- Close button on mobile -->
                    <button onclick="toggleMobileSidebar()" class="md:hidden text-slate-400 hover:text-slate-600 p-1 rounded-lg">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                        </svg>
                    </button>
                </div>

                <!-- Navigation Section -->
                <div class="px-3.5 py-4 space-y-6">
                    <div>
                        <p class="px-3 text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Main Menu</p>
                        <nav class="space-y-1">
                            <!-- Dashboard (Active) -->
                            <a href="#" onclick="switchNav('dashboard')" id="nav-dashboard" class="sidebar-nav-item active flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium">
                                <div class="flex items-center space-x-3">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2V6zM14 6a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2V6zM4 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2H6a2 2 0 01-2-2v-2zM14 16a2 2 0 012-2h2a2 2 0 012 2v2a2 2 0 01-2 2h-2a2 2 0 01-2-2v-2z"/>
                                    </svg>
                                    <span>Dashboard</span>
                                </div>
                                <span class="text-[10px] px-1.5 py-0.5 rounded-full bg-indigo-100 text-indigo-700 font-semibold">Live</span>
                            </a>

                            <!-- Students -->
                            <a href="#student-directory-section" onclick="switchNav('students')" id="nav-students" class="sidebar-nav-item text-slate-600 flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium">
                                <div class="flex items-center space-x-3">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/>
                                    </svg>
                                    <span>Students</span>
                                </div>
                                <span id="sidebar-student-count" class="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">0</span>
                            </a>

                            <!-- Classes -->
                            <a href="#classes" onclick="switchNav('classes')" id="nav-classes" class="sidebar-nav-item text-slate-600 flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium">
                                <div class="flex items-center space-x-3">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
                                    </svg>
                                    <span>Classes</span>
                                </div>
                                <span id="sidebar-class-count" class="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">0</span>
                            </a>

                            <!-- Attendance (Active Route Link) -->
                            <a href="#attendance" onclick="switchNav('attendance')" id="nav-attendance" class="sidebar-nav-item text-slate-600 flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium">
                                <div class="flex items-center space-x-3">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
                                    </svg>
                                    <span>Attendance</span>
                                </div>
                                <span id="sidebar-att-rate" class="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-semibold">—</span>
                            </a>

                            <!-- Reports -->
                            <a href="#reports" onclick="switchNav('reports')" id="nav-reports" class="sidebar-nav-item text-slate-600 flex items-center justify-between px-3 py-2 rounded-xl text-xs font-medium">
                                <div class="flex items-center space-x-3">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                                    </svg>
                                    <span>Reports &amp; Export</span>
                                </div>
                                <span class="text-[9px] uppercase px-1 py-0.5 rounded bg-emerald-50 text-emerald-600 font-bold">CSV</span>
                            </a>
                        </nav>
                    </div>

                    <!-- System Section -->
                    <div>
                        <p class="px-3 text-[11px] font-semibold text-slate-400 uppercase tracking-wider mb-2">Management</p>
                        <nav class="space-y-1">
                            <a href="#" onclick="showSectionToast('Database: SQLite3 connected and active')" class="sidebar-nav-item text-slate-600 flex items-center space-x-3 px-3 py-2 rounded-xl text-xs font-medium">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 7v10c0 2.21 3.582 4 8 4s8-1.79 8-4V7M4 7c0 2.21 3.582 4 8 4s8-1.79 8-4M4 7c0-2.21 3.582-4 8-4s8 1.79 8 4m0 5c0 2.21-3.582 4-8 4s-8-1.79-8-4"/>
                                </svg>
                                <span>Database Status</span>
                            </a>
                            <a href="#" onclick="showSectionToast('System Settings &amp; Configuration')" class="sidebar-nav-item text-slate-600 flex items-center space-x-3 px-3 py-2 rounded-xl text-xs font-medium">
                                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                </svg>
                                <span>Settings</span>
                            </a>
                        </nav>
                    </div>
                </div>
            </div>

            <!-- Sidebar Bottom: Admin Profile Card -->
            <div class="p-3.5 border-t border-slate-100 bg-slate-50/50">
                <div class="flex items-center justify-between p-2 rounded-xl bg-white border border-slate-200/80 shadow-sm">
                    <div class="flex items-center space-x-2.5 min-w-0">
                        <div class="w-8 h-8 rounded-lg bg-indigo-600 text-white flex items-center justify-center font-bold text-xs flex-shrink-0 shadow-sm">
                            {{ session.get('user', {}).get('username', 'A')[0]|upper }}
                        </div>
                        <div class="min-w-0 flex-1">
                            <p class="text-xs font-semibold text-slate-900 truncate">{{ session.get('user', {}).get('username', 'Admin') }}</p>
                            <p class="text-[10px] text-slate-400 truncate">{{ session.get('user', {}).get('role', 'System Admin') }}</p>
                        </div>
                    </div>
                    <a href="/logout" title="Sign Out" class="p-1.5 text-slate-400 hover:text-rose-600 hover:bg-rose-50 rounded-lg transition-colors flex-shrink-0">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/>
                        </svg>
                    </a>
                </div>
            </div>
        </aside>

        <!-- ============================================================================== -->
        <!-- 2. MAIN CONTENT WRAPPER -->
        <!-- ============================================================================== -->
        <div class="flex-1 flex flex-col min-w-0 overflow-y-auto custom-scrollbar">

            <!-- Top Header -->
            <header class="sticky top-0 z-30 bg-white/95 backdrop-blur-md border-b border-slate-200/80 px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
                
                <!-- Left: Mobile Menu & Breadcrumbs -->
                <div class="flex items-center space-x-3">
                    <button onclick="toggleMobileSidebar()" class="md:hidden p-2 -ml-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg">
                        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 6h16M4 12h16M4 18h16"/>
                        </svg>
                    </button>
                    
                    <div class="flex items-center space-x-2 text-xs">
                        <span class="text-slate-400">Home</span>
                        <span class="text-slate-300">/</span>
                        <span id="breadcrumb-current" class="font-semibold text-slate-800">Dashboard</span>
                    </div>
                </div>

                <!-- Right: Quick Search, Notifications, Admin Profile -->
                <div class="flex items-center space-x-2 sm:space-x-3">
                    
                    <!-- Quick Search Trigger -->
                    <button onclick="focusSearch()" class="hidden sm:inline-flex items-center space-x-2 px-3 py-1.5 text-xs text-slate-400 hover:text-slate-600 bg-slate-100/80 hover:bg-slate-100 rounded-lg border border-slate-200/60 transition-colors">
                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                        </svg>
                        <span>Search students...</span>
                        <kbd class="px-1.5 py-0.5 text-[10px] font-mono bg-white text-slate-500 rounded border border-slate-200 shadow-2xs">Ctrl K</kbd>
                    </button>

                    <!-- Notifications Button -->
                    <div class="relative">
                        <button onclick="toggleNotifications()" id="notif-btn" class="relative p-2 text-slate-500 hover:text-slate-700 hover:bg-slate-100 rounded-lg transition-colors">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-1.405-1.405A2.032 2.032 0 0118 14.158V11a6.002 6.002 0 00-4-5.659V5a2 2 0 10-4 0v.341C7.67 6.165 6 8.388 6 11v3.159c0 .538-.214 1.055-.595 1.436L4 17h5m6 0v1a3 3 0 11-6 0v-1m6 0H9"/>
                            </svg>
                            <span class="absolute top-1.5 right-1.5 w-2 h-2 bg-indigo-600 rounded-full badge-pulse"></span>
                        </button>

                        <!-- Notification Dropdown Popover -->
                        <div id="notif-popover" class="hidden absolute right-0 mt-2 w-80 bg-white rounded-2xl shadow-xl border border-slate-100 p-4 space-y-3 z-50">
                            <div class="flex items-center justify-between border-b border-slate-100 pb-2">
                                <h4 class="text-xs font-bold text-slate-800 uppercase tracking-wider">Activity Feed</h4>
                                <span class="text-[10px] text-indigo-600 font-semibold">2 New</span>
                            </div>
                            <div class="space-y-2 text-xs">
                                <div class="p-2 rounded-lg bg-indigo-50/60 border border-indigo-100/50 flex space-x-2.5">
                                    <div class="w-2 h-2 rounded-full bg-indigo-600 mt-1 flex-shrink-0"></div>
                                    <div>
                                        <p class="font-medium text-slate-800">Database Synchronized</p>
                                        <p class="text-[11px] text-slate-500 mt-0.5">SQLite live connection verified.</p>
                                    </div>
                                </div>
                                <div class="p-2 rounded-lg bg-emerald-50/60 border border-emerald-100/50 flex space-x-2.5">
                                    <div class="w-2 h-2 rounded-full bg-emerald-600 mt-1 flex-shrink-0"></div>
                                    <div>
                                        <p class="font-medium text-slate-800">Attendance Sync</p>
                                        <p class="text-[11px] text-slate-500 mt-0.5">94.8% semester rate updated.</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Export CSV Quick Button -->
                    <button onclick="exportToCSV()" class="inline-flex items-center space-x-1.5 px-3 py-1.5 text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 border border-slate-200 rounded-lg shadow-2xs transition-colors">
                        <svg class="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                        </svg>
                        <span class="hidden sm:inline">Export CSV</span>
                    </button>

                    <!-- User Avatar Pill -->
                    <div class="flex items-center space-x-2 pl-2 border-l border-slate-200">
                        <div class="w-7 h-7 rounded-full bg-gradient-to-tr from-indigo-600 to-violet-500 text-white flex items-center justify-center font-bold text-xs shadow-2xs">
                            {{ session.get('user', {}).get('username', 'A')[0]|upper }}
                        </div>
                        <span class="text-xs font-semibold text-slate-800 hidden md:inline">{{ session.get('user', {}).get('username', 'Admin') }}</span>
                    </div>
                </div>
            </header>

            <!-- Main Scrollable Dashboard Content -->
            <main class="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 sm:py-8 space-y-6">

                <!-- ============================================================================== -->
                <!-- 1. DASHBOARD PRIMARY VIEW -->
                <!-- ============================================================================== -->
                <div id="view-dashboard" class="space-y-6">

                <!-- Welcome Section Banner -->
                <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-2xs">
                    <div>
                        <h1 class="text-xl sm:text-2xl font-bold tracking-tight text-slate-900" id="welcome-heading">Good morning, Admin 👋</h1>
                        <p class="text-xs sm:text-sm text-slate-500 mt-1">Here's what's happening with your students today across all enrolled classes.</p>
                    </div>
                    <div class="flex items-center space-x-3">
                        <button onclick="openAddModal()" class="inline-flex items-center space-x-2 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white text-xs sm:text-sm font-semibold rounded-xl shadow-md shadow-indigo-500/20 transition duration-150 transform hover:-translate-y-0.5">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/>
                            </svg>
                            <span>Add Student</span>
                        </button>
                    </div>
                </div>

                <!-- ============================================================================== -->
                <!-- 3. STATISTICS CARDS (4 Modern SaaS Metric Cards) -->
                <!-- ============================================================================== -->
                <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
                    
                    <!-- Card 1: Total Students (Violet) -->
                    <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-2xs hover:shadow-sm transition-all">
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-semibold text-slate-500">Total Students</span>
                            <div class="w-9 h-9 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0zm6 3a2 2 0 11-4 0 2 2 0 014 0zM7 10a2 2 0 11-4 0 2 2 0 014 0z"/>
                                </svg>
                            </div>
                        </div>
                        <div class="mt-3">
                            <h3 class="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight" id="stat-total">0</h3>
                            <div class="mt-1 flex items-center space-x-1.5 text-xs">
                                <span class="inline-flex items-center text-emerald-600 font-semibold">
                                    <svg class="w-3.5 h-3.5 mr-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
                                    </svg>
                                    +12%
                                </span>
                                <span class="text-slate-400">from last month</span>
                            </div>
                        </div>
                    </div>

                    <!-- Card 2: Active Classes (Blue) -->
                    <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-2xs hover:shadow-sm transition-all">
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-semibold text-slate-500">Active Classes</span>
                            <div class="w-9 h-9 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 012-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"/>
                                </svg>
                            </div>
                        </div>
                        <div class="mt-3">
                            <h3 class="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight" id="stat-grades">0</h3>
                            <div class="mt-1 flex items-center space-x-1.5 text-xs">
                                <span class="inline-flex items-center px-1.5 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-blue-700">Currently active</span>
                                <span class="text-slate-400">cohorts</span>
                            </div>
                        </div>
                    </div>

                    <!-- Card 3: Average Age (Amber) -->
                    <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-2xs hover:shadow-sm transition-all">
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-semibold text-slate-500">Average Age</span>
                            <div class="w-9 h-9 rounded-xl bg-amber-50 text-amber-600 flex items-center justify-center">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                </svg>
                            </div>
                        </div>
                        <div class="mt-3">
                            <h3 class="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight" id="stat-avg-age">0</h3>
                            <div class="mt-1 flex items-center space-x-1.5 text-xs">
                                <span class="text-slate-500">Across all students</span>
                            </div>
                        </div>
                    </div>

                    <!-- Card 4: Attendance Rate (Green) -->
                    <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-2xs hover:shadow-sm transition-all">
                        <div class="flex items-center justify-between">
                            <span class="text-xs font-semibold text-slate-500">Attendance</span>
                            <div class="w-9 h-9 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                </svg>
                            </div>
                        </div>
                        <div class="mt-3">
                            <h3 class="text-2xl sm:text-3xl font-extrabold text-slate-900 tracking-tight" id="stat-attendance">—</h3>
                            <div class="mt-1 flex items-center space-x-1.5 text-xs">
                                <span class="text-slate-400" id="stat-attendance-subtitle">Academic participation</span>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ============================================================================== -->
                <!-- 4. ANALYTICS SECTION (Student Growth & Semester Distribution Charts) -->
                <!-- ============================================================================== -->
                <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                    
                    <!-- Growth Line Chart (2 Columns) -->
                    <div class="lg:col-span-2 bg-white p-5 sm:p-6 rounded-2xl border border-slate-200/80 shadow-2xs space-y-4">
                        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-2 border-b border-slate-100 pb-3">
                            <div>
                                <h3 class="text-sm font-bold text-slate-900">Student Growth</h3>
                                <p class="text-xs text-slate-500 mt-0.5">Historical enrollment trajectory over current academic year</p>
                            </div>
                            <div class="flex items-center space-x-2">
                                <span class="inline-flex items-center px-2 py-0.5 rounded-md text-[11px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100">
                                    <span class="w-1.5 h-1.5 rounded-full bg-indigo-600 mr-1.5"></span>
                                    Total: <span id="chart-total-badge" class="ml-1 font-bold">0</span>
                                </span>
                            </div>
                        </div>

                        <!-- Interactive SVG Line Chart Container -->
                        <div class="relative w-full h-56 pt-2 select-none" id="growth-chart-container">
                            <svg class="w-full h-full overflow-visible" id="growth-svg" viewBox="0 0 600 200" preserveAspectRatio="none">
                                <defs>
                                    <linearGradient id="growthGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                        <stop offset="0%" stop-color="#6366f1" stop-opacity="0.25"/>
                                        <stop offset="100%" stop-color="#6366f1" stop-opacity="0.0"/>
                                    </linearGradient>
                                </defs>
                                <!-- Grid Lines -->
                                <line x1="40" y1="20" x2="580" y2="20" stroke="#f1f5f9" stroke-width="1" stroke-dasharray="3 3"/>
                                <line x1="40" y1="65" x2="580" y2="65" stroke="#f1f5f9" stroke-width="1" stroke-dasharray="3 3"/>
                                <line x1="40" y1="110" x2="580" y2="110" stroke="#f1f5f9" stroke-width="1" stroke-dasharray="3 3"/>
                                <line x1="40" y1="155" x2="580" y2="155" stroke="#f1f5f9" stroke-width="1"/>

                                <!-- Y Axis Labels -->
                                <text x="10" y="24" fill="#94a3b8" font-size="10" font-family="Inter">30</text>
                                <text x="10" y="69" fill="#94a3b8" font-size="10" font-family="Inter">20</text>
                                <text x="10" y="114" fill="#94a3b8" font-size="10" font-family="Inter">10</text>
                                <text x="10" y="159" fill="#94a3b8" font-size="10" font-family="Inter">0</text>

                                <!-- Area and Line Paths (computed dynamically) -->
                                <path id="growth-area" fill="url(#growthGradient)" d="M50,155 L50,155 Z"/>
                                <path id="growth-line" fill="none" stroke="#4f46e5" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" d="M50,155 L50,155"/>
                                
                                <!-- Interactive Data Points Group -->
                                <g id="growth-points"></g>
                            </svg>

                            <!-- Tooltip Popover -->
                            <div id="chart-tooltip" class="chart-tooltip opacity-0 absolute bg-slate-900 text-white text-[11px] py-1 px-2.5 rounded-lg shadow-lg -translate-x-1/2 -translate-y-full mb-2 pointer-events-none">
                                <span id="tooltip-text" class="font-medium"></span>
                            </div>
                        </div>

                        <!-- Month Labels -->
                        <div class="flex justify-between pl-8 pr-4 text-[11px] text-slate-400 font-medium">
                            <span>Mar</span>
                            <span>Apr</span>
                            <span>May</span>
                            <span>Jun</span>
                            <span>Jul</span>
                            <span>Aug</span>
                        </div>
                    </div>

                    <!-- Students by Semester / Grade Donut & Progress (1 Column) -->
                    <div class="bg-white p-5 sm:p-6 rounded-2xl border border-slate-200/80 shadow-2xs flex flex-col justify-between space-y-4">
                        <div class="border-b border-slate-100 pb-3">
                            <h3 class="text-sm font-bold text-slate-900">Students by Semester</h3>
                            <p class="text-xs text-slate-500 mt-0.5">Cohort distribution across registered grades</p>
                        </div>

                        <!-- Semester Segmented Progress & Count List -->
                        <div id="semester-breakdown-list" class="space-y-3 flex-1 justify-center flex flex-col">
                            <!-- Populated dynamically based on database contents -->
                        </div>

                        <div class="pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
                            <span>Active Cohorts</span>
                            <span id="active-cohorts-count" class="font-semibold text-slate-800">0</span>
                        </div>
                    </div>
                </div>

                <!-- ============================================================================== -->
                <!-- 5. STUDENT DIRECTORY (Primary Section: Data Table, Search, Filter, Pagination) -->
                <!-- ============================================================================== -->
                <div id="student-directory-section" class="bg-white rounded-2xl border border-slate-200/80 shadow-2xs overflow-hidden">
                    
                    <!-- Table Header & Toolbar -->
                    <div class="p-5 sm:p-6 border-b border-slate-100 flex flex-col lg:flex-row justify-between items-start lg:items-center gap-4 bg-white">
                        <div>
                            <div class="flex items-center space-x-2">
                                <h2 class="text-lg font-bold text-slate-900">Students</h2>
                                <span id="table-total-count" class="px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-100 text-slate-600">0</span>
                            </div>
                            <p class="text-xs text-slate-500 mt-0.5">Manage, review, edit or remove student profile records.</p>
                        </div>

                        <!-- Actions Toolbar -->
                        <div class="flex flex-wrap items-center gap-2.5 w-full lg:w-auto">
                            
                            <!-- Search Input -->
                            <div class="relative flex-1 sm:w-72">
                                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                                    </svg>
                                </div>
                                <input type="text" id="search-input" oninput="handleSearchChange()" placeholder="Search by name, ID, grade, email..."
                                       class="w-full pl-9 pr-8 py-2 bg-slate-50 hover:bg-slate-100/70 focus:bg-white border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition duration-150">
                                <button onclick="clearSearch()" id="clear-search-btn" class="hidden absolute inset-y-0 right-0 pr-2.5 flex items-center text-slate-400 hover:text-slate-600">
                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                                    </svg>
                                </button>
                                <span id="search-result-badge" class="hidden absolute -top-1.5 -right-1.5 min-w-[18px] h-[18px] flex items-center justify-center px-1 rounded-full bg-indigo-600 text-white text-[9px] font-bold shadow"></span>
                            </div>

                            <!-- Filter Button & Popover -->
                            <div class="relative">
                                <button onclick="toggleFilterPopover()" id="filter-btn" class="inline-flex items-center space-x-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl transition-colors">
                                    <svg class="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/>
                                    </svg>
                                    <span>Filter</span>
                                    <span id="active-filter-badge" class="hidden w-2 h-2 rounded-full bg-indigo-600"></span>
                                </button>

                                <!-- Filter Popover Card -->
                                <div id="filter-popover" class="hidden absolute right-0 mt-2 w-72 bg-white rounded-2xl shadow-xl border border-slate-200/90 p-4 space-y-3.5 z-40">
                                    <div class="flex items-center justify-between border-b border-slate-100 pb-2">
                                        <h4 class="text-xs font-bold text-slate-900">Filter Directory</h4>
                                        <button onclick="resetFilters()" class="text-[11px] text-indigo-600 hover:text-indigo-800 font-semibold">Reset</button>
                                    </div>
                                    
                                    <!-- Filter by Grade/Semester -->
                                    <div class="space-y-1">
                                        <label class="block text-[11px] font-semibold text-slate-600">Grade / Semester</label>
                                        <select id="filter-grade" onchange="applyFilters()" class="w-full text-xs px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500">
                                            <option value="">All Semesters / Grades</option>
                                        </select>
                                    </div>

                                    <!-- Filter by Age Range -->
                                    <div class="space-y-1">
                                        <label class="block text-[11px] font-semibold text-slate-600">Age Range</label>
                                        <select id="filter-age" onchange="applyFilters()" class="w-full text-xs px-2.5 py-1.5 bg-slate-50 border border-slate-200 rounded-lg focus:outline-none focus:ring-1 focus:ring-indigo-500">
                                            <option value="">All Ages</option>
                                            <option value="under20">&lt; 20 yrs</option>
                                            <option value="20to22">20 - 22 yrs</option>
                                            <option value="above22">&gt; 22 yrs</option>
                                        </select>
                                    </div>

                                    <div class="pt-2 flex justify-end">
                                        <button onclick="toggleFilterPopover()" class="px-3 py-1.5 bg-indigo-600 text-white text-xs font-semibold rounded-lg hover:bg-indigo-700">Apply</button>
                                    </div>
                                </div>
                            </div>

                            <!-- Export CSV Button -->
                            <button onclick="exportToCSV()" class="inline-flex items-center space-x-1.5 px-3 py-2 text-xs font-medium text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-xl transition-colors">
                                <svg class="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                                </svg>
                                <span>Export</span>
                            </button>

                            <!-- Add Student Button -->
                            <button onclick="openAddModal()" class="inline-flex items-center space-x-1.5 px-3.5 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-2xs transition-colors">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"/>
                                </svg>
                                <span>Add Student</span>
                            </button>
                        </div>
                    </div>

                    <!-- Redesigned SaaS Table -->
                    <div class="overflow-x-auto custom-scrollbar">
                        <table class="min-w-full divide-y divide-slate-100">
                            <thead class="bg-slate-50/70">
                                <tr>
                                    <th scope="col" class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Student</th>
                                    <th scope="col" class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Student ID</th>
                                    <th scope="col" class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Age</th>
                                    <th scope="col" class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Grade / Semester</th>
                                    <th scope="col" class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Email Address</th>
                                    <th scope="col" class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Status</th>
                                    <th scope="col" class="px-6 py-3 text-right text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Actions</th>
                                </tr>
                            </thead>
                            <tbody id="student-table-body" class="bg-white divide-y divide-slate-100">
                                <!-- Student rows populated dynamically by JavaScript -->
                            </tbody>
                        </table>
                    </div>

                    <!-- Empty State Container -->
                    <div id="empty-state" class="hidden text-center py-16 px-4">
                        <div class="w-14 h-14 mx-auto mb-3 rounded-2xl bg-slate-100 text-slate-400 flex items-center justify-center">
                            <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/>
                            </svg>
                        </div>
                        <h4 class="text-sm font-bold text-slate-800" id="empty-title">No Students Found</h4>
                        <p class="text-xs text-slate-500 max-w-sm mx-auto mt-1" id="empty-description">Try adjusting your search criteria or register a new student using the button above.</p>
                        <div class="mt-4">
                            <button onclick="clearSearch(); resetFilters();" class="px-3 py-1.5 text-xs font-semibold text-indigo-600 bg-indigo-50 hover:bg-indigo-100 rounded-lg">Clear All Filters</button>
                        </div>
                    </div>

                    <!-- Pagination & Results Bar -->
                    <div class="px-6 py-3.5 bg-slate-50/70 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-3 text-xs text-slate-500">
                        <div class="flex items-center space-x-2">
                            <span id="pagination-summary">Showing 0 to 0 of 0 students</span>
                            <span class="text-slate-300">|</span>
                            <label class="flex items-center space-x-1">
                                <span>Show</span>
                                <select id="rows-per-page" onchange="changePageSize(this.value)" class="bg-white border border-slate-200 rounded px-1.5 py-0.5 text-xs text-slate-700">
                                    <option value="10">10</option>
                                    <option value="25">25</option>
                                    <option value="50">50</option>
                                    <option value="100">100</option>
                                </select>
                            </label>
                        </div>

                        <!-- Pagination Buttons -->
                        <div class="flex items-center space-x-1" id="pagination-controls">
                            <!-- Populated dynamically -->
                        </div>
                    </div>
                </div>
                </div> <!-- End #view-dashboard -->

                <!-- ============================================================================== -->
                <!-- 2. ATTENDANCE MANAGEMENT WORKSPACE -->
                <!-- ============================================================================== -->
                <div id="view-attendance" class="hidden space-y-6">
                    
                    <!-- Attendance Header & Controls Card -->
                    <div class="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-2xs space-y-5">
                        <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                            <div>
                                <div class="flex items-center space-x-2">
                                    <h1 class="text-xl sm:text-2xl font-bold tracking-tight text-slate-900">Attendance</h1>
                                    <span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200/60">Live Tracker</span>
                                </div>
                                <p class="text-xs sm:text-sm text-slate-500 mt-1">Track and manage daily student attendance across cohorts.</p>
                            </div>

                            <!-- Unsaved Changes Notice -->
                            <div id="att-unsaved-badge" class="hidden inline-flex items-center space-x-2 px-3 py-1.5 rounded-xl bg-amber-50 border border-amber-200 text-amber-800 text-xs font-medium animate-pulse">
                                <span class="w-2 h-2 rounded-full bg-amber-500"></span>
                                <span>Unsaved attendance changes</span>
                            </div>
                        </div>

                        <!-- Top Filters: Class Selector, Date Picker, Search -->
                        <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-4 pt-4 border-t border-slate-100">
                            
                            <!-- Class & Date Pickers -->
                            <div class="flex flex-wrap items-center gap-3">
                                <!-- Class / Semester Dropdown -->
                                <div class="space-y-1">
                                    <label class="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Class / Semester</label>
                                    <div class="relative">
                                        <select id="att-class-select" onchange="handleAttendanceClassChange()" class="min-w-[180px] text-xs font-medium py-2 pl-3 pr-8 bg-slate-50 hover:bg-slate-100/80 focus:bg-white border border-slate-200 rounded-xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/50">
                                            <option value="all">All Classes</option>
                                        </select>
                                    </div>
                                </div>

                                <!-- Attendance Date Picker -->
                                <div class="space-y-1">
                                    <label class="block text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Attendance Date</label>
                                    <div class="relative">
                                        <input type="date" id="att-date-select" onchange="handleAttendanceDateChange()" class="text-xs font-medium py-2 px-3 bg-slate-50 hover:bg-slate-100/80 focus:bg-white border border-slate-200 rounded-xl text-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/50">
                                    </div>
                                </div>

                                <!-- Quick Jump to Today -->
                                <div class="space-y-1 self-end">
                                    <button type="button" onclick="setAttendanceToday()" class="py-2 px-3 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-medium rounded-xl transition-colors">
                                        Today
                                    </button>
                                </div>
                            </div>

                            <!-- Search Input -->
                            <div class="relative w-full lg:w-72 self-end">
                                <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
                                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
                                    </svg>
                                </div>
                                <input type="text" id="att-search-input" oninput="handleAttendanceSearch()" placeholder="Search students in class..."
                                       class="w-full pl-9 pr-4 py-2 bg-slate-50 hover:bg-slate-100/70 focus:bg-white border border-slate-200 rounded-xl text-xs text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/50">
                            </div>
                        </div>

                        <!-- Sub-tab Navigation -->
                        <div class="flex items-center space-x-2 pt-2 border-t border-slate-100 overflow-x-auto custom-scrollbar">
                            <button onclick="switchAttSubTab('daily')" id="att-subtab-daily" class="px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white shadow-2xs transition-colors flex items-center space-x-1.5">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
                                </svg>
                                <span>Daily Sheet</span>
                            </button>
                            <button onclick="switchAttSubTab('history')" id="att-subtab-history" class="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors flex items-center space-x-1.5">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"/>
                                </svg>
                                <span>History Log</span>
                            </button>
                            <button onclick="switchAttSubTab('analytics')" id="att-subtab-analytics" class="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors flex items-center space-x-1.5">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"/>
                                </svg>
                                <span>Analytics &amp; Alerts</span>
                            </button>
                            <button onclick="switchAttSubTab('report')" id="att-subtab-report" class="px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors flex items-center space-x-1.5">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 17v-2m3 2v-4m3 4v-6m2 10H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
                                </svg>
                                <span>Attendance Report</span>
                            </button>
                        </div>
                    </div>

                    <!-- 1. DAILY ATTENDANCE SUB-TAB -->
                    <div id="att-view-daily" class="space-y-6">
                        <!-- Live Summary Cards -->
                        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                            <!-- Card 1: Total Students -->
                            <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-2xs">
                                <div class="flex items-center justify-between">
                                    <span class="text-xs font-semibold text-slate-500">Total Students</span>
                                    <div class="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 20h5v-2a3 3 0 00-5.356-1.857M17 20H7m10 0v-2c0-.656-.126-1.283-.356-1.857M7 20H2v-2a3 3 0 015.356-1.857M7 20v-2c0-.656.126-1.283.356-1.857m0 0a5.002 5.002 0 019.288 0M15 7a3 3 0 11-6 0 3 3 0 016 0z"/>
                                        </svg>
                                    </div>
                                </div>
                                <div class="mt-3">
                                    <h3 class="text-2xl sm:text-3xl font-extrabold text-slate-900" id="att-summary-total">0</h3>
                                    <p class="text-xs text-slate-400 mt-1" id="att-summary-cohort">In selected class</p>
                                </div>
                            </div>

                            <!-- Card 2: Present -->
                            <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-2xs">
                                <div class="flex items-center justify-between">
                                    <span class="text-xs font-semibold text-slate-500">Present</span>
                                    <div class="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-600 flex items-center justify-center">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                                        </svg>
                                    </div>
                                </div>
                                <div class="mt-3">
                                    <h3 class="text-2xl sm:text-3xl font-extrabold text-emerald-600" id="att-summary-present">0</h3>
                                    <p class="text-xs text-emerald-600/80 font-medium mt-1">Marked present</p>
                                </div>
                            </div>

                            <!-- Card 3: Absent -->
                            <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-2xs">
                                <div class="flex items-center justify-between">
                                    <span class="text-xs font-semibold text-slate-500">Absent</span>
                                    <div class="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                                        </svg>
                                    </div>
                                </div>
                                <div class="mt-3">
                                    <h3 class="text-2xl sm:text-3xl font-extrabold text-rose-600" id="att-summary-absent">0</h3>
                                    <p class="text-xs text-rose-600/80 font-medium mt-1">Marked absent</p>
                                </div>
                            </div>

                            <!-- Card 4: Attendance Rate -->
                            <div class="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-2xs">
                                <div class="flex items-center justify-between">
                                    <span class="text-xs font-semibold text-slate-500">Attendance Rate</span>
                                    <div class="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6"/>
                                        </svg>
                                    </div>
                                </div>
                                <div class="mt-3">
                                    <h3 class="text-2xl sm:text-3xl font-extrabold text-slate-900" id="att-summary-rate">0%</h3>
                                    <div class="mt-1.5 w-full bg-slate-100 rounded-full h-2 overflow-hidden">
                                        <div id="att-summary-progress" class="bg-indigo-600 h-2 rounded-full transition-all duration-300" style="width: 0%"></div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Attendance Table Section -->
                        <div class="bg-white rounded-2xl border border-slate-200/80 shadow-2xs overflow-hidden">
                            
                            <!-- Table Toolbar -->
                            <div class="p-5 sm:p-6 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div>
                                    <div class="flex items-center space-x-2">
                                        <h2 class="text-base font-bold text-slate-900">Student Attendance Sheet</h2>
                                        <span id="att-table-badge" class="px-2 py-0.5 text-xs font-semibold rounded-full bg-slate-100 text-slate-600">0 Students</span>
                                    </div>
                                    <p class="text-xs text-slate-500 mt-0.5" id="att-date-display">Date: Today</p>
                                </div>

                                <!-- Action Buttons -->
                                <div class="flex flex-wrap items-center gap-2">
                                    <!-- Mark All / Visible Present -->
                                    <button type="button" onclick="markAllAttendance('present')" class="inline-flex items-center space-x-1.5 px-3 py-2 bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 rounded-xl text-xs font-semibold transition-colors">
                                        <svg class="w-3.5 h-3.5 text-emerald-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                                        </svg>
                                        <span id="mark-all-present-text">Mark All Present</span>
                                    </button>

                                    <!-- Mark All Absent -->
                                    <button type="button" onclick="markAllAttendance('absent')" class="inline-flex items-center space-x-1.5 px-3 py-2 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200 rounded-xl text-xs font-semibold transition-colors">
                                        <svg class="w-3.5 h-3.5 text-rose-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                                        </svg>
                                        <span>Mark All Absent</span>
                                    </button>

                                    <!-- Reset -->
                                    <button type="button" onclick="resetCurrentAttendance()" class="inline-flex items-center space-x-1 px-3 py-2 bg-slate-100 hover:bg-slate-200 text-slate-700 rounded-xl text-xs font-semibold transition-colors" title="Reload original saved state">
                                        <svg class="w-3.5 h-3.5 text-slate-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                                        </svg>
                                        <span>Reset</span>
                                    </button>

                                    <!-- Save Attendance Button -->
                                    <button type="button" onclick="saveAttendance()" id="save-attendance-btn" class="inline-flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white rounded-xl text-xs font-semibold shadow-md shadow-indigo-500/20 transition-all">
                                        <svg id="save-att-spinner" class="hidden animate-spin w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24">
                                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                                        </svg>
                                        <span id="save-att-btn-text">Save Attendance</span>
                                    </button>
                                </div>
                            </div>

                            <!-- Attendance Data Table -->
                            <div class="overflow-x-auto custom-scrollbar">
                                <table class="min-w-full divide-y divide-slate-100">
                                    <thead class="bg-slate-50/70">
                                        <tr>
                                            <th scope="col" class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Student</th>
                                            <th scope="col" class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Student ID</th>
                                            <th scope="col" class="px-6 py-3 text-center text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Attendance Status</th>
                                            <th scope="col" class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Overall Rate</th>
                                            <th scope="col" class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Notes / Leave Reason</th>
                                            <th scope="col" class="px-6 py-3 text-right text-[11px] font-semibold text-slate-500 uppercase tracking-wider">Action</th>
                                        </tr>
                                    </thead>
                                    <tbody id="att-table-body" class="bg-white divide-y divide-slate-100">
                                        <!-- Populated dynamically -->
                                    </tbody>
                                </table>
                            </div>

                            <!-- Empty State for Attendance -->
                            <div id="att-empty-state" class="hidden text-center py-16 px-4">
                                <div class="w-12 h-12 mx-auto mb-3 rounded-2xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                                    <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/>
                                    </svg>
                                </div>
                                <h4 class="text-sm font-bold text-slate-800">No Students Found</h4>
                                <p class="text-xs text-slate-500 max-w-sm mx-auto mt-1">No enrolled students found for the selected class or search filter.</p>
                            </div>
                        </div>
                    </div>

                    <!-- 2. HISTORY LOG SUB-TAB -->
                    <div id="att-view-history" class="hidden space-y-6">
                        <div class="bg-white rounded-2xl border border-slate-200/80 shadow-2xs overflow-hidden">
                            <div class="p-5 sm:p-6 border-b border-slate-100 flex items-center justify-between">
                                <div>
                                    <h3 class="text-base font-bold text-slate-900">Attendance Session History</h3>
                                    <p class="text-xs text-slate-500 mt-0.5">Chronological record of saved attendance sessions.</p>
                                </div>
                                <button onclick="fetchAttendanceHistory()" class="px-3 py-1.5 bg-slate-100 hover:bg-slate-200 text-slate-700 text-xs font-semibold rounded-lg flex items-center space-x-1">
                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                                    </svg>
                                    <span>Refresh</span>
                                </button>
                            </div>
                            <div class="overflow-x-auto custom-scrollbar">
                                <table class="min-w-full divide-y divide-slate-100">
                                    <thead class="bg-slate-50/70">
                                        <tr>
                                            <th class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase">Date</th>
                                            <th class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase">Class / Semester</th>
                                            <th class="px-6 py-3 text-center text-[11px] font-semibold text-slate-500 uppercase">Total Students</th>
                                            <th class="px-6 py-3 text-center text-[11px] font-semibold text-slate-500 uppercase">Present</th>
                                            <th class="px-6 py-3 text-center text-[11px] font-semibold text-slate-500 uppercase">Absent</th>
                                            <th class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase">Attendance %</th>
                                            <th class="px-6 py-3 text-right text-[11px] font-semibold text-slate-500 uppercase">Actions</th>
                                        </tr>
                                    </thead>
                                    <tbody id="att-history-tbody" class="bg-white divide-y divide-slate-100">
                                        <!-- History rows -->
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <!-- 3. ANALYTICS & ALERTS SUB-TAB -->
                    <div id="att-view-analytics" class="hidden space-y-6">
                        <!-- Alert Banner for Low Attendance -->
                        <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
                            <!-- Low Attendance Watchlist (2 cols) -->
                            <div class="lg:col-span-2 bg-white p-6 rounded-2xl border border-slate-200/80 shadow-2xs space-y-4">
                                <div class="flex items-center justify-between border-b border-slate-100 pb-3">
                                    <div class="flex items-center space-x-2">
                                        <div class="w-8 h-8 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center">
                                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
                                            </svg>
                                        </div>
                                        <div>
                                            <h3 class="text-sm font-bold text-slate-900">Low Attendance Watchlist</h3>
                                            <p class="text-xs text-slate-500">Students falling below institutional 75% attendance threshold</p>
                                        </div>
                                    </div>
                                    <span id="low-att-count-badge" class="px-2 py-0.5 text-xs font-semibold rounded-full bg-rose-100 text-rose-700">0 Students</span>
                                </div>
                                <div id="low-att-list" class="space-y-2.5 max-h-96 overflow-y-auto custom-scrollbar">
                                    <!-- Low attendance student cards -->
                                </div>
                            </div>

                            <!-- Distribution & Stats (1 col) -->
                            <div class="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-2xs space-y-4 flex flex-col justify-between">
                                <div class="border-b border-slate-100 pb-3">
                                    <h3 class="text-sm font-bold text-slate-900">Attendance Health</h3>
                                    <p class="text-xs text-slate-500">Overall institutional participation</p>
                                </div>
                                <div class="space-y-4 py-2">
                                    <div class="p-4 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
                                        <span class="text-xs text-slate-600 font-medium">Lifetime Overall Rate</span>
                                        <span id="att-health-overall" class="text-base font-bold text-indigo-600">0%</span>
                                    </div>
                                    <div class="p-4 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
                                        <span class="text-xs text-slate-600 font-medium">Total Sessions Logged</span>
                                        <span id="att-health-sessions" class="text-base font-bold text-slate-800">0</span>
                                    </div>
                                    <div class="p-4 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
                                        <span class="text-xs text-slate-600 font-medium">Total Present Marks</span>
                                        <span id="att-health-present" class="text-base font-bold text-emerald-600">0</span>
                                    </div>
                                    <div class="p-4 rounded-xl bg-slate-50 border border-slate-100 flex items-center justify-between">
                                        <span class="text-xs text-slate-600 font-medium">Total Absent Marks</span>
                                        <span id="att-health-absent" class="text-base font-bold text-rose-600">0</span>
                                    </div>
                                </div>
                                <button onclick="switchAttSubTab('report')" class="w-full py-2 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold rounded-xl transition-colors">
                                    View Full Report &amp; Export
                                </button>
                            </div>
                        </div>
                    </div>

                    <!-- 4. ATTENDANCE REPORT SUB-TAB -->
                    <div id="att-view-report" class="hidden space-y-6">
                        <div class="bg-white rounded-2xl border border-slate-200/80 shadow-2xs overflow-hidden">
                            <div class="p-5 sm:p-6 border-b border-slate-100 flex flex-col md:flex-row md:items-center justify-between gap-4">
                                <div>
                                    <h3 class="text-base font-bold text-slate-900">Student Attendance Aggregate Report</h3>
                                    <p class="text-xs text-slate-500 mt-0.5">Comprehensive student-wise attendance records &amp; percentage metrics.</p>
                                </div>
                                <div class="flex items-center space-x-2">
                                    <button onclick="exportAttendanceReportCSV()" class="inline-flex items-center space-x-1.5 px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white rounded-xl text-xs font-semibold shadow-2xs transition-colors">
                                        <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4"/>
                                        </svg>
                                        <span>Export Attendance CSV</span>
                                    </button>
                                </div>
                            </div>
                            <div class="overflow-x-auto custom-scrollbar">
                                <table class="min-w-full divide-y divide-slate-100">
                                    <thead class="bg-slate-50/70">
                                        <tr>
                                            <th class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase">Student</th>
                                            <th class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase">Student ID</th>
                                            <th class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase">Class / Semester</th>
                                            <th class="px-6 py-3 text-center text-[11px] font-semibold text-slate-500 uppercase">Total Classes</th>
                                            <th class="px-6 py-3 text-center text-[11px] font-semibold text-slate-500 uppercase">Present</th>
                                            <th class="px-6 py-3 text-center text-[11px] font-semibold text-slate-500 uppercase">Absent</th>
                                            <th class="px-6 py-3 text-left text-[11px] font-semibold text-slate-500 uppercase">Attendance %</th>
                                        </tr>
                                    </thead>
                                    <tbody id="att-report-tbody" class="bg-white divide-y divide-slate-100">
                                        <!-- Report rows -->
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- ============================================================================== -->
                <!-- 3. CLASSES VIEW -->
                <!-- ============================================================================== -->
                <div id="view-classes" class="hidden space-y-6">
                    <div class="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-2xs">
                        <div class="flex items-center justify-between border-b border-slate-100 pb-4">
                            <div>
                                <h1 class="text-xl font-bold text-slate-900">Academic Cohorts &amp; Classes</h1>
                                <p class="text-xs text-slate-500 mt-0.5">Overview of registered semesters and student distributions.</p>
                            </div>
                        </div>
                        <div id="classes-grid" class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4 pt-6">
                            <!-- Populated dynamically -->
                        </div>
                    </div>
                </div>

                <!-- ============================================================================== -->
                <!-- 4. REPORTS & EXPORTS VIEW -->
                <!-- ============================================================================== -->
                <div id="view-reports" class="hidden space-y-6">
                    <div class="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-2xs space-y-6">
                        <div class="border-b border-slate-100 pb-4 flex items-center justify-between">
                            <div>
                                <h1 class="text-xl font-bold text-slate-900">Reports &amp; Data Exports</h1>
                                <p class="text-xs text-slate-500 mt-0.5">Export student registries and attendance audits in standard CSV format.</p>
                            </div>
                        </div>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-6">
                            <div class="p-6 rounded-2xl border border-slate-200 bg-slate-50/50 space-y-4">
                                <div class="w-10 h-10 rounded-xl bg-indigo-100 text-indigo-600 flex items-center justify-center">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"/>
                                    </svg>
                                </div>
                                <div>
                                    <h3 class="text-sm font-bold text-slate-900">Student Directory Export</h3>
                                    <p class="text-xs text-slate-500 mt-1">Download complete list of all student IDs, names, ages, grades, and email contacts.</p>
                                </div>
                                <button onclick="exportToCSV()" class="px-4 py-2 bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-semibold rounded-xl shadow-2xs">
                                    Download Directory CSV
                                </button>
                            </div>

                            <div class="p-6 rounded-2xl border border-slate-200 bg-slate-50/50 space-y-4">
                                <div class="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-600 flex items-center justify-center">
                                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
                                    </svg>
                                </div>
                                <div>
                                    <h3 class="text-sm font-bold text-slate-900">Attendance Audit Report</h3>
                                    <p class="text-xs text-slate-500 mt-1">Export full attendance percentages, total classes, present and absent aggregates.</p>
                                </div>
                                <button onclick="exportAttendanceReportCSV()" class="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-semibold rounded-xl shadow-2xs">
                                    Download Attendance CSV
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

            </main>

            <!-- Modern SaaS Footer -->
            <footer class="bg-white border-t border-slate-200/80 py-4 px-6 sm:px-8 flex flex-col sm:flex-row items-center justify-between text-xs text-slate-400 gap-2">
                <div>EduManager Pro &bull; Student Information &amp; Records Management</div>
                <div class="flex items-center space-x-4">
                    <span>SQLite3 Backend</span>
                    <span>&bull;</span>
                    <span>v2.6 SaaS Edition</span>
                </div>
            </footer>
        </div>
    </div>

    <!-- ============================================================================== -->
    <!-- 6. MODALS, DRAWERS & DIALOGS -->
    <!-- ============================================================================== -->

    <!-- ADD / EDIT STUDENT MODAL -->
    <div id="student-modal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm opacity-0 pointer-events-none transition-all duration-200">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-lg overflow-hidden transform scale-95 opacity-0 transition-all duration-200 border border-slate-200/80 modal-card">
            
            <!-- Modal Header -->
            <div class="px-6 py-4 border-b border-slate-100 flex items-center justify-between bg-slate-50/50">
                <div class="flex items-center space-x-2.5">
                    <div class="w-8 h-8 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center">
                        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"/>
                        </svg>
                    </div>
                    <div>
                        <h3 id="modal-title" class="text-sm font-bold text-slate-900">Add New Student</h3>
                        <p id="modal-subtitle" class="text-xs text-slate-500">Create a new student profile in directory</p>
                    </div>
                </div>
                <button onclick="closeModal()" type="button" class="w-7 h-7 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 flex items-center justify-center transition-colors">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            </div>

            <!-- Modal Form with Organized Sections -->
            <form id="student-form" onsubmit="saveStudent(event)" class="p-6 space-y-5">
                <input type="hidden" id="form-mode" value="add">

                <!-- Section 1: Personal Information -->
                <div class="space-y-3">
                    <p class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Personal Information</p>
                    
                    <!-- Full Name -->
                    <div>
                        <label class="block text-xs font-medium text-slate-700 mb-1">
                            Full Name <span class="text-rose-500">*</span>
                        </label>
                        <input type="text" id="name" required placeholder="e.g. Jnanesh PM"
                               class="w-full px-3.5 py-2 bg-slate-50 focus:bg-white border border-slate-200 rounded-xl text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition duration-150">
                    </div>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <!-- Age -->
                        <div>
                            <label class="block text-xs font-medium text-slate-700 mb-1">
                                Age <span class="text-rose-500">*</span>
                            </label>
                            <input type="number" id="age" required min="1" max="120" placeholder="20"
                                   class="w-full px-3.5 py-2 bg-slate-50 focus:bg-white border border-slate-200 rounded-xl text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition duration-150">
                        </div>

                        <!-- Email Address -->
                        <div>
                            <label class="block text-xs font-medium text-slate-700 mb-1">
                                Email Address
                            </label>
                            <input type="email" id="email" placeholder="student@edu.com"
                                   class="w-full px-3.5 py-2 bg-slate-50 focus:bg-white border border-slate-200 rounded-xl text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition duration-150">
                        </div>
                    </div>
                </div>

                <!-- Section 2: Academic Information -->
                <div class="space-y-3 pt-2 border-t border-slate-100">
                    <p class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Academic Information</p>

                    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        <!-- Student ID -->
                        <div>
                            <label class="block text-xs font-medium text-slate-700 mb-1 flex items-center justify-between">
                                <span>Student ID <span class="text-rose-500">*</span></span>
                            </label>
                            <input type="text" id="student_id" required placeholder="e.g. 330CS24008"
                                   class="w-full font-mono px-3.5 py-2 bg-slate-50 focus:bg-white border border-slate-200 rounded-xl text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition duration-150">
                            <p id="id-hint" class="text-[10px] text-slate-400 mt-1">Unique institutional ID</p>
                        </div>

                        <!-- Grade / Semester -->
                        <div>
                            <label class="block text-xs font-medium text-slate-700 mb-1">
                                Grade / Semester <span class="text-rose-500">*</span>
                            </label>
                            <input type="text" id="grade" required placeholder="e.g. 5th SEM CSE"
                                   class="w-full px-3.5 py-2 bg-slate-50 focus:bg-white border border-slate-200 rounded-xl text-xs sm:text-sm text-slate-800 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition duration-150">
                            <p class="text-[10px] text-slate-400 mt-1">Course cohort identifier</p>
                        </div>
                    </div>
                </div>

                <!-- Form Buttons -->
                <div class="pt-4 flex items-center justify-end space-x-2.5 border-t border-slate-100">
                    <button type="button" onclick="closeModal()" class="px-4 py-2 border border-slate-200 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-50 transition duration-150">
                        Cancel
                    </button>
                    <button type="submit" id="save-btn" class="inline-flex items-center space-x-2 px-4 py-2 bg-indigo-600 hover:bg-indigo-700 active:bg-indigo-800 text-white rounded-xl text-xs font-semibold shadow-2xs transition duration-150">
                        <svg id="save-btn-spinner" class="hidden animate-spin w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24">
                            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                        </svg>
                        <span id="save-btn-text">Save Student</span>
                    </button>
                </div>
            </form>
        </div>
    </div>

    <!-- STUDENT PROFILE SLIDE-OVER DRAWER -->
    <div id="profile-drawer-backdrop" onclick="closeProfileDrawer()" class="fixed inset-0 z-50 bg-slate-900/40 backdrop-blur-xs hidden transition-opacity"></div>
    <div id="profile-drawer" class="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-white shadow-2xl border-l border-slate-200 flex flex-col justify-between transform translate-x-full transition-transform duration-200 ease-in-out">
        <div>
            <!-- Drawer Header -->
            <div class="p-6 border-b border-slate-100 flex items-center justify-between bg-slate-50/40">
                <div class="flex items-center space-x-2">
                    <span class="px-2 py-0.5 text-[10px] font-bold uppercase tracking-wider bg-indigo-50 text-indigo-700 rounded-md">Student Profile</span>
                </div>
                <button onclick="closeProfileDrawer()" class="p-1.5 rounded-lg text-slate-400 hover:text-slate-600 hover:bg-slate-100 transition-colors">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </button>
            </div>

            <!-- Profile Info Body -->
            <div class="p-6 space-y-6">
                <!-- Avatar & Core Info -->
                <div class="flex items-center space-x-4">
                    <div id="drawer-avatar" class="w-16 h-16 rounded-2xl bg-gradient-to-br from-indigo-500 to-indigo-700 text-white flex items-center justify-center font-bold text-xl shadow-md">
                        JD
                    </div>
                    <div>
                        <h3 id="drawer-name" class="text-base font-bold text-slate-900">Student Name</h3>
                        <p id="drawer-id" class="font-mono text-xs text-indigo-600 font-semibold mt-0.5">330CS24008</p>
                        <div class="mt-1 flex items-center space-x-2">
                            <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                                <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1"></span>
                                Active Enrolled
                            </span>
                        </div>
                    </div>
                </div>

                <!-- Key Details Grid -->
                <div class="grid grid-cols-2 gap-3 pt-2">
                    <div class="p-3 rounded-xl bg-slate-50 border border-slate-100">
                        <p class="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Age</p>
                        <p id="drawer-age" class="text-sm font-bold text-slate-800 mt-0.5">-</p>
                    </div>
                    <div class="p-3 rounded-xl bg-slate-50 border border-slate-100">
                        <p class="text-[10px] font-semibold text-slate-400 uppercase tracking-wider">Semester / Grade</p>
                        <p id="drawer-grade" class="text-sm font-bold text-slate-800 mt-0.5">-</p>
                    </div>
                </div>

                <!-- Contact Info Section -->
                <div class="space-y-3 pt-2">
                    <p class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Contact &amp; Communication</p>
                    <div class="p-3.5 rounded-xl bg-slate-50 border border-slate-100 space-y-2 text-xs">
                        <div class="flex items-center justify-between">
                            <span class="text-slate-500">Email Address</span>
                            <a id="drawer-email-link" href="#" class="font-medium text-indigo-600 hover:underline">-</a>
                        </div>
                        <div class="flex items-center justify-between">
                            <span class="text-slate-500">Status</span>
                            <span id="drawer-standing" class="font-semibold text-slate-800">Good Academic Standing</span>
                        </div>
                    </div>
                </div>

                <!-- Real Attendance Analytics Section -->
                <div class="space-y-3 pt-2 border-t border-slate-100">
                    <div class="flex items-center justify-between">
                        <p class="text-[11px] font-bold text-slate-400 uppercase tracking-wider">Attendance Performance</p>
                        <span id="drawer-att-badge" class="px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-100 text-emerald-800">0%</span>
                    </div>
                    <div class="grid grid-cols-3 gap-2 text-center">
                        <div class="p-2 rounded-xl bg-slate-50 border border-slate-100">
                            <p class="text-[10px] text-slate-400 font-semibold">Classes</p>
                            <p id="drawer-att-total" class="text-xs font-bold text-slate-800 mt-0.5">0</p>
                        </div>
                        <div class="p-2 rounded-xl bg-emerald-50/60 border border-emerald-100">
                            <p class="text-[10px] text-emerald-600 font-semibold">Present</p>
                            <p id="drawer-att-present" class="text-xs font-bold text-emerald-700 mt-0.5">0</p>
                        </div>
                        <div class="p-2 rounded-xl bg-rose-50/60 border border-rose-100">
                            <p class="text-[10px] text-rose-600 font-semibold">Absent</p>
                            <p id="drawer-att-absent" class="text-xs font-bold text-rose-700 mt-0.5">0</p>
                        </div>
                    </div>

                    <!-- Recent Sessions Log -->
                    <div class="space-y-1.5 pt-1">
                        <p class="text-[10px] font-semibold text-slate-500 uppercase tracking-wider">Recent Attendance Logs</p>
                        <div id="drawer-att-history-list" class="space-y-1.5 max-h-40 overflow-y-auto custom-scrollbar text-xs">
                            <p class="text-slate-400 italic text-[11px] py-1 text-center">Loading logs...</p>
                        </div>
                    </div>
                </div>
            </div>
        </div>

        <!-- Drawer Footer Actions -->
        <div class="p-6 border-t border-slate-100 bg-slate-50/50 flex items-center space-x-3">
            <button id="drawer-edit-btn" onclick="" class="flex-1 px-4 py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white rounded-xl text-xs font-semibold shadow-2xs transition-colors flex items-center justify-center space-x-1.5">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                </svg>
                <span>Edit Profile</span>
            </button>
            <button id="drawer-delete-btn" onclick="" class="px-4 py-2.5 bg-rose-50 hover:bg-rose-100 text-rose-700 border border-rose-200/80 rounded-xl text-xs font-semibold transition-colors flex items-center justify-center space-x-1.5">
                <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
                <span>Delete</span>
            </button>
        </div>
    </div>

    <!-- DELETE CONFIRMATION DIALOG -->
    <div id="delete-modal" class="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/50 backdrop-blur-sm opacity-0 pointer-events-none transition-all duration-200">
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden transform scale-95 opacity-0 transition-all duration-200 border border-slate-200/80 p-6 space-y-4 modal-card">
            <div class="w-11 h-11 rounded-xl bg-rose-50 text-rose-600 flex items-center justify-center mx-auto">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
            </div>
            <div class="text-center">
                <h3 class="text-base font-bold text-slate-900">Delete student record?</h3>
                <p class="text-xs text-slate-500 mt-1">
                    Are you sure you want to permanently remove <span id="delete-student-name" class="font-bold text-slate-800"></span> from the student directory? This action cannot be undone.
                </p>
            </div>
            <div class="flex items-center space-x-2.5 pt-2">
                <button type="button" onclick="closeDeleteModal()" class="w-1/2 px-3.5 py-2 border border-slate-200 rounded-xl text-xs font-semibold text-slate-600 hover:bg-slate-50 transition duration-150">
                    Cancel
                </button>
                <button type="button" onclick="confirmDelete()" id="confirm-delete-btn" class="w-1/2 px-3.5 py-2 bg-rose-600 hover:bg-rose-700 active:bg-rose-800 text-white rounded-xl text-xs font-semibold shadow-2xs transition duration-150">
                    Delete Student
                </button>
            </div>
        </div>
    </div>

    <!-- TOAST NOTIFICATION CONTAINER -->
    <div id="toast-container" class="fixed bottom-5 right-5 z-50 flex flex-col space-y-2 pointer-events-none"></div>

    <!-- ============================================================================== -->
    <!-- 7. APPLICATION CLIENT-SIDE LOGIC -->
    <!-- ============================================================================== -->
    <script>
        let allStudents = [];
        let filteredStudents = [];
        let currentPage = 1;
        let pageSize = 10;
        let pendingDeleteId = null;
        let openActionMenuId = null;

        // Dynamic Time Greeting
        function updateGreeting() {
            const hour = new Date().getHours();
            let greeting = "Good morning, Admin 👋";
            if (hour >= 12 && hour < 17) {
                greeting = "Good afternoon, Admin 👋";
            } else if (hour >= 17) {
                greeting = "Good evening, Admin 👋";
            }
            const el = document.getElementById("welcome-heading");
            if (el) el.innerText = greeting;
        }

        document.addEventListener("DOMContentLoaded", () => {
            updateGreeting();
            fetchStudents();

            // Keyboard Shortcuts
            document.addEventListener("keydown", (e) => {
                if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === "k") {
                    e.preventDefault();
                    focusSearch();
                } else if (e.key === "Escape") {
                    closeModal();
                    closeDeleteModal();
                    closeProfileDrawer();
                    closeAllDropdowns();
                }
            });

            // Close dropdowns on outside click
            document.addEventListener("click", (e) => {
                if (!e.target.closest(".action-menu-container")) {
                    closeAllDropdowns();
                }
                if (!e.target.closest("#notif-btn") && !e.target.closest("#notif-popover")) {
                    const notif = document.getElementById("notif-popover");
                    if (notif) notif.classList.add("hidden");
                }
                if (!e.target.closest("#filter-btn") && !e.target.closest("#filter-popover")) {
                    const filter = document.getElementById("filter-popover");
                    if (filter) filter.classList.add("hidden");
                }
            });

            // Unsaved Attendance Changes Guard
            window.addEventListener("beforeunload", (e) => {
                if (hasUnsavedAttendance) {
                    e.preventDefault();
                    e.returnValue = "You have unsaved attendance changes. Leave without saving?";
                    return e.returnValue;
                }
            });

            // Browser Hash Routing
            window.addEventListener("hashchange", () => {
                const hash = (window.location.hash || '').replace('#', '').trim();
                if (hash && ['dashboard', 'students', 'attendance', 'classes', 'reports'].includes(hash)) {
                    switchNav(hash);
                }
            });

            const initialPath = window.location.pathname;
            const initialHash = (window.location.hash || '').replace('#', '').trim();
            if (initialPath.includes('/attendance') || initialHash === 'attendance') {
                switchNav('attendance');
            } else if (initialHash && ['dashboard', 'students', 'classes', 'reports'].includes(initialHash)) {
                switchNav(initialHash);
            }
        });

        // --- FETCH STUDENTS FROM API ---
        function fetchStudents() {
            fetch('/api/students')
                .then(response => {
                    if (response.status === 401) {
                        window.location.href = '/login';
                        return;
                    }
                    if (!response.ok) throw new Error('Failed to fetch records');
                    return response.json();
                })
                .then(data => {
                    if (!data) return;
                    allStudents = data;
                    populateGradeFilterOptions(allStudents);
                    populateAttendanceClassOptions();
                    applyFilters();
                    updateStats(allStudents);
                    renderAnalytics(allStudents);
                    fetchAttendanceAnalytics();
                })
                .catch(err => {
                    console.error("Error fetching students:", err);
                    showToast("Error loading student records database.", "error");
                });
        }

        // --- UPDATE METRIC CARDS ---
        function updateStats(students) {
            document.getElementById("stat-total").innerText = students.length;
            document.getElementById("sidebar-student-count").innerText = students.length;
            document.getElementById("chart-total-badge").innerText = students.length;
            
            const uniqueGrades = new Set(students.map(s => (s.grade || '').trim()).filter(Boolean));
            document.getElementById("stat-grades").innerText = uniqueGrades.size;
            document.getElementById("sidebar-class-count").innerText = uniqueGrades.size;
            document.getElementById("active-cohorts-count").innerText = uniqueGrades.size;

            if (students.length > 0) {
                const totalAge = students.reduce((sum, s) => sum + (parseInt(s.age) || 0), 0);
                const avgAge = (totalAge / students.length).toFixed(1);
                document.getElementById("stat-avg-age").innerText = `${avgAge} yrs`;
            } else {
                document.getElementById("stat-avg-age").innerText = "0 yrs";
            }
        }

        // --- RENDER ANALYTICS CHARTS ---
        function renderAnalytics(students) {
            // 1. Enrollment Line Chart
            renderGrowthChart(students.length);

            // 2. Students by Semester Breakdown
            renderSemesterBreakdown(students);
        }

        function renderGrowthChart(totalCount) {
            const months = ["Mar", "Apr", "May", "Jun", "Jul", "Aug"];
            // Build progressive enrollment curve leading to current total
            const baseCount = Math.max(1, Math.round(totalCount * 0.4));
            const diff = totalCount - baseCount;
            const pointsData = [
                Math.round(baseCount),
                Math.round(baseCount + diff * 0.2),
                Math.round(baseCount + diff * 0.45),
                Math.round(baseCount + diff * 0.7),
                Math.round(baseCount + diff * 0.88),
                totalCount
            ];

            const maxVal = Math.max(30, totalCount + 5);
            const xCoords = [50, 150, 250, 350, 450, 550];
            const yCoords = pointsData.map(val => {
                const ratio = val / maxVal;
                return Math.round(160 - (ratio * 135));
            });

            // Smooth Bezier Curve Path
            let pathD = `M ${xCoords[0]} ${yCoords[0]}`;
            for (let i = 0; i < xCoords.length - 1; i++) {
                const xc = (xCoords[i] + xCoords[i + 1]) / 2;
                const yc = (yCoords[i] + yCoords[i + 1]) / 2;
                pathD += ` Q ${xCoords[i]} ${yCoords[i]}, ${xc} ${yc}`;
            }
            pathD += ` T ${xCoords[xCoords.length - 1]} ${yCoords[yCoords.length - 1]}`;

            const lineEl = document.getElementById("growth-line");
            const areaEl = document.getElementById("growth-area");
            if (lineEl) lineEl.setAttribute("d", pathD);
            if (areaEl) {
                const areaD = `${pathD} L ${xCoords[xCoords.length - 1]} 160 L ${xCoords[0]} 160 Z`;
                areaEl.setAttribute("d", areaD);
            }

            // Render interactive data circles
            const pointsGroup = document.getElementById("growth-points");
            if (pointsGroup) {
                pointsGroup.innerHTML = "";
                pointsData.forEach((val, idx) => {
                    const cx = xCoords[idx];
                    const cy = yCoords[idx];
                    const month = months[idx];

                    const circle = document.createElementNS("http://www.w3.org/2000/svg", "circle");
                    circle.setAttribute("cx", cx);
                    circle.setAttribute("cy", cy);
                    circle.setAttribute("r", "5");
                    circle.setAttribute("fill", "#ffffff");
                    circle.setAttribute("stroke", "#4f46e5");
                    circle.setAttribute("stroke-width", "2.5");
                    circle.setAttribute("class", "cursor-pointer transition-all hover:r-7");

                    circle.addEventListener("mouseenter", (e) => {
                        showChartTooltip(month, val, e.target);
                    });
                    circle.addEventListener("mouseleave", hideChartTooltip);

                    pointsGroup.appendChild(circle);
                });
            }
        }

        function showChartTooltip(month, count, targetEl) {
            const tooltip = document.getElementById("chart-tooltip");
            const tooltipText = document.getElementById("tooltip-text");
            const container = document.getElementById("growth-chart-container");
            if (!tooltip || !container) return;

            const rect = targetEl.getBoundingClientRect();
            const containerRect = container.getBoundingClientRect();

            tooltipText.innerText = `${month}: ${count} students`;
            tooltip.style.left = `${rect.left - containerRect.left + (rect.width / 2)}px`;
            tooltip.style.top = `${rect.top - containerRect.top}px`;
            tooltip.classList.remove("opacity-0");
        }

        function hideChartTooltip() {
            const tooltip = document.getElementById("chart-tooltip");
            if (tooltip) tooltip.classList.add("opacity-0");
        }

        function renderSemesterBreakdown(students) {
            const container = document.getElementById("semester-breakdown-list");
            if (!container) return;

            if (students.length === 0) {
                container.innerHTML = `<p class="text-xs text-slate-400 text-center py-4 italic">No students registered yet</p>`;
                return;
            }

            const counts = {};
            students.forEach(s => {
                const grade = (s.grade || 'Unassigned').trim();
                counts[grade] = (counts[grade] || 0) + 1;
            });

            const sortedGrades = Object.entries(counts).sort((a, b) => b[1] - a[1]);
            const colors = ["bg-indigo-600", "bg-violet-500", "bg-blue-500", "bg-emerald-500", "bg-amber-500"];

            let html = "";
            sortedGrades.forEach(([grade, count], idx) => {
                const percentage = Math.round((count / students.length) * 100);
                const color = colors[idx % colors.length];
                html += `
                    <div class="space-y-1">
                        <div class="flex items-center justify-between text-xs">
                            <span class="font-medium text-slate-700 truncate max-w-[160px]">${escapeHtml(grade)}</span>
                            <span class="font-semibold text-slate-900">${count} (${percentage}%)</span>
                        </div>
                        <div class="w-full h-2 rounded-full bg-slate-100 overflow-hidden">
                            <div class="h-full rounded-full ${color}" style="width: ${percentage}%"></div>
                        </div>
                    </div>
                `;
            });

            container.innerHTML = html;
        }

        // --- FILTER & SEARCH SYSTEM ---
        function populateGradeFilterOptions(students) {
            const gradeSelect = document.getElementById("filter-grade");
            if (!gradeSelect) return;
            
            const currentVal = gradeSelect.value;
            const uniqueGrades = Array.from(new Set(students.map(s => (s.grade || '').trim()).filter(Boolean))).sort();

            gradeSelect.innerHTML = `<option value="">All Semesters / Grades</option>`;
            uniqueGrades.forEach(grade => {
                const opt = document.createElement("option");
                opt.value = grade;
                opt.innerText = grade;
                if (grade === currentVal) opt.selected = true;
                gradeSelect.appendChild(opt);
            });
        }

        function highlightText(text, query) {
            if (!text) return "";
            if (!query) return escapeHtml(text);
            const str = String(text);
            const q = query.toLowerCase();
            const lower = str.toLowerCase();
            let result = "";
            let start = 0;
            let idx = lower.indexOf(q, start);
            if (idx === -1) return escapeHtml(str);
            while (idx !== -1) {
                result += escapeHtml(str.substring(start, idx));
                result += '<mark class="bg-yellow-200 text-yellow-900 rounded px-0.5 font-semibold">' + 
                          escapeHtml(str.substring(idx, idx + query.length)) + 
                          '</mark>';
                start = idx + query.length;
                idx = lower.indexOf(q, start);
            }
            result += escapeHtml(str.substring(start));
            return result;
        }

        function handleSearchChange() {
            const query = document.getElementById("search-input").value.trim();
            const clearBtn = document.getElementById("clear-search-btn");
            if (clearBtn) {
                if (query) clearBtn.classList.remove("hidden");
                else clearBtn.classList.add("hidden");
            }
            applyFilters();
        }

        function clearSearch() {
            const input = document.getElementById("search-input");
            if (input) input.value = "";
            handleSearchChange();
        }

        function focusSearch() {
            const input = document.getElementById("search-input");
            if (input) {
                input.focus();
                input.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }

        function toggleFilterPopover() {
            const popover = document.getElementById("filter-popover");
            if (popover) popover.classList.toggle("hidden");
        }

        function toggleNotifications() {
            const notif = document.getElementById("notif-popover");
            if (notif) notif.classList.toggle("hidden");
        }

        function applyFilters() {
            const search = (document.getElementById("search-input")?.value || "").trim().toLowerCase();
            const gradeFilter = document.getElementById("filter-grade")?.value || "";
            const ageFilter = document.getElementById("filter-age")?.value || "";

            const hasActiveFilter = Boolean(gradeFilter || ageFilter);
            const filterBadge = document.getElementById("active-filter-badge");
            if (filterBadge) {
                if (hasActiveFilter) filterBadge.classList.remove("hidden");
                else filterBadge.classList.add("hidden");
            }

            filteredStudents = allStudents.filter(student => {
                // Search match
                const idMatch = (student.id || '').toLowerCase().includes(search);
                const nameMatch = (student.name || '').toLowerCase().includes(search);
                const gradeMatch = (student.grade || '').toLowerCase().includes(search);
                const emailMatch = (student.email || '').toLowerCase().includes(search);
                const matchesSearch = !search || idMatch || nameMatch || gradeMatch || emailMatch;

                // Grade match
                const matchesGrade = !gradeFilter || (student.grade || '').trim().toLowerCase() === gradeFilter.toLowerCase();

                // Age match
                const age = parseInt(student.age) || 0;
                let matchesAge = true;
                if (ageFilter === "under20") matchesAge = age < 20;
                else if (ageFilter === "20to22") matchesAge = age >= 20 && age <= 22;
                else if (ageFilter === "above22") matchesAge = age > 22;

                return matchesSearch && matchesGrade && matchesAge;
            });

            // Sort: name matches first, then ID matches, then rest
            if (search) {
                filteredStudents.sort((a, b) => {
                    const aName = (a.name || '').toLowerCase().includes(search) ? 0 : 1;
                    const bName = (b.name || '').toLowerCase().includes(search) ? 0 : 1;
                    return aName - bName;
                });
            }

            // Update result badge on search box
            const badge = document.getElementById("search-result-badge");
            if (badge) {
                if (search) {
                    badge.textContent = filteredStudents.length;
                    badge.classList.remove("hidden");
                } else {
                    badge.classList.add("hidden");
                }
            }

            currentPage = 1;
            renderPaginatedTable();
        }

        function resetFilters() {
            const gradeSelect = document.getElementById("filter-grade");
            const ageSelect = document.getElementById("filter-age");
            if (gradeSelect) gradeSelect.value = "";
            if (ageSelect) ageSelect.value = "";
            applyFilters();
        }

        // --- PAGINATION & TABLE RENDERING ---
        function changePageSize(size) {
            pageSize = parseInt(size, 10) || 10;
            currentPage = 1;
            renderPaginatedTable();
        }

        function goToPage(page) {
            currentPage = page;
            renderPaginatedTable();
        }

        function renderPaginatedTable() {
            const tbody = document.getElementById("student-table-body");
            const emptyState = document.getElementById("empty-state");
            const countBadge = document.getElementById("table-total-count");
            const summary = document.getElementById("pagination-summary");
            const controls = document.getElementById("pagination-controls");

            const total = filteredStudents.length;
            if (countBadge) countBadge.innerText = total;

            if (total === 0) {
                tbody.innerHTML = "";
                emptyState.classList.remove("hidden");
                if (summary) summary.innerText = "Showing 0 to 0 of 0 students";
                if (controls) controls.innerHTML = "";
                return;
            }

            emptyState.classList.add("hidden");

            const totalPages = Math.ceil(total / pageSize);
            if (currentPage > totalPages) currentPage = totalPages;
            if (currentPage < 1) currentPage = 1;

            const startIndex = (currentPage - 1) * pageSize;
            const endIndex = Math.min(startIndex + pageSize, total);
            const pageStudents = filteredStudents.slice(startIndex, endIndex);

            if (summary) {
                summary.innerText = `Showing ${startIndex + 1}–${endIndex} of ${total} students`;
            }

            // Render Table Rows
            tbody.innerHTML = "";
            const currentSearch = (document.getElementById("search-input")?.value || "").trim();
            pageStudents.forEach(student => {
                const tr = document.createElement("tr");
                tr.className = "hover:bg-slate-50/70 transition-colors group";
                
                const safeId = escapeHtml(student.id || '');
                const safeName = escapeHtml(student.name || '');
                const safeGrade = escapeHtml(student.grade || '');
                const safeEmail = escapeHtml(student.email || '');
                const age = student.age || 0;
                const initials = getInitials(student.name || 'S');
                const avatarColor = getAvatarColor(student.name || 'S');
                const highlightedName = highlightText(student.name || '', currentSearch);
                const highlightedId = highlightText(student.id || '', currentSearch);

                tr.innerHTML = `
                    <!-- Student Identity Cell -->
                    <td class="px-6 py-3.5 whitespace-nowrap">
                        <div class="flex items-center space-x-3">
                            <div class="w-8 h-8 rounded-xl ${avatarColor} text-white flex items-center justify-center font-bold text-xs shadow-2xs flex-shrink-0">
                                ${initials}
                            </div>
                            <div class="min-w-0">
                                <span class="text-xs font-semibold text-slate-900 block truncate cursor-pointer hover:text-indigo-600" onclick="viewStudentProfile('${safeId}')">${highlightedName}</span>
                                <span class="font-mono text-[10px] text-slate-400 block truncate">${highlightedId}</span>
                            </div>
                        </div>
                    </td>

                    <!-- Student ID Monospace Badge -->
                    <td class="px-6 py-3.5 whitespace-nowrap">
                        <span class="inline-flex items-center px-2 py-0.5 rounded-md text-xs font-mono font-medium bg-slate-100 text-slate-700 border border-slate-200/60">
                            ${highlightedId}
                        </span>
                    </td>

                    <!-- Age -->
                    <td class="px-6 py-3.5 whitespace-nowrap text-xs text-slate-600 font-medium">
                        ${age} yrs
                    </td>

                    <!-- Grade / Semester Badge -->
                    <td class="px-6 py-3.5 whitespace-nowrap">
                        <span class="inline-flex items-center px-2.5 py-0.5 rounded-lg text-[11px] font-semibold bg-indigo-50 text-indigo-700 border border-indigo-100">
                            ${highlightText(student.grade || '', currentSearch)}
                        </span>
                    </td>

                    <!-- Email Address -->
                    <td class="px-6 py-3.5 whitespace-nowrap text-xs text-slate-500 font-mono">
                        ${safeEmail ? `
                            <div class="flex items-center space-x-1.5">
                                <a href="mailto:${safeEmail}" class="hover:text-indigo-600 truncate max-w-[180px]">${highlightText(student.email || '', currentSearch)}</a>
                                <button onclick="copyToClipboard('${safeEmail}')" title="Copy email" class="opacity-0 group-hover:opacity-100 text-slate-400 hover:text-slate-600 p-0.5 rounded transition-opacity">
                                    <svg class="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"/>
                                    </svg>
                                </button>
                            </div>
                        ` : '<span class="text-slate-300 italic">None</span>'}
                    </td>

                    <!-- Status Badge -->
                    <td class="px-6 py-3.5 whitespace-nowrap">
                        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200/60">
                            <span class="w-1.5 h-1.5 rounded-full bg-emerald-500 mr-1.5"></span>
                            Active
                        </span>
                    </td>

                    <!-- Compact 3-Dot Action Menu -->
                    <td class="px-6 py-3.5 whitespace-nowrap text-right text-xs font-medium relative action-menu-container">
                        <button onclick="toggleActionMenu('${safeId}', event)" class="p-1 rounded-lg text-slate-400 hover:text-slate-700 hover:bg-slate-100 transition-colors">
                            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 5v.01M12 12v.01M12 19v.01M12 6a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2zm0 7a1 1 0 110-2 1 1 0 010 2z"/>
                            </svg>
                        </button>

                        <!-- Action Dropdown Popover -->
                        <div id="action-menu-${safeId}" class="hidden absolute right-6 mt-1 w-36 bg-white rounded-xl shadow-xl border border-slate-200/90 py-1 z-30 text-left">
                            <button onclick="viewStudentProfile('${safeId}')" class="w-full px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50 flex items-center space-x-2">
                                <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                                </svg>
                                <span>View profile</span>
                            </button>
                            <button onclick="editStudent('${safeId}')" class="w-full px-3 py-1.5 text-xs text-slate-700 hover:bg-slate-50 flex items-center space-x-2">
                                <svg class="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z"/>
                                </svg>
                                <span>Edit student</span>
                            </button>
                            <div class="border-t border-slate-100 my-1"></div>
                            <button onclick="promptDelete('${safeId}', '${safeName}')" class="w-full px-3 py-1.5 text-xs text-rose-600 hover:bg-rose-50 flex items-center space-x-2">
                                <svg class="w-3.5 h-3.5 text-rose-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                                </svg>
                                <span>Delete</span>
                            </button>
                        </div>
                    </td>
                `;
                tbody.appendChild(tr);
            });

            // Render Pagination Buttons
            if (controls) {
                let btnHtml = `
                    <button onclick="goToPage(${currentPage - 1})" ${currentPage === 1 ? 'disabled' : ''} class="px-2 py-1 rounded-lg border border-slate-200 text-xs font-medium text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed">
                        Previous
                    </button>
                `;

                for (let i = 1; i <= totalPages; i++) {
                    if (totalPages > 6 && (i > 3 && i < totalPages - 1 && Math.abs(i - currentPage) > 1)) {
                        if (i === 4 && currentPage > 4) btnHtml += `<span class="px-1 text-slate-400">...</span>`;
                        continue;
                    }
                    const isActive = i === currentPage;
                    btnHtml += `
                        <button onclick="goToPage(${i})" class="px-2.5 py-1 rounded-lg text-xs font-semibold ${isActive ? 'bg-indigo-600 text-white shadow-2xs' : 'border border-slate-200 text-slate-700 hover:bg-slate-100'}">
                            ${i}
                        </button>
                    `;
                }

                btnHtml += `
                    <button onclick="goToPage(${currentPage + 1})" ${currentPage === totalPages ? 'disabled' : ''} class="px-2 py-1 rounded-lg border border-slate-200 text-xs font-medium text-slate-600 hover:bg-slate-100 disabled:opacity-40 disabled:cursor-not-allowed">
                        Next
                    </button>
                `;
                controls.innerHTML = btnHtml;
            }
        }

        // --- ATTENDANCE & NAVIGATION STATE ---
        let currentAttendanceDate = new Date().toISOString().slice(0, 10);
        let currentAttendanceGrade = 'all';
        let attendanceData = { summary: {}, records: [] };
        let hasUnsavedAttendance = false;
        let activeAttSubTab = 'daily';
        let activeView = 'dashboard';

        // --- ACTION MENUS & NAVIGATION ---
        function toggleActionMenu(id, event) {
            event.stopPropagation();
            const targetMenu = document.getElementById(`action-menu-${id}`);
            const wasOpen = targetMenu && !targetMenu.classList.contains("hidden");
            closeAllDropdowns();
            if (targetMenu && !wasOpen) {
                targetMenu.classList.remove("hidden");
                openActionMenuId = id;
            }
        }

        function closeAllDropdowns() {
            document.querySelectorAll("[id^='action-menu-']").forEach(menu => {
                menu.classList.add("hidden");
            });
            openActionMenuId = null;
        }

        function toggleMobileSidebar() {
            const sidebar = document.getElementById("app-sidebar");
            const backdrop = document.getElementById("mobile-sidebar-backdrop");
            if (sidebar && backdrop) {
                sidebar.classList.toggle("-translate-x-full");
                backdrop.classList.toggle("hidden");
            }
        }

        function switchNav(section) {
            if (activeView === 'attendance' && section !== 'attendance' && hasUnsavedAttendance) {
                const leave = confirm("You have unsaved attendance changes. Leave without saving?");
                if (!leave) return;
                hasUnsavedAttendance = false;
                const unsavedBadge = document.getElementById("att-unsaved-badge");
                if (unsavedBadge) unsavedBadge.classList.add("hidden");
            }

            activeView = section;
            document.querySelectorAll(".sidebar-nav-item").forEach(item => item.classList.remove("active"));
            
            const navId = section === 'students' ? 'nav-students' : `nav-${section}`;
            const activeItem = document.getElementById(navId);
            if (activeItem) activeItem.classList.add("active");

            // Hide all view containers
            const views = ["view-dashboard", "view-attendance", "view-classes", "view-reports"];
            views.forEach(v => {
                const el = document.getElementById(v);
                if (el) el.classList.add("hidden");
            });

            const breadcrumb = document.getElementById("breadcrumb-current");

            if (section === 'attendance') {
                const attView = document.getElementById("view-attendance");
                if (attView) attView.classList.remove("hidden");
                if (breadcrumb) breadcrumb.innerText = "Attendance";
                initAttendanceView();
            } else if (section === 'classes') {
                const clsView = document.getElementById("view-classes");
                if (clsView) clsView.classList.remove("hidden");
                if (breadcrumb) breadcrumb.innerText = "Classes & Cohorts";
                loadClassesView();
            } else if (section === 'reports') {
                const repView = document.getElementById("view-reports");
                if (repView) repView.classList.remove("hidden");
                if (breadcrumb) breadcrumb.innerText = "Reports & Export";
            } else {
                // Dashboard or Students Directory
                const dashView = document.getElementById("view-dashboard");
                if (dashView) dashView.classList.remove("hidden");
                if (breadcrumb) breadcrumb.innerText = section === 'students' ? "Students Directory" : "Dashboard";
                
                if (section === 'students') {
                    const studentSection = document.getElementById("student-directory-section");
                    if (studentSection) studentSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
                }
            }

            if (window.innerWidth < 768) toggleMobileSidebar();
        }

        function showSectionToast(name) {
            showToast(`${name}`, "info");
        }

        // --- ATTENDANCE MANAGEMENT SYSTEM ---
        function initAttendanceView() {
            populateAttendanceClassOptions();
            const dateInput = document.getElementById("att-date-select");
            if (dateInput) dateInput.value = currentAttendanceDate;

            fetchAttendance();
            fetchAttendanceAnalytics();
        }

        function populateAttendanceClassOptions() {
            const classSelect = document.getElementById("att-class-select");
            if (!classSelect) return;

            const current = classSelect.value || currentAttendanceGrade;
            const uniqueGrades = Array.from(new Set(allStudents.map(s => (s.grade || '').trim()).filter(Boolean))).sort();

            let optionsHtml = `<option value="all">All Classes &amp; Cohorts</option>`;
            uniqueGrades.forEach(grade => {
                const isSel = grade === current ? 'selected' : '';
                optionsHtml += `<option value="${escapeHtml(grade)}" ${isSel}>${escapeHtml(grade)}</option>`;
            });
            classSelect.innerHTML = optionsHtml;
        }

        function handleAttendanceClassChange() {
            if (hasUnsavedAttendance) {
                const proceed = confirm("You have unsaved attendance changes. Discard and switch class?");
                if (!proceed) {
                    document.getElementById("att-class-select").value = currentAttendanceGrade;
                    return;
                }
            }
            currentAttendanceGrade = document.getElementById("att-class-select").value;
            fetchAttendance();
        }

        function handleAttendanceDateChange() {
            if (hasUnsavedAttendance) {
                const proceed = confirm("You have unsaved attendance changes. Discard and change date?");
                if (!proceed) {
                    document.getElementById("att-date-select").value = currentAttendanceDate;
                    return;
                }
            }
            currentAttendanceDate = document.getElementById("att-date-select").value || new Date().toISOString().slice(0, 10);
            fetchAttendance();
        }

        function setAttendanceToday() {
            const today = new Date().toISOString().slice(0, 10);
            if (currentAttendanceDate === today) return;
            document.getElementById("att-date-select").value = today;
            handleAttendanceDateChange();
        }

        function handleAttendanceSearch() {
            const query = (document.getElementById("att-search-input")?.value || "").trim().toLowerCase();
            const markAllBtnText = document.getElementById("mark-all-present-text");
            if (markAllBtnText) {
                markAllBtnText.innerText = query ? "Mark Visible Present" : "Mark All Present";
            }
            renderAttendanceTable();
        }

        function switchAttSubTab(tab) {
            activeAttSubTab = tab;
            const tabs = ["daily", "history", "analytics", "report"];
            tabs.forEach(t => {
                const btn = document.getElementById(`att-subtab-${t}`);
                const view = document.getElementById(`att-view-${t}`);
                if (btn && view) {
                    if (t === tab) {
                        btn.className = "px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-indigo-600 text-white shadow-2xs transition-colors flex items-center space-x-1.5";
                        view.classList.remove("hidden");
                    } else {
                        btn.className = "px-3.5 py-1.5 rounded-lg text-xs font-semibold text-slate-600 hover:bg-slate-100 transition-colors flex items-center space-x-1.5";
                        view.classList.add("hidden");
                    }
                }
            });

            if (tab === 'history') fetchAttendanceHistory();
            else if (tab === 'analytics') fetchAttendanceAnalytics();
            else if (tab === 'report') fetchAttendanceReport();
        }

        function fetchAttendance() {
            const query = (document.getElementById("att-search-input")?.value || "").trim();
            const tbody = document.getElementById("att-table-body");
            if (tbody) {
                tbody.innerHTML = `<tr><td colspan="6" class="px-6 py-8 text-center text-xs text-slate-400">Loading attendance sheet...</td></tr>`;
            }

            const url = `/api/attendance?date=${encodeURIComponent(currentAttendanceDate)}&grade=${encodeURIComponent(currentAttendanceGrade)}&search=${encodeURIComponent(query)}`;
            
            fetch(url)
                .then(res => {
                    if (!res.ok) throw new Error("Failed to load attendance");
                    return res.json();
                })
                .then(data => {
                    attendanceData = data;
                    hasUnsavedAttendance = false;
                    const unsavedBadge = document.getElementById("att-unsaved-badge");
                    if (unsavedBadge) unsavedBadge.classList.add("hidden");

                    renderAttendanceTable();
                    recalculateAttendanceSummary();
                })
                .catch(err => {
                    console.error("Attendance fetch error:", err);
                    showToast("Error loading attendance records.", "error");
                });
        }

        function renderAttendanceTable() {
            const tbody = document.getElementById("att-table-body");
            const emptyState = document.getElementById("att-empty-state");
            const badge = document.getElementById("att-table-badge");
            const dateDisplay = document.getElementById("att-date-display");

            if (!tbody || !attendanceData || !attendanceData.records) return;

            const searchQuery = (document.getElementById("att-search-input")?.value || "").trim().toLowerCase();
            const records = attendanceData.records.filter(r => {
                if (!searchQuery) return true;
                return (r.student_id || '').toLowerCase().includes(searchQuery) ||
                       (r.name || '').toLowerCase().includes(searchQuery) ||
                       (r.email || '').toLowerCase().includes(searchQuery);
            });

            if (badge) badge.innerText = `${records.length} Student${records.length === 1 ? '' : 's'}`;
            if (dateDisplay) {
                const dateObj = new Date(currentAttendanceDate + 'T00:00:00');
                const formattedDate = dateObj.toLocaleDateString('en-US', { day: 'numeric', month: 'short', year: 'numeric' });
                dateDisplay.innerText = `Class: ${currentAttendanceGrade === 'all' ? 'All Classes' : currentAttendanceGrade} • Date: ${formattedDate}`;
            }

            if (records.length === 0) {
                tbody.innerHTML = "";
                if (emptyState) emptyState.classList.remove("hidden");
                return;
            }

            if (emptyState) emptyState.classList.add("hidden");

            tbody.innerHTML = "";
            records.forEach(student => {
                const safeId = escapeHtml(student.student_id);
                const safeName = escapeHtml(student.name);
                const safeGrade = escapeHtml(student.grade || 'Unassigned');
                const initials = getInitials(student.name);
                const avatarColor = getAvatarColor(student.name);

                const status = student.status; // 'present', 'absent', or null
                const isPresent = status === 'present';
                const isAbsent = status === 'absent';

                // Lifetime rate color
                const rate = student.lifetime_rate !== undefined ? student.lifetime_rate : 100.0;
                const rateColor = rate >= 75 ? 'text-emerald-600 bg-emerald-50 border-emerald-200' : 'text-rose-600 bg-rose-50 border-rose-200';
                const barColor = rate >= 75 ? 'bg-emerald-500' : 'bg-rose-500';

                const tr = document.createElement("tr");
                tr.className = "hover:bg-slate-50/70 transition-colors";
                tr.id = `att-row-${safeId}`;

                tr.innerHTML = `
                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="flex items-center space-x-3">
                            <div class="w-9 h-9 rounded-xl ${avatarColor} text-white flex items-center justify-center font-bold text-xs shadow-2xs flex-shrink-0">
                                ${initials}
                            </div>
                            <div class="min-w-0">
                                <p class="text-xs font-bold text-slate-900 truncate">${safeName}</p>
                                <span class="inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-semibold bg-indigo-50 text-indigo-700 mt-0.5">${safeGrade}</span>
                            </div>
                        </div>
                    </td>

                    <td class="px-6 py-4 whitespace-nowrap">
                        <span class="font-mono text-xs font-medium text-slate-700 bg-slate-100 px-2 py-1 rounded-lg border border-slate-200/80">${safeId}</span>
                    </td>

                    <td class="px-6 py-4 whitespace-nowrap text-center">
                        <div class="inline-flex items-center p-1 bg-slate-100 rounded-xl border border-slate-200/80 space-x-1" role="group">
                            <button type="button" onclick="setStudentAttendance('${safeId}', 'present')" id="btn-present-${safeId}"
                                    class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 ${isPresent ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-600 hover:text-emerald-700 hover:bg-white/80'}">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                                </svg>
                                <span>Present</span>
                            </button>

                            <button type="button" onclick="setStudentAttendance('${safeId}', 'absent')" id="btn-absent-${safeId}"
                                    class="px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 ${isAbsent ? 'bg-rose-600 text-white shadow-sm' : 'text-slate-600 hover:text-rose-700 hover:bg-white/80'}">
                                <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                                </svg>
                                <span>Absent</span>
                            </button>
                        </div>
                    </td>

                    <td class="px-6 py-4 whitespace-nowrap">
                        <div class="space-y-1">
                            <div class="flex items-center space-x-1.5">
                                <span class="px-2 py-0.5 text-xs font-bold rounded-md border ${rateColor}">${rate}%</span>
                                <span class="text-[10px] text-slate-400">(${student.lifetime_present || 0}/${student.lifetime_total || 0})</span>
                            </div>
                            <div class="w-24 bg-slate-100 rounded-full h-1.5 overflow-hidden">
                                <div class="${barColor} h-1.5 rounded-full" style="width: ${rate}%"></div>
                            </div>
                        </div>
                    </td>

                    <td class="px-6 py-4 whitespace-nowrap">
                        <input type="text" value="${escapeHtml(student.notes || '')}" onchange="updateStudentNote('${safeId}', this.value)" placeholder="Add note / reason..."
                               class="w-full max-w-[200px] text-xs px-2.5 py-1 bg-slate-50 hover:bg-white focus:bg-white border border-slate-200 rounded-lg text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-1 focus:ring-indigo-500">
                    </td>

                    <td class="px-6 py-4 whitespace-nowrap text-right text-xs">
                        <button type="button" onclick="viewStudentProfile('${safeId}')" class="px-2.5 py-1 text-slate-600 hover:text-indigo-600 hover:bg-indigo-50 rounded-lg font-medium transition-colors inline-flex items-center space-x-1">
                            <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                            </svg>
                            <span>Profile</span>
                        </button>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        }

        function setStudentAttendance(studentId, status) {
            const student = attendanceData.records.find(s => String(s.student_id) === String(studentId));
            if (!student) return;

            student.status = status;
            hasUnsavedAttendance = true;
            
            const unsavedBadge = document.getElementById("att-unsaved-badge");
            if (unsavedBadge) unsavedBadge.classList.remove("hidden");

            // Update row buttons instantly
            const btnPresent = document.getElementById(`btn-present-${studentId}`);
            const btnAbsent = document.getElementById(`btn-absent-${studentId}`);

            if (btnPresent && btnAbsent) {
                if (status === 'present') {
                    btnPresent.className = "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 bg-emerald-600 text-white shadow-sm";
                    btnAbsent.className = "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 text-slate-600 hover:text-rose-700 hover:bg-white/80";
                } else if (status === 'absent') {
                    btnPresent.className = "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 text-slate-600 hover:text-emerald-700 hover:bg-white/80";
                    btnAbsent.className = "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 bg-rose-600 text-white shadow-sm";
                }
            }

            recalculateAttendanceSummary();
        }

        function markAllAttendance(status) {
            const searchQuery = (document.getElementById("att-search-input")?.value || "").trim().toLowerCase();
            const targetStudents = attendanceData.records.filter(r => {
                if (!searchQuery) return true;
                return (r.student_id || '').toLowerCase().includes(searchQuery) ||
                       (r.name || '').toLowerCase().includes(searchQuery) ||
                       (r.email || '').toLowerCase().includes(searchQuery);
            });

            if (targetStudents.length === 0) return;

            targetStudents.forEach(s => {
                s.status = status;
                const btnPresent = document.getElementById(`btn-present-${s.student_id}`);
                const btnAbsent = document.getElementById(`btn-absent-${s.student_id}`);
                if (btnPresent && btnAbsent) {
                    if (status === 'present') {
                        btnPresent.className = "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 bg-emerald-600 text-white shadow-sm";
                        btnAbsent.className = "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 text-slate-600 hover:text-rose-700 hover:bg-white/80";
                    } else {
                        btnPresent.className = "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 text-slate-600 hover:text-emerald-700 hover:bg-white/80";
                        btnAbsent.className = "px-3 py-1.5 rounded-lg text-xs font-semibold transition-all flex items-center space-x-1 bg-rose-600 text-white shadow-sm";
                    }
                }
            });

            hasUnsavedAttendance = true;
            const unsavedBadge = document.getElementById("att-unsaved-badge");
            if (unsavedBadge) unsavedBadge.classList.remove("hidden");

            recalculateAttendanceSummary();
            showToast(`Marked ${targetStudents.length} student(s) as ${status.toUpperCase()}. Click Save to persist.`, "info");
        }

        function updateStudentNote(studentId, note) {
            const student = attendanceData.records.find(s => String(s.student_id) === String(studentId));
            if (student) {
                student.notes = note;
                hasUnsavedAttendance = true;
                const unsavedBadge = document.getElementById("att-unsaved-badge");
                if (unsavedBadge) unsavedBadge.classList.remove("hidden");
            }
        }

        function recalculateAttendanceSummary() {
            if (!attendanceData || !attendanceData.records) return;

            const total = attendanceData.records.length;
            const present = attendanceData.records.filter(r => r.status === 'present').length;
            const absent = attendanceData.records.filter(r => r.status === 'absent').length;
            const markedTotal = present + absent;
            const rate = markedTotal > 0 ? (present / markedTotal * 100.0).toFixed(1) : (present > 0 ? '100.0' : '0.0');

            document.getElementById("att-summary-total").innerText = total;
            document.getElementById("att-summary-present").innerText = present;
            document.getElementById("att-summary-absent").innerText = absent;
            document.getElementById("att-summary-rate").innerText = `${rate}%`;

            const progress = document.getElementById("att-summary-progress");
            if (progress) progress.style.width = `${rate}%`;
        }

        function resetCurrentAttendance() {
            fetchAttendance();
            showToast("Attendance reset to saved state.", "info");
        }

        function saveAttendance() {
            if (!attendanceData || !attendanceData.records || attendanceData.records.length === 0) {
                showToast("No student records to save.", "error");
                return;
            }

            const payloadAttendance = attendanceData.records
                .filter(r => r.status === 'present' || r.status === 'absent')
                .map(r => ({
                    student_id: r.student_id,
                    status: r.status,
                    notes: r.notes || '',
                    grade: r.grade || currentAttendanceGrade
                }));

            if (payloadAttendance.length === 0) {
                showToast("Please mark at least one student Present or Absent before saving.", "error");
                return;
            }

            const saveBtn = document.getElementById("save-attendance-btn");
            const spinner = document.getElementById("save-att-spinner");
            const btnText = document.getElementById("save-att-btn-text");

            if (saveBtn) saveBtn.disabled = true;
            if (spinner) spinner.classList.remove("hidden");
            if (btnText) btnText.innerText = "Saving...";

            fetch('/api/attendance/bulk', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    date: currentAttendanceDate,
                    grade: currentAttendanceGrade,
                    attendance: payloadAttendance
                })
            })
            .then(async res => {
                const data = await res.json();
                if (!res.ok) throw new Error(data.error || "Unable to save attendance.");
                return data;
            })
            .then(data => {
                hasUnsavedAttendance = false;
                const unsavedBadge = document.getElementById("att-unsaved-badge");
                if (unsavedBadge) unsavedBadge.classList.add("hidden");

                if (btnText) btnText.innerText = "✓ Saved";
                showToast("Attendance saved successfully!", "success");

                // Re-fetch fresh lifetime rates and history
                setTimeout(() => {
                    if (btnText) btnText.innerText = "Save Attendance";
                    fetchAttendance();
                    fetchAttendanceAnalytics();
                }, 1000);
            })
            .catch(err => {
                console.error("Save attendance error:", err);
                showToast("Unable to save attendance. Please try again.", "error");
                if (btnText) btnText.innerText = "Save Attendance";
            })
            .finally(() => {
                if (saveBtn) saveBtn.disabled = false;
                if (spinner) spinner.classList.add("hidden");
            });
        }

        // --- ATTENDANCE HISTORY & ANALYTICS ---
        function fetchAttendanceHistory() {
            const tbody = document.getElementById("att-history-tbody");
            if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="px-6 py-6 text-center text-xs text-slate-400">Loading history logs...</td></tr>`;

            fetch(`/api/attendance/history?grade=${encodeURIComponent(currentAttendanceGrade)}`)
                .then(res => res.json())
                .then(history => {
                    if (!tbody) return;
                    if (history.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="7" class="px-6 py-8 text-center text-xs text-slate-400 italic">No attendance records found yet. Mark and save attendance to build history.</td></tr>`;
                        return;
                    }

                    tbody.innerHTML = "";
                    history.forEach(item => {
                        const tr = document.createElement("tr");
                        tr.className = "hover:bg-slate-50/70 transition-colors";
                        const rateColor = item.attendance_rate >= 75 ? 'text-emerald-600 bg-emerald-50' : 'text-rose-600 bg-rose-50';

                        tr.innerHTML = `
                            <td class="px-6 py-4 whitespace-nowrap text-xs font-bold text-slate-900">${escapeHtml(item.attendance_date)}</td>
                            <td class="px-6 py-4 whitespace-nowrap"><span class="px-2 py-0.5 text-xs font-semibold rounded bg-indigo-50 text-indigo-700">${escapeHtml(item.class_id || 'All')}</span></td>
                            <td class="px-6 py-4 whitespace-nowrap text-center text-xs font-semibold text-slate-700">${item.total_students}</td>
                            <td class="px-6 py-4 whitespace-nowrap text-center text-xs font-bold text-emerald-600">${item.present_count}</td>
                            <td class="px-6 py-4 whitespace-nowrap text-center text-xs font-bold text-rose-600">${item.absent_count}</td>
                            <td class="px-6 py-4 whitespace-nowrap"><span class="px-2 py-0.5 text-xs font-bold rounded ${rateColor}">${item.attendance_rate}%</span></td>
                            <td class="px-6 py-4 whitespace-nowrap text-right">
                                <button onclick="openHistoricalAttendance('${escapeHtml(item.attendance_date)}', '${escapeHtml(item.class_id)}')" class="px-3 py-1 bg-indigo-50 hover:bg-indigo-100 text-indigo-700 text-xs font-semibold rounded-lg transition-colors">
                                    Open &amp; Edit
                                </button>
                            </td>
                        `;
                        tbody.appendChild(tr);
                    });
                })
                .catch(err => {
                    console.error("History fetch error:", err);
                    if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="px-6 py-6 text-center text-xs text-rose-500">Failed to load history logs.</td></tr>`;
                });
        }

        function openHistoricalAttendance(dateStr, classId) {
            currentAttendanceDate = dateStr;
            currentAttendanceGrade = classId || 'all';

            const dateInput = document.getElementById("att-date-select");
            const classSelect = document.getElementById("att-class-select");
            if (dateInput) dateInput.value = dateStr;
            if (classSelect) classSelect.value = currentAttendanceGrade;

            switchAttSubTab('daily');
            fetchAttendance();
            showToast(`Opened attendance session for ${dateStr} (${classId})`, "info");
        }

        function fetchAttendanceAnalytics() {
            fetch(`/api/attendance/analytics?grade=${encodeURIComponent(currentAttendanceGrade)}`)
                .then(res => res.json())
                .then(data => {
                    // Update stat badge
                    const statAtt = document.getElementById("stat-attendance");
                    const sidebarRate = document.getElementById("sidebar-att-rate");
                    
                    if (data.total_sessions > 0 && data.overall_rate !== null && data.overall_rate !== undefined) {
                        const rateText = `${data.overall_rate}%`;
                        if (statAtt) statAtt.innerText = rateText;
                        if (sidebarRate) {
                            sidebarRate.innerText = rateText;
                            sidebarRate.className = "text-[10px] px-1.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 font-semibold";
                        }
                    } else {
                        if (statAtt) statAtt.innerText = "No data";
                        if (sidebarRate) {
                            sidebarRate.innerText = "—";
                            sidebarRate.className = "text-[10px] px-1.5 py-0.5 rounded-full bg-slate-100 text-slate-600 font-semibold";
                        }
                    }

                    // Health metrics in Analytics tab
                    const hOverall = document.getElementById("att-health-overall");
                    const hSessions = document.getElementById("att-health-sessions");
                    const hPresent = document.getElementById("att-health-present");
                    const hAbsent = document.getElementById("att-health-absent");
                    if (hOverall) hOverall.innerText = data.total_sessions > 0 && data.overall_rate !== null ? `${data.overall_rate}%` : "—";
                    if (hSessions) hSessions.innerText = data.total_sessions || 0;
                    if (hPresent) hPresent.innerText = data.present_total || 0;
                    if (hAbsent) hAbsent.innerText = data.absent_total || 0;

                    // Low attendance watchlist
                    const listContainer = document.getElementById("low-att-list");
                    const countBadge = document.getElementById("low-att-count-badge");
                    if (countBadge) countBadge.innerText = `${(data.low_attendance_students || []).length} Students`;

                    if (listContainer) {
                        if (data.low_attendance_students.length === 0) {
                            listContainer.innerHTML = `<p class="text-xs text-slate-400 text-center py-6 italic">No students currently below the 75% attendance threshold! 🎉</p>`;
                        } else {
                            listContainer.innerHTML = "";
                            data.low_attendance_students.forEach(s => {
                                const card = document.createElement("div");
                                card.className = "p-3 rounded-xl bg-rose-50/50 border border-rose-100 flex items-center justify-between";
                                card.innerHTML = `
                                    <div class="flex items-center space-x-3">
                                        <div class="w-8 h-8 rounded-lg bg-rose-600 text-white font-bold text-xs flex items-center justify-center">
                                            ${getInitials(s.name)}
                                        </div>
                                        <div>
                                            <p class="text-xs font-bold text-slate-900">${escapeHtml(s.name)} <span class="font-mono text-[10px] text-slate-400">(${escapeHtml(s.id)})</span></p>
                                            <p class="text-[10px] text-slate-500">${escapeHtml(s.grade)} • ${s.present} Present / ${s.total_classes} Classes</p>
                                        </div>
                                    </div>
                                    <div class="flex items-center space-x-3">
                                        <span class="px-2 py-0.5 text-xs font-extrabold rounded-md bg-rose-200 text-rose-800">${s.rate}%</span>
                                        <button onclick="viewStudentProfile('${escapeHtml(s.id)}')" class="px-2.5 py-1 bg-white border border-rose-200 text-rose-700 hover:bg-rose-100 rounded-lg text-xs font-medium transition-colors">
                                            View
                                        </button>
                                    </div>
                                `;
                                listContainer.appendChild(card);
                            });
                        }
                    }
                })
                .catch(err => console.error("Analytics fetch error:", err));
        }

        function fetchAttendanceReport() {
            const tbody = document.getElementById("att-report-tbody");
            if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="px-6 py-6 text-center text-xs text-slate-400">Loading aggregate report...</td></tr>`;

            fetch(`/api/attendance/report?grade=${encodeURIComponent(currentAttendanceGrade)}`)
                .then(res => res.json())
                .then(report => {
                    if (!tbody) return;
                    if (report.length === 0) {
                        tbody.innerHTML = `<tr><td colspan="7" class="px-6 py-6 text-center text-xs text-slate-400">No report data found.</td></tr>`;
                        return;
                    }

                    tbody.innerHTML = "";
                    report.forEach(r => {
                        const tr = document.createElement("tr");
                        tr.className = "hover:bg-slate-50/70 transition-colors";
                        const rateColor = r.rate >= 75 ? 'text-emerald-700 bg-emerald-50 border-emerald-200' : 'text-rose-700 bg-rose-50 border-rose-200';

                        tr.innerHTML = `
                            <td class="px-6 py-4 whitespace-nowrap text-xs font-bold text-slate-900">${escapeHtml(r.name)}</td>
                            <td class="px-6 py-4 whitespace-nowrap"><span class="font-mono text-xs text-slate-600 bg-slate-100 px-2 py-0.5 rounded">${escapeHtml(r.id)}</span></td>
                            <td class="px-6 py-4 whitespace-nowrap text-xs text-slate-600">${escapeHtml(r.grade || 'N/A')}</td>
                            <td class="px-6 py-4 whitespace-nowrap text-center text-xs font-semibold text-slate-800">${r.total_classes}</td>
                            <td class="px-6 py-4 whitespace-nowrap text-center text-xs font-bold text-emerald-600">${r.present}</td>
                            <td class="px-6 py-4 whitespace-nowrap text-center text-xs font-bold text-rose-600">${r.absent}</td>
                            <td class="px-6 py-4 whitespace-nowrap"><span class="px-2 py-0.5 text-xs font-bold rounded border ${rateColor}">${r.rate}%</span></td>
                        `;
                        tbody.appendChild(tr);
                    });
                })
                .catch(err => {
                    console.error("Report fetch error:", err);
                    if (tbody) tbody.innerHTML = `<tr><td colspan="7" class="px-6 py-6 text-center text-xs text-rose-500">Failed to load report data.</td></tr>`;
                });
        }

        function exportAttendanceReportCSV() {
            fetch(`/api/attendance/report?grade=${encodeURIComponent(currentAttendanceGrade)}`)
                .then(res => res.json())
                .then(data => {
                    if (!data || data.length === 0) {
                        showToast("No attendance data to export.", "error");
                        return;
                    }

                    let csvContent = "data:text/csv;charset=utf-8,Student ID,Full Name,Grade/Semester,Email Address,Total Classes,Present Classes,Absent Classes,Attendance Rate (%)\\n";
                    data.forEach(s => {
                        const row = [
                            `"${(s.id || '').replace(/"/g, '""')}"`,
                            `"${(s.name || '').replace(/"/g, '""')}"`,
                            `"${(s.grade || '').replace(/"/g, '""')}"`,
                            `"${(s.email || '').replace(/"/g, '""')}"`,
                            s.total_classes || 0,
                            s.present || 0,
                            s.absent || 0,
                            `${s.rate || 0}%`
                        ].join(",");
                        csvContent += row + "\\n";
                    });

                    const encodedUri = encodeURI(csvContent);
                    const link = document.createElement("a");
                    link.setAttribute("href", encodedUri);
                    link.setAttribute("download", `attendance_audit_report_${new Date().toISOString().slice(0, 10)}.csv`);
                    document.body.appendChild(link);
                    link.click();
                    document.body.removeChild(link);
                    showToast(`Exported attendance audit report (${data.length} students) to CSV!`, "success");
                })
                .catch(err => {
                    console.error("Export error:", err);
                    showToast("Failed to generate CSV export.", "error");
                });
        }

        function loadClassesView() {
            const grid = document.getElementById("classes-grid");
            if (!grid) return;

            fetch('/api/classes')
                .then(res => res.json())
                .then(classes => {
                    if (classes.length === 0) {
                        grid.innerHTML = `<p class="col-span-3 text-xs text-slate-400 text-center py-8">No class cohorts found in database.</p>`;
                        return;
                    }

                    grid.innerHTML = "";
                    classes.forEach(c => {
                        const card = document.createElement("div");
                        card.className = "p-5 rounded-2xl border border-slate-200 bg-white hover:shadow-sm transition-all space-y-3";
                        card.innerHTML = `
                            <div class="flex items-center justify-between">
                                <div class="w-10 h-10 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center font-bold text-sm">
                                    ${escapeHtml(c.grade.slice(0, 2))}
                                </div>
                                <span class="px-2 py-0.5 text-xs font-semibold rounded-full bg-indigo-50 text-indigo-700">${c.student_count} Students</span>
                            </div>
                            <div>
                                <h3 class="text-sm font-bold text-slate-900">${escapeHtml(c.grade)}</h3>
                                <p class="text-xs text-slate-400 mt-0.5">Active Academic Cohort</p>
                            </div>
                            <div class="pt-2 flex items-center justify-between border-t border-slate-100">
                                <button onclick="openClassAttendance('${escapeHtml(c.grade)}')" class="text-xs font-semibold text-indigo-600 hover:text-indigo-800 flex items-center space-x-1">
                                    <span>Take Attendance</span>
                                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7"/>
                                    </svg>
                                </button>
                            </div>
                        `;
                        grid.appendChild(card);
                    });
                })
                .catch(err => console.error("Classes load error:", err));
        }

        function openClassAttendance(grade) {
            currentAttendanceGrade = grade;
            switchNav('attendance');
        }

        // --- ENHANCED STUDENT PROFILE SLIDE-OVER DRAWER ---
        function viewStudentProfile(id) {
            closeAllDropdowns();
            const student = allStudents.find(s => String(s.id) === String(id));
            if (!student) return;

            document.getElementById("drawer-name").innerText = student.name;
            document.getElementById("drawer-id").innerText = student.id;
            document.getElementById("drawer-age").innerText = `${student.age || 0} yrs`;
            document.getElementById("drawer-grade").innerText = student.grade || 'Unassigned';
            
            const emailLink = document.getElementById("drawer-email-link");
            if (student.email) {
                emailLink.innerText = student.email;
                emailLink.href = `mailto:${student.email}`;
            } else {
                emailLink.innerText = "No email provided";
                emailLink.removeAttribute("href");
            }

            const avatar = document.getElementById("drawer-avatar");
            avatar.innerText = getInitials(student.name);
            avatar.className = `w-16 h-16 rounded-2xl ${getAvatarColor(student.name)} text-white flex items-center justify-center font-bold text-xl shadow-md`;

            document.getElementById("drawer-edit-btn").onclick = () => {
                closeProfileDrawer();
                editStudent(student.id);
            };
            document.getElementById("drawer-delete-btn").onclick = () => {
                closeProfileDrawer();
                promptDelete(student.id, student.name);
            };

            // Fetch Real Attendance Analytics for this student
            const historyList = document.getElementById("drawer-att-history-list");
            const badge = document.getElementById("drawer-att-badge");
            const totalEl = document.getElementById("drawer-att-total");
            const presEl = document.getElementById("drawer-att-present");
            const absEl = document.getElementById("drawer-att-absent");
            const standingEl = document.getElementById("drawer-standing");

            if (historyList) historyList.innerHTML = `<p class="text-slate-400 italic text-[11px] py-1 text-center">Loading logs...</p>`;

            fetch(`/api/attendance/student/${encodeURIComponent(id)}`)
                .then(res => res.json())
                .then(data => {
                    if (badge) {
                        badge.innerText = `${data.stats.rate}%`;
                        badge.className = data.stats.rate >= 75 ? 'px-2 py-0.5 text-[10px] font-bold rounded-full bg-emerald-100 text-emerald-800' : 'px-2 py-0.5 text-[10px] font-bold rounded-full bg-rose-100 text-rose-800';
                    }
                    if (totalEl) totalEl.innerText = data.stats.total_classes;
                    if (presEl) presEl.innerText = data.stats.present;
                    if (absEl) absEl.innerText = data.stats.absent;

                    if (standingEl) {
                        standingEl.innerText = data.stats.rate >= 75 ? "Good Academic Standing" : "Attendance Warning";
                        standingEl.className = data.stats.rate >= 75 ? "font-semibold text-emerald-600" : "font-semibold text-rose-600";
                    }

                    if (historyList) {
                        if (data.history.length === 0) {
                            historyList.innerHTML = `<p class="text-slate-400 italic text-[11px] py-2 text-center">No attendance records logged yet.</p>`;
                        } else {
                            historyList.innerHTML = "";
                            data.history.forEach(h => {
                                const row = document.createElement("div");
                                row.className = "flex items-center justify-between p-2 rounded-lg bg-slate-50 border border-slate-100";
                                const isPres = h.status === 'present';
                                row.innerHTML = `
                                    <div class="min-w-0">
                                        <p class="font-medium text-slate-800 truncate">${escapeHtml(h.attendance_date)}</p>
                                        <p class="text-[10px] text-slate-400">${escapeHtml(h.class_id || '')} ${h.notes ? '• ' + escapeHtml(h.notes) : ''}</p>
                                    </div>
                                    <span class="px-2 py-0.5 text-[10px] font-bold rounded ${isPres ? 'bg-emerald-100 text-emerald-800' : 'bg-rose-100 text-rose-800'}">
                                        ${isPres ? 'Present' : 'Absent'}
                                    </span>
                                `;
                                historyList.appendChild(row);
                            });
                        }
                    }
                })
                .catch(err => {
                    console.error("Student attendance load error:", err);
                    if (historyList) historyList.innerHTML = `<p class="text-rose-400 text-[11px] py-1 text-center">Could not load logs</p>`;
                });

            const drawer = document.getElementById("profile-drawer");
            const backdrop = document.getElementById("profile-drawer-backdrop");
            drawer.classList.remove("translate-x-full");
            backdrop.classList.remove("hidden");
        }

        function closeProfileDrawer() {
            const drawer = document.getElementById("profile-drawer");
            const backdrop = document.getElementById("profile-drawer-backdrop");
            if (drawer) drawer.classList.add("translate-x-full");
            if (backdrop) backdrop.classList.add("hidden");
        }

        // --- ADD / EDIT STUDENT MODAL ---
        function openAddModal() {
            document.getElementById("modal-title").innerText = "Add New Student";
            document.getElementById("modal-subtitle").innerText = "Create a new student profile in directory";
            document.getElementById("form-mode").value = "add";
            document.getElementById("student-form").reset();
            
            const idInput = document.getElementById("student_id");
            idInput.disabled = false;
            idInput.classList.remove("bg-slate-100", "cursor-not-allowed");
            document.getElementById("id-hint").innerText = "Unique institutional ID (e.g. 330CS24008)";
            
            document.getElementById("save-btn-text").innerText = "Add Student";
            toggleModal("student-modal", true);
        }

        function editStudent(id) {
            closeAllDropdowns();
            const student = allStudents.find(s => String(s.id) === String(id));
            if (!student) {
                showToast("Student profile not found", "error");
                return;
            }

            document.getElementById("modal-title").innerText = "Edit Student Profile";
            document.getElementById("modal-subtitle").innerText = `Modifying records for ${student.name}`;
            document.getElementById("form-mode").value = "edit";

            const idInput = document.getElementById("student_id");
            idInput.value = student.id;
            idInput.disabled = true;
            idInput.classList.add("bg-slate-100", "cursor-not-allowed");
            document.getElementById("id-hint").innerText = "Student ID cannot be changed";

            document.getElementById("name").value = student.name;
            document.getElementById("age").value = student.age;
            document.getElementById("grade").value = student.grade;
            document.getElementById("email").value = student.email || "";

            document.getElementById("save-btn-text").innerText = "Update Record";
            toggleModal("student-modal", true);
        }

        function closeModal() {
            toggleModal("student-modal", false);
        }

        function toggleModal(modalId, show) {
            const modal = document.getElementById(modalId);
            if (!modal) return;
            const card = modal.querySelector(".modal-card");

            if (show) {
                modal.classList.remove("opacity-0", "pointer-events-none");
                if (card) {
                    card.classList.remove("scale-95", "opacity-0");
                    card.classList.add("scale-100", "opacity-100");
                }
            } else {
                modal.classList.add("opacity-0", "pointer-events-none");
                if (card) {
                    card.classList.remove("scale-100", "opacity-100");
                    card.classList.add("scale-95", "opacity-0");
                }
            }
        }

        // --- SAVE STUDENT (POST / PUT) ---
        function saveStudent(event) {
            event.preventDefault();

            const mode = document.getElementById("form-mode").value;
            const studentId = document.getElementById("student_id").value.trim();
            const name = document.getElementById("name").value.trim();
            const age = parseInt(document.getElementById("age").value.trim(), 10);
            const grade = document.getElementById("grade").value.trim();
            const email = document.getElementById("email").value.trim();

            if (!studentId || !name || isNaN(age) || !grade) {
                showToast("Please complete all required fields.", "error");
                return;
            }

            if (age <= 0 || age > 120) {
                showToast("Please enter a valid age between 1 and 120.", "error");
                return;
            }

            const payload = {
                id: studentId,
                name: name,
                age: age,
                grade: grade,
                email: email
            };

            const saveBtn = document.getElementById("save-btn");
            const spinner = document.getElementById("save-btn-spinner");
            const btnText = document.getElementById("save-btn-text");
            saveBtn.disabled = true;
            spinner.classList.remove("hidden");

            let url = '/api/students';
            let method = 'POST';

            if (mode === 'edit') {
                url = `/api/students/${encodeURIComponent(studentId)}`;
                method = 'PUT';
            }

            fetch(url, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            })
            .then(async response => {
                const data = await response.json();
                if (!response.ok) {
                    throw new Error(data.error || 'Failed to save student record');
                }
                return data;
            })
            .then(data => {
                showToast(mode === 'edit' ? "Student record updated successfully!" : "New student registered successfully!", "success");
                closeModal();
                fetchStudents();
            })
            .catch(err => {
                console.error("Save error:", err);
                showToast(err.message, "error");
            })
            .finally(() => {
                saveBtn.disabled = false;
                spinner.classList.add("hidden");
            });
        }

        // --- DELETE OPERATIONS ---
        function promptDelete(id, name) {
            closeAllDropdowns();
            pendingDeleteId = id;
            document.getElementById("delete-student-name").innerText = name;
            toggleModal("delete-modal", true);
        }

        function closeDeleteModal() {
            pendingDeleteId = null;
            toggleModal("delete-modal", false);
        }

        function confirmDelete() {
            if (!pendingDeleteId) return;

            const deleteBtn = document.getElementById("confirm-delete-btn");
            deleteBtn.disabled = true;
            deleteBtn.innerText = "Deleting...";

            fetch(`/api/students/${encodeURIComponent(pendingDeleteId)}`, {
                method: 'DELETE'
            })
            .then(async response => {
                const data = await response.json();
                if (!response.ok) throw new Error(data.error || 'Failed to delete');
                return data;
            })
            .then(() => {
                showToast("Student record permanently removed.", "success");
                closeDeleteModal();
                fetchStudents();
            })
            .catch(err => {
                showToast(err.message || "Failed to delete student.", "error");
            })
            .finally(() => {
                deleteBtn.disabled = false;
                deleteBtn.innerText = "Delete Student";
            });
        }

        // --- EXPORT TO CSV ---
        function exportToCSV() {
            const dataToExport = filteredStudents.length > 0 ? filteredStudents : allStudents;
            if (!dataToExport || dataToExport.length === 0) {
                showToast("No student records to export.", "error");
                return;
            }

            let csvContent = "data:text/csv;charset=utf-8,Student ID,Full Name,Age,Grade/Semester,Email Address\\n";
            dataToExport.forEach(s => {
                const row = [
                    `"${(s.id || '').replace(/"/g, '""')}"`,
                    `"${(s.name || '').replace(/"/g, '""')}"`,
                    s.age || '',
                    `"${(s.grade || '').replace(/"/g, '""')}"`,
                    `"${(s.email || '').replace(/"/g, '""')}"`
                ].join(",");
                csvContent += row + "\\n";
            });

            const encodedUri = encodeURI(csvContent);
            const link = document.createElement("a");
            link.setAttribute("href", encodedUri);
            link.setAttribute("download", `student_records_${new Date().toISOString().slice(0, 10)}.csv`);
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
            showToast(`Exported ${dataToExport.length} student records to CSV!`, "success");
        }

        // --- UTILITY FUNCTIONS ---
        function copyToClipboard(text) {
            navigator.clipboard.writeText(text).then(() => {
                showToast("Email address copied to clipboard!", "success");
            });
        }

        function getInitials(name) {
            if (!name) return "S";
            const parts = name.trim().split(/\\s+/);
            if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
            return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
        }

        function getAvatarColor(name) {
            const colors = [
                "bg-indigo-600",
                "bg-violet-600",
                "bg-blue-600",
                "bg-sky-600",
                "bg-emerald-600",
                "bg-teal-600",
                "bg-amber-600"
            ];
            let hash = 0;
            for (let i = 0; i < name.length; i++) {
                hash = name.charCodeAt(i) + ((hash << 5) - hash);
            }
            return colors[Math.abs(hash) % colors.length];
        }

        function showToast(message, type = "info") {
            const container = document.getElementById("toast-container");
            const toast = document.createElement("div");
            
            const isSuccess = type === "success";
            const isError = type === "error";

            const bgClass = isSuccess ? "bg-slate-900 border-emerald-500/50 text-white" : (isError ? "bg-slate-900 border-rose-500/50 text-white" : "bg-slate-900 border-indigo-500/50 text-white");
            const iconSvg = isSuccess ? `
                <div class="w-5 h-5 rounded-full bg-emerald-500/20 text-emerald-400 flex items-center justify-center flex-shrink-0">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M5 13l4 4L19 7"/>
                    </svg>
                </div>` : (isError ? `
                <div class="w-5 h-5 rounded-full bg-rose-500/20 text-rose-400 flex items-center justify-center flex-shrink-0">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
                    </svg>
                </div>` : `
                <div class="w-5 h-5 rounded-full bg-indigo-500/20 text-indigo-400 flex items-center justify-center flex-shrink-0">
                    <svg class="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>
                    </svg>
                </div>`);

            toast.className = `${bgClass} border px-4 py-3 rounded-xl shadow-xl text-xs font-medium flex items-center space-x-2.5 pointer-events-auto transform translate-y-4 opacity-0 transition-all duration-200 max-w-sm`;
            toast.innerHTML = `${iconSvg}<span>${escapeHtml(message)}</span>`;
            container.appendChild(toast);

            setTimeout(() => {
                toast.classList.remove("translate-y-4", "opacity-0");
            }, 10);

            setTimeout(() => {
                toast.classList.add("translate-y-4", "opacity-0");
                setTimeout(() => toast.remove(), 250);
            }, 3500);
        }

        function escapeHtml(string) {
            return String(string).replace(/[&<>"']/g, function(s) {
                return ({
                    '&': '&amp;',
                    '<': '&lt;',
                    '>': '&gt;',
                    '"': '&quot;',
                    "'": '&#39;'
                })[s];
            });
        }
    </script>
</body>
</html>
"""

# ==============================================================================
# FLASK AUTH & ROUTE HANDLERS
# ==============================================================================

@app.route("/login", methods=["GET"])
def login_page():
    """Renders the login interface, or redirects to dashboard if already authenticated."""
    if "user" in session:
        return redirect(url_for("index"))
    return render_template_string(LOGIN_TEMPLATE)

@app.route("/api/login", methods=["POST"])
def api_login():
    """Authenticates username and password against SQLite database."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid login request"}), 400

    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not username or not password:
        return jsonify({"error": "Please provide both username and password."}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, password_hash, role FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()
    conn.close()

    if not user or user["password_hash"] != hash_password(password):
        return jsonify({"error": "Invalid username or password. Please try again."}), 401

    # Store user in session
    session["user"] = {
        "id": user["id"],
        "username": user["username"],
        "role": user["role"]
    }

    return jsonify({
        "success": True,
        "message": "Login successful",
        "user": session["user"]
    }), 200

@app.route("/logout", methods=["GET", "POST"])
@app.route("/api/logout", methods=["GET", "POST"])
def logout():
    """Clears the session and redirects to the login screen."""
    session.pop("user", None)
    if request.path.startswith("/api/"):
        return jsonify({"success": True, "message": "Logged out successfully"}), 200
    return redirect(url_for("login_page"))

@app.route("/api/me", methods=["GET"])
def get_current_user():
    """Returns the currently authenticated user profile."""
    if "user" not in session:
        return jsonify({"authenticated": False}), 401
    return jsonify({"authenticated": True, "user": session["user"]}), 200

@app.route("/")
@login_required
def index():
    """Renders the main student management dashboard."""
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route("/api/students", methods=["GET"])
@login_required
def get_students():
    """Fetches all students with optional search filter (name-first priority)."""
    search_query = request.args.get("search", "").strip().lower()
    name_query = request.args.get("name", "").strip().lower()
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, age, grade, email FROM students ORDER BY id ASC")
    rows = cursor.fetchall()
    conn.close()

    students = [dict(row) for row in rows]

    # Dedicated name search
    if name_query:
        students = [s for s in students if name_query in s["name"].lower()]
    elif search_query:
        students = [
            s for s in students
            if search_query in s["id"].lower()
            or search_query in s["name"].lower()
            or search_query in (s["grade"] or "").lower()
            or search_query in (s["email"] or "").lower()
        ]
        # Sort: name matches come first
        students.sort(key=lambda s: (0 if search_query in s["name"].lower() else 1))

    return jsonify(students)

@app.route("/api/students", methods=["POST"])
@login_required
def add_student():
    """Creates a new student record."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request payload"}), 400

    student_id = str(data.get("id", "")).strip()
    name = str(data.get("name", "")).strip()
    grade = str(data.get("grade", "")).strip()
    email = str(data.get("email", "")).strip()

    try:
        age = int(data.get("age", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Age must be a valid number"}), 400

    if not student_id:
        return jsonify({"error": "Student ID cannot be empty"}), 400
    if not name:
        return jsonify({"error": "Student Name cannot be empty"}), 400
    if age <= 0 or age > 120:
        return jsonify({"error": "Age must be between 1 and 120"}), 400
    if not grade:
        return jsonify({"error": "Grade/Semester cannot be empty"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO students (id, name, age, grade, email)
            VALUES (?, ?, ?, ?, ?)
        """, (student_id, name, age, grade, email))
        conn.commit()
        return jsonify({"success": True, "message": f"Student '{name}' added successfully."}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": f"A student with ID '{student_id}' already exists."}), 400
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

@app.route("/api/students/<string:student_id>", methods=["PUT"])
@login_required
def update_student(student_id):
    """Updates an existing student record."""
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request payload"}), 400

    name = str(data.get("name", "")).strip()
    grade = str(data.get("grade", "")).strip()
    email = str(data.get("email", "")).strip()

    try:
        age = int(data.get("age", 0))
    except (ValueError, TypeError):
        return jsonify({"error": "Age must be a valid number"}), 400

    if not name:
        return jsonify({"error": "Student Name cannot be empty"}), 400
    if age <= 0 or age > 120:
        return jsonify({"error": "Age must be between 1 and 120"}), 400
    if not grade:
        return jsonify({"error": "Grade/Semester cannot be empty"}), 400

    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM students WHERE id = ?", (student_id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Student with ID '{student_id}' not found."}), 404

        cursor.execute("""
            UPDATE students
            SET name = ?, age = ?, grade = ?, email = ?
            WHERE id = ?
        """, (name, age, grade, email, student_id))
        conn.commit()
        return jsonify({"success": True, "message": "Student record updated successfully."}), 200
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

@app.route("/api/students/<string:student_id>", methods=["DELETE"])
@login_required
def delete_student(student_id):
    """Deletes a student record."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT id FROM students WHERE id = ?", (student_id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Student with ID '{student_id}' not found."}), 404

        cursor.execute("DELETE FROM students WHERE id = ?", (student_id,))
        conn.commit()
        return jsonify({"success": True, "message": "Student record deleted successfully."}), 200
    except Exception as e:
        return jsonify({"error": f"Database error: {str(e)}"}), 500
    finally:
        conn.close()

# ==============================================================================
# ATTENDANCE MANAGEMENT API HANDLERS
# ==============================================================================

@app.route("/attendance", methods=["GET"])
@login_required
def attendance_page():
    """Renders the dashboard with the Attendance view active."""
    return render_template_string(DASHBOARD_TEMPLATE)

@app.route("/api/attendance", methods=["GET"])
@login_required
def get_attendance():
    """
    Fetches student list and attendance records for a specific date and class/grade.
    Computes real-time class summary and individual lifetime attendance stats.
    """
    from datetime import date
    date_str = request.args.get("date", "").strip() or date.today().isoformat()
    grade = request.args.get("grade", "").strip()
    search = request.args.get("search", "").strip().lower()

    conn = get_db_connection()
    cursor = conn.cursor()

    # Query students belonging to selected class/grade (or all)
    student_query = "SELECT id, name, age, grade, email FROM students"
    params = []
    if grade and grade.lower() != "all":
        student_query += " WHERE grade = ?"
        params.append(grade)
    student_query += " ORDER BY id ASC"

    cursor.execute(student_query, params)
    students = [dict(row) for row in cursor.fetchall()]

    if search:
        students = [
            s for s in students
            if search in (s["id"] or "").lower()
            or search in (s["name"] or "").lower()
            or search in (s["grade"] or "").lower()
            or search in (s["email"] or "").lower()
        ]

    # Query attendance records for this date
    att_query = "SELECT student_id, class_id, status, notes, updated_at FROM attendance WHERE attendance_date = ?"
    att_params = [date_str]
    if grade and grade.lower() != "all":
        att_query += " AND class_id = ?"
        att_params.append(grade)

    cursor.execute(att_query, att_params)
    att_map = {row["student_id"]: dict(row) for row in cursor.fetchall()}

    # Query lifetime attendance statistics per student
    cursor.execute("""
        SELECT 
            student_id,
            COUNT(id) as total_classes,
            SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN status = 'absent' THEN 1 ELSE 0 END) as absent_count
        FROM attendance
        GROUP BY student_id
    """)
    stats_map = {row["student_id"]: dict(row) for row in cursor.fetchall()}
    conn.close()

    present_count = 0
    absent_count = 0
    unmarked_count = 0

    records = []
    for s in students:
        s_id = s["id"]
        att = att_map.get(s_id)
        stat = stats_map.get(s_id, {"total_classes": 0, "present_count": 0, "absent_count": 0})

        status = att["status"] if att else None
        notes = att["notes"] if att else ""

        if status == "present":
            present_count += 1
        elif status == "absent":
            absent_count += 1
        else:
            unmarked_count += 1

        tot = stat["total_classes"] or 0
        pres = stat["present_count"] or 0
        abs_cnt = stat["absent_count"] or 0
        rate = round((pres / tot * 100.0), 1) if tot > 0 else 100.0

        records.append({
            "student_id": s_id,
            "name": s["name"],
            "grade": s["grade"],
            "email": s["email"],
            "age": s["age"],
            "status": status,
            "notes": notes,
            "lifetime_total": tot,
            "lifetime_present": pres,
            "lifetime_absent": abs_cnt,
            "lifetime_rate": rate
        })

    marked_total = present_count + absent_count
    attendance_rate = round((present_count / marked_total * 100.0), 1) if marked_total > 0 else (100.0 if present_count > 0 else 0.0)

    return jsonify({
        "date": date_str,
        "grade": grade,
        "summary": {
            "total_students": len(students),
            "present_count": present_count,
            "absent_count": absent_count,
            "unmarked_count": unmarked_count,
            "attendance_rate": attendance_rate
        },
        "records": records
    })

@app.route("/api/attendance/bulk", methods=["POST"])
@login_required
def save_bulk_attendance():
    """
    Atomically saves or updates attendance records with strict SQLite UPSERT conflict resolution.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Invalid request payload"}), 400

    date_str = str(data.get("date", "")).strip()
    grade = str(data.get("grade", "")).strip()
    records = data.get("attendance", [])

    if not date_str:
        return jsonify({"error": "Attendance date is required."}), 400

    if not isinstance(records, list) or len(records) == 0:
        return jsonify({"error": "No attendance items provided to save."}), 400

    valid_statuses = {"present", "absent", "late", "excused"}
    conn = get_db_connection()
    cursor = conn.cursor()

    try:
        saved_count = 0
        for item in records:
            student_id = str(item.get("student_id", "")).strip()
            status = str(item.get("status", "")).strip().lower()
            notes = str(item.get("notes", "")).strip()
            item_grade = str(item.get("grade", grade)).strip() or grade

            if not student_id or not status or status not in valid_statuses:
                continue

            # Atomic SQLite UPSERT
            cursor.execute("""
                INSERT INTO attendance (student_id, class_id, attendance_date, status, notes, updated_at)
                VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(student_id, attendance_date, class_id)
                DO UPDATE SET 
                    status = excluded.status,
                    notes = excluded.notes,
                    updated_at = CURRENT_TIMESTAMP
            """, (student_id, item_grade, date_str, status, notes))
            saved_count += 1

        conn.commit()
        return jsonify({
            "success": True,
            "message": f"Successfully saved attendance for {saved_count} student(s).",
            "saved_count": saved_count
        }), 200
    except Exception as e:
        conn.rollback()
        return jsonify({"error": f"Failed to save attendance: {str(e)}"}), 500
    finally:
        conn.close()

@app.route("/api/attendance/history", methods=["GET"])
@login_required
def get_attendance_history():
    """
    Returns distinct historical attendance sessions grouped by date and class.
    """
    grade = request.args.get("grade", "").strip()
    conn = get_db_connection()
    cursor = conn.cursor()

    params = []
    query = """
        SELECT 
            attendance_date,
            class_id,
            COUNT(id) as total_students,
            SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN status = 'absent' THEN 1 ELSE 0 END) as absent_count,
            MAX(updated_at) as last_updated
        FROM attendance
    """
    if grade and grade.lower() != "all":
        query += " WHERE class_id = ?"
        params.append(grade)

    query += " GROUP BY attendance_date, class_id ORDER BY attendance_date DESC, class_id ASC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    history = []
    for r in rows:
        tot = r["total_students"] or 0
        pres = r["present_count"] or 0
        abs_cnt = r["absent_count"] or 0
        rate = round((pres / tot * 100.0), 1) if tot > 0 else 0.0

        history.append({
            "attendance_date": r["attendance_date"],
            "class_id": r["class_id"],
            "total_students": tot,
            "present_count": pres,
            "absent_count": abs_cnt,
            "attendance_rate": rate,
            "last_updated": r["last_updated"]
        })

    return jsonify(history)

@app.route("/api/attendance/student/<string:student_id>", methods=["GET"])
@login_required
def get_student_attendance(student_id):
    """
    Returns student attendance profile with total metrics and full session log.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT id, name, age, grade, email FROM students WHERE id = ?", (student_id,))
    student = cursor.fetchone()
    if not student:
        conn.close()
        return jsonify({"error": f"Student with ID '{student_id}' not found."}), 404

    cursor.execute("""
        SELECT attendance_date, class_id, status, notes, updated_at
        FROM attendance
        WHERE student_id = ?
        ORDER BY attendance_date DESC
    """, (student_id,))
    history_rows = cursor.fetchall()
    conn.close()

    history = [dict(r) for r in history_rows]
    total_classes = len(history)
    present_count = sum(1 for r in history if r["status"] == "present")
    absent_count = sum(1 for r in history if r["status"] == "absent")
    rate = round((present_count / total_classes * 100.0), 1) if total_classes > 0 else 100.0

    return jsonify({
        "student": dict(student),
        "stats": {
            "total_classes": total_classes,
            "present": present_count,
            "absent": absent_count,
            "rate": rate
        },
        "history": history
    })

@app.route("/api/attendance/analytics", methods=["GET"])
@login_required
def get_attendance_analytics():
    """
    Returns aggregate attendance analytics: overall rate, today's rate, low attendance students (<75%), and trend points.
    """
    grade = request.args.get("grade", "").strip()
    from datetime import date
    today_str = date.today().isoformat()

    conn = get_db_connection()
    cursor = conn.cursor()

    params = []
    where_clause = ""
    if grade and grade.lower() != "all":
        where_clause = " WHERE class_id = ?"
        params.append(grade)

    cursor.execute(f"""
        SELECT 
            COUNT(id) as total_records,
            SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN status = 'absent' THEN 1 ELSE 0 END) as absent_count
        FROM attendance
        {where_clause}
    """, params)
    overall = cursor.fetchone()

    total_records = overall["total_records"] or 0
    present_total = overall["present_count"] or 0
    absent_total = overall["absent_count"] or 0
    overall_rate = round((present_total / total_records * 100.0), 1) if total_records > 0 else None

    # Today's attendance
    today_params = [today_str]
    today_where = " WHERE attendance_date = ?"
    if grade and grade.lower() != "all":
        today_where += " AND class_id = ?"
        today_params.append(grade)

    cursor.execute(f"""
        SELECT 
            COUNT(id) as total_records,
            SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN status = 'absent' THEN 1 ELSE 0 END) as absent_count
        FROM attendance
        {today_where}
    """, today_params)
    today_row = cursor.fetchone()
    today_tot = today_row["total_records"] or 0
    today_pres = today_row["present_count"] or 0
    today_rate = round((today_pres / today_tot * 100.0), 1) if today_tot > 0 else None

    # Trend by date (last 10 distinct dates)
    trend_params = []
    trend_where = ""
    if grade and grade.lower() != "all":
        trend_where = " WHERE class_id = ?"
        trend_params.append(grade)

    cursor.execute(f"""
        SELECT 
            attendance_date,
            COUNT(id) as total_students,
            SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) as present_count
        FROM attendance
        {trend_where}
        GROUP BY attendance_date
        ORDER BY attendance_date DESC
        LIMIT 10
    """, trend_params)
    trend_rows = cursor.fetchall()
    trends = []
    for tr in reversed(trend_rows):
        t_tot = tr["total_students"] or 0
        t_pres = tr["present_count"] or 0
        t_rate = round((t_pres / t_tot * 100.0), 1) if t_tot > 0 else 0.0
        trends.append({
            "date": tr["attendance_date"],
            "total": t_tot,
            "present": t_pres,
            "rate": t_rate
        })

    # Students with low attendance (< 75% with at least 1 marked class)
    low_att_query = """
        SELECT 
            s.id,
            s.name,
            s.grade,
            s.email,
            COUNT(a.id) as total_classes,
            SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) as absent_count
        FROM students s
        JOIN attendance a ON s.id = a.student_id
    """
    low_params = []
    if grade and grade.lower() != "all":
        low_att_query += " WHERE s.grade = ?"
        low_params.append(grade)
    low_att_query += " GROUP BY s.id HAVING total_classes > 0 AND (CAST(present_count AS FLOAT) / total_classes * 100.0) < 75.0 ORDER BY (CAST(present_count AS FLOAT) / total_classes) ASC"

    cursor.execute(low_att_query, low_params)
    low_students = []
    for r in cursor.fetchall():
        tot = r["total_classes"]
        pres = r["present_count"]
        rate = round((pres / tot * 100.0), 1) if tot > 0 else 0.0
        low_students.append({
            "id": r["id"],
            "name": r["name"],
            "grade": r["grade"],
            "email": r["email"],
            "total_classes": tot,
            "present": pres,
            "absent": r["absent_count"],
            "rate": rate
        })

    # Total distinct sessions
    cursor.execute(f"SELECT COUNT(DISTINCT attendance_date || class_id) as session_count FROM attendance {where_clause}", params)
    session_count = cursor.fetchone()["session_count"] or 0
    conn.close()

    return jsonify({
        "overall_rate": overall_rate,
        "today_rate": today_rate,
        "total_records": total_records,
        "present_total": present_total,
        "absent_total": absent_total,
        "total_sessions": session_count,
        "trends": trends,
        "low_attendance_students": low_students
    })

@app.route("/api/attendance/report", methods=["GET"])
@login_required
def get_attendance_report():
    """
    Returns student-wise attendance aggregated report filtered by grade and date range.
    """
    grade = request.args.get("grade", "").strip()
    start_date = request.args.get("start_date", "").strip()
    end_date = request.args.get("end_date", "").strip()

    conn = get_db_connection()
    cursor = conn.cursor()

    conditions = []
    params = []

    if grade and grade.lower() != "all":
        conditions.append("s.grade = ?")
        params.append(grade)

    att_conditions = []
    att_params = []
    if start_date:
        att_conditions.append("a.attendance_date >= ?")
        att_params.append(start_date)
    if end_date:
        att_conditions.append("a.attendance_date <= ?")
        att_params.append(end_date)

    att_join_clause = ""
    if att_conditions:
        att_join_clause = " AND " + " AND ".join(att_conditions)

    query = f"""
        SELECT 
            s.id,
            s.name,
            s.age,
            s.grade,
            s.email,
            COUNT(a.id) as total_classes,
            SUM(CASE WHEN a.status = 'present' THEN 1 ELSE 0 END) as present_count,
            SUM(CASE WHEN a.status = 'absent' THEN 1 ELSE 0 END) as absent_count
        FROM students s
        LEFT JOIN attendance a ON s.id = a.student_id {att_join_clause}
    """
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " GROUP BY s.id ORDER BY s.id ASC"

    all_params = att_params + params
    cursor.execute(query, all_params)
    rows = cursor.fetchall()
    conn.close()

    report = []
    for r in rows:
        tot = r["total_classes"] or 0
        pres = r["present_count"] or 0
        abs_cnt = r["absent_count"] or 0
        rate = round((pres / tot * 100.0), 1) if tot > 0 else 0.0

        report.append({
            "id": r["id"],
            "name": r["name"],
            "grade": r["grade"],
            "email": r["email"],
            "total_classes": tot,
            "present": pres,
            "absent": abs_cnt,
            "rate": rate
        })

    return jsonify(report)

@app.route("/api/classes", methods=["GET"])
@login_required
def get_classes():
    """
    Returns list of distinct classes with student count and average attendance rate.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT 
            grade,
            COUNT(id) as student_count
        FROM students
        WHERE grade IS NOT NULL AND grade != ''
        GROUP BY grade
        ORDER BY grade ASC
    """)
    rows = cursor.fetchall()
    conn.close()

    classes = [dict(r) for r in rows]
    return jsonify(classes)

if __name__ == "__main__":
    init_db()
    print("\n=======================================================")
    print(" [OK] EduManager Pro Web Dashboard is running!")
    print(" [AUTH] Login credentials: admin / admin123")
    print(" [URL] Open in browser: http://127.0.0.1:5000")
    print("=======================================================\n")
    app.run(debug=True, port=5000)