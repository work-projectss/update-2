@echo off
REM For Windows Task Scheduler: run this every 30 minutes
cd /d "%~dp0"
if exist .venv\Scripts\activate.bat call .venv\Scripts\activate.bat
python run_report.py >> logs\report.log 2>&1
