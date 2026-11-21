import { Link } from "react-router-dom";

import { PageHeader } from "../components/ui/PageHeader";
import { EmptyState } from "../components/ui/States";

export function RouteComparisonPage() {
  return (
    <div className="observatory-content">
      <PageHeader
        title="Route Comparison"
        description="Compare boardings, punctuality and reliability across two or three bus routes over a shared reporting period."
        meta={["Planned for v0.6.6"]}
      />
      <EmptyState>
        Route comparison is not implemented yet. Select a route in{" "}
        <Link to="/routes">Route Intelligence</Link>, then the v0.6.6 workspace will use
        the shared reporting period and compatibility warnings before showing a comparison.
      </EmptyState>
    </div>
  );
}
