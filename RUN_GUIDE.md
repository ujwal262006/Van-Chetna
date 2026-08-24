# Van-Chetna (Forest Guard) — MVP Run Guide

How to run the whole system end to end: hardware (Node A sender, Node B receiver),
backend, and frontend, and how they all connect.

---

## First, the key question: does the receiver/sender code run on the laptop?

**No.** The `.ino` files run **on the ESP32 boards, not the laptop**.

- `lora_sender.ino` / `node_main.ino` → flashed onto **Node A** (the ESP32 with the mic).
- `lora_receiver.ino` → flashed onto **Node B** (the ESP32 that receives).

You use the laptop (Arduino IDE) only to **compile and upload** the code onto each board
over USB. After upload, each ESP32 runs its own program independently.

Two supporting programs DO run on a laptop/Pi:

- **`09_node_companion.py`** — runs on the laptop that Node A is plugged into. It does the
  actual AI classification (Node A just streams raw audio to it and gets a result back).
- **A gateway host** — the laptop that Node B is plugged into. It reads the JSON that Node B
  prints to serial and HTTP-POSTs it to the backend.

### Can this all be one laptop?

For a **demo on one table, yes** — one laptop can host the companion (Node A), the gateway
reader (Node B), the backend, and the frontend at once, as long as both ESP32s are plugged
into that laptop on two different USB ports.

In a **real deployment** they're separate: Node A + its companion sit in the forest; Node B +
gateway sit at a ranger station with internet. They only talk over LoRa radio.

---

## System overview (who talks to whom)

```
[Mic] --I2S--> [Node A ESP32] --USB serial--> [Companion 09_node_companion.py]
                     |                                    |
                     |<---- JSON result (serial) ---------|
                     |
                  LoRa 866 MHz
                     |
                     v
              [Node B ESP32] --USB serial--> [Gateway host reads serial]
                                                     |
                                              HTTP POST /events
                                                     v
                                          [Backend FastAPI + Postgres]
                                                     |
                                          WebSocket /ws/live + REST
                                                     v
                                          [Frontend dashboard :5173]
```

---

## Part 1 — Backend (run this first)

Everything downstream needs the backend, so start here. Runs on any laptop/server.

1. Install PostgreSQL 3.11+ and Python 3.11+, then create the database:
   ```bash
   createdb forest_guard
   ```
   Or with Docker:
   ```bash
   docker run -d --name forest-guard-db \
     -e POSTGRES_PASSWORD=postgres \
     -e POSTGRES_DB=forest_guard \
     -p 5432:5432 postgres:16
   ```

2. Install dependencies and configure env:
   ```bash
   cd backend
   pip install -r requirements.txt
   cp .env.example .env
   ```
   Default `.env` works for local Postgres. Note `CORS_ORIGINS` already allows the frontend
   at `http://localhost:5173`.

3. Start the server:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```
   Tables auto-create on startup. Confirm it's up: open http://localhost:8000/docs

4. (Optional) Seed sample nodes/events so the dashboard isn't empty:
   ```bash
   python seed.py
   ```

Leave this terminal running.

---

## Part 2 — Frontend

Runs on any laptop; point it at the backend from Part 1.

1. Install and configure:
   ```bash
   cd frontend
   npm install
   cp .env.example .env
   ```

2. Edit `frontend/.env` to talk to the real backend (not mock data):
   ```env
   VITE_API_URL=http://localhost:8000
   VITE_DEMO_MODE=false
   ```
   > If you set `VITE_DEMO_MODE=true`, the dashboard runs standalone on fake data with no
   > backend or hardware — useful for a UI-only demo.

3. Start it:
   ```bash
   npm run dev
   ```
   Open http://localhost:5173

At this point backend + frontend are connected. You can verify the full software path
without any hardware using the simulator below.

---

## Part 3 — Software-only test (no hardware)

Best way to confirm backend + frontend work before touching ESP32s. In a new terminal:

```bash
cd backend
pip install httpx
python simulate.py
```

This POSTs randomized events to `/events` every few seconds. Watch the dashboard: alerts
should appear live (toast + map marker), KPIs update, and the alert feed fills. If this
works, your software stack is correct and any later problem is in the hardware/companion.

---

## Part 4 — Hardware: build and test in order

> Build **Node B first** (it's simpler), confirm the LoRa link, then build Node A.

### Prereqs in Arduino IDE (one time)

- Install the **ESP32 board package** (Boards Manager → "esp32" by Espressif).
- Install libraries (Library Manager): **LoRa** (by Sandeep Mistry) and **ArduinoJson**.
- Select board: **ESP32 Dev Module**. Pick the correct **Port** each time you plug a board in.

### Step 4a — Flash Node B (receiver)

1. Wire Node B per the header comment in `firmware/lora_receiver.ino`
   (RA-01H: NSS=D5, RST=D14, DIO0=D26, SCK=D18, MISO=D19, MOSI=D23, 3V3, GND).
2. Plug Node B into the laptop, open `lora_receiver.ino`, upload.
3. Open Serial Monitor at **115200 baud**. You should see `Node B ready`.

### Step 4b — Flash Node A and test the LoRa link

Before wiring the mic, prove the radios talk:

1. Wire Node A's RA-01H identically to Node B.
2. Open `firmware/lora_sender.ino`, upload it to Node A.
3. Open Node A's Serial Monitor at **115200** — you'll see `Sent: {...}` every 3 s.
4. On Node B's Serial Monitor you should see `Received: {...}` with the same JSON.

If Node B prints the packets, the LoRa link works. If not, recheck DIO0=D26 and the antenna.

### Step 4c — Wire the mic and flash the real Node A firmware

1. Add the INMP441 to Node A per the header in `firmware/node_main.ino`
   (mic: SCK=D27, WS=D25, SD=D32, L/R=GND, VDD=3V3, GND).
2. (Optional) Upload `mic_test.ino` first, open Serial Monitor at 115200, tap the mic and
   confirm the printed `sample:` numbers move. Then move on.
3. Upload `node_main.ino` to Node A. It now streams audio over serial at **921600 baud**
   and waits for the companion's reply.

---

## Part 5 — Companion (AI) for Node A

The companion needs the trained model. It must run from the `Van-Chetna/` folder so the
relative paths resolve (`models/best_model_yamnet.keras`, `features_yamnet/classes.txt`).

1. Install deps (same env used for training scripts 05/06/07):
   ```bash
   pip install pyserial numpy tensorflow tensorflow_hub
   ```

2. Sanity-check the AI logic with no hardware:
   ```bash
   python 09_node_companion.py --selftest
   ```

3. Run against Node A. Find the port (macOS: something like `/dev/tty.usbserial-XXXX`;
   Windows: `COM5`). Plug in Node A, close its Arduino Serial Monitor (only one program
   can own the port), then:
   ```bash
   python 09_node_companion.py --port /dev/tty.usbserial-XXXX
   ```
   Make noise near the mic. On a confirmed threat (chainsaw/fire/vehicle, confidence ≥ 0.7,
   two windows in a row) it prints `SENT TO ESP32 FOR LoRa` and writes the JSON back to
   Node A, which LoRa-transmits it.

> Before a real demo, edit `NODE_ID`, `NODE_LAT`, `NODE_LON` near the top of
> `09_node_companion.py` to your actual location so the map marker lands correctly.

---

## Part 6 — Gateway host for Node B (serial → backend)

Node B prints received JSON to serial as `Received: {...}`. A small host program reads that
line, extracts the JSON, and POSTs it to the backend. This bridge script isn't in the repo
yet — here's a minimal one. Save it as `gateway_forward.py` in `Van-Chetna/` and run it on
the laptop where Node B is plugged in.

```python
import re, json, requests, serial

PORT = "/dev/tty.usbserial-YYYY"   # Node B's port
BACKEND = "http://localhost:8000/events"

ser = serial.Serial(PORT, 115200, timeout=5)
print("Gateway forwarding Node B -> backend...")
while True:
    line = ser.readline().decode(errors="ignore").strip()
    if not line.startswith("Received:"):
        continue
    payload = line[len("Received:"):].strip()
    try:
        event = json.loads(payload)
    except json.JSONDecodeError:
        continue
    r = requests.post(BACKEND, json=event, timeout=5)
    print(f"POST /events -> {r.status_code}  {event.get('class')}")
```

Run it (install deps first):
```bash
pip install pyserial requests
python gateway_forward.py
```

Now a confirmed detection travels: Node A mic → companion → Node A LoRa → Node B → this
gateway script → backend `/events` → fusion → WebSocket → dashboard alert.

---

## Full startup order (single-laptop demo)

Open several terminals on the one laptop (both ESP32s plugged into two USB ports):

1. **Terminal 1** — backend: `uvicorn app.main:app --reload --port 8000`
2. **Terminal 2** — frontend: `npm run dev` (in `frontend/`, with `VITE_DEMO_MODE=false`)
3. Flash **Node B** (`lora_receiver.ino`) and **Node A** (`node_main.ino`), then close their
   Arduino Serial Monitors.
4. **Terminal 3** — companion: `python 09_node_companion.py --port <Node A port>`
5. **Terminal 4** — gateway: `python gateway_forward.py` (pointed at Node B's port)
6. Open http://localhost:5173 and trigger a sound near Node A's mic.

No hardware handy? Skip steps 3–5 and run `python backend/simulate.py` instead — the
dashboard behaves identically.

---

## Quick troubleshooting

- **Port busy / can't open serial:** close the Arduino Serial Monitor; only one program can
  hold a port. The companion and Arduino Monitor can't share Node A at the same time.
- **Node B receives nothing:** check DIO0 is on **D26** (not the old D2), antenna soldered,
  both boards on 866 MHz.
- **Companion can't find model:** run it from the `Van-Chetna/` folder; confirm
  `models/best_model_yamnet.keras` and `features_yamnet/classes.txt` exist (run scripts
  05 and 06 first if not).
- **Dashboard empty / CORS error:** set `VITE_DEMO_MODE=false`, confirm `VITE_API_URL` points
  at the backend, and that the backend's `CORS_ORIGINS` includes `http://localhost:5173`.
- **Baud mismatch:** Node A firmware and the companion must both be **921600**; Node B and
  the gateway must both be **115200**.
