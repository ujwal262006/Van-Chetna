"""
simulate_hazard.py

Simulates VCN1 hazard-node packets by HTTP-POSTing directly to
POST /hazard-events, exactly as vcn1_gateway_bridge.py would do after
parsing them from the gateway serial port.

Use this tonight to validate the full backend+frontend integration pipeline
WITHOUT real hardware.  Runs alongside the existing simulate.py (which
covers acoustic/vision nodes) without conflict.

Run (from the backend/ directory or repo root):
    python backend/simulate_hazard.py

Press Ctrl+C to stop.

Three simulated scenarios are interleaved on a realistic timing cycle:
  URB01 — Air Quality: slowly rising ADC, escalates from NORMAL → CRITICAL
  RIV01 — Water Level: rising water + rate-of-rise, escalates to WARNING
  FOR01 — Fire/Smoke: combined smoke + heat signal, correlates with acoustic
          silence to trigger the UNATTENDED_FIRE_RISK cross-signal case

Test coverage targets:
  [T1] All three VCN1 hazard types parse and store correctly
  [T2] Severity ladder: NORMAL/WATCH/WARNING/CRITICAL all appear in DB
  [T3] Node upsert: URB01/RIV01/FOR01 appear in GET /nodes/status
  [T4] GET /hazard-events returns readings for all three nodes
  [T5] GET /hazard-events/FOR01/history returns time-series
  [T6] Fusion engine produces Threat+Alert for WATCH and above
  [T7] Cross-signal fire case: when FOR01 fire risk ≥ WARNING and no recent
       acoustic activity, the Threat label contains UNATTENDED
  [T8] GET /alerts returns hazard-sourced alerts alongside acoustic ones
  [T9] GET /nodes/summary returns latest_hazard for each hazard node
  [T10] Existing acoustic alerts (from simulate.py) are unaffected
"""

import asyncio
import random
import time
import uuid
from datetime import datetime, timezone

import httpx

API_URL = "http://localhost:8000"

# ── Scenario state ────────────────────────────────────────────────────────────

# URB01: air quality rising over ~2 minutes (20 ticks × 6s)
urb_tick = 0
urb_baseline = 520.0

# RIV01: water level rising steadily
riv_level = 60.0     # starting water level cm
riv_rise_rate = 8.0  # cm/min — will ramp up

# FOR01: fire/smoke cycle — low at first, then escalates
for_tick = 0


def gen_event_id(node: str) -> str:
    return f"vcn1_{node.lower()}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4]}"


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def severity_from_risk(risk: int) -> str:
    if risk < 25:  return "normal"
    if risk < 50:  return "watch"
    if risk < 80:  return "warning"
    return "critical"


# ── Per-node payload builders ─────────────────────────────────────────────────

def build_urb01_payload() -> dict:
    """
    Simulate gradual air quality degradation: first 6 ticks are NORMAL,
    then rises through WATCH → WARNING → CRITICAL.
    """
    global urb_tick, urb_baseline
    # Simulate a pollution event: raw ADC rises from baseline
    deviation_pct = min(urb_tick * 7.0, 95.0)  # 0% → 95% over 14 ticks
    raw_adc = int(urb_baseline * (1 + deviation_pct / 100.0) + random.uniform(-10, 10))

    if deviation_pct < 15:
        risk, severity = int(deviation_pct / 15 * 25), "NORMAL"
        confidence = 85
    elif deviation_pct < 40:
        risk = int(25 + (deviation_pct - 15) / 25 * 25)
        severity, confidence = "WATCH", 80
    elif deviation_pct < 80:
        risk = int(50 + (deviation_pct - 40) / 40 * 30)
        severity, confidence = "WARNING", 85
    else:
        risk, severity, confidence = 90, "CRITICAL", 90

    urb_tick += 1

    return {
        "node_id":        "URB01",
        "event_id":       gen_event_id("URB01"),
        "timestamp":      now_iso(),
        "hazard_type":    "AIR_QUALITY",
        "risk_score":     max(0, min(100, risk)),
        "severity":       severity.lower(),
        "confidence":     confidence,
        "sensor_value_1": float(raw_adc),
        "sensor_value_2": None,
        "sensor_value_3": None,
        "rssi":           random.randint(-100, -75),
        "snr":            round(random.uniform(6.0, 12.0), 1),
        "lat":            28.52050,
        "lon":            77.36700,
    }


def build_riv01_payload() -> dict:
    """
    Simulate water level rising with increasing rate-of-rise.
    Escalates from WATCH → WARNING over ~2 minutes.
    """
    global riv_level, riv_rise_rate

    # Accelerating rise: level goes up by rise_rate/10 each tick (10 ticks/min)
    riv_level = min(200.0, riv_level + riv_rise_rate / 10.0 + random.uniform(-0.5, 0.5))
    riv_rise_rate = min(25.0, riv_rise_rate + 0.5)   # rate accelerates slightly

    # Mirror firmware scoring: levelScore + riseScore
    level_score = max(0, min(60, int(riv_level / 150.0 * 60)))
    rise_score  = max(0, min(40, int(riv_rise_rate / 20.0 * 40)))
    risk = level_score + rise_score
    severity = severity_from_risk(risk)

    return {
        "node_id":        "RIV01",
        "event_id":       gen_event_id("RIV01"),
        "timestamp":      now_iso(),
        "hazard_type":    "WATER_LEVEL",
        "risk_score":     max(0, min(100, risk)),
        "severity":       severity,
        "confidence":     90,
        "sensor_value_1": round(riv_level, 1),
        "sensor_value_2": round(riv_rise_rate, 1),
        "sensor_value_3": None,
        "rssi":           random.randint(-100, -80),
        "snr":            round(random.uniform(5.0, 10.0), 1),
        "lat":            28.51800,
        "lon":            77.36400,
    }


def build_for01_payload(phase: str = "normal") -> dict:
    """
    Fire/smoke node.  Three phases:
      'normal'  — low risk, below baseline (NORMAL severity)
      'watch'   — moderate smoke + temp rise (WATCH severity)
      'warning' — high smoke + heat + low humidity (WARNING → crosses the
                  UNATTENDED_FIRE_RISK threshold when acoustic is quiet)

    NOTE: the backend's cross-signal disambiguation rule requires that
    no recent acoustic activity (confidence ≥ 0.5) exists in the DB.
    For this to trigger cleanly in simulation, run this script WITHOUT
    running simulate.py simultaneously — or run the acoustic simulator
    with class='normal' only.
    """
    global for_tick
    for_tick += 1

    if phase == "normal":
        smoke_raw = random.randint(260, 320)
        temp_c    = round(random.uniform(24.0, 28.0), 1)
        humidity  = round(random.uniform(55.0, 70.0), 1)
    elif phase == "watch":
        smoke_raw = random.randint(380, 450)
        temp_c    = round(random.uniform(30.0, 36.0), 1)
        humidity  = round(random.uniform(45.0, 55.0), 1)
    else:  # warning
        smoke_raw = random.randint(500, 650)
        temp_c    = round(random.uniform(38.0, 44.0), 1)
        humidity  = round(random.uniform(28.0, 40.0), 1)

    # Mirror firmware scoring (approximate — exact formula is in forest_fire_addon.ino)
    baseline   = 300.0
    smoke_dev  = max(0.0, (smoke_raw - baseline) / baseline * 100.0)
    smoke_score = max(0, min(60, int(smoke_dev / 100.0 * 60)))
    temp_score  = max(0, min(25, int((temp_c - 25.0) / 20.0 * 25)))
    humid_score = max(0, min(15, int((100.0 - humidity - 30.0) / 40.0 * 15)))
    risk = smoke_score + temp_score + humid_score
    severity = severity_from_risk(risk)

    signals_elevated = (
        (1 if smoke_score > 20 else 0) +
        (1 if temp_score  > 10 else 0) +
        (1 if humid_score >  5 else 0)
    )
    confidence = 60 + signals_elevated * 10

    return {
        "node_id":        "FOR01",
        "event_id":       gen_event_id("FOR01"),
        "timestamp":      now_iso(),
        "hazard_type":    "FIRE",
        "risk_score":     max(0, min(100, risk)),
        "severity":       severity,
        "confidence":     confidence,
        "sensor_value_1": float(smoke_raw),
        "sensor_value_2": temp_c,
        "sensor_value_3": humidity,
        "rssi":           random.randint(-90, -70),
        "snr":            round(random.uniform(8.0, 12.0), 1),
        "lat":            28.51975,
        "lon":            77.36538,
    }


# ── HTTP poster ───────────────────────────────────────────────────────────────

async def post_hazard(client: httpx.AsyncClient, payload: dict) -> None:
    node  = payload["node_id"]
    htype = payload["hazard_type"]
    risk  = payload["risk_score"]
    sev   = payload["severity"].upper()

    try:
        resp = await client.post(f"{API_URL}/hazard-events", json=payload)
        status_icon = "✅" if resp.status_code == 201 else f"⚠️  HTTP {resp.status_code}"
        result = resp.json().get("status", "?")
        print(f"{status_icon} [{node}] {htype:12s} risk={risk:3d} sev={sev:8s} → {result}")
    except Exception as exc:
        print(f"❌ [{node}] Error: {exc}")


# ── Main simulation loop ──────────────────────────────────────────────────────

async def main() -> None:
    print("🌿 Van-Chetna Hazard Node Simulator")
    print(f"   Sending events to {API_URL}/hazard-events")
    print("   Scenarios: URB01 (escalating air quality) · RIV01 (rising water) · FOR01 (fire phases)")
    print("   Press Ctrl+C to stop.\n")

    # Fire phase schedule: first 4 sends = normal, next 4 = watch, then warning
    fire_phases = ["normal"] * 4 + ["watch"] * 4 + ["warning"] * 100

    tick = 0
    async with httpx.AsyncClient(timeout=10) as client:
        while True:
            fire_phase = fire_phases[min(tick, len(fire_phases) - 1)]

            # Send all three nodes on each tick
            await post_hazard(client, build_urb01_payload())
            await asyncio.sleep(0.3)
            await post_hazard(client, build_riv01_payload())
            await asyncio.sleep(0.3)
            await post_hazard(client, build_for01_payload(fire_phase))

            tick += 1
            interval = random.uniform(5.0, 8.0)
            print(f"   — tick {tick}, fire phase: {fire_phase}  (next in {interval:.1f}s)")
            await asyncio.sleep(interval)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n🛑 Hazard simulator stopped.")
