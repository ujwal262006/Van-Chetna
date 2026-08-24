# Van-Chetna — One-Laptop Presentation Guide

Everything running on a single laptop for a live demo: backend, frontend, both ESP32s
(Node A mic sender + Node B receiver), the AI companion, and the gateway bridge.

This is the demo-day cheat sheet. For deployment details and wiring, see `RUN_GUIDE.md`.

---

## What you'll have open

- **4 terminal windows** (backend, frontend, companion, gateway)
- **1 browser tab** → the dashboard
- **2 ESP32 boards** plugged into 2 USB ports
- Arduino IDE (only to flash the boards; close its Serial Monitor after)

---

## The night before (do this once, not on stage)

Getting these done ahead of time is what separates a smooth demo from a scramble.

1. **Backend deps + database exist:**
   ```bash
   cd backend
   pip install -r requirements.txt httpx
   createdb forest_guard        # or start the Postgres Docker container
   cp .env.example .env
   ```

2. **Frontend deps + demo pointed at real backend:**
   ```bash
   cd frontend
   npm install
   cp .env.example .env
   ```
   Edit `frontend/.env`:
   ```env
   VITE_API_URL=http://localhost:8000
   VITE_DEMO_MODE=false
   ```

3. **Companion deps + model present:**
   ```bash
   pip install pyserial requests numpy tensorflow tensorflow_hub
   ```
   Confirm these exist (run training scripts 05 then 06 if not):
   `models/best_model_yamnet.keras` and `features_yamnet/classes.txt`

4. **Set your demo location** in `09_node_companion.py` (near the top) so the map marker
   lands where you say it does:
   ```python
   NODE_ID  = "NODE_01"
   NODE_LAT = 21.1466     # your venue / demo coordinates
   NODE_LON = 79.0889
   ```

5. **Flash both boards** (see `RUN_GUIDE.md` Part 4):
   - Node B ← `firmware/lora_receiver.ino`
   - Node A ← `firmware/node_main.ino`
   Verify once that Node B receives a test packet, then **close all Arduino Serial Monitors**
   (a monitor holding a port blocks the Python scripts).

6. **Find and note both serial ports** so you're not hunting during the demo:
   ```bash
   ls /dev/tty.usb*        # macOS  (Windows: check Device Manager -> Ports)
   ```
   Write down which port is Node A (mic) and which is Node B (receiver).

7. **Do one full dry run** end to end. Then quit everything.

---

## On stage — startup order (4 terminals)

Start them in this order. Plug both ESP32s in first and close any Arduino Serial Monitor.

### Terminal 1 — Backend
```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```
Wait for it to say it's running. Optional: seed a little history so the dashboard isn't
blank when you open it:
```bash
python seed.py      # run once, in another shell, then close it
```

### Terminal 2 — Frontend
```bash
cd frontend
npm run dev
```
Open the URL it prints (http://localhost:5173). Leave the dashboard on screen.

### Terminal 3 — Companion (Node A / the AI)
```bash
python 09_node_companion.py --port <NODE_A_PORT>
```
Example: `python 09_node_companion.py --port /dev/tty.usbserial-0001`
It loads YAMNet + the classifier, then prints a line per audio window.

### Terminal 4 — Gateway (Node B → backend)
```bash
python gateway_forward.py --port <NODE_B_PORT>
```
Example: `python gateway_forward.py --port /dev/tty.usbserial-0002`
It prints `POST /events -> 200` each time Node B relays a detection.

---

## The live moment

1. Make a chainsaw / vehicle / loud human sound near Node A's mic (a chainsaw clip on your
   phone works great).
2. Terminal 3 (companion) shows the class and confidence climbing; on 2 confirmed windows
   it prints `SENT TO ESP32 FOR LoRa`.
3. Node A transmits over LoRa → Node B receives → Terminal 4 prints `POST /events -> 200`.
4. The dashboard pops a **toast**, drops a **colored marker** on the map, and the alert
   appears in the feed. Click it to show the **AI confidence breakdown**, then
   **Acknowledge** it as the officer would.

That's the full "sound in the forest → officer alerted" story in one motion.

---

## Safety net — if hardware misbehaves on stage

Keep this ready. It drives the exact same backend + dashboard with zero hardware, so the
demo never dies:

```bash
cd backend
python simulate.py
```

It POSTs realistic events every few seconds; the dashboard lights up identically. You can
narrate it as "here's the system under a stream of field events." If a board flakes out,
switch to this and keep talking — nobody needs to know.

Alternatively, a **pure-frontend** fallback needs nothing else running at all: set
`VITE_DEMO_MODE=true` in `frontend/.env`, restart `npm run dev`, and the dashboard
self-generates mock alerts.

---

## 30-second recovery checklist

- **Companion won't open port** → an Arduino Serial Monitor is still holding it. Close it.
- **Node B relays nothing** → confirm both boards powered, antenna on, DIO0 = D26, 866 MHz.
- **Dashboard blank or CORS error** → `VITE_DEMO_MODE=false`, `VITE_API_URL=http://localhost:8000`,
  backend running.
- **Everything's flaky** → `python backend/simulate.py` and carry on.
- **Baud rates**: Node A + companion = 921600; Node B + gateway = 115200.

---

## One-glance startup summary

| # | Terminal | Command | Purpose |
|---|----------|---------|---------|
| 1 | Backend | `uvicorn app.main:app --reload --port 8000` | API + fusion + WebSocket |
| 2 | Frontend | `npm run dev` (in `frontend/`) | Dashboard on :5173 |
| 3 | Companion | `python 09_node_companion.py --port <NODE_A>` | AI classification for Node A |
| 4 | Gateway | `python gateway_forward.py --port <NODE_B>` | Node B serial → backend |
| — | Fallback | `python backend/simulate.py` | Runs the demo with no hardware |
