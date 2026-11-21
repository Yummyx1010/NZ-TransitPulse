import { createContext, useContext, useMemo } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { RouteCatalogItem } from "../api/types";

interface RouteContextValue {
  routeNo: string | null;
  routeId: string | null;
  routeIds: string[];
  routeLabel: string | null;
  matchedInGtfs: boolean;
  setRoute: (routeNo: string | null) => void;
}

const RouteContext = createContext<RouteContextValue | null>(null);

export function RouteContextProvider({ children }: { children: React.ReactNode }) {
  const [searchParams, setSearchParams] = useSearchParams();
  const routeNo = searchParams.get("route");

  const catalog = useQuery({
    queryKey: ["analytics-route-identity", routeNo],
    queryFn: () => api.analyticsRoutes(routeNo ?? undefined),
    enabled: Boolean(routeNo),
    retry: 1,
  });

  const identity = useMemo<RouteCatalogItem | null>(() => {
    if (!routeNo) return null;
    return (
      catalog.data?.items.find((item) => item.route_no === routeNo) ?? null
    );
  }, [catalog.data?.items, routeNo]);

  const value = useMemo<RouteContextValue>(
    () => ({
      routeNo,
      routeId: identity?.route_ids[0] ?? null,
      routeIds: identity?.route_ids ?? [],
      routeLabel: identity
        ? identity.route_name
          ? `${identity.route_no} · ${identity.route_name}`
          : identity.route_no
        : routeNo,
      matchedInGtfs: identity?.matched_in_gtfs ?? false,
      setRoute: (next) => {
        const params = new URLSearchParams(searchParams);
        if (next) params.set("route", next);
        else params.delete("route");
        setSearchParams(params, { replace: true });
      },
    }),
    [identity, routeNo, searchParams, setSearchParams],
  );

  return <RouteContext.Provider value={value}>{children}</RouteContext.Provider>;
}

export function useRouteContext(): RouteContextValue {
  const context = useContext(RouteContext);
  if (!context) {
    throw new Error("useRouteContext must be used inside RouteContextProvider");
  }
  return context;
}
