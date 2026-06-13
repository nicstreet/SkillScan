@echo off
if exist "%~dp0.venv\Scripts\python.exe" (
    "%~dp0.venv\Scripts\python.exe" -m skill_scan %*
) else (
    python -m skill_scan %*
)
