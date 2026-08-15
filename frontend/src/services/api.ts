import { LoRaEvent, Alert, NodeStatus } from '../types';
import { MOCK_EVENTS, MOCK_ALERTS, MOCK_NODES, generateMockAlert } from './mockData';

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

export async function getAlerts(): Promise<Alert[]> {
  if (DEMO_MODE) {
    await delay(120);
    return [...MOCK_ALERTS];
  }
  const res = await fetch(`${API_URL}/alerts`);
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
