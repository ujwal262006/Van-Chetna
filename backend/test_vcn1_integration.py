"""
test_vcn1_integration.py

End-to-end integration tests for the Van-Chetna multi-node extension.

These tests run entirely WITHOUT hardware — they use pytest + httpx
to hit the live FastAPI app backed by an in-memory SQLite database.

Run:
    cd acoustic-ai/backend
    pip install pytest pytest-asyncio httpx
    pytest test_vcn1_integration.py -v

The test DB is created fresh for each test session; it is separate from
your production/dev forest_guard.db so no data is disturbed.

Coverage:
  [T1]  VCN1 parser (vcn1_gateway_bridge.py) — all three hazard types
  [T2]  POST /hazard-events — URB01, RIV01, FOR01 payloads accepted
  [T3]  POST /hazard-events — duplicate event_id returns 'duplicate'
  [T4]  GET /hazard-events — returns all three node types
  [T5]  GET /hazard-events?node_id=RIV01 — node filter works
  [T6]  GET /hazard-events?hazard_type=FIRE — type filter works
  [T7]  GET /hazard-events/FOR01/history — history endpoint works
  [T8]  GET /nodes/status — URB01/RIV01/FOR01 appear with correct node_type
  [T9]  GET /nodes/summary — latest_hazard populated for hazard nodes
  [T10] Fusion — WATCH+ hazard produces Threat+Alert in DB
  [T11] Fusion cross-signal — fire WARNING + no acoustic → UNATTENDED label
  [T12] Fusion cross-signal — fire WARNING + active acoustic → not UNATTENDED
  [T13] Acoustic pipeline regression — existing POST /events still works
  [T14] Acoustic fusion regression — acoustic-only threat creation unchanged
  [T15] GET /alerts — hazard-sourced and acoustic-sourced alerts coexist
"""

import asyncio
import sys
import os
from datetime import datetime, timezone
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport

# ── Path setup ────────────────────────────────────────────────────────────────
# Allows running from backend/ or repo root
sys.path.insert(0, os.path.dirname(__file__))

# Override DATABASE_URL to use a separate test SQLite DB (not the dev forest_guard.db)
os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./test_vcn1_temp.db"

from app.main import app
from app.database import engine, Base

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db():
    """Create all tables at start of session; drop them after."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    # Dispose the engine (closes all pooled connections) before deleting the file
    await engine.dispose()
    db_path = "./test_vcn1_temp.db"
    if os.path.exists(db_path):
        try:
            os.remove(db_path)
        except PermissionError:
            pass  # Windows may still hold the handle briefly; file will be cleaned next run


@pytest_asyncio.fixture(scope="session")
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


# ── [T1] VCN1 parser unit tests ───────────────────────────────────────────────
# Import the parser directly from vcn1_gateway_bridge.py
# We add the parent directory to sys.path temporarily.

import importlib.util

_BRIDGE_PATH = os.path.join(os.path.dirname(__file__), "..", "vcn1_gateway_bridge.py")

def _load_bridge():
    spec = importlib.util.spec_from_file_location("vcn1_gateway_bridge", _BRIDGE_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

try:
    _bridge = _load_bridge()
    parse_vcn1_line = _bridge.parse_vcn1_line
    BRIDGE_AVAILABLE = True
except Exception as _e:
    BRIDGE_AVAILABLE = False
    parse_vcn1_line = None


@pytest.mark.skipif(not BRIDGE_AVAILABLE, reason="vcn1_gateway_bridge.py not loadable")
class TestVCN1Parser:
    """[T1] Parse-only tests — no network, no DB."""

    def test_air_quality_parses(self):
        line = "VCN1,URB01,AIR_QUALITY,42,WATCH,80,612,184532|RSSI=-87|SNR=9.2"
        result = parse_vcn1_line(line)
        assert result is not None
        assert result["node_id"] == "URB01"
        assert result["hazard_type"] == "AIR_QUALITY"
        assert result["risk_score"] == 42
        assert result["severity"] == "watch"      # lowercased by bridge
        assert result["confidence"] == 80
        assert result["sensor_value_1"] == 612.0
        assert result["sensor_value_2"] is None
        assert result["rssi"] == -87
        assert abs(result["snr"] - 9.2) < 0.01

    def test_water_level_parses(self):
        line = "VCN1,RIV01,WATER_LEVEL,75,WARNING,90,142.3,18.2,201044|RSSI=-91|SNR=7.8"
        result = parse_vcn1_line(line)
        assert result is not None
        assert result["node_id"] == "RIV01"
        assert result["hazard_type"] == "WATER_LEVEL"
        assert result["risk_score"] == 75
        assert result["severity"] == "warning"
        assert result["confidence"] == 90
        assert abs(result["sensor_value_1"] - 142.3) < 0.01
        assert abs(result["sensor_value_2"] - 18.2) < 0.01
        assert result["sensor_value_3"] is None

    def test_fire_parses(self):
        line = "VCN1,FOR01,FIRE,60,WATCH,85,410,32.1,45.2,215880|RSSI=-79|SNR=10.1"
        result = parse_vcn1_line(line)
        assert result is not None
        assert result["node_id"] == "FOR01"
        assert result["hazard_type"] == "FIRE"
        assert result["risk_score"] == 60
        assert result["severity"] == "watch"
        assert result["confidence"] == 85
        assert abs(result["sensor_value_1"] - 410.0) < 0.01
        assert abs(result["sensor_value_2"] - 32.1) < 0.01
        assert abs(result["sensor_value_3"] - 45.2) < 0.01
        assert result["rssi"] == -79
        assert abs(result["snr"] - 10.1) < 0.01

    def test_non_vcn1_returns_none(self):
        assert parse_vcn1_line("Received: {json}") is None
        assert parse_vcn1_line("[GATEWAY] LoRa initialized OK") is None
        assert parse_vcn1_line("") is None

    def test_malformed_missing_fields_returns_none(self):
        # AIR_QUALITY needs at least 8 comma-fields total
        assert parse_vcn1_line("VCN1,URB01,AIR_QUALITY,42") is None

    def test_critical_severity_lowercased(self):
        line = "VCN1,URB01,AIR_QUALITY,90,CRITICAL,90,800,300000|RSSI=-85|SNR=9.0"
        result = parse_vcn1_line(line)
        assert result["severity"] == "critical"

    def test_normal_severity_lowercased(self):
        line = "VCN1,URB01,AIR_QUALITY,10,NORMAL,85,510,300000|RSSI=-87|SNR=9.0"
        result = parse_vcn1_line(line)
        assert result["severity"] == "normal"


# ── [T2] POST /hazard-events — ingestion ──────────────────────────────────────

def _now_iso():
    """Current UTC time as ISO string — ensures timestamps are inside the fusion window."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

_URB01_PAYLOAD = {
    "node_id": "URB01", "event_id": "test_urb01_001",
    "timestamp": _now_iso(),
    "hazard_type": "AIR_QUALITY", "risk_score": 42, "severity": "watch",
    "confidence": 80, "sensor_value_1": 612.0,
    "sensor_value_2": None, "sensor_value_3": None,
    "rssi": -87, "snr": 9.2, "lat": 28.52050, "lon": 77.36700,
}
_RIV01_PAYLOAD = {
    "node_id": "RIV01", "event_id": "test_riv01_001",
    "timestamp": _now_iso(),
    "hazard_type": "WATER_LEVEL", "risk_score": 75, "severity": "warning",
    "confidence": 90, "sensor_value_1": 142.3, "sensor_value_2": 18.2,
    "sensor_value_3": None,
    "rssi": -91, "snr": 7.8, "lat": 28.51800, "lon": 77.36400,
}
_FOR01_PAYLOAD = {
    "node_id": "FOR01", "event_id": "test_for01_001",
    "timestamp": _now_iso(),
    "hazard_type": "FIRE", "risk_score": 60, "severity": "watch",
    "confidence": 85, "sensor_value_1": 410.0, "sensor_value_2": 32.1,
    "sensor_value_3": 45.2,
    "rssi": -79, "snr": 10.1, "lat": 28.51975, "lon": 77.36538,
}

@pytest.mark.asyncio
class TestHazardIngest:
    async def test_urb01_accepted(self, client):
        """[T2a] URB01 air quality payload accepted."""
        resp = await client.post("/hazard-events", json=_URB01_PAYLOAD)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "accepted"
        assert data["event_id"] == "test_urb01_001"

    async def test_riv01_accepted(self, client):
        """[T2b] RIV01 water level payload accepted."""
        resp = await client.post("/hazard-events", json=_RIV01_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["status"] == "accepted"

    async def test_for01_accepted(self, client):
        """[T2c] FOR01 fire payload accepted."""
        resp = await client.post("/hazard-events", json=_FOR01_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["status"] == "accepted"

    async def test_duplicate_returns_duplicate(self, client):
        """[T3] Re-sending same event_id returns 'duplicate', not 'accepted'."""
        resp = await client.post("/hazard-events", json=_URB01_PAYLOAD)
        assert resp.status_code == 201
        assert resp.json()["status"] == "duplicate"


# ── [T4-T7] GET hazard-events endpoints ───────────────────────────────────────

@pytest.mark.asyncio
class TestHazardRetrieval:
    async def test_get_all_hazard_events(self, client):
        """[T4] GET /hazard-events returns all three hazard types."""
        resp = await client.get("/hazard-events")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) >= 3
        types = {e["hazard_type"] for e in events}
        assert "AIR_QUALITY" in types
        assert "WATER_LEVEL" in types
        assert "FIRE" in types

    async def test_filter_by_node_id(self, client):
        """[T5] ?node_id=RIV01 returns only RIV01 readings."""
        resp = await client.get("/hazard-events?node_id=RIV01")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) >= 1
        assert all(e["node_id"] == "RIV01" for e in events)

    async def test_filter_by_hazard_type(self, client):
        """[T6] ?hazard_type=FIRE returns only fire readings."""
        resp = await client.get("/hazard-events?hazard_type=FIRE")
        assert resp.status_code == 200
        events = resp.json()
        assert len(events) >= 1
        assert all(e["hazard_type"] == "FIRE" for e in events)

    async def test_history_endpoint(self, client):
        """[T7] GET /hazard-events/FOR01/history returns FOR01 readings in order."""
        resp = await client.get("/hazard-events/FOR01/history")
        assert resp.status_code == 200
        history = resp.json()
        assert len(history) >= 1
        assert all(e["node_id"] == "FOR01" for e in history)
        # Newest first
        if len(history) > 1:
            t0 = history[0]["recorded_at"]
            t1 = history[1]["recorded_at"]
            assert t0 >= t1

    async def test_history_404_for_unknown_node(self, client):
        """GET /hazard-events/UNKNOWN/history returns 404."""
        resp = await client.get("/hazard-events/UNKNOWN_NODE_XYZ/history")
        assert resp.status_code == 404


# ── [T8-T9] Node endpoints ─────────────────────────────────────────────────────

@pytest.mark.asyncio
class TestNodeEndpoints:
    async def test_nodes_status_includes_hazard_nodes(self, client):
        """[T8] GET /nodes/status includes URB01/RIV01/FOR01 with correct node_type."""
        resp = await client.get("/nodes/status")
        assert resp.status_code == 200
        nodes = {n["node_id"]: n for n in resp.json()}

        assert "URB01" in nodes
        assert nodes["URB01"]["node_type"] == "air_quality"
        assert nodes["URB01"]["status"] == "online"

        assert "RIV01" in nodes
        assert nodes["RIV01"]["node_type"] == "water_level"

        assert "FOR01" in nodes
        assert nodes["FOR01"]["node_type"] == "fire"

    async def test_nodes_summary_has_latest_hazard(self, client):
        """[T9] GET /nodes/summary includes latest_hazard for hazard nodes."""
        resp = await client.get("/nodes/summary")
        assert resp.status_code == 200
        data = resp.json()

        assert "nodes" in data
        assert "total_online" in data
        assert "total_offline" in data
        assert data["total_online"] >= 3  # URB01, RIV01, FOR01 all sent recently

        nodes = {n["node_id"]: n for n in data["nodes"]}

        assert "URB01" in nodes
        lh = nodes["URB01"]["latest_hazard"]
        assert lh is not None
        assert lh["hazard_type"] == "AIR_QUALITY"
        assert lh["risk_score"] == 42   # matches test_urb01_001

        assert "RIV01" in nodes
        lh_riv = nodes["RIV01"]["latest_hazard"]
        assert lh_riv is not None
        assert lh_riv["hazard_type"] == "WATER_LEVEL"

        assert "FOR01" in nodes
        lh_for = nodes["FOR01"]["latest_hazard"]
        assert lh_for is not None
        assert lh_for["hazard_type"] == "FIRE"


# ── [T10-T12] Fusion engine tests ─────────────────────────────────────────────

@pytest.mark.asyncio
class TestFusionEngine:
    async def test_watch_hazard_produces_alert(self, client):
        """[T10] A WATCH-severity hazard reading creates a Threat and Alert."""
        # RIV01 with WARNING (risk 75) was already ingested above — should have alert
        resp = await client.get("/alerts")
        assert resp.status_code == 200
        alerts = resp.json()
        riv_alerts = [a for a in alerts if a["node_id"] == "RIV01"]
        assert len(riv_alerts) >= 1
        assert riv_alerts[0]["severity"] in ("medium", "critical")

    async def test_fire_warning_no_acoustic_triggers_unattended(self, client):
        """
        [T11] Fire node at CRITICAL severity with no recent human acoustic activity
        should produce the UNATTENDED FIRE RISK label.

        The ordering fix (risk_score DESC, then recorded_at DESC) ensures fusion
        always picks the highest-risk event in the window — not whichever arrived
        last by timestamp when the simulator sends multiple readings per second.
        This test would have been non-deterministic before that fix.
        """
        await asyncio.sleep(1)   # ensure clean recorded_at separation from prior events
        payload = {
            **_FOR01_PAYLOAD,
            "event_id":   "test_for01_warning_001",
            "timestamp":  _now_iso(),
            "risk_score": 85,
            "severity":   "critical",
            "sensor_value_1": 700.0,
            "sensor_value_2": 43.0,
            "sensor_value_3": 25.0,
        }
        resp = await client.post("/hazard-events", json=payload)
        assert resp.status_code == 201

        await asyncio.sleep(0.2)

        resp = await client.get("/alerts")
        alerts = resp.json()
        for01_alerts = [a for a in alerts if a["node_id"] == "FOR01"]
        assert len(for01_alerts) >= 1, "Expected at least one FOR01 alert"
        latest = sorted(for01_alerts, key=lambda a: a["generated_at"], reverse=True)[0]
        # With no acoustic human activity present and risk_score ordering fixed,
        # the UNATTENDED disambiguation branch must fire.
        assert "UNATTENDED" in latest["label"], (
            f"Expected UNATTENDED label when no acoustic activity present, got: {latest['label']}"
        )

    async def test_fire_warning_with_acoustic_not_unattended(self, client):
        """
        [T12] Fire node at WARNING + active acoustic (human_activity, conf 0.8)
        should NOT produce an UNATTENDED label.
        """
        acoustic_payload = {
            "node_id":     "NODE_01",
            "event_id":    "test_acoustic_human_001",
            "timestamp":   _now_iso(),
            "sensor_type": "acoustic",
            "class":       "human_activity",
            "confidence":  0.85,
            "battery_pct": 78,
            "lat":         28.51975,
            "lon":         77.36538,
        }
        resp = await client.post("/events", json=acoustic_payload)
        assert resp.status_code == 201

        payload = {
            **_FOR01_PAYLOAD,
            "event_id":  "test_for01_warning_002",
            "timestamp": _now_iso(),
            "risk_score": 72,
            "severity":  "warning",
        }
        resp = await client.post("/hazard-events", json=payload)
        assert resp.status_code == 201

        await asyncio.sleep(0.1)

        resp = await client.get("/alerts")
        alerts = resp.json()
        for01_alerts = [a for a in alerts if a["node_id"] == "FOR01"]
        latest = sorted(for01_alerts, key=lambda a: a["generated_at"], reverse=True)[0]
        # With human_activity at 0.85 confidence in the window, should NOT be UNATTENDED
        assert "UNATTENDED" not in latest["label"], (
            f"Should not label as UNATTENDED when human acoustic activity is present, "
            f"got: {latest['label']}"
        )


# ── [T13-T14] Acoustic pipeline regression ────────────────────────────────────

@pytest.mark.asyncio
class TestAcousticRegression:
    async def test_existing_events_endpoint_still_works(self, client):
        """[T13] POST /events still accepts acoustic payloads correctly."""
        payload = {
            "node_id":     "NODE_01",
            "event_id":    "test_acoustic_regression_001",
            "timestamp":   _now_iso(),
            "sensor_type": "acoustic",
            "class":       "chainsaw",
            "confidence":  0.92,
            "battery_pct": 78,
            "lat":         28.51975,
            "lon":         77.36538,
        }
        resp = await client.post("/events", json=payload)
        assert resp.status_code == 201
        data = resp.json()
        assert data["status"] == "accepted"

    async def test_acoustic_fusion_produces_critical_alert(self, client):
        """[T14] Acoustic event with confidence ≥ 0.85 produces 'critical' threat."""
        payload = {
            "node_id":     "NODE_01",
            "event_id":    "test_acoustic_regression_002",
            "timestamp":   _now_iso(),
            "sensor_type": "acoustic",
            "class":       "chainsaw",
            "confidence":  0.91,
            "battery_pct": 78,
            "lat":         28.51975,
            "lon":         77.36538,
        }
        resp = await client.post("/events", json=payload)
        assert resp.status_code == 201

        await asyncio.sleep(0.1)

        resp = await client.get("/alerts")
        alerts = resp.json()
        node01_alerts = [a for a in alerts if a["node_id"] == "NODE_01"]
        assert len(node01_alerts) >= 1
        # acoustic-only: fused_score = max confidence = 0.92 → ≥ 0.85 → critical
        severities = {a["severity"] for a in node01_alerts}
        assert "critical" in severities, (
            f"Expected critical alert for 0.92 acoustic confidence, got: {severities}"
        )

    async def test_get_events_returns_acoustic_events(self, client):
        """GET /events still returns acoustic events in the existing shape."""
        resp = await client.get("/events")
        assert resp.status_code == 200
        events = resp.json()
        acoustic = [e for e in events if e["sensor_type"] == "acoustic"]
        assert len(acoustic) >= 1
        # Verify the "class" alias is present (existing contract)
        for e in acoustic:
            assert "class" in e, "EventOut should use 'class' alias for event_class"

    async def test_nodes_status_still_returns_existing_format(self, client):
        """GET /nodes/status response shape is backward-compatible."""
        resp = await client.get("/nodes/status")
        assert resp.status_code == 200
        nodes = resp.json()
        # All items must have these fields — the new node_type field is additive
        for n in nodes:
            assert "node_id"     in n
            assert "node_type"   in n    # new field — must be present
            assert "last_seen"   in n
            assert "battery_pct" in n
            assert "status"      in n


# ── [T15] Mixed alerts coexistence ────────────────────────────────────────────

@pytest.mark.asyncio
class TestMixedAlerts:
    async def test_acoustic_and_hazard_alerts_coexist(self, client):
        """
        [T15] GET /alerts returns both acoustic-sourced and hazard-sourced alerts
        in the same list without errors.
        """
        resp = await client.get("/alerts")
        assert resp.status_code == 200
        alerts = resp.json()

        node_ids = {a["node_id"] for a in alerts}
        # Should contain at least one acoustic node and at least one hazard node
        acoustic_nodes = {"NODE_01", "NODE_02", "NODE_03", "NODE_04"}
        hazard_nodes   = {"URB01", "RIV01", "FOR01"}

        has_acoustic = bool(node_ids & acoustic_nodes)
        has_hazard   = bool(node_ids & hazard_nodes)

        assert has_acoustic, f"No acoustic-node alerts found. node_ids in alerts: {node_ids}"
        assert has_hazard,   f"No hazard-node alerts found. node_ids in alerts: {node_ids}"

        # All items must conform to AlertOut schema
        for a in alerts:
            assert "id"           in a
            assert "fused_score"  in a
            assert "label"        in a
            assert "severity"     in a
            assert "node_id"      in a
            assert "generated_at" in a
            assert a["severity"]  in ("critical", "medium", "low")
