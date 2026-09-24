@echo off
pushd "%~dp0backend"
"..\venv\Scripts\python.exe" simulate.py
popd
