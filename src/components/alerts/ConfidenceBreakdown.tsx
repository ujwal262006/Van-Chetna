import { Alert } from '../../types';

function Bar({ label, value }: { label: string; value: number }) {
  const pct = Math.round(value * 100);
  return (
    <div>
      <div className="flex justify-between mb-1">
        <span className="text-xs text-gray-600 dark:text-gray-400">{label}</span>
        <span className="font-mono text-xs text-gray-800 dark:text-gray-200">{pct}%</span>
      </div>
      <div className="h-2 bg-gray-100 dark:bg-white/5 rounded-full overflow-hidden">
        <div className="h-full bg-emerald-500 rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function ConfidenceBreakdown({ alert }: { alert: Alert }) {
  return (
    <div className="space-y-3">
      <h4 className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold">AI Confidence Breakdown</h4>
      <Bar label="Acoustic" value={alert.acoustic_confidence} />
      <Bar label="Vision — Person" value={alert.vision_person_confidence} />
      <Bar label="Vision — Vehicle" value={alert.vision_vehicle_confidence} />
    </div>
  );
}
