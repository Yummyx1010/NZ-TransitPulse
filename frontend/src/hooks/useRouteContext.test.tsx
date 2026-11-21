import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, renderHook, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { api } from "../api/client";
import { RouteContextProvider, useRouteContext } from "./useRouteContext";

vi.mock("../api/client", () => ({
  api: { analyticsRoutes: vi.fn() },
}));

function wrapper(initialEntry: string) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[initialEntry]}>
        <RouteContextProvider>{children}</RouteContextProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

beforeEach(() => {
  vi.mocked(api.analyticsRoutes).mockImplementation(async (q) => {
    if (q === "24B") {
      return {
        total: 1,
        items: [
          {
            route_no: "24B",
            route_ids: ["24B-205"],
            route_name: "Parnell To Newmarket",
            matched_in_gtfs: true,
          },
        ],
      };
    }
    return {
      total: 1,
      items: [
        {
          route_no: "70",
          route_ids: ["70-205"],
          route_name: "Botany To Britomart",
          matched_in_gtfs: true,
        },
      ],
    };
  });
});

describe("useRouteContext", () => {
  it("syncs route number and GTFS route id from the URL", async () => {
    const { result } = renderHook(() => useRouteContext(), {
      wrapper: wrapper("/analytics/performance?route=70"),
    });

    await waitFor(() => expect(result.current.routeId).toBe("70-205"));
    expect(result.current.routeNo).toBe("70");
    expect(result.current.routeLabel).toBe("70 · Botany To Britomart");
    expect(result.current.matchedInGtfs).toBe(true);
  });

  it("updates the URL when another route is selected", async () => {
    const { result } = renderHook(() => useRouteContext(), {
      wrapper: wrapper("/routes?route=70"),
    });

    await waitFor(() => expect(result.current.routeId).toBe("70-205"));
    act(() => result.current.setRoute("24B"));

    await waitFor(() => expect(result.current.routeId).toBe("24B-205"));
    expect(result.current.routeNo).toBe("24B");
  });
});
