/**
 * NodeHazardTrend
 *
 * Renders a compact risk-score trend sparkline for a single hazard node
 * (fire, air_quality, or water_level).  Matches the existing dashboard's
 * Recharts-based visual language — same axis style, same colour palette.
 *
 * Usage:
 *   <NodeHazardTrend nodeId="RIV01" hazardType="WATER_LEVEL" />
 *
 * Data is fetched from GET /hazard-events/{nodeId}/history.
 * In DEMO_MODE, uses MOCK_HAZARD_EVENTS from mockData.ts.
 */

import { useEffect, useState } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, ReferenceLine,
} from 'recharts';
import { HazardEventOut } from '../../types';
import { getNodeHazardHistory } from '../../services/api';

interface Props {
  nodeId: string;
  hazardType: 'FIRE' | 'AIR_QUALITY' | 'WATER_LEVEL';
  /** How many readings to show in the sparkline (default 20) */
  limit?: number;
}

// Colour per hazard type — matches node icon colours in ThreatMap
const HAZARD_COLORS: Record<string, string> = {
  FIRE:        '#ef4444',
  AIR_QUALITY: '#f97316',
  WATER_LEVEL: '#38bdf8',
};

const HAZARD_LABELS: Record<string, string> = {
  FIRE:        'Fire Risk Score',
  AIR_QUALITY: 'Air Quality Risk Score',
  WATER_LEVEL: 'Water Level Risk Score',
};

interface ChartPoint {
  time: string;
  risk: number;
  severity: string;
}

function toChartPoints(events: HazardEventOut[]): ChartPoint[] {
  // Reverse so oldest is on the left
  return [...events].reverse().map(e => ({
    time: new Date(e.recorded_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }),
    risk: e.risk_score,
    severity: e.severity,
  }));
}

// Severity band reference lines (MVP thresholds — matches firmware ladder)
const SEV_BANDS = [
  { value: 25, label: 'Watch',    stroke: '#f59e0b' },
  { value: 50, label: 'Warning',  stroke: '#f97316' },
  { value: 80, label: 'Critical', stroke: '#ef4444' },
];

export default function NodeHazardTrend({ nodeId, hazardType, limit = 20 }: Props) {
  const [points, setPoints] = useState<ChartPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getNodeHazardHistory(nodeId, limit)
      .then(events => {
        setPoints(toChartPoints(events));
        setError(null);
      })
      .catch(err => setError(String(err)))
      .finally(() => setLoading(false));
  }, [nodeId, limit]);

  const color = HAZARD_COLORS[hazardType] ?? '#94a3b8';
  const label = HAZARD_LABELS[hazardType] ?? 'Risk Score';

  if (loading) {
    return (
      <div className="flex items-center justify-center h-24 text-xs text-gray-500">
        Loading trend…
      </div>
    );
  }

  if (error || points.length === 0) {
    return (
      <div className="flex items-center justify-center h-24 text-xs text-gray-500">
        {error ? `Error: ${error}` : 'No readings yet'}
      </div>
    );
  }

  return (
    <div className="space-y-1">
      <p className="text-[10px] text-gray-400 font-medium uppercase tracking-wide">{label}</p>
      <ResponsiveContainer width="100%" height={80}>
        <AreaChart data={points} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <defs>
            <linearGradient id={`grad_${nodeId}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%"  stopColor={color} stopOpacity={0.35} />
              <stop offset="95%" stopColor={color} stopOpacity={0.02} />
            </linearGradient>
          </defs>
          <XAxis dataKey="time" tick={{ fontSize: 8, fill: '#6b7280' }} interval="preserveStartEnd" />
          <YAxis domain={[0, 100]} tick={{ fontSize: 8, fill: '#6b7280' }} />
          {SEV_BANDS.map(band => (
            <ReferenceLine
              key={band.value}
              y={band.value}
              stroke={band.stroke}
              strokeDasharray="3 3"
              strokeOpacity={0.5}
              label={{ value: band.label, fontSize: 7, fill: band.stroke, position: 'insideTopRight' }}
            />
          ))}
          <Tooltip
            contentStyle={{ background: '#111827', border: '1px solid #374151', borderRadius: 6, fontSize: 11 }}
            labelStyle={{ color: '#9ca3af' }}
            formatter={(val: number, _name: string, entry: { payload: ChartPoint }) => [
              `${val}  (${entry.payload.severity.toUpperCase()})`,
              'Risk',
            ]}
          />
          <Area
            type="monotone"
            dataKey="risk"
            stroke={color}
            strokeWidth={1.5}
            fill={`url(#grad_${nodeId})`}
            dot={false}
            activeDot={{ r: 3, fill: color }}
          />
        </AreaChart>
      </ResponsiveContainer>
      <p className="text-[9px] text-gray-600 italic">
        Thresholds are MVP placeholder defaults — not field-calibrated.
      </p>
    </div>
  );
}
