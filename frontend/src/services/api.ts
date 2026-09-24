import { LoRaEvent, Alert, NodeStatus, HazardEventOut, MultiNodeSummary } from '../types';
import { MOCK_EVENTS, MOCK_ALERTS, MOCK_NODES, MOCK_HAZARD_EVENTS, generateMockAlert } from './mockData';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';
const DEMO_MODE = import.meta.env.VITE_DEMO_MODE === 'true';

function delay(ms: number) {
  return new Promise<void>(r => setTimeout(r, ms));
}

// ─── API Functions ──────────────────────────────────────────

export async function getEvents(): Promise<LoRaEvent[]> {
  if (DEMO_MODE) {
    await delay(100);
    return [...MOCK_EVENTS];
  }
  const res = await fetch(`${API_URL}/events`);
  if (!res.ok) throw new Error(`GET /events failed: ${res.status}`);
  return res.json();
}

export async function getAlerts(params?: {
  node_id?: string;
  severity?: string;
  limit?: number;
}): Promise<Alert[]> {
  if (DEMO_MODE) {
    await delay(120);
    let results = [...MOCK_ALERTS];
    if (params?.node_id) results = results.filter(a => a.node_id === params.node_id);
    if (params?.severity) results = results.filter(a => a.severity === params.severity);
    return results.slice(0, params?.limit ?? 100);
  }
  const qs = new URLSearchParams();
  if (params?.node_id) qs.set('node_id', params.node_id);
  if (params?.severity) qs.set('severity', params.severity);
  if (params?.limit) qs.set('limit', String(params.limit));
  const res = await fetch(`${API_URL}/alerts?${qs}`);
  if (!res.ok) throw new Error(`GET /alerts failed: ${res.status}`);
  return res.json();
}

export async function getNodeStatus(): Promise<NodeStatus[]> {
  if (DEMO_MODE) {
    await delay(80);
    return [...MOCK_NODES];
  }
  const res = await fetch(`${API_URL}/nodes/status`);
  if (!res.ok) throw new Error(`GET /nodes/status failed: ${res.status}`);
  return res.json();
}

/**
 * Unified multi-node summary: all nodes + latest hazard reading.
 * Use this for the map and the multi-node status panel.
 */
export async function getNodesSummary(): Promise<MultiNodeSummary> {
  if (DEMO_MODE) {
    await delay(90);
    return {
      nodes: [...MOCK_NODES],
      total_online: MOCK_NODES.filter(n => n.status === 'online').length,
      total_offline: MOCK_NODES.filter(n => n.status === 'offline').length,
    };
  }
  const res = await fetch(`${API_URL}/nodes/summary`);
  if (!res.ok) throw new Error(`GET /nodes/summary failed: ${res.status}`);
  return res.json();
}

/** Hazard readings across all nodes, with optional filters. */
export async function getHazardEvents(params?: {
  node_id?: string;
  hazard_type?: string;
  limit?: number;
}): Promise<HazardEventOut[]> {
  if (DEMO_MODE) {
    await delay(100);
    let results = [...MOCK_HAZARD_EVENTS];
    if (params?.node_id) results = results.filter(e => e.node_id === params.node_id);
    if (params?.hazard_type) results = results.filter(e => e.hazard_type === params.hazard_type);
    return results.slice(0, params?.limit ?? 50);
  }
  const qs = new URLSearchParams();
  if (params?.node_id) qs.set('node_id', params.node_id);
  if (params?.hazard_type) qs.set('hazard_type', params.hazard_type);
  if (params?.limit) qs.set('limit', String(params.limit));
  const res = await fetch(`${API_URL}/hazard-events?${qs}`);
  if (!res.ok) throw new Error(`GET /hazard-events failed: ${res.status}`);
  return res.json();
}

/** Time-series history for a single hazard node — used by trend charts. */
export async function getNodeHazardHistory(
  nodeId: string,
  limit = 100,
): Promise<HazardEventOut[]> {
  if (DEMO_MODE) {
    await delay(80);
    return MOCK_HAZARD_EVENTS.filter(e => e.node_id === nodeId).slice(0, limit);
  }
  const res = await fetch(`${API_URL}/hazard-events/${encodeURIComponent(nodeId)}/history?limit=${limit}`);
  if (!res.ok) throw new Error(`GET /hazard-events/${nodeId}/history failed: ${res.status}`);
  return res.json();
}

export async function acknowledgeAlert(id: number, officerName: string): Promise<void> {
  if (DEMO_MODE) {
    await delay(200);
    const alert = MOCK_ALERTS.find(a => a.id === id);
    if (alert) {
      alert.acknowledged = true;
      alert.acknowledged_by = officerName;
    }
    return;
  }
  const res = await fetch(`${API_URL}/alerts/${id}/acknowledge`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ acknowledged_by: officerName }),
  });
  if (!res.ok) throw new Error(`POST /alerts/${id}/acknowledge failed: ${res.status}`);
}

// WebSocket URL helper
export function getWebSocketUrl(): string {
  if (DEMO_MODE) return '';
  const wsBase = API_URL.replace(/^http/, 'ws');
  return `${wsBase}/ws/live`;
}

export function isDemoMode(): boolean {
  return DEMO_MODE;
}

export { generateMockAlert };
