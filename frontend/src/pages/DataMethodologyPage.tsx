import { PageHeader } from "../components/ui/PageHeader";
import { MethodologyView } from "./analytics/MethodologyView";

export function DataMethodologyPage() {
  return (
    <div className="observatory-content">
      <PageHeader
        title="Data & Methodology"
        description="Official AT report sources, GTFS coverage, metric definitions, reported months and route-number mapping."
        meta={["Provenance", "Definitions", "Coverage"]}
      />
      <MethodologyView />
    </div>
  );
}
