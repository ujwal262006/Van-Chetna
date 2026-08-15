import { useEffect, useState } from 'react';
import { AlertTriangle, X } from 'lucide-react';
import { Alert } from '../../types';

interface Props {
  alert: Alert | null;
  onDismiss: () => void;
}

export default function NotificationToast({ alert, onDismiss }: Props) {
  const [visible, setVisible] = useState(false);

  useEffect(() => {
    if (alert) {
      setVisible(true);
      const timer = setTimeout(() => { setVisible(false); onDismiss(); }, 5000);
      return () => clearTimeout(timer);
    }
  }, [alert, onDismiss]);

  if (!alert || !visible) return null;

  const borderColor = alert.severity === 'critical' ? 'border-l-red-500' : 'border-l-amber-500';

  return (
    <div className={`fixed top-4 right-4 z-[9999] w-80 bg-white dark:bg-[#0f1419] border border-gray-200 dark:border-white/10 ${borderColor} border-l-[3px] rounded-lg p-4 shadow-lg dark:shadow-2xl animate-slide-in`}>
      <div className="flex items-start gap-3">
        <AlertTriangle size={16} className={alert.severity === 'critical' ? 'text-red-500' : 'text-amber-500'} />
        <div className="flex-1 min-w-0">
          <p className="text-xs font-semibold text-gray-800 dark:text-gray-200 truncate">{alert.label}</p>
          <p className="text-[11px] text-gray-500 mt-0.5 font-mono">{alert.node_id} · {Math.round(alert.fused_score * 100)}%</p>
        </div>
        <button onClick={() => { setVisible(false); onDismiss(); }} className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
          <X size={14} />
        </button>
      </div>
    </div>
  );
}
