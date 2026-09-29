# -*- coding: utf-8 -*-
"""
simulate_demo.py  --  Van-Chetna DEMO RECORDING Simulator

PURPOSE
-------
This is NOT the integration test simulator (simulate_hazard.py).
This script is purpose-built for the demo video recording session.

Key differences from simulate_hazard.py:
  - Slow, deliberate tick interval (15-20s) -- camera-friendly pacing
  - Controlled story: each node follows a pre-scripted arc with clear
    on-screen moments timed for narration
  - Acoustic events are sparse so the dashboard does not stack up with
    ILLEGAL LOGGING noise
  - Scene-gated: press ENTER to advance each scene so recording does
    not race ahead of narration
  - All three UNATTENDED / DELIBERATE_BURN label flips are guaranteed
    to happen at predictable moments

STORY ARC (8 scenes, ~8 minutes total)
  Scene 0  IDLE        -- all nodes NORMAL, system quiet
  Scene 1  RISING      -- URB01 and RIV01 enter WATCH
  Scene 2  WATCH       -- FOR01 enters WATCH, first alerts
  Scene 3  UNATTENDED  -- FOR01 WARNING/CRITICAL, no acoustic -> UNATTENDED
  Scene 4  FLIP        -- inject human_activity -> label flips
  Scene 5  CRITICAL    -- all three nodes CRITICAL simultaneously
  Scene 6  ACK         -- ranger acknowledges (manual browser action)
  Scene 7  RECOVERY    -- sensors return to NORMAL

HOW TO RUN
----------
  From the repo root:
    venv\\Scripts\\python.exe backend\\simulate_demo.py

  -- OR double-click run_demo_sim.bat --

  Controls:
    - Each scene waits for ENTER before sending data
    - Scene 3 auto-waits 65 seconds after sending the fire WARNING
      to clear the acoustic fusion window -- the script prints a countdown

  DO NOT run simulate.py or simulate_hazard.py at the same time.

BEFORE RECORDING
-----------------
  1. Delete the old database so the alert feed starts clean:
       del backend\\forest_guard.db
  2. Restart the backend:
       run_backend.bat
  3. Start the frontend:
       run_frontend.bat
  4. Open browser at http://localhost:5173/dashboard
"""

import asyncio
import random
import time
import uuid
from datetime import datetime, timezone

import httpx

API_URL = "http://localhost:8000"


# ── Helpers ───────────────────────────────────────────────────────────────────

def gen_id(node):
    return "demo_{}_{}_{}" .format(node.lower(), int(time.time() * 1000), uuid.uuid4().hex[:4])

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def sev(risk):
    if risk < 25: return "normal"
    if risk < 50: return "watch"
    if risk < 80: return "warning"
    return "critical"

def print_scene(n, title, description):
    print("\n" + "=" * 60)
    print("  SCENE {}  --  {}".format(n, title))
    for line in description.splitlines():
        print("  {}".format(line))
    print("=" * 60)

def wait_enter(prompt="  >> Press ENTER when ready to send this scene's data..."):
    input(prompt)


# ── Payload builders ──────────────────────────────────────────────────────────

def urb(risk, raw):
    return {
        "node_id": "URB01", "event_id": gen_id("URB01"), "timestamp": now_iso(),
        "hazard_type": "AIR_QUALITY", "risk_score": risk, "severity": sev(risk),
        "confidence": 85, "sensor_value_1": float(raw),
        "sensor_value_2": None, "sensor_value_3": None,
        "rssi": random.randint(-95, -78), "snr": round(random.uniform(7.0, 11.0), 1),
        "lat": 28.52050, "lon": 77.36700,
    }

def riv(risk, level, rise):
    return {
        "node_id": "RIV01", "event_id": gen_id("RIV01"), "timestamp": now_iso(),
        "hazard_type": "WATER_LEVEL", "risk_score": risk, "severity": sev(risk),
        "confidence": 90, "sensor_value_1": float(level), "sensor_value_2": float(rise),
        "sensor_value_3": None,
        "rssi": random.randint(-98, -82), "snr": round(random.uniform(6.0, 10.0), 1),
        "lat": 28.51800, "lon": 77.36400,
    }

def fire(risk, smoke, temp, hum):
    signals = (
        (1 if smoke > 380 else 0) +
        (1 if temp  > 32  else 0) +
        (1 if hum   < 48  else 0)
    )
    return {
        "node_id": "FOR01", "event_id": gen_id("FOR01"), "timestamp": now_iso(),
        "hazard_type": "FIRE", "risk_score": risk, "severity": sev(risk),
        "confidence": 60 + signals * 10,
        "sensor_value_1": float(smoke), "sensor_value_2": float(temp), "sensor_value_3": float(hum),
        "rssi": random.randint(-88, -72), "snr": round(random.uniform(8.0, 12.0), 1),
        "lat": 28.51975, "lon": 77.36538,
    }

def acoustic_event(event_class, confidence):
    return {
        "node_id": "NODE_01",
        "event_id": "demo_acoustic_{}_{}".format(int(time.time() * 1000), uuid.uuid4().hex[:4]),
        "timestamp": now_iso(),
        "sensor_type": "acoustic",
        "class": event_class,
        "confidence": confidence,
        "battery_pct": 78,
        "lat": 28.51975,
        "lon": 77.36538,
    }


# ── HTTP senders ──────────────────────────────────────────────────────────────

async def post_hazard(client, payload):
    node  = payload["node_id"]
    htype = payload["hazard_type"]
    risk  = payload["risk_score"]
    sv    = payload["severity"].upper()
    try:
        resp = await client.post("{}/hazard-events".format(API_URL), json=payload)
        icon = "[OK] " if resp.status_code == 201 else "[!!] {}".format(resp.status_code)
        st   = resp.json().get("status", "?")
        print("  {} [{}] {:12s}  risk={:3d}  sev={:8s}  -> {}".format(icon, node, htype, risk, sv, st))
    except Exception as e:
        print("  [ERR] [{}] {}".format(node, e))

async def post_acoustic(client, payload):
    cls  = payload["class"]
    conf = payload["confidence"]
    try:
        resp = await client.post("{}/events".format(API_URL), json=payload)
        icon = "[OK] " if resp.status_code == 201 else "[!!] {}".format(resp.status_code)
        st   = resp.json().get("status", "?")
        print("  {} [NODE_01] acoustic  class={:16s}  conf={:.2f}  -> {}".format(icon, cls, conf, st))
    except Exception as e:
        print("  [ERR] [NODE_01] acoustic {}".format(e))

async def send_batch(client, payloads):
    for p in payloads:
        await post_hazard(client, p)
        await asyncio.sleep(0.4)


# ── Main demo ─────────────────────────────────────────────────────────────────

async def run_demo():
    print("\n" + "=" * 60)
    print("  Van-Chetna  --  DEMO RECORDING SIMULATOR")
    print("  Backend:", API_URL)
    print()
    print("  BEFORE YOU START:")
    print("    1. del backend\\forest_guard.db  (start with empty alerts)")
    print("    2. run_backend.bat  -> wait for Application startup complete")
    print("    3. run_frontend.bat -> wait for Vite ready")
    print("    4. Open http://localhost:5173/dashboard")
    print("    5. DO NOT run simulate.py alongside this")
    print("=" * 60)

    async with httpx.AsyncClient(timeout=10) as client:

        # ── SCENE 0 -- IDLE ───────────────────────────────────────────────────
        print_scene(0, "IDLE",
            "All three nodes online, all readings NORMAL.\n"
            "Show the dashboard map -- three markers appearing, all calm colours.\n"
            "Narrate the node types and the map legend.")
        wait_enter()

        await send_batch(client, [
            urb(8,  523),
            riv(18, 45.2, 4.1),
            fire(6, 285, 26.5, 62.0),
        ])
        print("\n  [DONE] Scene 0 sent. Nodes will appear on map.")
        print("  >> Wait for all three markers to appear (~3s), then narrate.")
        await asyncio.sleep(3)

        # ── SCENE 1 -- RISING ─────────────────────────────────────────────────
        print_scene(1, "RISING",
            "URB01 and RIV01 enter WATCH. FOR01 still NORMAL.\n"
            "Show the diamond and teardrop markers turning amber.\n"
            "Show the hazard node cards updating below the map.")
        wait_enter()

        await send_batch(client, [
            urb(32, 610),
            riv(38, 78.5, 9.3),
            fire(14, 305, 28.1, 58.0),
        ])
        print("\n  [DONE] Scene 1 tick 1 sent.")
        print("  >> Narrate air quality and water level rising. Wait ~12s for tick 2.")
        await asyncio.sleep(12)

        await send_batch(client, [
            urb(40, 648),
            riv(45, 88.0, 11.2),
            fire(18, 315, 29.0, 56.0),
        ])
        print("  [DONE] Scene 1 tick 2 sent -- sparklines now have 2 data points.")

        # ── SCENE 2 -- WATCH ──────────────────────────────────────────────────
        print_scene(2, "WATCH",
            "FOR01 enters WATCH. First alerts appear in the feed.\n"
            "Navigate to Alerts -> click the [Fire Hazard Nodes] tab.\n"
            "Show the three node cards all updating simultaneously.")
        wait_enter()

        await send_batch(client, [
            urb(47, 682),
            riv(52, 98.4, 13.5),
            fire(42, 370, 31.5, 50.0),
        ])
        print("\n  [DONE] Scene 2 sent. FOR01 now WATCH.")
        print("  >> Navigate to Alerts page -> Hazard Nodes tab now.")
        await asyncio.sleep(3)

        # ── SCENE 3 -- UNATTENDED FIRE ────────────────────────────────────────
        print_scene(3, "UNATTENDED FIRE  (cross-signal case)",
            "FOR01 escalates to WARNING with no acoustic activity present.\n"
            "Expected label: UNATTENDED FIRE RISK -- POSSIBLE WILDFIRE\n\n"
            "IMPORTANT: After pressing Enter, the script sends the fire WARNING,\n"
            "then waits 65 seconds for the acoustic fusion window to clear.\n"
            "Use this time to narrate the fusion engine logic on camera.")
        wait_enter()

        await send_batch(client, [
            urb(58, 721),
            riv(68, 115.3, 16.2),
            fire(72, 510, 38.5, 34.0),
        ])
        print("\n  [DONE] FOR01 WARNING sent.")
        print("  [WAIT] Holding 65 seconds for fusion window to clear of old acoustic events.")
        print("  >> Talk about the cross-signal disambiguation logic on camera now.\n")

        for remaining in range(65, 0, -5):
            await asyncio.sleep(5)
            print("         ... {}s remaining ...".format(remaining))

        # Send CRITICAL to guarantee UNATTENDED branch fires
        await send_batch(client, [fire(88, 610, 42.0, 27.0)])
        print("\n  [DONE] FOR01 CRITICAL sent -- UNATTENDED label should now be live.")
        print("  >> Navigate to Alerts -> Hazard Nodes. Show the UNATTENDED FIRE RISK label.")
        print("  >> Let the camera hold on that label for 3-4 seconds.\n")
        input("  >> Press ENTER after you have shown the UNATTENDED label on camera...")

        # ── SCENE 4 -- LABEL FLIP ─────────────────────────────────────────────
        print_scene(4, "LABEL FLIP  (human activity detected)",
            "Inject human_activity at high confidence.\n"
            "On the next fire tick the fusion engine sees human presence.\n"
            "Expected label: FIRE/SMOKE DETECTED -- POSSIBLE DELIBERATE BURN\n\n"
            "Script: sends acoustic event, waits 8s, sends fire tick to trigger flip.")
        wait_enter()

        await post_acoustic(client, acoustic_event("human_activity", 0.91))
        print("\n  [DONE] human_activity (0.91) injected.")
        print("  [WAIT] 8 seconds, then sending fire tick to trigger fusion flip...")
        await asyncio.sleep(8)

        await send_batch(client, [fire(85, 595, 41.0, 29.0)])
        print("\n  [DONE] FOR01 CRITICAL (with human presence) sent.")
        print("  >> Label should now read: FIRE/SMOKE DETECTED -- POSSIBLE DELIBERATE BURN OR CAMPFIRE")
        print("  >> Hold on the label for 3-4 seconds.\n")
        input("  >> Press ENTER after you have shown the flipped label on camera...")

        # ── SCENE 5 -- ALL CRITICAL ───────────────────────────────────────────
        print_scene(5, "ALL NODES CRITICAL",
            "All three hazard nodes simultaneously at maximum severity.\n"
            "Show the dashboard KPI row and map with all markers red/amber.")
        wait_enter()

        await send_batch(client, [
            urb(90, 812),
            riv(95, 148.0, 23.5),
            fire(92, 640, 43.5, 26.0),
        ])
        print("\n  [DONE] All three nodes at CRITICAL sent.")
        print("  >> Show dashboard KPI counts, map markers, hazard cards.")
        print("  >> Show Alerts page with all three nodes listed.\n")
        await asyncio.sleep(3)

        # ── SCENE 6 -- ACKNOWLEDGE ────────────────────────────────────────────
        print_scene(6, "RANGER ACKNOWLEDGES ALERT  (manual browser action)",
            "In the browser:\n"
            "  Alerts page -> click the FOR01 fire alert -> Details -> Acknowledge\n"
            "  Enter 'Ranger Arjun' when prompted.\n"
            "  Show the alert turning to acknowledged state.\n\n"
            "No data to send here -- press ENTER after the browser action.")
        input("  >> Press ENTER after acknowledging the alert on camera...")

        # ── SCENE 7 -- RECOVERY ───────────────────────────────────────────────
        print_scene(7, "RECOVERY -- returning to NORMAL",
            "All nodes return to normal readings.\n"
            "Show markers fading back to calm colours on the map.\n"
            "Show sparklines coming down in the hazard node cards.")
        wait_enter()

        await send_batch(client, [
            urb(14, 545),
            riv(22, 62.0, 3.8),
            fire(8,  290, 27.0, 61.0),
        ])
        print("\n  [DONE] Recovery readings sent. All nodes returning to NORMAL.")
        print("  >> Show map markers returning to calm colours.")
        print("  >> Final wide shot of the dashboard.\n")

        # ── DONE ─────────────────────────────────────────────────────────────
        print("=" * 60)
        print("  DEMO SIMULATION COMPLETE")
        print("  All scenes sent. Stop the recording.")
        print("=" * 60 + "\n")


if __name__ == "__main__":
    try:
        asyncio.run(run_demo())
    except KeyboardInterrupt:
        print("\n\n  [STOPPED] Demo simulator stopped.")
