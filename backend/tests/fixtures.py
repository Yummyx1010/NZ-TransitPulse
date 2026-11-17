"""Small in-memory GTFS bundles used by the test suite.

The fixture mimics the parts of the AT feed that the loader consumes, including a
nested folder, a UTF-8 BOM, an invalid coordinate, a time past midnight, two
different shapes on the same route, and shape points supplied out of order.
"""

from __future__ import annotations

import io
import zipfile

AGENCY = (
    "agency_id,agency_name,agency_url,agency_timezone\n"
    "AT,Auckland Transport,https://at.govt.nz,Pacific/Auckland\n"
)
ROUTES = (
    "route_id,agency_id,route_short_name,route_long_name,route_type,"
    "route_color,route_text_color\n"
    "R1,AT,18,New North Road,3,FF0000,FFFFFF\n"
    "R2,AT,WEST,Western Line,2,0000FF,FFFFFF\n"
    "R3,AT,DEV,Devonport Ferry,4,00AA00,FFFFFF\n"
)
STOPS = (
    "stop_id,stop_code,stop_name,stop_lat,stop_lon,location_type\n"
    "S1,1001,Britomart,-36.8443,174.7670,0\n"
    "S2,1002,Newmarket,-36.8710,174.7770,0\n"
    "S3,1003,Devonport,-36.8270,174.7960,0\n"
    "S4,,Bad Stop,999,999,0\n"
)
TRIPS = (
    "trip_id,route_id,service_id,trip_headsign,direction_id,shape_id\n"
    "T1,R1,WEEKDAY,City Centre,0,SH1\n"
    "T4,R1,WEEKDAY,Newmarket,1,SH4\n"
    "T2,R2,WEEKDAY,Swanson,1,SH2\n"
    "T3,R3,WEEKDAY,Devonport,0,SH3\n"
)
STOP_TIMES = (
    "trip_id,arrival_time,departure_time,stop_id,stop_sequence\n"
    "T1,08:00:00,08:00:30,S2,1\n"
    "T1,08:15:00,08:15:00,S1,2\n"
    "T4,09:00:00,09:00:00,S1,1\n"
    "T4,09:20:00,09:20:00,S2,2\n"
    "T2,25:10:00,25:10:00,S2,1\n"
    "T3,09:00:00,09:00:00,S3,1\n"
)
SHAPES = (
    "shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence,shape_dist_traveled\n"
    "SH1,-36.8500,174.7600,3,0.6\n"
    "SH1,-36.8443,174.7670,1,0\n"
    "SH1,-36.8470,174.7630,2,0.3\n"
    "SH4,-36.8710,174.7770,1,0\n"
    "SH4,-36.8600,174.7700,2,0.4\n"
    "SH2,-36.8710,174.7770,1,0\n"
    "SH3,-36.8270,174.7960,1,0\n"
)

BASE_TABLES: dict[str, str] = {
    "agency.txt": AGENCY,
    "routes.txt": ROUTES,
    "stops.txt": STOPS,
    "trips.txt": TRIPS,
    "stop_times.txt": STOP_TIMES,
    "shapes.txt": SHAPES,
}


def build_realtime_payload() -> dict:
    """Synthetic AT aggregated feed covering the field quirks seen in production."""
    return {
        "status": "OK",
        "response": {
            "header": {
                "timestamp": 1794707735.359,
                "gtfs_realtime_version": "1.0",
                "incrementality": 0,
            },
            "entity": [
                {
                    "id": "v1",
                    "is_deleted": False,
                    "vehicle": {
                        "position": {
                            "latitude": -36.8443,
                            "longitude": 174.767,
                            "bearing": "286",
                            "speed": 0,
                        },
                        "timestamp": 1794707698,
                        "vehicle": {"id": "BUS1", "label": "", "license_plate": ""},
                        "trip": {"trip_id": "T1", "route_id": "70-205", "direction_id": 0},
                    },
                },
                {
                    "id": "v2",
                    "vehicle": {
                        "position": {"latitude": -36.871, "longitude": 174.777},
                        "vehicle": {"id": "BUS2"},
                        "trip": {"trip_id": "T2"},
                    },
                },
                {
                    "id": "v3",
                    "is_deleted": True,
                    "vehicle": {
                        "position": {"latitude": -36.9, "longitude": 174.8},
                        "vehicle": {"id": "BUS3"},
                    },
                },
                {
                    "id": "t1",
                    "trip_update": {
                        "trip": {"trip_id": "T1", "route_id": "70-205", "start_date": "20261115"},
                        "timestamp": 1794707700,
                        "delay": -30,
                        "stop_time_update": {
                            "stop_sequence": 1,
                            "stop_id": "9103-0e65d9b8",
                            "arrival": {"delay": -30, "time": 1794732060},
                            "departure": {"delay": -20, "time": 1794732070},
                        },
                    },
                },
                {
                    "id": "t2",
                    "trip_update": {
                        "trip": {"trip_id": "T2", "route_id": "WEST-201"},
                        "delay": 120,
                        "stop_time_update": [
                            {"stop_sequence": 1, "stop_id": "S2", "arrival": {"delay": 120}},
                            {"stop_sequence": 2, "stop_id": "S1", "arrival": {"delay": 150}},
                        ],
                    },
                },
                {
                    "id": "a1",
                    "alert": {
                        "cause": "CONSTRUCTION",
                        "effect": "STOP_MOVED",
                        "header_text": {
                            "translation": [{"text": "Stops skipped: Route 313", "language": "en"}]
                        },
                        "description_text": {
                            "translation": [{"text": "Bus stop moved", "language": "en"}]
                        },
                        "active_period": [{"start": 1795258800, "end": None}],
                        "informed_entity": [{"route_id": "70-205"}],
                    },
                    "timestamp": 1794707700,
                },
            ],
        },
        "error": None,
    }


def build_fixture_zip(
    *,
    overrides: dict[str, str] | None = None,
    omit: tuple[str, ...] = (),
) -> bytes:
    """Build a GTFS zip in memory; override or omit tables to test edge cases."""
    tables = {**BASE_TABLES, **(overrides or {})}
    for name in omit:
        tables.pop(name, None)

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, content in tables.items():
            member = f"at_gtfs/{name}" if name == "agency.txt" else name
            payload = f"\ufeff{content}" if name == "routes.txt" else content
            archive.writestr(member, payload)
    return buffer.getvalue()
