import DashboardLayout from '../components/layout/DashboardLayout';
import EventTable from '../components/events/EventTable';
import { useEvents } from '../hooks/useEvents';
import { useLiveAlerts } from '../hooks/useLiveAlerts';
import { useCallback } from 'react';

export default function Events() {
  const { events, loading } = useEvents();
  const { connectionState } = useLiveAlerts(useCallback(() => {}, []));

  return (
    <DashboardLayout title="Events" connectionState={connectionState}>
      <EventTable events={events} loading={loading} />
    </DashboardLayout>
  );
}
