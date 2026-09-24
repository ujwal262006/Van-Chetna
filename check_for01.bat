@echo off
pushd "%~dp0"
"venv\Scripts\python.exe" -c "import urllib.request,json; d=json.loads(urllib.request.urlopen('http://localhost:8000/alerts?node_id=FOR01&limit=1').read()); print('LABEL:',d[0]['label'] if d else 'NO ALERTS'); print('SEV:',d[0]['severity'] if d else '-')"
popd
