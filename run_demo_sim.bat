@echo off
pushd "%~dp0"
echo.
echo  Van-Chetna DEMO RECORDING Simulator
echo  Read DEMO_SCRIPT.txt before running this.
echo  Press ENTER at each scene when narration is ready.
echo.
"venv\Scripts\python.exe" backend\simulate_demo.py
popd
