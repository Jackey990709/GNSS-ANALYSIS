from dataclasses import dataclass
from enum import IntEnum

CLIENT_VERSION: str = "v2.1"
VERSION: str = "v2.1.1"


class HandleItem(IntEnum):
    INTERNAL = 1  # 生成对内报告
    EXTERNAL = 2  # 生成对外报告


title_map = {
    HandleItem.INTERNAL: "-Internal",
    HandleItem.EXTERNAL: "-External",
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
    VTG: str = "VTG,"
    GLL: str = "GLL,"

    GNRMC: str = "GNRMC,"
    GPRMC: str = "GPRMC,"
    GNGGA: str = "GNGGA,"
    GPGGA: str = "GPGGA,"

    PQTMVEL: str = "PQTMVEL,"
    PQSOL: str = "PQSOL,"
    PCAS50: str = "PCAS50,"
    PQTMTAR: str = "PQTMTAR,"
    PSTMDRPVA: str = "PSTMDRPVA,"
    PQTMDRPVA: str = "PQTMDRPVA,"
    PQTMVEHATT: str = "PQTMVEHATT,"
    HEADINGA: str = "HEADINGA,"

    TTFF_P: str = GGA


@dataclass
class Point:
    lat: float
    lng: float
    hgt: float
