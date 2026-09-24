"""
vcn1_gateway_bridge.py

Serial bridge for the Van-Chetna multi-node gateway (gateway_receiver.ino).

The gateway ESP32 prints one line per received LoRa packet to Serial at 115200:
    VCN1,<NODE_ID>,<HAZARD_TYPE>,<RISK_SCORE>,<SEVERITY>,<CONFIDENCE>,<...sensor fields...>,<TIMESTAMP_MS>|RSSI=<rssi>|SNR=<snr>

This script:
  1. Reads those lines from the gateway's USB-serial port.
  2. Parses the VCN1 CSV protocol (handles all three hazard types).
  3. HTTP-POSTs each valid reading to POST /hazard-events on the backend.

NOTE: This script handles ONLY VCN1 packets (new hazard nodes).
      The acoustic pipeline (09_node_companion.py) and the legacy JSON
      gateway bridge (gateway_forward.py) continue to operate independently
      on their own serial ports — this script does NOT touch them.

Usage:
    python vcn1_gateway_bridge.py --port COM6 --backend http://localhost:8000

Find your port:
    Windows: Device Manager → Ports (COM & LPT), e.g. COM6
    macOS:   ls /dev/tty.usb*
    Linux:   ls /dev/ttyUSB*

Packet formats parsed (from firmware comments):
    AIR_QUALITY  : VCN1,URB01,AIR_QUALITY,<RISK>,<SEV>,<CONF>,<RAW_ADC>,<TS_MS>
    WATER_LEVEL  : VCN1,RIV01,WATER_LEVEL,<RISK>,<SEV>,<CONF>,<LEVEL_CM>,<RISE_RATE>,<TS_MS>
    FIRE         : VCN1,FOR01,FIRE,<RISK>,<SEV>,<CONF>,<SMOKE_RAW>,<TEMP_C>,<HUMIDITY>,<TS_MS>

Calibration note (from firmware README):
    Risk thresholds in all three node types are MVP placeholder defaults.
    Do NOT treat NORMAL/WATCH/WARNING/CRITICAL outputs as field-validated
    values until site-specific calibration has been completed per the README.
"""

import argparse
import sys
import time
import uuid
from datetime import datetime, timezone

import requests
import serial

# ── Node-ID → static lat/lon mapping ────────────────────────────────────────
# These are placeholder deployment coordinates — update to your real site
# positions before hardware wiring tomorrow.  They are used to seed the Node
# row in the database so the frontend can place markers on the map.
NODE_COORDS: dict[str, tuple[float, float]] = {
    "URB01": (28.52050, 77.36700),   # urban/industrial site — update to real coords
    "RIV01": (28.51800, 77.36400),   # riverine monitoring point — update to real coords
    "FOR01": (28.51975, 77.36538),   # forest node (same site as acoustic node)
}


# ── VCN1 severity (uppercase from firmware) → backend lowercase ──────────────
SEVERITY_MAP: dict[str, str] = {
    "NORMAL":   "normal",
    "WATCH":    "watch",
    "WARNING":  "warning",
    "CRITICAL": "critical",
}


def parse_vcn1_line(line: str) -> dict | None:
    """
    Parse a single VCN1 gateway output line into a HazardEventIn-compatible dict.

    Returns None if the line cannot be parsed (malformed, non-VCN1, etc).

    Format expected:
        VCN1,<fields...>|RSSI=<rssi>|SNR=<snr>

    The gateway appends |RSSI=...|SNR=... — split on '|' first, then parse
    the CSV body.
    """
    line = line.strip()
    if not line.startswith("VCN1,"):
        return None

    # Split radio metadata from payload
    parts = line.split("|")
    payload_str = parts[0]   # e.g. "VCN1,URB01,AIR_QUALITY,42,WATCH,80,612,184532"

    rssi: int | None = None
    snr: float | None = None
    for part in parts[1:]:
        if part.startswith("RSSI="):
            try:
                rssi = int(part.split("=", 1)[1])
            except ValueError:
                pass
        elif part.startswith("SNR="):
            try:
                snr = float(part.split("=", 1)[1])
            except ValueError:
                pass

    fields = payload_str.split(",")
    if len(fields) < 7:
        return None   # too short to be any valid VCN1 packet

    try:
        # Common header fields (indices 0–5)
        # fields[0] = "VCN1"
        node_id    = fields[1]
        hazard_type = fields[2]   # "AIR_QUALITY" | "WATER_LEVEL" | "FIRE"
        risk_score  = int(fields[3])
        severity_fw = fields[4].upper()   # from firmware — uppercase
        confidence  = int(fields[5])

        severity = SEVERITY_MAP.get(severity_fw, "normal")

        # Sensor-specific payload fields start at index 6
        sensor_fields = fields[6:]

        sv1: float | None = None
        sv2: float | None = None
        sv3: float | None = None

        if hazard_type == "AIR_QUALITY":
            # sensor_fields: [RAW_ADC, TIMESTAMP_MS]
            if len(sensor_fields) < 2:
                return None
            sv1 = float(sensor_fields[0])   # raw ADC

        elif hazard_type == "WATER_LEVEL":
            # sensor_fields: [LEVEL_CM, RISE_RATE, TIMESTAMP_MS]
            if len(sensor_fields) < 3:
                return None
            sv1 = float(sensor_fields[0])   # water_level_cm
            sv2 = float(sensor_fields[1])   # rise_rate_cm_per_min

        elif hazard_type == "FIRE":
            # sensor_fields: [SMOKE_RAW, TEMP_C, HUMIDITY, TIMESTAMP_MS]
            if len(sensor_fields) < 4:
                return None
            sv1 = float(sensor_fields[0])   # smoke raw ADC
            sv2 = float(sensor_fields[1])   # temp °C
            sv3 = float(sensor_fields[2])   # humidity %

        else:
            # Unknown hazard type — log and skip; don't break the loop
            print(f"  [BRIDGE] Unknown hazard_type '{hazard_type}' — skipped")
            return None

    except (ValueError, IndexError) as exc:
        print(f"  [BRIDGE] Parse error ({exc}) on: {line[:80]}")
        return None

    # Unique event_id generated here — firmware timestamp + UUID suffix prevents
    # collisions if the same risk score is transmitted multiple times.
    event_id = f"vcn1_{node_id.lower()}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

    lat, lon = NODE_COORDS.get(node_id, (0.0, 0.0))

    return {
        "node_id":        node_id,
        "event_id":       event_id,
        "timestamp":      timestamp,
        "hazard_type":    hazard_type,
        "risk_score":     risk_score,
        "severity":       severity,
        "confidence":     confidence,
        "sensor_value_1": sv1,
        "sensor_value_2": sv2,
        "sensor_value_3": sv3,
        "rssi":           rssi,
        "snr":            snr,
        "lat":            lat,
        "lon":            lon,
    }


def post_hazard_event(backend_url: str, payload: dict) -> None:
    """POST a parsed hazard event to the backend."""
    endpoint = f"{backend_url}/hazard-events"
    try:
        resp = requests.post(endpoint, json=payload, timeout=5)
        sev = payload["severity"].upper()
        risk = payload["risk_score"]
        node = payload["node_id"]
        htype = payload["hazard_type"]
        status_icon = "✅" if resp.status_code == 201 else f"⚠️  HTTP {resp.status_code}"
        result = resp.json().get("status", "?")
        print(f"{status_icon} [{node}] {htype} risk={risk} sev={sev} → {result}")
    except requests.RequestException as exc:
        print(f"  [BRIDGE] POST failed: {exc}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Van-Chetna VCN1 gateway serial bridge"
    )
    parser.add_argument(
        "--port", required=True,
        help="Gateway ESP32 serial port, e.g. COM6 or /dev/ttyUSB0",
    )
    parser.add_argument(
        "--baud", type=int, default=115200,
        help="Must match gateway_receiver.ino Serial.begin() (default 115200)",
    )
    parser.add_argument(
        "--backend", default="http://localhost:8000",
        help="Backend base URL (default http://localhost:8000)",
    )
    args = parser.parse_args()

    print("🌿 Van-Chetna VCN1 Gateway Bridge")
    print(f"   Serial port : {args.port} @ {args.baud} baud")
    print(f"   Backend     : {args.backend}/hazard-events")
    print("   Press Ctrl+C to stop.\n")

    try:
        ser = serial.Serial(args.port, args.baud, timeout=5)
    except serial.SerialException as exc:
        print(f"❌ Cannot open serial port '{args.port}': {exc}")
        sys.exit(1)

    while True:
        try:
            raw = ser.readline()
        except serial.SerialException as exc:
            print(f"❌ Serial read error: {exc}")
            break

        line = raw.decode(errors="ignore").strip()
        if not line:
            continue

        # Pass through gateway diagnostic lines to stdout for visibility
        if line.startswith("[GATEWAY]"):
            print(f"  {line}")
            continue

        payload = parse_vcn1_line(line)
        if payload is None:
            # Non-VCN1 line (startup messages, dropped-packet warnings) — ignore
            if line:
                print(f"  [skip] {line[:80]}")
            continue

        post_hazard_event(args.backend, payload)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n🛑 VCN1 gateway bridge stopped.")
