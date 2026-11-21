import { NavLink, Outlet } from "react-router-dom";

import { RouteContextProvider } from "../hooks/useRouteContext";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `observatory-nav-link${isActive ? " is-active" : ""}`;

export function AppShell() {
  return (
    <RouteContextProvider>
      <div className="observatory-shell">
        <a className="observatory-skip-link" href="#main-content">
          Skip to main content
        </a>
        <aside className="observatory-sidebar" aria-label="Main navigation">
          <div className="observatory-brand">
            <span className="observatory-brand-mark" aria-hidden="true">TP</span>
            <div>
              <h1>NZ TransitPulse</h1>
              <p>Auckland transport observatory</p>
            </div>
          </div>

          <nav className="observatory-nav" aria-label="Main navigation">
            <p className="observatory-nav-label">Explore</p>
            <NavLink to="/overview" className={navClass} aria-label="Network Overview">
              <span className="observatory-nav-index" aria-hidden="true">01</span>
              Network Overview
            </NavLink>
            <NavLink to="/live" className={navClass} aria-label="Live Network">
              <span className="observatory-nav-index" aria-hidden="true">02</span>
              Live Network
            </NavLink>
            <NavLink to="/routes" className={navClass} aria-label="Route Intelligence">
              <span className="observatory-nav-index" aria-hidden="true">03</span>
              Route Intelligence
            </NavLink>
            <NavLink to="/health" className={navClass} aria-label="Service Health">
              <span className="observatory-nav-index" aria-hidden="true">04</span>
              Service Health
            </NavLink>
            <NavLink to="/compare" className={navClass} aria-label="Route Comparison">
              <span className="observatory-nav-index" aria-hidden="true">05</span>
              Route Comparison
            </NavLink>

            <p className="observatory-nav-label">Analytics</p>
            <NavLink to="/analytics/ridership" className={navClass} aria-label="Ridership">
              Ridership
            </NavLink>
            <NavLink to="/analytics/performance" className={navClass} aria-label="Performance">
              Performance
            </NavLink>
            <NavLink
              to="/analytics/relationships"
              className={navClass}
              aria-label="Relationships"
            >
              Relationships
            </NavLink>

            <p className="observatory-nav-label">Reference</p>
            <NavLink to="/data" className={navClass} aria-label="Data and Methodology">
              Data &amp; Methodology
            </NavLink>

            <p className="observatory-nav-label">Planned</p>
            <span className="observatory-nav-link is-disabled" aria-disabled="true">
              Prediction models
            </span>
          </nav>

          <p className="observatory-nav-note">
            Buses only. Static network from GTFS; performance from published AT reports.
          </p>
        </aside>

        <main className="observatory-main" id="main-content">
          <Outlet />
        </main>
      </div>
    </RouteContextProvider>
  );
}
