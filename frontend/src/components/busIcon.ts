import { divIcon, type DivIcon } from "leaflet";

/** Top-down bus glyph; the front (windscreen) points north before rotation. */
const BUS_SVG = `
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 28 28" width="26" height="26" aria-hidden="true">
  <rect x="7" y="2.5" width="14" height="23" rx="4.5" fill="#ea580c" stroke="#ffffff" stroke-width="1.8"/>
  <path d="M8.8 6.2h10.4l-1.2 4.4H10z" fill="#ffedd5"/>
  <rect x="9.4" y="12" width="9.2" height="3.2" rx="1" fill="#ffffff" opacity="0.85"/>
  <rect x="9.4" y="17" width="9.2" height="3.2" rx="1" fill="#ffffff" opacity="0.7"/>
  <path d="M10 23.2h8" stroke="#7c2d12" stroke-width="1.6" stroke-linecap="round"/>
  <circle cx="7" cy="8.5" r="1.2" fill="#ffffff"/>
  <circle cx="21" cy="8.5" r="1.2" fill="#ffffff"/>
</svg>`;

export function busIconRotation(bearing: number | null): number {
  const value = typeof bearing === "number" && Number.isFinite(bearing) ? bearing : 0;
  return ((Math.round(value / 15) * 15) % 360 + 360) % 360;
}

export function busIconHtml(): string {
  return `<span class="bus-glyph">${BUS_SVG}</span>`;
}

const iconCache = new Map<number, DivIcon>();

/** Leaflet DivIcon rotated to the vehicle bearing, cached in 15-degree buckets. */
export function createBusIcon(bearing: number | null): DivIcon {
  const rotation = busIconRotation(bearing);
  const cached = iconCache.get(rotation);
  if (cached) return cached;
  const icon = divIcon({
    className: "bus-marker",
    html: `<div class="bus-marker-inner" style="transform: rotate(${rotation}deg)">${busIconHtml()}</div>`,
    iconSize: [26, 26],
    iconAnchor: [13, 13],
    popupAnchor: [0, -13],
  });
  iconCache.set(rotation, icon);
  return icon;
}
