import { useState, useEffect } from 'react';
import { LoRaEvent } from '../types';
import { getEvents } from '../services/api';

export function useEvents() {
  const [events, setEvents] = useState<LoRaEvent[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    getEvents()
      .then(data => { setEvents(data); setError(null); })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  return { events, loading, error };
}
