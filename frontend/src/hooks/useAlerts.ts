import { useState, useEffect, useCallback } from 'react';
import { Alert } from '../types';
import { getAlerts, acknowledgeAlert as ackApi } from '../services/api';

export function useAlerts() {
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getAlerts()
      .then(data => { setAlerts(data); setError(null); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const pushAlert = useCallback((alert: Alert) => {
    setAlerts(prev => [alert, ...prev]);
  }, []);

  const acknowledge = useCallback(async (id: number, officer: string) => {
    await ackApi(id, officer);
    setAlerts(prev => prev.map(a => a.id === id ? { ...a, acknowledged: true, acknowledged_by: officer } : a));
  }, []);

  return { alerts, loading, error, pushAlert, acknowledge };
}
