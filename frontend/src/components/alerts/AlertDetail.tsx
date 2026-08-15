import { X, CheckCircle } from 'lucide-react';
import { Alert } from '../../types';
import SeverityBadge from '../ui/SeverityBadge';
import ConfidenceBreakdown from './ConfidenceBreakdown';

interface Props {
  alert: Alert;
  onClose: () => void;
  onAcknowledge: (id: number) => void;
}

export default function AlertDetail({ alert, onClose, onAcknowledge }: Props) {
  const scorePct = Math.round(alert.fused_score * 100);
  const scoreColor = alert.severity === 'critical' ? 'text-red-500' : alert.severity === 'medium' ? 'text-amber-500' : 'text-blue-500';

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/50 dark:bg-black/70 backdrop-blur-sm" onClick={onClose}>
      <div className="bg-white dark:bg-[#0c1016] border border-gray-200 dark:border-white/10 rounded-xl w-[520px] max-w-[95vw] max-h-[90vh] overflow-y-auto shadow-xl dark:shadow-2xl animate-slide-in" onClick={e => e.stopPropagation()}>
        {/* Header */}
        <div className="flex items-start justify-between p-5 border-b border-gray-100 dark:border-white/5">
          <div>
            <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100 mb-2">{alert.label}</h2>
            <div className="flex items-center gap-2">
              <SeverityBadge severity={alert.severity} />
              {alert.acknowledged && (
                <span className="text-[10px] text-emerald-700 dark:text-emerald-400 bg-emerald-50 dark:bg-emerald-500/10 border border-emerald-200 dark:border-emerald-500/20 rounded px-2 py-0.5">
                  Acknowledged by {alert.acknowledged_by}
                </span>
              )}
            </div>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 transition-colors p-1">
            <X size={18} />
          </button>
        </div>

        {/* Score */}
        <div className="p-5 text-center border-b border-gray-100 dark:border-white/5 bg-gray-50 dark:bg-white/[0.01]">
          <span className={`font-mono text-5xl font-bold ${scoreColor}`}>{scorePct}%</span>
          <p className="text-[10px] uppercase tracking-widest text-gray-500 mt-2">Fused Confidence Score</p>
        </div>

        {/* Body */}
        <div className="p-5 space-y-5">
          <ConfidenceBreakdown alert={alert} />

          <div className="grid grid-cols-2 gap-3">
            <MetaItem label="Node ID" value={alert.node_id} />
            <MetaItem label="Acoustic Class" value={alert.acoustic_class || '—'} />
            <MetaItem label="Generated At" value={new Date(alert.generated_at).toLocaleString()} />
            <MetaItem label="Alert ID" value={`#${alert.id}`} />
          </div>

          {!alert.acknowledged && (
            <button
              onClick={() => onAcknowledge(alert.id)}
              className="w-full flex items-center justify-center gap-2 py-3 bg-emerald-600 hover:bg-emerald-500 text-white text-sm font-semibold rounded-lg transition-colors"
            >
              <CheckCircle size={16} />
              ACKNOWLEDGE ALERT
            </button>
          )}
        </div>
      </div>
    </div>
  );
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-[10px] uppercase tracking-wider text-gray-500">{label}</dt>
      <dd className="font-mono text-sm text-gray-800 dark:text-gray-200 mt-0.5">{value}</dd>
    </div>
  );
}
