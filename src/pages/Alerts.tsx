import { useState, useCallback } from 'react';
import DashboardLayout from '../components/layout/DashboardLayout';
import AlertFeed from '../components/alerts/AlertFeed';
import AlertDetail from '../components/alerts/AlertDetail';
import { Alert } from '../types';
import { useAlerts } from '../hooks/useAlerts';
import { useLiveAlerts } from '../hooks/useLiveAlerts';

export default function Alerts() {
  const { alerts, loading, pushAlert, acknowledge } = useAlerts();
  const [selected, setSelected] = useState<Alert | null>(null);

  const { connectionState } = useLiveAlerts(useCallback((a: Alert) => pushAlert(a), [pushAlert]));

  return (
    <DashboardLayout title="Alerts" connectionState={connectionState}>
      <div className="max-w-3xl">
        <AlertFeed alerts={alerts} loading={loading} onAlertClick={setSelected} />
      </div>
      {selected && <AlertDetail alert={selected} onClose={() => setSelected(null)} onAcknowledge={id => { acknowledge(id, 'Officer Priya'); setSelected(prev => prev ? { ...prev, acknowledged: true, acknowledged_by: 'Officer Priya' } : null); }} />}
    </DashboardLayout>
  );
}
