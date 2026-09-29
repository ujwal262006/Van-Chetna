@echo off
pushd "%~dp0"
"venv\Scripts\python.exe" -c "import ast; ast.parse(open('backend/simulate_demo.py', encoding='utf-8').read()); print('simulate_demo.py syntax OK')"
popd
