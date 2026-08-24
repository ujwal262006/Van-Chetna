@echo off
pushd "%~dp0backend"
"%~dp0venv\Scripts\python.exe" -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
popd
