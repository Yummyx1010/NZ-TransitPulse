"""Human-readable labels for GTFS route types."""

from __future__ import annotations

_MODE_LABELS: dict[int, str] = {
    0: "Tram",
    1: "Metro",
    2: "Rail",
    3: "Bus",
    4: "Ferry",
    5: "Cable tram",
    6: "Aerial lift",
    7: "Funicular",
    11: "Trolleybus",
    12: "Monorail",
}


def mode_label(route_type: int) -> str:
    """Return the display label for a GTFS ``route_type`` code."""
    return _MODE_LABELS.get(route_type, "Other")


def mode_from_label(label: str) -> int | None:
    """Return the GTFS route type for a label, or ``None`` if unrecognised."""
    for code, name in _MODE_LABELS.items():
        if name.lower() == label.strip().lower():
            return code
    return None
