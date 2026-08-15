import { MapContainer, TileLayer, CircleMarker, Popup, Marker } from 'react-leaflet';
import L from 'leaflet';
import IndiaBoundaryLayer from './IndiaBoundaryLayer';
import IndiaLabelsOverlay from './IndiaLabelsOverlay';
import { Alert, NodeStatus } from '../../types';
import { MOCK_NODES } from '../../services/mockData';

interface Props {
  nodes: NodeStatus[];
  alerts: Alert[];
  onAlertClick?: (alert: Alert) => void;
}

const sevColor: Record<string, string> = { critical: '#ef4444', medium: '#f59e0b', low: '#3b82f6' };
const nodeColor: Record<string, string> = { online: '#34d399', offline: '#4b5563' };

const gatewayIcon = L.divIcon({
  html: '<div style="width:12px;height:12px;background:#2d7a48;border:2px solid #166534;transform:rotate(45deg);border-radius:2px"></div>',
  className: '', iconSize: [12, 12], iconAnchor: [6, 6],
});

// get lat/lon for a node (from mock data if not on the node itself)
function getNodeCoords(node: NodeStatus): [number, number] {
  if (node.lat && node.lon) return [node.lat, node.lon];
  const mock = MOCK_NODES.find(m => m.node_id === node.node_id);
  return mock ? [mock.lat!, mock.lon!] : [21.148, 79.09];
}

function getAlertCoords(alert: Alert, nodes: NodeStatus[]): [number, number] {
  const node = nodes.find(n => n.node_id === alert.node_id);
  if (node) return getNodeCoords(node);
  return [21.148, 79.09];
}

export default function ThreatMap({ nodes, alerts, onAlertClick }: Props) {
  const center: [number, number] = [21.148, 79.09];
  const activeAlerts = alerts.filter(a => !a.acknowledged && a.severity !== 'low');

  return (
    <div className="bg-white dark:bg-[#0f1419] border border-gray-200 dark:border-white/5 rounded-lg overflow-hidden">
      <div className="h-[400px] lg:h-[480px]">
        <MapContainer center={center} zoom={13} minZoom={4} maxZoom={18} style={{ height: '100%', width: '100%' }} zoomControl={true}>
          <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_nolabels/{z}/{x}/{y}{r}.png" attribution="&copy; CARTO" />
          <TileLayer url="https://{s}.basemaps.cartocdn.com/dark_only_labels/{z}/{x}/{y}{r}.png" zIndex={400} />
          <IndiaLabelsOverlay />
          <IndiaBoundaryLayer visible={true} />

          {/* Gateway */}
          <Marker position={center} icon={gatewayIcon}>
            <Popup><span className="text-xs font-mono font-medium">LoRa Gateway</span></Popup>
          </Marker>

          {/* Nodes */}
          {nodes.map(node => {
            const pos = getNodeCoords(node);
            return (
              <CircleMarker key={node.node_id} center={pos} radius={6}
                pathOptions={{ fillColor: nodeColor[node.status], color: nodeColor[node.status], weight: 1.5, fillOpacity: 0.8, opacity: 0.5 }}>
                <Popup>
                  <div className="text-[11px] leading-relaxed font-sans space-y-0.5">
                    <p className="font-mono font-bold">{node.node_id}</p>
                    <p className="uppercase text-[10px]">{node.status}</p>
                    <p>Battery: {node.battery_pct}%</p>
                    <p>Last seen: {new Date(node.last_seen).toLocaleTimeString()}</p>
                  </div>
                </Popup>
              </CircleMarker>
            );
          })}

          {/* Threat markers */}
          {activeAlerts.map(alert => {
            const pos = getAlertCoords(alert, nodes);
            const color = sevColor[alert.severity];
            return (
              <CircleMarker key={alert.id} center={pos} radius={8}
                pathOptions={{ fillColor: color, color, weight: 2.5, fillOpacity: 0.85, opacity: 0.4 }}
                eventHandlers={{ click: () => onAlertClick?.(alert) }}>
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
