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
  last_seen: string;
  battery_pct: number;
  status: 'online' | 'offline';
  lat?: number;
  lon?: number;
}

export type Severity = 'critical' | 'medium' | 'low';
export type ConnectionState = 'connected' | 'reconnecting' | 'disconnected';
