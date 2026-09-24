/**
 * MultiNodeStatusPanel
 *
 * Shows a compact status card for each hazard node (fire, air_quality,
 * water_level) with its latest reading and a trend sparkline.
 *
 * Matches existing dashboard card styling (dark bg, border-white/5, same
 * font sizes as NodeHealthPanel and AlertFeed).
 *
 * Place this below ThreatMap on the Dashboard / LiveMap pages.
 */

import { NodeStatus, NODE_TYPE_LABELS, SENSOR_FIELD_LABELS, HazardSeverity } from '../../types';
import NodeHazardTrend from './NodeHazardTrend';

interface Props {
  nodes: NodeStatus[];
}

const SEV_BADGE: Record<string, { bg: string; text: string }> = {
  critical: { bg: 'bg-red-500/20',    text: 'text-red-400' },
  warning:  { bg: 'bg-orange-500/20', text: 'text-orange-400' },
  watch:    { bg: 'bg-amber-500/20',  text: 'text-amber-400' },
  normal:   { bg: 'bg-green-500/20',  text: 'text-green-400' },
};

const NODE_TYPE_ICON: Record<string, string> = {
  fire:        '🔥',
  air_quality: '🏭',
  water_level: '🌊',
};

function SeverityBadge({ sev }: { sev: string }) {
  const style = SEV_BADGE[sev] ?? SEV_BADGE.normal;
  return (
    <span className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${style.bg} ${style.text}`}>
      {sev}
    </span>
  );
}

function HazardNodeCard({ node }: { node: NodeStatus }) {
  const h = node.latest_hazard;
  const icon = NODE_TYPE_ICON[node.node_type] ?? '📡';
  const label = NODE_TYPE_LABELS[node.node_type] ?? node.node_type;
  const fieldLabels = h ? (SENSOR_FIELD_LABELS[h.hazard_type] ?? []) : [];
  const sensorValues = h ? [h.sensor_value_1, h.sensor_value_2, h.sensor_value_3] : [];

  return (
    <div className="bg-white dark:bg-[#0f1419] border border-gray-200 dark:border-white/5 rounded-lg p-3 space-y-2">
      {/* Header row */}
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-mono font-semibold text-white/90 flex items-center gap-1">
            <span>{icon}</span>
            {node.node_id}
          </p>
          <p className="text-[10px] text-gray-400">{label}</p>
        </div>
        <div className="flex flex-col items-end gap-1 shrink-0">
          <span
            className={`text-[9px] font-bold uppercase px-1.5 py-0.5 rounded ${
              node.status === 'online'
                ? 'bg-green-500/20 text-green-400'
                : 'bg-gray-500/20 text-gray-400'
            }`}
          >
            {node.status}
          </span>
          {h && <SeverityBadge sev={h.severity} />}
        </div>
      </div>

      {/* Latest reading */}
      {h ? (
        <div className="space-y-0.5">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-gray-400">Risk score</span>
            <span className="text-xs font-semibold text-white/90">{h.risk_score}/100</span>
            <span className="text-[10px] text-gray-400">Conf. {h.confidence}%</span>
          </div>
          {fieldLabels.map((fl, i) =>
            sensorValues[i] != null ? (
              <p key={i} className="text-[10px] text-gray-400">
                {fl}: <span className="text-white/70">{sensorValues[i]}</span>
              </p>
            ) : null
          )}
          {h.rssi != null && (
            <p className="text-[9px] text-gray-600">
              RSSI {h.rssi} dBm · SNR {h.snr} dB
            </p>
          )}
        </div>
      ) : (
        <p className="text-[10px] text-gray-500 italic">No readings yet</p>
      )}

      {/* Trend sparkline */}
      {node.status === 'online' && h && (
        <NodeHazardTrend
          nodeId={node.node_id}
          hazardType={h.hazard_type as 'FIRE' | 'AIR_QUALITY' | 'WATER_LEVEL'}
          limit={20}
        />
      )}
    </div>
  );
}

export default function MultiNodeStatusPanel({ nodes }: Props) {
  const hazardNodes = nodes.filter(n =>
    ['fire', 'air_quality', 'water_level'].includes(n.node_type)
  );

  if (hazardNodes.length === 0) return null;

  return (
    <div className="space-y-2">
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-widest px-0.5">
        Environmental Hazard Nodes
      </h3>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {hazardNodes.map(node => (
          <HazardNodeCard key={node.node_id} node={node} />
        ))}
      </div>
      <p className="text-[9px] text-gray-600 italic px-0.5">
        Risk thresholds are MVP rule-based defaults (see firmware README) — not field-validated values.
      </p>
    </div>
  );
}
