import { useState, useEffect } from 'react';
import { NodeStatus } from '../types';
import { getNodeStatus } from '../services/api';

export function useNodes() {
  const [nodes, setNodes] = useState<NodeStatus[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getNodeStatus()
      .then(data => { setNodes(data); setError(null); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  const onlineCount = nodes.filter(n => n.status === 'online').length;
  const offlineCount = nodes.filter(n => n.status === 'offline').length;

  return { nodes, loading, error, onlineCount, offlineCount };
}
