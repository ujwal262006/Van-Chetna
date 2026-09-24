@echo off
pushd "%~dp0backend"
"..\venv\Scripts\python.exe" -m pytest test_vcn1_integration.py -v
popd
