# Forest Guard / Van-Chetna — Shared Schemas

This is the single source of truth for every data shape that crosses a
boundary between team members' code. If you're building backend, frontend,
or firmware, build against THIS document, not against guesses. If this needs
to change, update it here first and tell the team — don't silently drift.

---

## 1. LoRa Payload (Firmware → Gateway → Backend)

This is what an ESP32 node sends over LoRa when it detects something. Member 2's
`lora_sender.ino` already implements this exact shape.

```json
{
  "node_id": "NODE_01",
  "event_id": "evt_1755123456789",
  "timestamp": "2026-08-15T14:31:22Z",
  "sensor_type": "acoustic",
  "class": "chainsaw",
  "confidence": 0.91,
  "battery_pct": 78,
  "lat": 30.4520,
  "lon": 77.5890
}
```

| Field | Type | Notes |
|---|---|---|
| `node_id` | string | e.g. `"NODE_01"`, `"NODE_02"` — identifies which physical sensor node |
| `event_id` | string | Unique per event, format `evt_<epoch millis>` |
| `timestamp` | string (ISO8601, UTC) | When the event was detected |
| `sensor_type` | string | `"acoustic"` or `"vision"` |
| `class` | string | Lowercase, underscore-free: `"chainsaw"`, `"fire"`, `"vehicle"`, `"human_activity"`, `"animal"`, `"normal_environmental"`, or for vision: `"person"`, `"vehicle"` |
| `confidence` | float | 0.0–1.0 |
| `battery_pct` | int | 0–100, node's battery level |
| `lat`, `lon` | float | Node's fixed GPS coordinates |

---

## 2. Fusion Engine Output (Backend internal, after combining events)

This is what `acoustic-ai/08_fusion_engine.py`'s `fuse_events()` / `process_event_batch()`
produces. The backend calls this whenever new events arrive within the same
30-second window, and this is what gets stored as a `threat` + surfaced as an `alert`.

```json
{
  "fused_score": 0.94,
  "label": "POSSIBLE ILLEGAL LOGGING — HIGH CONFIDENCE",
  "severity": "critical",
  "acoustic_confidence": 0.91,
  "vision_person_confidence": 0.87,
  "vision_vehicle_confidence": 0.76,
  "acoustic_class": "chainsaw",
  "node_id": "NODE_01",
  "generated_at": "2026-08-15T14:31:35.123456+00:00"
}
```

| Field | Type | Notes |
|---|---|---|
| `fused_score` | float | 0.0–1.0, combined threat score |
| `label` | string | One of: `"POSSIBLE ILLEGAL LOGGING — HIGH CONFIDENCE"`, `"SUSPICIOUS ACTIVITY — VERIFY"`, `"LOW CONFIDENCE / MONITOR"` |
| `severity` | string | `"critical"` \| `"medium"` \| `"low"` — use this for UI color-coding, not `label` |
| `acoustic_confidence`, `vision_person_confidence`, `vision_vehicle_confidence` | float | 0.0 if that sensor didn't report anything in this window |
| `acoustic_class` | string or null | The specific detected class, e.g. `"chainsaw"` |
| `node_id` | string | Primary node this event is associated with |
| `generated_at` | string (ISO8601, UTC) | When the fusion engine produced this result |

**Alert threshold for the dashboard:** only `severity: "critical"` and `severity: "medium"` should show as active alerts. `"low"` severity events should be logged for analytics but NOT push a live alert — otherwise you'll flood the dashboard with noise.

---

## 3. Backend REST API (Member 3 builds this)

| Endpoint | Method | Purpose |
|---|---|---|
| `/events` | POST | Gateway posts a raw LoRa-payload-shaped event here (schema in section 1) |
| `/events` | GET | Dashboard fetches recent raw events |
| `/alerts` | GET | Dashboard fetches fused/scored alerts (schema in section 2, plus a DB-assigned `id`) |
| `/alerts/{id}/acknowledge` | POST | Officer acknowledges an alert. Body: `{"acknowledged_by": "officer_name"}` |
| `/nodes/status` | GET | Returns all nodes with `node_id`, `last_seen`, `battery_pct`, `status` (`"online"`/`"offline"`) |
| `/ws/live` | WebSocket | Pushes new alerts to the dashboard in real time as they're created |

## 4. Database Schema (Member 3 builds this)

```sql
nodes (
  node_id TEXT PRIMARY KEY,
  node_type TEXT,          -- 'acoustic' | 'vision'
  lat FLOAT, lon FLOAT,
  last_seen TIMESTAMP,
  battery_pct INT,
  status TEXT               -- 'online' | 'offline'
);

acoustic_events (
  id SERIAL PRIMARY KEY,
  node_id TEXT REFERENCES nodes(node_id),
  class TEXT,
  confidence FLOAT,
  recorded_at TIMESTAMP
);

vision_events (
  id SERIAL PRIMARY KEY,
  node_id TEXT REFERENCES nodes(node_id),
  class TEXT,
  confidence FLOAT,
  recorded_at TIMESTAMP
);

threats (
  id SERIAL PRIMARY KEY,
  fused_score FLOAT,
  label TEXT,
  severity TEXT,
  node_id TEXT REFERENCES nodes(node_id),
  created_at TIMESTAMP
);

alerts (
  id SERIAL PRIMARY KEY,
  threat_id INT REFERENCES threats(id),
  acknowledged BOOLEAN DEFAULT FALSE,
  acknowledged_by TEXT,
  acknowledged_at TIMESTAMP
);
```

---

## 5. Frontend expectations (Member 4 builds against this)

- **Map markers:** color by `severity` (`critical` = red, `medium` = orange, `low` = not shown as alert)
- **Alert detail view:** show `label`, `acoustic_confidence`/`vision_*_confidence` breakdown, `node_id`, timestamp — matches the mockup in the architecture doc
- **Node health panel:** `battery_pct`, `status`, `last_seen` per node from `/nodes/status`
- **Live updates:** subscribe to `/ws/live`, don't poll — push new alerts into the feed as they arrive

---

## Change log
- 2026-08-15: Initial version, based on `08_fusion_engine.py` output shape and `lora_sender.ino` payload
