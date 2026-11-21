import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import AnalyticsPage from "./pages/AnalyticsPage";
import { DataMethodologyPage } from "./pages/DataMethodologyPage";
import LiveMapPage from "./pages/LiveMapPage";
import { NetworkOverviewPage } from "./pages/NetworkOverviewPage";
import { RouteComparisonPage } from "./pages/RouteComparisonPage";
import { RouteIntelligencePage } from "./pages/RouteIntelligencePage";
import { ServiceHealthPage } from "./pages/ServiceHealthPage";
import { PerformanceView } from "./pages/analytics/PerformanceView";
import { RelationshipsView } from "./pages/analytics/RelationshipsView";
import { RidershipView } from "./pages/analytics/RidershipView";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<Navigate to="/overview" replace />} />
          <Route path="/overview" element={<NetworkOverviewPage />} />
          <Route path="/live" element={<LiveMapPage />} />
          <Route path="/routes" element={<RouteIntelligencePage />} />
          <Route path="/routes/:routeNo" element={<RouteIntelligencePage />} />
          <Route path="/health" element={<ServiceHealthPage />} />
          <Route path="/compare" element={<RouteComparisonPage />} />
          <Route path="/data" element={<DataMethodologyPage />} />

          <Route path="/analytics" element={<AnalyticsPage />}>
            <Route index element={<Navigate to="/analytics/ridership" replace />} />
            <Route path="ridership" element={<RidershipView />} />
            <Route path="performance" element={<PerformanceView />} />
            <Route path="relationships" element={<RelationshipsView />} />
            <Route path="overview" element={<Navigate to="/overview" replace />} />
            <Route path="methodology" element={<Navigate to="/data" replace />} />
          </Route>

          <Route path="*" element={<Navigate to="/overview" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
