@echo off
cd /d "%~dp0"

echo ========================================
echo   Parakh Seva Backend
echo ========================================
echo.

python -m uvicorn app.main:app --reload

pause