import { useState, useCallback } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import ThreatMap from '../components/map/ThreatMap';
import MultiNodeStatusPanel from '../components/nodes/MultiNodeStatusPanel';
import AlertDetail from '../components/alerts/AlertDetail';
import { Alert } from '../types';
import { useAlerts } from '../hooks/useAlerts';
import { useNodesSummary } from '../hooks/useNodesSummary';
import { useLiveAlerts } from '../hooks/useLiveAlerts';

export default function LiveMap() {
  const { alerts, pushAlert, acknowledge } = useAlerts();
  const { nodes } = useNodesSummary();
  const [selected, setSelected] = useState<Alert | null>(null);

  const { connectionState } = useLiveAlerts(useCallback((a: Alert) => pushAlert(a), [pushAlert]));

  return (
    <DashboardLayout title="Live Map" connectionState={connectionState}>
      <div className="space-y-4">
        <ThreatMap nodes={nodes} alerts={alerts} onAlertClick={setSelected} />
        <MultiNodeStatusPanel nodes={nodes} />
      </div>
      {selected && <AlertDetail alert={selected} onClose={() => setSelected(null)} onAcknowledge={id => { acknowledge(id, 'Officer Priya'); setSelected(null); }} />}
    </DashboardLayout>
  );
}
