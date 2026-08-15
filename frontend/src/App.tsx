import { Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import LiveMap from './pages/LiveMap';
import Alerts from './pages/Alerts';
import Events from './pages/Events';
import Nodes from './pages/Nodes';
import Analytics from './pages/Analytics';
import Settings from './pages/Settings';

export default function App() {
  return (
    <Routes>
      <Route path="/dashboard" element={<Dashboard />} />
      <Route path="/map" element={<LiveMap />} />
      <Route path="/alerts" element={<Alerts />} />
      <Route path="/events" element={<Events />} />
      <Route path="/nodes" element={<Nodes />} />
      <Route path="/analytics" element={<Analytics />} />
      <Route path="/settings" element={<Settings />} />
      <Route path="/" element={<Navigate to="/dashboard" replace />} />
      <Route path="*" element={<Navigate to="/dashboard" replace />} />
    </Routes>
  );
}
