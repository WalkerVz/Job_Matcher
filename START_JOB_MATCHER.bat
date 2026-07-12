@echo off
title AI Job Matcher Server & Web Launcher
echo ========================================================
echo        MEMULAI AI JOB MATCHER (GROQ LLAMA 3.3)
echo ========================================================
echo.
echo [1/2] Menjalankan AI Service di Port 5001...
start "AI Job Matcher Service (Port 5001)" /MIN cmd /k "python ai_service.py"

echo [2/2] Membuka Aplikasi Job Matcher di Browser...
timeout /t 2 /nobreak > nul
start "" index.html

echo.
echo ========================================================
echo   SIAP DIGUNAKAN! AI Service berjalan di background.
echo ========================================================
exit
