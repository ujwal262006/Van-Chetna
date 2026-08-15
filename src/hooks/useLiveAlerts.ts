import { useEffect, useRef, useState, useCallback } from 'react';
import { Alert, ConnectionState } from '../types';
import { getWebSocketUrl, isDemoMode, generateMockAlert } from '../services/api';

interface UseLiveAlertsReturn {
  connectionState: ConnectionState;
  latestAlert: Alert | null;
}

export function useLiveAlerts(onNewAlert: (alert: Alert) => void): UseLiveAlertsReturn {
  const [connectionState, setConnectionState] = useState<ConnectionState>('disconnected');
  const [latestAlert, setLatestAlert] = useState<Alert | null>(null);
  const wsRef = useRef<WebSocket | null>(null);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout>>();
  const demoTimer = useRef<ReturnType<typeof setInterval>>();
  const onNewAlertRef = useRef(onNewAlert);
  onNewAlertRef.current = onNewAlert;

  const connectWs = useCallback(() => {
    const url = getWebSocketUrl();
    if (!url) return;

    setConnectionState('reconnecting');
    const ws = new WebSocket(url);
    wsRef.current = ws;

    ws.onopen = () => setConnectionState('connected');

    ws.onmessage = (evt) => {
      try {
        const alert: Alert = JSON.parse(evt.data);
        setLatestAlert(alert);
        onNewAlertRef.current(alert);
      } catch { /* ignore malformed */ }
    };

    ws.onclose = () => {
      setConnectionState('disconnected');
      reconnectTimer.current = setTimeout(connectWs, 3000);
    };

    ws.onerror = () => ws.close();
  }, []);

  useEffect(() => {
    if (isDemoMode()) {
      // Simulate WebSocket with periodic mock alerts
      setConnectionState('connected');
      demoTimer.current = setInterval(() => {
        const alert = generateMockAlert();
        setLatestAlert(alert);
        onNewAlertRef.current(alert);
      }, 10000 + Math.random() * 8000);

      return () => {
        if (demoTimer.current) clearInterval(demoTimer.current);
      };
    }

    // Real WebSocket
    connectWs();
    return () => {
      if (wsRef.current) wsRef.current.close();
      if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    };
  }, [connectWs]);

  return { connectionState, latestAlert };
}
