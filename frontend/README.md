# Van-Chetna / Forest Guard — Frontend

AI-powered forest surveillance dashboard for real-time threat monitoring.

## Tech Stack

- React 18 + TypeScript
- Vite
- Tailwind CSS
- React Router
- Leaflet / React-Leaflet (map)
- Recharts (analytics)
- Lucide React (icons)

## Quick Start

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Environment Variables

Copy `.env.example` to `.env`:

```bash
cp .env.example .env
```

| Variable | Description | Default |
|----------|-------------|---------|
| `VITE_API_URL` | Backend API base URL | `http://localhost:8000` |
| `VITE_DEMO_MODE` | Use mock data (no backend needed) | `true` |

### Demo Mode

With `VITE_DEMO_MODE=true`, the frontend runs entirely standalone with mock data and simulated WebSocket alerts. No backend required.

### Production Mode

Set `VITE_DEMO_MODE=false` and point `VITE_API_URL` to your running backend:

```env
VITE_API_URL=http://localhost:8000
VITE_DEMO_MODE=false
```

## API Endpoints Used

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/events` | Raw sensor events |
| GET | `/alerts` | Fused/scored alerts |
| POST | `/alerts/{id}/acknowledge` | Acknowledge an alert |
| GET | `/nodes/status` | Sensor node health |
| WS | `/ws/live` | Real-time alert stream |

## Project Structure

```
src/
├── types/          # TypeScript interfaces (exact backend contract)
├── services/       # API layer + mock data
├── hooks/          # useAlerts, useNodes, useEvents, useLiveAlerts, useTheme
├── components/
│   ├── layout/     # DashboardLayout, Sidebar, TopBar
│   ├── map/        # ThreatMap, IndiaBoundaryLayer, IndiaLabelsOverlay
│   ├── alerts/     # AlertFeed, AlertCard, AlertDetail, ConfidenceBreakdown
│   ├── nodes/      # NodeHealthPanel
│   ├── events/     # EventTable
│   ├── analytics/  # AnalyticsCharts
│   └── ui/         # SeverityBadge, StatCard, BatteryIndicator, etc.
├── pages/          # Dashboard, LiveMap, Alerts, Events, Nodes, Analytics, Settings
└── App.tsx         # Router
```

## Features

- **Light/Dark mode** toggle (persists to localStorage)
- **Real-time alerts** via WebSocket with toast notifications
- **Interactive map** with Survey of India boundary overlay
- **Alert detail modal** with AI confidence breakdown
- **Node health** monitoring with battery indicators
- **Analytics** charts (events over time, detection categories, severity)
- **Fully typed** — interfaces match backend API contract exactly

## Map

Uses Leaflet with:
- CartoDB dark/light basemap (no-labels + labels layer)
- Survey of India GeoJSON boundary overlay (`public/india-boundary.geojson`)
- Correct J&K / Ladakh labels per Government of India position

## Build

```bash
npm run build
```

Output goes to `dist/`.
