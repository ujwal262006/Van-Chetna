import { AlertTriangle, AlertCircle, Info } from 'lucide-react';
import { Severity } from '../../types';

const config: Record<Severity, { bg: string; text: string; icon: typeof AlertTriangle }> = {
  critical: { bg: 'bg-red-500/10 border-red-500/30', text: 'text-red-400', icon: AlertTriangle },
  medium: { bg: 'bg-amber-500/10 border-amber-500/30', text: 'text-amber-400', icon: AlertCircle },
  low: { bg: 'bg-blue-400/10 border-blue-400/30', text: 'text-blue-400', icon: Info },
};

export default function SeverityBadge({ severity }: { severity: Severity }) {
  const { bg, text, icon: Icon } = config[severity];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded border text-[10px] font-semibold uppercase tracking-wide ${bg} ${text}`}>
      <Icon size={11} />
      {severity}
    </span>
  );
}
