@echo off
setlocal
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 -m csvplan_corrected
) else (
  python -m csvplan_corrected
)
echo.
pause
