@echo off
chcp 65001 >nul
echo Starting Diia API Server...
echo.

REM Create necessary directories
if not exist "database" mkdir database
if not exist "uploads\photos" mkdir uploads\photos

echo Starting uvicorn on http://localhost:8000
python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000

