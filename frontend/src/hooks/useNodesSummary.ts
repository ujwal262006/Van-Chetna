/**
 * useNodesSummary
 *
 * Fetches the unified multi-node summary from GET /nodes/summary.
 * Returns all nodes (acoustic + vision + hazard) with their latest
 * hazard readings attached.
 *
 * This hook is intended for components that need the full picture
 * (ThreatMap, MultiNodeStatusPanel, Dashboard KPIs).
 *
 * The existing useNodes hook (which calls GET /nodes/status) is kept
 * untouched and still used by NodeHealthPanel.
 */

import { useState, useEffect, useCallback } from 'react';
import { NodeStatus } from '../types';
import { getNodesSummary } from '../services/api';

export function useNodesSummary(refreshIntervalMs = 10000) {
  const [nodes, setNodes] = useState<NodeStatus[]>([]);
  const [totalOnline, setTotalOnline] = useState(0);
  const [totalOffline, setTotalOffline] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetch = useCallback(() => {
    getNodesSummary()
      .then(data => {
        setNodes(data.nodes);
        setTotalOnline(data.total_online);
        setTotalOffline(data.total_offline);
        setError(null);
      })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    fetch();
    const timer = setInterval(fetch, refreshIntervalMs);
    return () => clearInterval(timer);
  }, [fetch, refreshIntervalMs]);

  return { nodes, totalOnline, totalOffline, loading, error };
}
