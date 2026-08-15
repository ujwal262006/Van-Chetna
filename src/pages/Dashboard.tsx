import { useState, useCallback } from 'react';
import { AlertTriangle, AlertCircle, Radio, RadioTower, Activity } from 'lucide-react';
import DashboardLayout from '../components/layout/DashboardLayout';
import ThreatMap from '../components/map/ThreatMap';
import AlertFeed from '../components/alerts/AlertFeed';
import AlertDetail from '../components/alerts/AlertDetail';
import NodeHealthPanel from '../components/nodes/NodeHealthPanel';
import StatCard from '../components/ui/StatCard';
import NotificationToast from '../components/ui/NotificationToast';
import { Alert } from '../types';
import { useAlerts } from '../hooks/useAlerts';
import { useNodes } from '../hooks/useNodes';
import { useEvents } from '../hooks/useEvents';
import { useLiveAlerts } from '../hooks/useLiveAlerts';

export default function Dashboard() {
  const { alerts, loading: alertsLoading, pushAlert, acknowledge } = useAlerts();
  const { nodes, loading: nodesLoading, onlineCount, offlineCount } = useNodes();
  const { events } = useEvents();
  const [selected, setSelected] = useState<Alert | null>(null);
  const [toast, setToast] = useState<Alert | null>(null);
  const [recentIds, setRecentIds] = useState<Set<number>>(new Set());

  const handleNewAlert = useCallback((alert: Alert) => {
    pushAlert(alert);
    setToast(alert);
    setRecentIds(prev => new Set([...prev, alert.id]));
    setTimeout(() => setRecentIds(prev => { const n = new Set(prev); n.delete(alert.id); return n; }), 4000);
  }, [pushAlert]);

  const { connectionState } = useLiveAlerts(handleNewAlert);

  const handleAck = useCallback(async (id: number) => {
    await acknowledge(id, 'Officer Priya');
    if (selected?.id === id) setSelected(prev => prev ? { ...prev, acknowledged: true, acknowledged_by: 'Officer Priya' } : null);
  }, [acknowledge, selected]);

  const criticalCount = alerts.filter(a => a.severity === 'critical' && !a.acknowledged).length;
  const mediumCount = alerts.filter(a => a.severity === 'medium' && !a.acknowledged).length;

  return (
    <DashboardLayout title="Dashboard" connectionState={connectionState} alertCount={criticalCount + mediumCount}>
      {/* KPI */}
      <div className="grid grid-cols-2 lg:grid-cols-5 gap-3 mb-5">
        <StatCard label="Critical Alerts" value={criticalCount} icon={AlertTriangle} color="text-red-400" />
        <StatCard label="Medium Alerts" value={mediumCount} icon={AlertCircle} color="text-amber-400" />
        <StatCard label="Online Nodes" value={onlineCount} icon={Radio} color="text-emerald-400" />
        <StatCard label="Offline Nodes" value={offlineCount} icon={RadioTower} color="text-gray-500" />
        <StatCard label="Events Today" value={events.length} icon={Activity} color="text-blue-400" />
      </div>

      {/* Main grid */}
      <div className="grid grid-cols-1 xl:grid-cols-3 gap-4">
        <div className="xl:col-span-2 space-y-4">
          <ThreatMap nodes={nodes} alerts={alerts} onAlertClick={setSelected} />
          <div className="bg-white dark:bg-[#0f1419] border border-gray-200 dark:border-white/5 rounded-lg p-4">
            <h3 className="text-[11px] uppercase tracking-wider text-gray-500 font-semibold mb-3">Active Alerts</h3>
            <AlertFeed alerts={alerts} loading={alertsLoading} onAlertClick={setSelected} recentIds={recentIds} />
          </div>
        </div>
        <div>
          <NodeHealthPanel nodes={nodes} loading={nodesLoading} />
        </div>
      </div>

      {selected && <AlertDetail alert={selected} onClose={() => setSelected(null)} onAcknowledge={handleAck} />}
      <NotificationToast alert={toast} onDismiss={() => setToast(null)} />
    </DashboardLayout>
  );
}
