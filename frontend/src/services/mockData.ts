import { LoRaEvent, Alert, NodeStatus, HazardEventOut } from '../types';

// ─── Mock Nodes ─────────────────────────────────────────────

export const MOCK_NODES: NodeStatus[] = [
  { node_id: 'NODE_01', node_type: 'acoustic',    last_seen: new Date(Date.now() - 15000).toISOString(), battery_pct: 78, status: 'online',  lat: 21.1458, lon: 79.0882 },
  { node_id: 'NODE_02', node_type: 'acoustic',    last_seen: new Date(Date.now() - 4000).toISOString(),  battery_pct: 91, status: 'online',  lat: 21.1502, lon: 79.0925 },
  { node_id: 'NODE_03', node_type: 'acoustic',    last_seen: new Date(Date.now() - 480000).toISOString(),battery_pct: 12, status: 'offline', lat: 21.1535, lon: 79.0850 },
  { node_id: 'NODE_04', node_type: 'vision',       last_seen: new Date(Date.now() - 8000).toISOString(),  battery_pct: 64, status: 'online',  lat: 21.1480, lon: 79.0960 },
  // New multi-node hardware
  { node_id: 'URB01',   node_type: 'air_quality', last_seen: new Date(Date.now() - 6000).toISOString(),  battery_pct: 100, status: 'online', lat: 21.1560, lon: 79.0870,
    latest_hazard: { id: 1, event_id: 'vcn1_urb01_demo_001', node_id: 'URB01', hazard_type: 'AIR_QUALITY', risk_score: 42, severity: 'watch', confidence: 80, sensor_value_1: 612, sensor_value_2: null, sensor_value_3: null, rssi: -87, snr: 9.2, recorded_at: new Date(Date.now() - 6000).toISOString() } },
  { node_id: 'RIV01',   node_type: 'water_level', last_seen: new Date(Date.now() - 9000).toISOString(),  battery_pct: 100, status: 'online', lat: 21.1420, lon: 79.0840,
    latest_hazard: { id: 2, event_id: 'vcn1_riv01_demo_001', node_id: 'RIV01', hazard_type: 'WATER_LEVEL', risk_score: 75, severity: 'warning', confidence: 90, sensor_value_1: 142.3, sensor_value_2: 18.2, sensor_value_3: null, rssi: -91, snr: 7.8, recorded_at: new Date(Date.now() - 9000).toISOString() } },
  { node_id: 'FOR01',   node_type: 'fire',         last_seen: new Date(Date.now() - 5000).toISOString(),  battery_pct: 100, status: 'online', lat: 21.1470, lon: 79.0900,
    latest_hazard: { id: 3, event_id: 'vcn1_for01_demo_001', node_id: 'FOR01', hazard_type: 'FIRE', risk_score: 60, severity: 'watch', confidence: 85, sensor_value_1: 410, sensor_value_2: 32.1, sensor_value_3: 45.2, rssi: -79, snr: 10.1, recorded_at: new Date(Date.now() - 5000).toISOString() } },
];

// ─── Mock Hazard Events ──────────────────────────────────────

export const MOCK_HAZARD_EVENTS: HazardEventOut[] = [
  // Air quality trend (URB01)
  { id: 1,  event_id: 'vcn1_urb01_demo_001', node_id: 'URB01', hazard_type: 'AIR_QUALITY', risk_score: 42, severity: 'watch',   confidence: 80, sensor_value_1: 612,  sensor_value_2: null, sensor_value_3: null, rssi: -87, snr: 9.2,  recorded_at: new Date(Date.now() - 10000).toISOString() },
  { id: 2,  event_id: 'vcn1_urb01_demo_002', node_id: 'URB01', hazard_type: 'AIR_QUALITY', risk_score: 38, severity: 'watch',   confidence: 80, sensor_value_1: 590,  sensor_value_2: null, sensor_value_3: null, rssi: -88, snr: 8.9,  recorded_at: new Date(Date.now() - 20000).toISOString() },
  { id: 3,  event_id: 'vcn1_urb01_demo_003', node_id: 'URB01', hazard_type: 'AIR_QUALITY', risk_score: 21, severity: 'normal',  confidence: 85, sensor_value_1: 520,  sensor_value_2: null, sensor_value_3: null, rssi: -87, snr: 9.1,  recorded_at: new Date(Date.now() - 30000).toISOString() },
  { id: 4,  event_id: 'vcn1_urb01_demo_004', node_id: 'URB01', hazard_type: 'AIR_QUALITY', risk_score: 15, severity: 'normal',  confidence: 85, sensor_value_1: 502,  sensor_value_2: null, sensor_value_3: null, rssi: -86, snr: 9.4,  recorded_at: new Date(Date.now() - 40000).toISOString() },
  // Water level trend (RIV01)
  { id: 5,  event_id: 'vcn1_riv01_demo_001', node_id: 'RIV01', hazard_type: 'WATER_LEVEL', risk_score: 75, severity: 'warning', confidence: 90, sensor_value_1: 142.3, sensor_value_2: 18.2, sensor_value_3: null, rssi: -91, snr: 7.8,  recorded_at: new Date(Date.now() - 10000).toISOString() },
  { id: 6,  event_id: 'vcn1_riv01_demo_002', node_id: 'RIV01', hazard_type: 'WATER_LEVEL', risk_score: 68, severity: 'warning', confidence: 90, sensor_value_1: 130.1, sensor_value_2: 15.4, sensor_value_3: null, rssi: -91, snr: 7.6,  recorded_at: new Date(Date.now() - 20000).toISOString() },
  { id: 7,  event_id: 'vcn1_riv01_demo_003', node_id: 'RIV01', hazard_type: 'WATER_LEVEL', risk_score: 55, severity: 'watch',   confidence: 90, sensor_value_1: 112.0, sensor_value_2: 10.1, sensor_value_3: null, rssi: -92, snr: 7.4,  recorded_at: new Date(Date.now() - 30000).toISOString() },
  { id: 8,  event_id: 'vcn1_riv01_demo_004', node_id: 'RIV01', hazard_type: 'WATER_LEVEL', risk_score: 40, severity: 'watch',   confidence: 90, sensor_value_1: 95.5,  sensor_value_2: 6.2,  sensor_value_3: null, rssi: -90, snr: 7.9,  recorded_at: new Date(Date.now() - 40000).toISOString() },
  // Fire/smoke trend (FOR01)
  { id: 9,  event_id: 'vcn1_for01_demo_001', node_id: 'FOR01', hazard_type: 'FIRE',        risk_score: 60, severity: 'watch',   confidence: 85, sensor_value_1: 410,  sensor_value_2: 32.1, sensor_value_3: 45.2, rssi: -79, snr: 10.1, recorded_at: new Date(Date.now() - 10000).toISOString() },
  { id: 10, event_id: 'vcn1_for01_demo_002', node_id: 'FOR01', hazard_type: 'FIRE',        risk_score: 52, severity: 'watch',   confidence: 80, sensor_value_1: 380,  sensor_value_2: 30.5, sensor_value_3: 48.1, rssi: -80, snr: 10.0, recorded_at: new Date(Date.now() - 20000).toISOString() },
  { id: 11, event_id: 'vcn1_for01_demo_003', node_id: 'FOR01', hazard_type: 'FIRE',        risk_score: 30, severity: 'watch',   confidence: 70, sensor_value_1: 320,  sensor_value_2: 28.0, sensor_value_3: 52.0, rssi: -79, snr: 10.3, recorded_at: new Date(Date.now() - 30000).toISOString() },
  { id: 12, event_id: 'vcn1_for01_demo_004', node_id: 'FOR01', hazard_type: 'FIRE',        risk_score: 18, severity: 'normal',  confidence: 60, sensor_value_1: 290,  sensor_value_2: 26.2, sensor_value_3: 58.0, rssi: -80, snr: 9.8,  recorded_at: new Date(Date.now() - 40000).toISOString() },
];

// ─── Mock Events ────────────────────────────────────────────

export const MOCK_EVENTS: LoRaEvent[] = [
  { node_id: 'NODE_01', event_id: 'evt_001', timestamp: new Date(Date.now() - 180000).toISOString(), sensor_type: 'acoustic', class: 'chainsaw', confidence: 0.91, battery_pct: 78, lat: 21.1458, lon: 79.0882 },
  { node_id: 'NODE_02', event_id: 'evt_002', timestamp: new Date(Date.now() - 300000).toISOString(), sensor_type: 'acoustic', class: 'vehicle', confidence: 0.82, battery_pct: 91, lat: 21.1502, lon: 79.0925 },
  { node_id: 'NODE_04', event_id: 'evt_003', timestamp: new Date(Date.now() - 600000).toISOString(), sensor_type: 'vision', class: 'person', confidence: 0.87, battery_pct: 64, lat: 21.1480, lon: 79.0960 },
  { node_id: 'NODE_01', event_id: 'evt_004', timestamp: new Date(Date.now() - 900000).toISOString(), sensor_type: 'acoustic', class: 'gunshot', confidence: 0.76, battery_pct: 78, lat: 21.1458, lon: 79.0882 },
  { node_id: 'NODE_04', event_id: 'evt_005', timestamp: new Date(Date.now() - 1800000).toISOString(), sensor_type: 'vision', class: 'vehicle', confidence: 0.79, battery_pct: 64, lat: 21.1480, lon: 79.0960 },
  { node_id: 'NODE_02', event_id: 'evt_006', timestamp: new Date(Date.now() - 3600000).toISOString(), sensor_type: 'acoustic', class: 'normal', confidence: 0.95, battery_pct: 91, lat: 21.1502, lon: 79.0925 },
  { node_id: 'NODE_03', event_id: 'evt_007', timestamp: new Date(Date.now() - 7200000).toISOString(), sensor_type: 'acoustic', class: 'animal', confidence: 0.68, battery_pct: 18, lat: 21.1535, lon: 79.0850 },
];

// ─── Mock Alerts ────────────────────────────────────────────

export const MOCK_ALERTS: Alert[] = [
  {
    id: 1,
    fused_score: 0.94,
    label: 'POSSIBLE ILLEGAL LOGGING — HIGH CONFIDENCE',
    severity: 'critical',
    acoustic_confidence: 0.91,
    vision_person_confidence: 0.87,
    vision_vehicle_confidence: 0.76,
    acoustic_class: 'chainsaw',
    node_id: 'NODE_01',
    generated_at: new Date(Date.now() - 120000).toISOString(),
    acknowledged: false,
  },
  {
    id: 2,
    fused_score: 0.82,
    label: 'UNAUTHORIZED VEHICLE DETECTED',
    severity: 'medium',
    acoustic_confidence: 0.82,
    vision_person_confidence: 0.0,
    vision_vehicle_confidence: 0.79,
    acoustic_class: 'vehicle',
    node_id: 'NODE_02',
    generated_at: new Date(Date.now() - 600000).toISOString(),
    acknowledged: false,
  },
  {
    id: 3,
    fused_score: 0.88,
    label: 'SUSPICIOUS HUMAN ACTIVITY',
    severity: 'critical',
    acoustic_confidence: 0.76,
    vision_person_confidence: 0.88,
    vision_vehicle_confidence: 0.0,
    acoustic_class: 'gunshot',
    node_id: 'NODE_04',
    generated_at: new Date(Date.now() - 900000).toISOString(),
    acknowledged: true,
    acknowledged_by: 'Officer Priya',
  },
  {
    id: 4,
    fused_score: 0.55,
    label: 'ANIMAL MOVEMENT DETECTED',
    severity: 'low',
    acoustic_confidence: 0.68,
    vision_person_confidence: 0.0,
    vision_vehicle_confidence: 0.0,
    acoustic_class: 'animal',
    node_id: 'NODE_03',
    generated_at: new Date(Date.now() - 7200000).toISOString(),
    acknowledged: false,
  },
  // New hazard-node alerts
  {
    id: 5,
    fused_score: 0.75,
    label: 'RISING WATER LEVEL — POTENTIAL FLOOD WARNING',
    severity: 'medium',
    acoustic_confidence: 0.0,
    vision_person_confidence: 0.0,
    vision_vehicle_confidence: 0.0,
    acoustic_class: 'WATER_LEVEL:75',
    node_id: 'RIV01',
    generated_at: new Date(Date.now() - 10000).toISOString(),
    acknowledged: false,
  },
  {
    id: 6,
    fused_score: 0.60,
    label: 'UNATTENDED FIRE RISK — POSSIBLE WILDFIRE (no human activity detected)',
    severity: 'medium',
    acoustic_confidence: 0.0,
    vision_person_confidence: 0.0,
    vision_vehicle_confidence: 0.0,
    acoustic_class: 'FIRE:60',
    node_id: 'FOR01',
    generated_at: new Date(Date.now() - 5000).toISOString(),
    acknowledged: false,
  },
];

// ─── Alert Generator (for demo WebSocket simulation) ────────

let _nextId = 100;
const LABELS = [
  'POSSIBLE ILLEGAL LOGGING — HIGH CONFIDENCE',
  'UNAUTHORIZED VEHICLE DETECTED',
  'SUSPICIOUS HUMAN ACTIVITY',
  'POSSIBLE POACHING ACTIVITY',
  'RISING WATER LEVEL — POTENTIAL FLOOD WARNING',
  'UNATTENDED FIRE RISK — POSSIBLE WILDFIRE (no human activity detected)',
  'CRITICAL AIR QUALITY ANOMALY — POSSIBLE INDUSTRIAL RELEASE',
];
const CLASSES = ['chainsaw', 'vehicle', 'gunshot', 'person', 'WATER_LEVEL:75', 'FIRE:60', 'AIR_QUALITY:90'];
const NODES = ['NODE_01', 'NODE_02', 'NODE_04', 'URB01', 'RIV01', 'FOR01'];

export function generateMockAlert(): Alert {
  const sev = Math.random() > 0.5 ? 'critical' : 'medium';
  const idx = Math.floor(Math.random() * LABELS.length);
  const nodeId = NODES[Math.floor(Math.random() * NODES.length)];
  return {
    id: _nextId++,
    fused_score: +(0.7 + Math.random() * 0.25).toFixed(2),
    label: LABELS[idx],
    severity: sev as 'critical' | 'medium',
    acoustic_confidence: +(Math.random() * 0.9).toFixed(2),
    vision_person_confidence: +(Math.random() * 0.9).toFixed(2),
    vision_vehicle_confidence: +(Math.random() * 0.8).toFixed(2),
    acoustic_class: CLASSES[idx],
    node_id: nodeId,
    generated_at: new Date().toISOString(),
    acknowledged: false,
  };
}
