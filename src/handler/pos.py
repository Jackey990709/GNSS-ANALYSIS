import os
from datetime import datetime
from threading import Thread

import numpy as np
import pandas as pd


HEAD_LINES = [
    "% (lat/lon/height=WGS84/ellipsoidal,Q=1:fix,2:float,3:sbas,4:dgps,5:single,6:ppp,ns=# of satellites)\n",
    "%  UTC            latitude(deg)   longitude(deg)   height(m)   Q   ns    sdn(m)   sde(m)   sdu(m)  "
    "sdne(m)  sdeu(m)  sdun(m)  age(s)   ratio\n",
]
TAIL_LINE = "    0.0   0.0  0.0 0.0   0.0   0.0  %s   0.0\n"


def format_utc_time(utc_time: pd.Timestamp, separator: str = " ") -> str:
    time_str = str(utc_time)
    if "." not in time_str:
        time_str += ".000"

    dt = datetime.strptime(time_str, f"%Y-%m-%d{separator}%H:%M:%S.%f")
    return dt.strftime("%Y/%m/%d %H:%M:%S.%f")[:-3]


def is_valid_position(row) -> bool:
    return (
        row.label != "0"
        and not np.isnan(row.lat)
        and not np.isnan(row.lng)
        and not np.isnan(row.hgt)
    )


def format_delay(delay) -> str:
    """格式化延迟值"""
    if delay is None:
        return ""

    try:
        delay_float = float(delay)
        return "" if np.isnan(delay_float) else str(delay)
    except (ValueError, TypeError):
        return ""


class PosProcessor(Thread):
    def __init__(self, result_path: str, filename: str, df: pd.DataFrame):
        super().__init__()
        self.df = df.copy()
        self.filename = filename
        self.result_path = result_path

    def run(self) -> None:
        pos_file_path = os.path.join(self.result_path, f"{self.filename[:-4]}.pos")

        with open(pos_file_path, "w", errors="ignore") as pos_file:
            pos_file.writelines(HEAD_LINES)

            for row in self.df.itertuples():
                if is_valid_position(row):
                    line = self._format_position_line(row)
                    pos_file.write(line)

    def _format_position_line(self, row) -> str:
        position_data = (
            f"{format_utc_time(row.Index)}  "
            f"{row.lat:.11f} "
            f"{row.lng:.11f}  "
            f"{row.hgt:.4f}      {row.label}   {row.satellites}"
        )

        delay = format_delay(getattr(row, "delay", None))
        return f"{position_data}{TAIL_LINE % delay}"
