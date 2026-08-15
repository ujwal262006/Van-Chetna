import DashboardLayout from '../components/layout/DashboardLayout';
import { useLiveAlerts } from '../hooks/useLiveAlerts';
import { useCallback } from 'react';

export default function Settings() {
  const { connectionState } = useLiveAlerts(useCallback(() => {}, []));

  return (
    <DashboardLayout title="Settings" connectionState={connectionState}>
      <div className="bg-[#0f1419] border border-white/5 rounded-lg p-6 max-w-xl">
        <h2 className="text-sm font-semibold text-gray-200 mb-4">System Configuration</h2>
        <div className="space-y-4 text-sm text-gray-400">
          <div className="flex justify-between items-center py-2 border-b border-white/5">
            <span>API Endpoint</span>
            <span className="font-mono text-xs text-gray-500">{import.meta.env.VITE_API_URL || 'http://localhost:8000'}</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-white/5">
            <span>Demo Mode</span>
            <span className="font-mono text-xs text-emerald-400">{import.meta.env.VITE_DEMO_MODE === 'true' ? 'Enabled' : 'Disabled'}</span>
          </div>
          <div className="flex justify-between items-center py-2 border-b border-white/5">
            <span>WebSocket</span>
            <span className="font-mono text-xs text-gray-500">/ws/live</span>
          </div>
        </div>
      </div>
    </DashboardLayout>
  );
}
