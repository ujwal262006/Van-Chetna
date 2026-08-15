import { ShieldCheck } from 'lucide-react';

interface Props {
  title?: string;
  message?: string;
}

export default function EmptyState({ title = 'NO ACTIVE THREATS', message = 'All monitored zones are currently operating normally.' }: Props) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="w-12 h-12 rounded-full bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center mb-4">
        <ShieldCheck size={24} className="text-emerald-400" />
      </div>
      <h3 className="text-sm font-semibold text-gray-300 mb-1">{title}</h3>
      <p className="text-xs text-gray-500 max-w-xs">{message}</p>
    </div>
  );
}
