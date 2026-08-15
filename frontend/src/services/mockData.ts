import { LoRaEvent, Alert, NodeStatus } from '../types';

// ─── Mock Nodes ─────────────────────────────────────────────

export const MOCK_NODES: NodeStatus[] = [
  { node_id: 'NODE_01', last_seen: new Date(Date.now() - 15000).toISOString(), battery_pct: 78, status: 'online', lat: 21.1458, lon: 79.0882 },
  { node_id: 'NODE_02', last_seen: new Date(Date.now() - 4000).toISOString(), battery_pct: 91, status: 'online', lat: 21.1502, lon: 79.0925 },
  { node_id: 'NODE_03', last_seen: new Date(Date.now() - 480000).toISOString(), battery_pct: 12, status: 'offline', lat: 21.1535, lon: 79.0850 },
  { node_id: 'NODE_04', last_seen: new Date(Date.now() - 8000).toISOString(), battery_pct: 64, status: 'online', lat: 21.1480, lon: 79.0960 },
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
];

// ─── Alert Generator (for demo WebSocket simulation) ────────

let _nextId = 100;
const LABELS = [
  'POSSIBLE ILLEGAL LOGGING — HIGH CONFIDENCE',
  'UNAUTHORIZED VEHICLE DETECTED',
  'SUSPICIOUS HUMAN ACTIVITY',
  'POSSIBLE POACHING ACTIVITY',
];
const CLASSES = ['chainsaw', 'vehicle', 'gunshot', 'person'];
const NODES = ['NODE_01', 'NODE_02', 'NODE_04'];

export function generateMockAlert(): Alert {
  const sev = Math.random() > 0.5 ? 'critical' : 'medium';
  const idx = Math.floor(Math.random() * LABELS.length);
  const nodeId = NODES[Math.floor(Math.random() * NODES.length)];
  return {
    id: _nextId++,
    fused_score: +(0.7 + Math.random() * 0.25).toFixed(2),
    label: LABELS[idx],
    severity: sev as 'critical' | 'medium',
    acoustic_confidence: +(0.6 + Math.random() * 0.35).toFixed(2),
    vision_person_confidence: +(Math.random() * 0.9).toFixed(2),
    vision_vehicle_confidence: +(Math.random() * 0.8).toFixed(2),
    acoustic_class: CLASSES[idx],
    node_id: nodeId,
    generated_at: new Date().toISOString(),
    acknowledged: false,
  };
}
