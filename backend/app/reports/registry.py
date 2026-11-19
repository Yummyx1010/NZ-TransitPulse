"""Official AT report files used by Phase 4."""

from __future__ import annotations

from dataclasses import dataclass

AT_BASE = "https://at.govt.nz"


@dataclass(frozen=True)
class ReportSpec:
    source_key: str
    family: str
    title: str
    url: str
    file_name: str
    reporting_period: str


REPORTS: tuple[ReportSpec, ...] = (
    ReportSpec(
        "punctuality_2023_2024",
        "punctuality",
        "Monthly punctuality and reliability July 2023 to June 2024",
        f"{AT_BASE}/media/fonhut3i/auckland-transport-monthly-punctuality-and-reliability-2023-to-2024.xlsx",
        "punctuality_2023_2024.xlsx",
        "2023-07..2024-06",
    ),
    ReportSpec(
        "punctuality_2024_2025",
        "punctuality",
        "Monthly punctuality and reliability July 2024 to June 2025",
        f"{AT_BASE}/media/soieg3up/auckland-transport-monthly-punctuality-and-reliability-2024-to-2025.xlsx",
        "punctuality_2024_2025.xlsx",
        "2024-07..2025-06",
    ),
    ReportSpec(
        "punctuality_2025_2026",
        "punctuality",
        "Monthly punctuality and reliability July 2025 to June 2026",
        f"{AT_BASE}/media/x1loqu23/auckland-transport-monthly-punctuality-and-reliability-june-2026.xlsx",
        "punctuality_2025_2026.xlsx",
        "2025-07..2026-06",
    ),
    ReportSpec(
        "punctuality_2026_10",
        "punctuality",
        "Monthly punctuality and reliability October 2026",
        f"{AT_BASE}/media/geufqbwf/auckland-transport-monthly-punctuality-and-reliability-october-2026.xlsx",
        "punctuality_2026_10.xlsx",
        "2026-10",
    ),
    ReportSpec(
        "bus_performance_2019_2020",
        "bus_performance",
        "AT Metro bus performance report 2019 and 2020",
        f"{AT_BASE}/media/1986640/at-bus-performance-report-2019-and-2020.xlsx",
        "bus_performance_2019_2020.xlsx",
        "2019..2020",
    ),
    ReportSpec(
        "bus_performance_2020_2023",
        "bus_performance",
        "AT Metro bus performance report January 2020 to February 2023",
        f"{AT_BASE}/media/1991363/at-bus-performance-report-jan2020-to-feb2023.xlsx",
        "bus_performance_2020_2023.xlsx",
        "2020-01..2023-02",
    ),
    ReportSpec(
        "bus_performance_2023",
        "bus_performance",
        "Bus performance report January to December 2023",
        f"{AT_BASE}/media/24boon21/bus-performance-report-for-january-2023-to-december-2023.xlsx",
        "bus_performance_2023.xlsx",
        "2023-01..2023-12",
    ),
    ReportSpec(
        "bus_performance_2024",
        "bus_performance",
        "Bus performance report January to December 2024",
        f"{AT_BASE}/media/sxnlgvh2/auckland-transport-bus-performance-report-january-2024-to-december-2024.xlsx",
        "bus_performance_2024.xlsx",
        "2024-01..2024-12",
    ),
    ReportSpec(
        "bus_performance_2025_q1",
        "bus_performance",
        "Bus performance report January to March 2025",
        f"{AT_BASE}/media/n3chrbkp/auckland-transport-bus-performance-report-january-to-march-2025.xlsx",
        "bus_performance_2025_q1.xlsx",
        "2025-01..2025-03",
    ),
    ReportSpec(
        "hourly_boardings_2023_2024",
        "hourly_boardings",
        "Bus boardings per service hour July 2023 to June 2024",
        f"{AT_BASE}/media/5o5fltsf/auckland-transport-hourly-bus-boardings-23-24.xlsx",
        "hourly_boardings_2023_2024.xlsx",
        "2023-07..2024-06",
    ),
    ReportSpec(
        "hourly_boardings_2024_2025",
        "hourly_boardings",
        "Bus boardings per service hour July 2024 to June 2025",
        f"{AT_BASE}/media/imzbqy3p/auckland-transport-hourly-bus-boardings-24-25.xlsx",
        "hourly_boardings_2024_2025.xlsx",
        "2024-07..2025-06",
    ),
    ReportSpec(
        "hourly_boardings_2025_2026",
        "hourly_boardings",
        "Bus boardings per service hour July 2025 to June 2026",
        f"{AT_BASE}/media/kibopzpj/auckland-transport-hourly-bus-boardings-25-26.xlsx",
        "hourly_boardings_2025_2026.xlsx",
        "2025-07..2026-06",
    ),
    ReportSpec(
        "patronage_2005_2025",
        "patronage",
        "Monthly patronage report July 2005 to June 2025",
        f"{AT_BASE}/media/l4ugvfd4/auckland-transport-monthly-patronage-from-july-2005-to-june-2025.xlsx",
        "patronage_2005_2025.xlsx",
        "2005-07..2025-06",
    ),
)

REPORTS_BY_KEY = {spec.source_key: spec for spec in REPORTS}
