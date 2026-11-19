import { NavLink, Outlet } from "react-router-dom";

const navClass = ({ isActive }: { isActive: boolean }) =>
  `observatory-nav-link${isActive ? " is-active" : ""}`;

export function AppShell() {
  return (
    <div className="observatory-shell">
      <aside className="observatory-sidebar" aria-label="Main navigation">
        <div className="observatory-brand">
          <span className="observatory-brand-mark" aria-hidden="true">TP</span>
          <div>
            <h1>NZ TransitPulse</h1>
            <p>Auckland transport observatory</p>
          </div>
        </div>

        <nav className="observatory-nav" aria-label="Main navigation">
          <p className="observatory-nav-label">Product</p>
          <NavLink to="/" className={navClass} end aria-label="Live map">
            Live map
          </NavLink>
          <NavLink to="/analytics" className={navClass} aria-label="Analytics">
            Analytics
          </NavLink>

          <p className="observatory-nav-label">Planned modules</p>
          <span className="observatory-nav-link is-disabled" aria-disabled="true">
            Prediction models
          </span>
          <span className="observatory-nav-link is-disabled" aria-disabled="true">
            Network analysis
          </span>
        </nav>

        <p className="observatory-nav-note">
          Buses only. Static network from GTFS; performance from published AT reports.
        </p>
      </aside>

      <div className="observatory-main">
        <Outlet />
      </div>
    </div>
  );
}
