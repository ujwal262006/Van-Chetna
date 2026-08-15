import { Battery, BatteryLow, BatteryWarning } from 'lucide-react';

export default function BatteryIndicator({ pct }: { pct: number }) {
  const color = pct > 50 ? 'text-emerald-400' : pct > 20 ? 'text-amber-400' : 'text-red-400';
  const barColor = pct > 50 ? 'bg-emerald-500' : pct > 20 ? 'bg-amber-500' : 'bg-red-500';
  const Icon = pct > 50 ? Battery : pct > 20 ? BatteryWarning : BatteryLow;

  return (
    <div className="flex items-center gap-2">
      <Icon size={14} className={color} />
      <div className="w-12 h-1.5 bg-white/5 rounded-full overflow-hidden">
        <div className={`h-full rounded-full ${barColor}`} style={{ width: `${pct}%` }} />
      </div>
      <span className={`font-mono text-[11px] ${color}`}>{pct}%</span>
    </div>
  );
}
