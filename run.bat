@echo off
title EduManager Pro
color 0A
echo.
echo  =====================================================
echo   EduManager Pro - Student Management System
echo  =====================================================
echo.
echo  [*] Starting server...
echo  [*] Open your browser at: http://127.0.0.1:5000
echo  [*] Login: admin / admin123
echo  [*] Press CTRL+C to stop the server
echo.
cd /d "%~dp0"
python web_app.py
pause
