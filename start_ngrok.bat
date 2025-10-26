@echo off
chcp 65001 >nul
echo Starting ngrok tunnel on port 8000...
echo.
echo После запуска скопируй URL из строки "Forwarding"
echo Пример: https://xxxx.ngrok-free.app
echo.

ngrok http 8000

