@echo off
chcp 65001 >nul
echo Starting Diia Backend System...
echo.

REM Create necessary directories
if not exist "database" mkdir database
if not exist "uploads\photos" mkdir uploads\photos

echo [1/3] Starting API Server (Uvicorn)...
start "Diia API" cmd /k "python -m uvicorn api.main:app --reload --host 0.0.0.0 --port 8000"

timeout /t 3 /nobreak >nul

echo [2/3] Starting ngrok tunnel...
start "Diia ngrok" cmd /k "ngrok http 8000"

timeout /t 3 /nobreak >nul

echo [3/3] Starting Telegram Bot...
start "Diia Bot" cmd /k "python -m bot.bot"

timeout /t 2 /nobreak >nul

echo.
echo ========================================
echo Diia Backend System Started!
echo ========================================
echo API Server: http://localhost:8000
echo ngrok: Check ngrok window for public URL
echo Telegram Bot: Running
echo ========================================
echo.
echo Press any key to stop all services...
pause >nul

echo.
echo Stopping all services...

taskkill /FI "WindowTitle eq Diia API*" /T /F
taskkill /FI "WindowTitle eq Diia ngrok*" /T /F
taskkill /FI "WindowTitle eq Diia Bot*" /T /F

REM Also kill ngrok by process name (backup)
taskkill /IM ngrok.exe /F 2>nul

echo All services stopped.
pause
