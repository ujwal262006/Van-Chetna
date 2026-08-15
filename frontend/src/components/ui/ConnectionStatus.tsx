import { Wifi, WifiOff, Loader2 } from 'lucide-react';
import { ConnectionState } from '../../types';

const cfg: Record<ConnectionState, { color: string; label: string; icon: typeof Wifi }> = {
  connected: { color: 'text-emerald-400', label: 'LIVE', icon: Wifi },
  reconnecting: { color: 'text-amber-400', label: 'RECONNECTING', icon: Loader2 },
  disconnected: { color: 'text-red-400', label: 'DISCONNECTED', icon: WifiOff },
};

export default function ConnectionStatus({ state }: { state: ConnectionState }) {
  const { color, label, icon: Icon } = cfg[state];
  return (
    <div className={`flex items-center gap-1.5 text-xs font-medium ${color}`}>
      <Icon size={13} className={state === 'reconnecting' ? 'animate-spin' : ''} />
      <span className="hidden sm:inline">{label}</span>
      <span className="relative flex h-2 w-2">
        <span className={`absolute inline-flex h-full w-full rounded-full opacity-75 ${state === 'connected' ? 'animate-ping bg-emerald-400' : ''}`} />
        <span className={`relative inline-flex h-2 w-2 rounded-full ${state === 'connected' ? 'bg-emerald-400' : state === 'reconnecting' ? 'bg-amber-400' : 'bg-red-400'}`} />
      </span>
    </div>
  );
}
