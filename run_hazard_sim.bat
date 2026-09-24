@echo off
pushd "%~dp0"
"venv\Scripts\python.exe" backend\simulate_hazard.py
popd
