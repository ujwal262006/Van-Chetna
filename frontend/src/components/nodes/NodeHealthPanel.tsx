import { Radio } from 'lucide-react';
import { NodeStatus } from '../../types';
import BatteryIndicator from '../ui/BatteryIndicator';
import LoadingState from '../ui/LoadingState';

interface Props {
  nodes: NodeStatus[];
  loading: boolean;
}

function timeAgo(iso: string) {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${s}s ago`;
  if (s < 3600) return `${Math.floor(s / 60)}m ago`;
  return `${Math.floor(s / 3600)}h ago`;
}

export default function NodeHealthPanel({ nodes, loading }: Props) {
  if (loading) return <LoadingState message="Loading nodes..." />;

  return (
    <div className="bg-white dark:bg-[#0f1419] border border-gray-200 dark:border-white/5 rounded-lg overflow-hidden">
      <div className="px-4 py-3 border-b border-gray-100 dark:border-white/5 flex items-center justify-between">
        <h3 className="text-[11px] font-semibold uppercase tracking-wider text-gray-500">Node Health</h3>
        <span className="text-[10px] font-mono text-emerald-600 dark:text-emerald-400">{nodes.filter(n => n.status === 'online').length}/{nodes.length} online</span>
      </div>
      <div className="divide-y divide-gray-100 dark:divide-white/[0.03]">
        {nodes.map(node => (
          <div key={node.node_id} className="px-4 py-3 flex items-center gap-3 hover:bg-gray-50 dark:hover:bg-white/[0.01] transition-colors">
            <div className={`w-2 h-2 rounded-full shrink-0 ${node.status === 'online' ? 'bg-emerald-500' : 'bg-gray-400 dark:bg-gray-600'}`} />
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2">
                <Radio size={12} className="text-gray-400" />
                <span className="font-mono text-sm text-gray-800 dark:text-gray-200 font-medium">{node.node_id}</span>
                <span className={`text-[9px] uppercase font-bold ${node.status === 'online' ? 'text-emerald-600 dark:text-emerald-400' : 'text-gray-500'}`}>{node.status}</span>
              </div>
              <div className="flex items-center gap-4 mt-1">
                <BatteryIndicator pct={node.battery_pct} />
                <span className="font-mono text-[10px] text-gray-500">{timeAgo(node.last_seen)}</span>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
