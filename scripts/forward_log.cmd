@echo off
cd /d "%~dp0.."
set PYTHONPATH=src
.venv\Scripts\python.exe scriptsorward_log.py >> ..\data\yahooorward_log_runs.txt 2>&1
