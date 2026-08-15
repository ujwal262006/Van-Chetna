import DashboardLayout from '../components/layout/DashboardLayout';
import NodeHealthPanel from '../components/nodes/NodeHealthPanel';
import BatteryIndicator from '../components/ui/BatteryIndicator';
import LoadingState from '../components/ui/LoadingState';
import { useNodes } from '../hooks/useNodes';
import { useLiveAlerts } from '../hooks/useLiveAlerts';
import { useCallback } from 'react';

export default function Nodes() {
  const { nodes, loading } = useNodes();
  const { connectionState } = useLiveAlerts(useCallback(() => {}, []));

  if (loading) return <DashboardLayout title="Sensor Nodes" connectionState={connectionState}><LoadingState message="Loading nodes..." /></DashboardLayout>;

  return (
    <DashboardLayout title="Sensor Nodes" connectionState={connectionState}>
      <div className="bg-[#0f1419] border border-white/5 rounded-lg overflow-hidden">
        <table className="w-full text-left">
          <thead>
            <tr className="bg-white/[0.02] text-[10px] uppercase tracking-wider text-gray-600 border-b border-white/5">
              <th className="px-4 py-3 font-medium">Node ID</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Battery</th>
              <th className="px-4 py-3 font-medium">Last Seen</th>
              <th className="px-4 py-3 font-medium">Lat</th>
              <th className="px-4 py-3 font-medium">Lon</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-white/[0.03]">
            {nodes.map(node => (
              <tr key={node.node_id} className="hover:bg-white/[0.01] transition-colors">
                <td className="px-4 py-3 font-mono text-sm text-gray-200 font-medium">{node.node_id}</td>
                <td className="px-4 py-3">
                  <span className={`inline-flex items-center gap-1.5 text-[10px] font-semibold uppercase ${node.status === 'online' ? 'text-emerald-400' : 'text-red-400'}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${node.status === 'online' ? 'bg-emerald-400' : 'bg-red-400'}`} />
                    {node.status}
                  </span>
                </td>
                <td className="px-4 py-3"><BatteryIndicator pct={node.battery_pct} /></td>
                <td className="px-4 py-3 font-mono text-[11px] text-gray-500">{new Date(node.last_seen).toLocaleString()}</td>
                <td className="px-4 py-3 font-mono text-[11px] text-gray-500">{node.lat?.toFixed(4) ?? '—'}</td>
                <td className="px-4 py-3 font-mono text-[11px] text-gray-500">{node.lon?.toFixed(4) ?? '—'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </DashboardLayout>
  );
}
