@echo off
pushd "%~dp0"
"venv\Scripts\python.exe" -c "import urllib.request,json,time,uuid; now=__import__('datetime').datetime.utcnow(); ts=now.strftime('%%Y-%%m-%%dT%%H:%%M:%%SZ'); eid='inject_human_'+str(int(time.time()*1000))+'_'+uuid.uuid4().hex[:4]; payload=json.dumps({'node_id':'NODE_01','event_id':eid,'timestamp':ts,'sensor_type':'acoustic','class':'human_activity','confidence':0.92,'battery_pct':78,'lat':28.51975,'lon':77.36538}).encode(); req=urllib.request.Request('http://localhost:8000/events',data=payload,headers={'Content-Type':'application/json'},method='POST'); r=urllib.request.urlopen(req).read().decode(); print(r)"
popd
