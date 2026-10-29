@echo off
rem Daily SC-FUT-0005 forward paper log (no orders). Run by hand or from Task Scheduler.
cd /d "%~dp0.."
set PYTHONPATH=src
.venv\Scripts\python.exe scripts\forward_log.py >> ..\data\yahoo\forward_log_runs.txt 2>&1
