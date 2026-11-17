import type { RouteSummary, StopSummary } from "../api/types";

export function displayRouteName(route: RouteSummary): string {
  const short = route.short_name.trim();
  const long = route.long_name.trim();
  if (short && long && short.toLowerCase() !== long.toLowerCase()) {
    return `${short} · ${long}`;
  }
  return short || long || "Unnamed route";
}

export function displayStopName(stop: StopSummary): string {
  return stop.code ? `${stop.name} (${stop.code})` : stop.name;
}

export function formatCoordinate(value: number): string {
  return value.toFixed(5);
}

export function modeClass(mode: string): string {
  return `badge badge-${mode.toLowerCase().replace(/\s+/g, "-")}`;
}

export function formatFeedTime(timestamp: number | null | undefined): string {
  if (!timestamp) return "No feed yet";
  return new Date(timestamp * 1000).toLocaleTimeString("en-NZ", {
    timeZone: "Pacific/Auckland",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  });
}

export function formatMinutesAway(minutes: number): string {
  return minutes <= 0 ? "Due" : `${minutes} min`;
}

export function formatDelay(seconds: number | null): string {
  if (seconds === null) return "timetable only";
  const minutes = Math.round(Math.abs(seconds) / 60);
  if (seconds > 0) return `+${minutes} min`;
  if (seconds < 0) return `-${minutes} min`;
  return "On time";
}

export function delayStatusClass(status: string): string {
  return `delay-badge delay-${status.toLowerCase().replace(/\s+/g, "-")}`;
}
