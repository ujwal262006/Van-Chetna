/**
 * ThreatMap — multi-node geospatial risk map.
 *
 * Visual conventions (unchanged from existing design):
 *   Severity colours: critical=#ef4444  medium=#f59e0b  low=#3b82f6
 *   Online nodes: #34d399   Offline nodes: #4b5563
 *
 * New (multi-node integration):
 *   Node markers now carry distinct icons per environment type:
 *     acoustic/vision  → circle (existing behaviour)
 *     fire             → triangle (red tint)
 *     air_quality      → hexagon (orange tint)
 *     water_level      → teardrop / raindrop (blue tint)
 *   Hazard-node popups show the latest sensor reading with labelled fields.
 *   Severity is derived from the node's latest_hazard.severity field.
 */

import { MapContainer, TileLayer, CircleMarker, Popup, Marker } from 'react-leaflet';
import L from 'leaflet';
import IndiaBoundaryLayer from './IndiaBoundaryLayer';
import IndiaLabelsOverlay from './IndiaLabelsOverlay';
import { Alert, NodeStatus, SENSOR_FIELD_LABELS, NODE_TYPE_LABELS, HazardSeverity } from '../../types';
import { MOCK_NODES } from '../../services/mockData';

interface Props {
  nodes: NodeStatus[];
  alerts: Alert[];
  onAlertClick?: (alert: Alert) => void;
}

// ── Colour palettes (unchanged from existing) ────────────────────────────────
const sevColor: Record<string, string> = {
  critical: '#ef4444',
  medium:   '#f59e0b',
  low:      '#3b82f6',
};
const nodeOnlineColor  = '#34d399';
const nodeOfflineColor = '#4b5563';

/**
 * Map a 4-tier hazard severity to the existing 3-tier severity colour scheme.
 * 'normal' → low (blue),  'watch' → medium (amber),
 * 'warning' → medium (amber),  'critical' → critical (red)
 */
function hazardSevToColor(sev: HazardSeverity | string): string {
  if (sev === 'critical') return sevColor.critical;
  if (sev === 'warning' || sev === 'watch') return sevColor.medium;
  return sevColor.low;
}

// ── Node-type icon builders ──────────────────────────────────────────────────

function makeIcon(html: string): L.DivIcon {
  return L.divIcon({ html, className: '', iconSize: [16, 16], iconAnchor: [8, 8] });
}

/** Forest acoustic/vision — existing circle style */
function acousticIcon(online: boolean): L.DivIcon {
  const c = online ? nodeOnlineColor : nodeOfflineColor;
  return makeIcon(
    `<div style="width:12px;height:12px;background:${c};border:2px solid ${c}dd;border-radius:50%;opacity:0.85"></div>`
  );
}

/** Fire/smoke node — triangle */
function fireIcon(online: boolean, hazardSev?: string): L.DivIcon {
  const borderC = online ? (hazardSev ? hazardSevToColor(hazardSev) : nodeOnlineColor) : nodeOfflineColor;
  return makeIcon(
    `<div style="width:0;height:0;border-left:8px solid transparent;border-right:8px solid transparent;border-bottom:14px solid ${borderC};opacity:0.9;margin-top:-1px"></div>`
  );
}

/** Air quality node — hexagon (CSS approximation: rotated square) */
function airQualityIcon(online: boolean, hazardSev?: string): L.DivIcon {
  const c = online ? (hazardSev ? hazardSevToColor(hazardSev) : '#f97316') : nodeOfflineColor;
  return makeIcon(
    `<div style="width:11px;height:11px;background:${c};border:2px solid ${c}cc;border-radius:2px;transform:rotate(45deg);opacity:0.9"></div>`
  );
}

/** Water level node — circle with inner dot (raindrop feel) */
function waterIcon(online: boolean, hazardSev?: string): L.DivIcon {
  const c = online ? (hazardSev ? hazardSevToColor(hazardSev) : '#38bdf8') : nodeOfflineColor;
  return makeIcon(
    `<div style="width:13px;height:13px;background:${c};border:2px solid ${c}cc;border-radius:50% 50% 50% 0;transform:rotate(-45deg);opacity:0.9"></div>`
  );
}

function getNodeIcon(node: NodeStatus): L.DivIcon {
  const online = node.status === 'online';
  const sev = node.latest_hazard?.severity;
  switch (node.node_type) {
    case 'fire':        return fireIcon(online, sev);
    case 'air_quality': return airQualityIcon(online, sev);
    case 'water_level': return waterIcon(online, sev);
    default:            return acousticIcon(online);
  }
}

// Gateway icon (unchanged)
const gatewayIcon = L.divIcon({
  html: '<div style="width:12px;height:12px;background:#2d7a48;border:2px solid #166534;transform:rotate(45deg);border-radius:2px"></div>',
  className: '', iconSize: [12, 12], iconAnchor: [6, 6],
});

// ── Coordinate helpers (unchanged) ───────────────────────────────────────────

function getNodeCoords(node: NodeStatus): [number, number] {
  if (node.lat && node.lon) return [node.lat, node.lon];
  const mock = MOCK_NODES.find(m => m.node_id === node.node_id);
  return mock ? [mock.lat!, mock.lon!] : [28.51975, 77.36538];
}

function getAlertCoords(alert: Alert, nodes: NodeStatus[]): [number, number] {
  const node = nodes.find(n => n.node_id === alert.node_id);
  if (node) return getNodeCoords(node);
  return [28.51975, 77.36538];
}

// ── Hazard popup content ─────────────────────────────────────────────────────

function HazardDetail({ node }: { node: NodeStatus }) {
  const h = node.latest_hazard;
  if (!h) return null;

  const fieldLabels = SENSOR_FIELD_LABELS[h.hazard_type] ?? [];
  const sensorValues = [h.sensor_value_1, h.sensor_value_2, h.sensor_value_3];
  const sevLabel = h.severity.toUpperCase();
  const sevBg: Record<string, string> = {
    critical: '#ef4444', warning: '#f97316', watch: '#f59e0b', normal: '#22c55e',
  };

  return (
    <div className="text-[11px] leading-relaxed font-sans space-y-0.5">
      <p className="font-mono font-bold">{node.node_id}</p>
      <p className="text-[10px] text-gray-400">{NODE_TYPE_LABELS[node.node_type] ?? node.node_type}</p>
      <p className="uppercase text-[10px]">{node.status}</p>
      <hr style={{ borderColor: '#333', margin: '3px 0' }} />
      <p>
        <span
          style={{
            background: sevBg[h.severity] ?? '#6b7280',
            color: '#fff',
            padding: '1px 4px',
            borderRadius: 3,
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: '0.05em',
          }}
        >
          {sevLabel}
        </span>
        {' '}Risk: {h.risk_score}/100
      </p>
      <p>Confidence: {h.confidence}%</p>
      {fieldLabels.map((label, i) =>
        sensorValues[i] != null ? (
          <p key={i}>{label}: {sensorValues[i]}</p>
        ) : null
      )}
      {h.rssi != null && <p style={{ color: '#9ca3af', fontSize: 10 }}>RSSI {h.rssi} dBm · SNR {h.snr} dB</p>}
      <p style={{ color: '#9ca3af', fontSize: 10 }}>
        {new Date(h.recorded_at).toLocaleTimeString()}
      </p>
      <p style={{ color: '#6b7280', fontSize: 9, fontStyle: 'italic', marginTop: 2 }}>
        Thresholds are MVP defaults — not field-calibrated
      </p>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ThreatMap({ nodes, alerts, onAlertClick }: Props) {
  const center: [number, number] = [28.51975, 77.36538];
  const activeAlerts = alerts.filter(a => !a.acknowledged && a.severity !== 'low');

  return (
    <div className="bg-white dark:bg-[#0f1419] border border-gray-200 dark:border-white/5 rounded-lg overflow-hidden">
      {/* Legend */}
      <div className="flex flex-wrap gap-x-4 gap-y-1 px-3 py-1.5 bg-black/30 text-[10px] text-gray-400 border-b border-white/5">
        <span className="flex items-center gap-1">
          <span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: nodeOnlineColor }} />
          Acoustic/Vision
        </span>
        <span className="flex items-center gap-1">
          <span style={{ display: 'inline-block', width: 0, height: 0, borderLeft: '5px solid transparent', borderRight: '5px solid transparent', borderBottom: '9px solid #ef4444' }} />
          Fire/Smoke
        </span>
        <span className="flex items-center gap-1">
          <span style={{ display: 'inline-block', width: 8, height: 8, background: '#f97316', borderRadius: 2, transform: 'rotate(45deg)' }} />
          Air Quality
        </span>
        <span className="flex items-center gap-1">
          <span style={{ display: 'inline-block', width: 8, height: 8, background: '#38bdf8', borderRadius: '50% 50% 50% 0', transform: 'rotate(-45deg)' }} />
          Water Level
        </span>
        <span className="ml-auto flex items-center gap-2">
          <span className="flex items-center gap-1"><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: '#ef4444' }} />Critical</span>
          <span className="flex items-center gap-1"><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: '#f59e0b' }} />Medium</span>
          <span className="flex items-center gap-1"><span style={{ display: 'inline-block', width: 8, height: 8, borderRadius: '50%', background: '#3b82f6' }} />Low</span>
        </span>
      </div>

      <div className="h-[400px] lg:h-[460px]">
        <MapContainer center={center} zoom={13} minZoom={4} maxZoom={18} style={{ height: '100%', width: '100%' }} zoomControl={true}>
          <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png" attribution="&copy; CARTO" />
          <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png" zIndex={400} />
          <IndiaLabelsOverlay />
          <IndiaBoundaryLayer visible={true} />

          {/* Gateway */}
          <Marker position={center} icon={gatewayIcon}>
            <Popup><span className="text-xs font-mono font-medium">LoRa Gateway — NODE_B</span></Popup>
          </Marker>

          {/* Nodes — distinct icon per type */}
          {nodes.map(node => {
            const pos = getNodeCoords(node);
            const icon = getNodeIcon(node);
            const isHazardNode = ['fire', 'air_quality', 'water_level'].includes(node.node_type);

            return (
              <Marker key={node.node_id} position={pos} icon={icon}>
                <Popup>
                  {isHazardNode ? (
                    <HazardDetail node={node} />
                  ) : (
                    <div className="text-[11px] leading-relaxed font-sans space-y-0.5">
                      <p className="font-mono font-bold">{node.node_id}</p>
                      <p className="text-[10px] text-gray-400">{NODE_TYPE_LABELS[node.node_type] ?? node.node_type}</p>
                      <p className="uppercase text-[10px]">{node.status}</p>
                      <p>Battery: {node.battery_pct}%</p>
                      <p>Last seen: {new Date(node.last_seen).toLocaleTimeString()}</p>
                    </div>
                  )}
                </Popup>
              </Marker>
            );
          })}

          {/* Threat markers (unchanged visual behaviour) */}
          {activeAlerts.map(alert => {
            const pos = getAlertCoords(alert, nodes);
            const color = sevColor[alert.severity];
            return (
              <CircleMarker
                key={alert.id}
                center={pos}
                radius={8}
                pathOptions={{ fillColor: color, color, weight: 2.5, fillOpacity: 0.85, opacity: 0.4 }}
                eventHandlers={{ click: () => onAlertClick?.(alert) }}
              >
                <Popup>
                  <div className="text-[11px] leading-relaxed font-sans space-y-0.5">
                    <p className="font-semibold uppercase text-xs">{alert.label}</p>
                    <p>Severity: {alert.severity}</p>
                    <p>Score: {Math.round(alert.fused_score * 100)}%</p>
                    <p>Node: {alert.node_id}</p>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}
        </MapContainer>
      </div>
    </div>
  );
}
