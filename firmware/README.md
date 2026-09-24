# Van-Chetna Firmware — Setup & Flashing Guide

## Folder structure

```
firmware/
├── urban_node/urban_node.ino            → flash to Urban/Industrial ESP32
├── riverine_node/riverine_node.ino       → flash to Riverine ESP32
├── gateway_receiver/gateway_receiver.ino → flash to a 4th ESP32 acting as base station
└── forest_fire_addon/forest_fire_addon.ino → MERGE into your existing forest-node sketch, don't flash directly
```

Each folder name matches its .ino filename — this is required by the Arduino IDE. Open each folder's .ino directly in Arduino IDE, don't rename or move files independently.

## Required libraries (install via Arduino IDE → Library Manager)

- **LoRa** by Sandeep Mistry — used by all 4 sketches
- **DHT sensor library** by Adafruit — used only by the forest fire add-on (also auto-installs "Adafruit Unified Sensor")

## Board settings (all nodes)

- Board: **ESP32 Dev Module**
- Upload Speed: 921600 (or 115200 if you get upload errors)
- Flash Frequency: 80MHz
- Partition Scheme: Default

## Flashing order (recommended)

1. **Gateway first** — flash `gateway_receiver.ino` to a spare ESP32, connect it to your laptop/backend machine via USB, open Serial Monitor at 115200 baud. This is your "always listening" base station for testing every other node as you bring them up.
2. **Urban node** — flash `urban_node.ino`. Watch its own Serial Monitor for baseline priming and TX logs, and confirm the Gateway's Serial Monitor shows matching received packets.
3. **Riverine node** — same process with `riverine_node.ino`.
4. **Forest node** — do NOT flash `forest_fire_addon.ino` directly. Open your existing working forest-node sketch and merge in the marked sections per the instructions at the top of that file. Recompile and reflash your existing sketch (now with fire/smoke added), and confirm both acoustic and fire packets arrive at the Gateway.

## Critical settings: LoRa Frequency + Sync Word (verified against existing forest node)

Your existing `lora_sender.ino`/`node_main.ino` use **866E6** and never call `setSyncWord()` (library default `0x34` applies). All four new sketches have been corrected to match exactly:

- `LORA_FREQ` = `866E6` (was originally written as `868E6` — fixed to match your real hardware)
- `LoRa.setSyncWord(0x34)` (was originally `0xF3` — fixed to match your existing node's default)

Both values are now identical across `urban_node.ino`, `riverine_node.ino`, `gateway_receiver.ino`, and your existing forest node code. **Do not change these again without updating all nodes together** — a mismatch on either value means zero radio communication with no error shown on either end.

## Packet protocol (shared format)

```
VCN1,<NODE_ID>,<HAZARD_TYPE>,<RISK_SCORE 0-100>,<SEVERITY>,<CONFIDENCE 0-100>,<sensor-specific fields...>,<TIMESTAMP_MS>
```

Examples:
```
VCN1,URB01,AIR_QUALITY,42,WATCH,80,612,184532
VCN1,RIV01,WATER_LEVEL,75,WARNING,90,142.3,18.2,201044
VCN1,FOR01,FIRE,60,WATCH,85,410,32.1,45.2,215880
```

The Gateway appends `|RSSI=<value>|SNR=<value>` before forwarding to the backend over Serial — Krrish's ingestion service should parse on the `|` delimiter first, then the `,` fields.

## Before trusting any live alert — calibration checklist

Every risk-scoring function in this firmware uses **placeholder thresholds** built for a working MVP demo, not verified field-calibrated values. Before relying on these for real alerts (or even a convincing live demo), do the following for each node:

- **Urban (air quality):** Let the 20-sample rolling baseline prime in a genuinely clean-air location first. Test response by introducing a known pollutant source (e.g., a lit incense stick from a safe distance) and confirm severity escalates as expected.
- **Riverine (water level):** Physically measure `SENSOR_MOUNT_HEIGHT_CM` on-site and update the constant. The default 200cm is a placeholder. Test rate-of-rise scoring by simulating a rising water level (e.g., raising a reflective object toward the sensor at a known rate).
- **Forest (fire/smoke):** Let the MQ-2 complete its 24–48hr burn-in before calibrating. Recalibrate the temp/humidity reference ranges in `readAndScoreFire()` against actual ambient forest conditions at your test site, not generic defaults.

## Known limitations to mention honestly in your demo/report

- Risk thresholds are rule-based MVP defaults, not learned from real historical hazard data at each site — this is explicitly scoped as a Phase 2 improvement.
- HC-SR04 has a real-world range/accuracy limit (~2cm–400cm, ±0.3cm ideal conditions) and is sensitive to angle/surface — a real deployment would likely upgrade to a radar or pressure-based water level sensor; HC-SR04 is a cost-effective MVP stand-in.
- MQ-2/MQ-135 are semiconductor gas sensors — good for relative anomaly detection, not calibrated absolute ppm readings without a proper reference-gas calibration process.
