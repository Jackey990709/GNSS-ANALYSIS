import logging
import math
import os
from collections import Counter

import numpy as np
import pandas as pd

from src.libs.nmea import Default

logger = logging.getLogger(__name__)


def check_folder(fpath):
    return (e for e in os.listdir(fpath) if os.path.isdir(os.path.join(fpath, e)))


def check_log_file(fpath, endswith=[".log"]):
    try:
        return [
            e
            for e in os.listdir(fpath)
            if any(e.lower().endswith(ext) for ext in endswith)
            and os.path.isfile(os.path.join(fpath, e))
        ]
    except FileNotFoundError:
        return []


def get_freq(utc_date_time, interval=1e6):
    if isinstance(utc_date_time, np.ndarray):
        try:
            t = np.diff(utc_date_time).astype("datetime64[s]").astype("float")
            diff = t / interval
            delta = round(
                Counter(diff[diff > 0.0]).most_common(1)[0][0],
                Default.KEEP_DECIMAL_DIGIT,
            )
            return int(1 / delta)
        except (IndexError, OverflowError):
            pass

    if isinstance(utc_date_time, list):
        return get_freq(np.array(utc_date_time, dtype="datetime64"), interval)

    return 1


def calc_rms(n: pd.Series) -> float:
    try:
        m: np.ndarray = n.dropna().to_numpy()
        return round(math.sqrt(sum(m**2) / m.size), 3)
    except ZeroDivisionError:
        return np.nan


def create_folder(folder_path):
    try:
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)
    except FileExistsError:
        ...


def calc_value(total: float, n: float) -> float:
    if total == 0 or np.isnan(n):
        return np.nan
    try:
        return round(n / total * 100, Default.PERCENT_DECIMAL_DIGIT)
    except (ZeroDivisionError, RuntimeWarning):
        return np.nan


def decode_line(line: bytes) -> tuple[bool, str]:
    try:
        line_str = line.decode()
        return (False, line_str) if line_str[0] in ["$", "#"] else (True, line_str)
    except UnicodeDecodeError:
        return True, line.decode(errors="replace")


def get_date_from_log(*filepaths: str, skip_count: int = 30) -> str:
    """遍历 NMEA log 文件，取第一个找到的有效日期（跳过前 skip_count 条 status=='A' 的 RMC）"""
    from src.libs.nmea import NMEAHeaderByte
    from src.libs.nmea.rmc import RMCParser

    for fp in filepaths:
        count = 0
        with open(fp, "rb") as f:
            for line in f:
                if NMEAHeaderByte.RMC_BYTE in line:
                    err_code, line_str = decode_line(line)
                    parser = RMCParser(line_str, error_code=err_code)
                    if parser.status != "A":
                        count = 0
                        continue
                    count += 1
                    if count <= skip_count:
                        continue
                    utc_date = parser.utc_date
                    if (
                        isinstance(utc_date, str)
                        and len(utc_date) == 6
                        and utc_date[4:] != "80"
                    ):
                        day, month, year = utc_date[:2], utc_date[2:4], utc_date[4:]
                        return f"20{year}{month}{day}"
    return ""


a = 6378137
b = 6356752.3142
f = (a - b) / a
e_sq = f * (2 - f)
pi = 3.14159265359


def geodetic_to_ecef(lat, lng, h):
    lamb = np.radians(lat)
    phi = np.radians(lng)
    s = np.sin(lamb)
    N = a / np.sqrt(1 - e_sq * s * s)

    sin_lambda = np.sin(lamb)
    cos_lambda = np.cos(lamb)
    sin_phi = np.sin(phi)
    cos_phi = np.cos(phi)

    x = (h + N) * cos_lambda * cos_phi
    y = (h + N) * cos_lambda * sin_phi
    z = (h + (1 - e_sq) * N) * sin_lambda

    return x, y, z


def ecef_to_enu(x, y, z, lat0, lng0, h0):
    lamb = np.radians(lat0)
    phi = np.radians(lng0)
    s = np.sin(lamb)
    N = a / np.sqrt(1 - e_sq * s * s)

    sin_lambda = np.sin(lamb)
    cos_lambda = np.cos(lamb)
    sin_phi = np.sin(phi)
    cos_phi = np.cos(phi)

    x0 = (h0 + N) * cos_lambda * cos_phi
    y0 = (h0 + N) * cos_lambda * sin_phi
    z0 = (h0 + (1 - e_sq) * N) * sin_lambda

    xd = x - x0
    yd = y - y0
    zd = z - z0

    t = -cos_phi * xd - sin_phi * yd

    e = -sin_phi * xd + cos_phi * yd
    n = t * sin_lambda + cos_lambda * zd
    u = cos_lambda * cos_phi * xd + cos_lambda * sin_phi * yd + sin_lambda * zd

    return np.round(e, 4), np.round(n, 4), np.round(u, 4)


def calculate_data(lat, lng, h, lat0, lng0, h0):
    e, n, u = ecef_to_enu(*geodetic_to_ecef(lat, lng, h), lat0, lng0, h0)

    e2 = np.power(e, 2)
    n2 = np.power(n, 2)
    u2 = np.power(u, 2)

    return e, n, u, np.round(np.sqrt(e2 + n2 + u2), 4), np.round(np.sqrt(e2 + n2), 4)
