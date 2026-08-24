"""
gateway_forward.py

Gateway host bridge for Node B (the LoRa receiver ESP32).

Node B receives LoRa packets and prints them to serial as:
    Received: {"node_id": "...", "class": "chainsaw", ...}

This script reads those lines, extracts the JSON event, and HTTP-POSTs it to
the backend /events endpoint so it flows into fusion -> WebSocket -> dashboard.

Run on the laptop that Node B is plugged into:
    python gateway_forward.py --port /dev/tty.usbserial-YYYY

Find the port (macOS):   ls /dev/tty.usb*
Find the port (Windows): Device Manager -> Ports (COM & LPT), e.g. COM6
"""

import argparse
import json

import requests
import serial


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", required=True,
                        help="Node B serial port, e.g. /dev/tty.usbserial-YYYY or COM6")
    parser.add_argument("--baud", type=int, default=115200,
                        help="Must match lora_receiver.ino Serial.begin() (115200)")
    parser.add_argument("--backend", default="http://localhost:8000/events",
                        help="Backend events endpoint")
    args = parser.parse_args()

    ser = serial.Serial(args.port, args.baud, timeout=5)
    print(f"Gateway forwarding Node B ({args.port}) -> {args.backend}")

    while True:
        line = ser.readline().decode(errors="ignore").strip()
        if not line.startswith("Received:"):
            continue

        payload = line[len("Received:"):].strip()
        try:
            event = json.loads(payload)
        except json.JSONDecodeError:
            print(f"  skipped non-JSON line: {payload[:60]}")
            continue

        try:
            resp = requests.post(args.backend, json=event, timeout=5)
            print(f"POST /events -> {resp.status_code}  "
                  f"{event.get('node_id')} / {event.get('class')} "
                  f"({event.get('confidence')})")
        except requests.RequestException as exc:
            print(f"  backend POST failed: {exc}")


if __name__ == "__main__":
    main()
