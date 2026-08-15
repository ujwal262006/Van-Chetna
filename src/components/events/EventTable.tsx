import { LoRaEvent } from '../../types';
import LoadingState from '../ui/LoadingState';

interface Props {
  events: LoRaEvent[];
  loading: boolean;
}

export default function EventTable({ events, loading }: Props) {
  if (loading) return <LoadingState message="Loading events..." />;

  return (
    <div className="bg-white dark:bg-[#0f1419] border border-gray-200 dark:border-white/5 rounded-lg overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="bg-gray-50 dark:bg-white/[0.02] text-[10px] uppercase tracking-wider text-gray-500 border-b border-gray-200 dark:border-white/5">
              <th className="px-4 py-3 font-medium">Event ID</th>
              <th className="px-4 py-3 font-medium">Node</th>
              <th className="px-4 py-3 font-medium">Sensor</th>
              <th className="px-4 py-3 font-medium">Class</th>
              <th className="px-4 py-3 font-medium">Confidence</th>
              <th className="px-4 py-3 font-medium">Timestamp</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100 dark:divide-white/[0.03]">
            {events.map(evt => (
              <tr key={evt.event_id} className="hover:bg-gray-50 dark:hover:bg-white/[0.01] transition-colors">
                <td className="px-4 py-3 font-mono text-xs text-gray-500">{evt.event_id}</td>
                <td className="px-4 py-3 font-mono text-xs text-gray-800 dark:text-gray-200 font-medium">{evt.node_id}</td>
                <td className="px-4 py-3 text-xs text-gray-600 dark:text-gray-400 capitalize">{evt.sensor_type}</td>
                <td className="px-4 py-3 text-xs text-gray-700 dark:text-gray-300 capitalize">{evt.class}</td>
                <td className="px-4 py-3 font-mono text-xs text-emerald-600 dark:text-emerald-400">{Math.round(evt.confidence * 100)}%</td>
                <td className="px-4 py-3 font-mono text-[11px] text-gray-500">{new Date(evt.timestamp).toLocaleString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
