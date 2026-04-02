from dataclasses import dataclass
from enum import IntEnum

VERSION: str = "v1.0.1"


class HandleItem(IntEnum):
    INTERNAL = 1  # 生成对内报告
    EXTERNAL = 2  # 生成对外报告


title_map = {
    HandleItem.INTERNAL: "-Internal",
    HandleItem.EXTERNAL: "",
    HandleItem.INTERNAL | HandleItem.EXTERNAL: "-I+External",
}


# HandleItem.INTERNAL 只生成对内报告
# HandleItem.EXTERNAL 只生成对外报告
# HandleItem.INTERNAL | HandleItem.EXTERNAL 同时生成对内和对外报告
HANDLE_ITEM: int = HandleItem.INTERNAL  # 报告类型管控


title = title_map[HANDLE_ITEM]


class NMEAHeader:
    RMC: str = "RMC,"
    GGA: str = "GGA,"
    GSA: str = "GSA,"
    GSV: str = "GSV,"

    GNRMC: str = "GNRMC,"
    GPRMC: str = "GPRMC,"
    GNGGA: str = "GNGGA,"
    GPGGA: str = "GPGGA,"

    TTFF_P: str = GGA


@dataclass
class Point:
    lat: float
    lng: float
    hgt: float
