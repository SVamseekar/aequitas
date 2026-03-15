"""Core type definitions for Aequitas pipeline.

Enums for regions, stop types, urban/rural classification, and IMD deciles.
All values match government data source coding schemes.
"""

from enum import Enum, IntEnum


class RegionCode(str, Enum):
    """ONS statistical regions of England (9 regions)."""

    NORTH_EAST = "E12000001"
    NORTH_WEST = "E12000002"
    YORKSHIRE = "E12000003"
    EAST_MIDLANDS = "E12000004"
    WEST_MIDLANDS = "E12000005"
    EAST_OF_ENGLAND = "E12000006"
    LONDON = "E12000007"
    SOUTH_EAST = "E12000008"
    SOUTH_WEST = "E12000009"


class StopType(str, Enum):
    """NaPTAN bus stop types — only these three are bus stops."""

    BCT = "BCT"  # On-street Bus/Coach/Tram stop (most common type)
    BCS = "BCS"  # Bus/Coach station bay
    BCE = "BCE"  # Bus/Coach station entrance


class UrbanRural(str, Enum):
    """Binary urban/rural classification (collapsed from RUC 6-class)."""

    URBAN = "urban"
    RURAL = "rural"


class IMDDecile(IntEnum):
    """IMD 2025 decile (1 = most deprived, 10 = least deprived)."""

    D1 = 1
    D2 = 2
    D3 = 3
    D4 = 4
    D5 = 5
    D6 = 6
    D7 = 7
    D8 = 8
    D9 = 9
    D10 = 10


# ATCO area codes 000-499 are England (500+ is Scotland/Wales/NI)
ENGLAND_ATCO_PREFIXES: frozenset[str] = frozenset(
    f"{i:03d}" for i in range(500)
)
