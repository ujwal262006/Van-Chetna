// Exact backend API contract — DO NOT rename fields

export interface LoRaEvent {
  node_id: string;
  event_id: string;
  timestamp: string;
  sensor_type: 'acoustic' | 'vision';
  class: string;
  confidence: number;
  battery_pct: number;
  lat: number;
  lon: number;
}

export interface Alert {
  id: number;
  fused_score: number;
  label: string;
  severity: 'critical' | 'medium' | 'low';
  acoustic_confidence: number;
  vision_person_confidence: number;
  vision_vehicle_confidence: number;
  acoustic_class: string | null;
  node_id: string;
  generated_at: string;
  acknowledged?: boolean;
  acknowledged_by?: string;
}

export interface NodeStatus {
  node_id: string;
  /** Extended: includes new hazard-node types */
  node_type: 'acoustic' | 'vision' | 'fire' | 'air_quality' | 'water_level';
  last_seen: string;
  battery_pct: number;
  status: 'online' | 'offline';
  lat?: number;
  lon?: number;
  /** Only present for hazard-type nodes via GET /nodes/summary */
  latest_hazard?: HazardEventOut | null;
}

// ── New: hazard-event types ──────────────────────────────────────────────────

export interface HazardEventOut {
  id: number;
  event_id: string;
  node_id: string;
  hazard_type: 'FIRE' | 'AIR_QUALITY' | 'WATER_LEVEL';
  risk_score: number;        // 0–100
  severity: HazardSeverity;
  confidence: number;        // 0–100
  sensor_value_1: number | null;
  sensor_value_2: number | null;
  sensor_value_3: number | null;
  rssi: number | null;
  snr: number | null;
  recorded_at: string;
}

export interface MultiNodeSummary {
  nodes: NodeStatus[];
  total_online: number;
  total_offline: number;
}

/** Backend severity levels — acoustic/vision nodes use 3-tier; hazard nodes 4-tier */
export type Severity = 'critical' | 'medium' | 'low';
/** Hazard-node severity: direct from firmware (stored lowercase in backend) */
export type HazardSeverity = 'critical' | 'warning' | 'watch' | 'normal';

export type ConnectionState = 'connected' | 'reconnecting' | 'disconnected';

/** Maps a hazard node's node_type to a human-readable environment label */
export const NODE_TYPE_LABELS: Record<string, string> = {
  acoustic:    'Forest (Acoustic)',
  vision:      'Forest (Vision)',
  fire:        'Forest (Fire/Smoke)',
  air_quality: 'Urban/Industrial',
  water_level: 'Riverine',
};

/** Hazard-specific sensor field labels for the detail popup */
export const SENSOR_FIELD_LABELS: Record<string, [string, string?, string?]> = {
  AIR_QUALITY:  ['Raw ADC'],
  WATER_LEVEL:  ['Water Level (cm)', 'Rise Rate (cm/min)'],
  FIRE:         ['Smoke Raw ADC', 'Temp (°C)', 'Humidity (%)'],
};
