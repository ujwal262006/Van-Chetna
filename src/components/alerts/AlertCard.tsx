import { Clock, Eye } from 'lucide-react';
import { Alert } from '../../types';
import SeverityBadge from '../ui/SeverityBadge';

interface Props {
  alert: Alert;
  onClick: (alert: Alert) => void;
  isNew?: boolean;
}

function timeAgo(iso: string) {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

const borderColor: Record<string, string> = { critical: 'border-l-red-500', medium: 'border-l-amber-500' };

export default function AlertCard({ alert, onClick, isNew }: Props) {
  return (
    <div
      onClick={() => onClick(alert)}
      className={[
        'relative border-l-[3px] bg-white dark:bg-[#0f1419] border border-gray-200 dark:border-white/5 rounded-r-lg p-4 cursor-pointer transition-all hover:bg-gray-50 dark:hover:bg-white/[0.02] hover:border-gray-300 dark:hover:border-white/10',
        borderColor[alert.severity] || 'border-l-blue-400',
        isNew ? 'ring-1 ring-emerald-500/30 animate-slide-in' : '',
        alert.acknowledged ? 'opacity-50' : '',
      ].join(' ')}
      role="button"
      tabIndex={0}
      onKeyDown={e => e.key === 'Enter' && onClick(alert)}
    >
      <div className="flex items-start justify-between gap-3 mb-2">
        <SeverityBadge severity={alert.severity} />
        <span className="flex items-center gap-1 text-[10px] text-gray-500 font-mono shrink-0">
          <Clock size={10} />
          {timeAgo(alert.generated_at)}
        </span>
      </div>

      <p className="text-sm font-semibold text-gray-800 dark:text-gray-200 leading-snug mb-2">{alert.label}</p>

      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3 text-[11px] text-gray-500 font-mono">
          <span>{alert.node_id}</span>
          <span>Fused: {Math.round(alert.fused_score * 100)}%</span>
        </div>
        <button className="flex items-center gap-1 text-[11px] text-emerald-600 dark:text-emerald-500 hover:text-emerald-700 dark:hover:text-emerald-400 transition-colors">
          <Eye size={12} /> Details
        </button>
      </div>

      {alert.acknowledged && (
        <div className="absolute top-3 right-3 text-[9px] bg-emerald-100 dark:bg-emerald-500/10 text-emerald-700 dark:text-emerald-400 border border-emerald-200 dark:border-emerald-500/20 rounded px-1.5 py-0.5 font-medium">
          ACK
        </div>
      )}
    </div>
  );
}
