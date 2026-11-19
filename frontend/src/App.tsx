import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";

import { AppShell } from "./components/AppShell";
import AnalyticsPage from "./pages/AnalyticsPage";
import LiveMapPage from "./pages/LiveMapPage";
import { OverviewView } from "./pages/analytics/OverviewView";
import { RidershipView } from "./pages/analytics/RidershipView";
import { PerformanceView } from "./pages/analytics/PerformanceView";
import { RelationshipsView } from "./pages/analytics/RelationshipsView";
import { MethodologyView } from "./pages/analytics/MethodologyView";

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/" element={<LiveMapPage />} />
          <Route path="/analytics" element={<AnalyticsPage />}>
            <Route index element={<OverviewView />} />
            <Route path="ridership" element={<RidershipView />} />
            <Route path="performance" element={<PerformanceView />} />
            <Route path="relationships" element={<RelationshipsView />} />
            <Route path="methodology" element={<MethodologyView />} />
          </Route>
          <Route path="*" element={<Navigate to="/" replace />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
