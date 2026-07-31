import numpy as np

from src import NMEAHeader


class NMEAHeaderByte:
    RMC_BYTE: bytes = NMEAHeader.RMC.encode()
    GGA_BYTE: bytes = NMEAHeader.GGA.encode()
    GSA_BYTE: bytes = NMEAHeader.GSA.encode()
    GSV_BYTE: bytes = NMEAHeader.GSV.encode()
    VTG_BYTE: bytes = NMEAHeader.VTG.encode()
    GLL_BYTE: bytes = NMEAHeader.GLL.encode()

    GNRMC_BYTE: bytes = NMEAHeader.GNRMC.encode()
    GPRMC_BYTE: bytes = NMEAHeader.GPRMC.encode()
    GNGGA_BYTE: bytes = NMEAHeader.GNGGA.encode()
    GPGGA_BYTE: bytes = NMEAHeader.GPGGA.encode()

    PQTMVEL_BYTE: bytes = NMEAHeader.PQTMVEL.encode()
    PQSOL_BYTE: bytes = NMEAHeader.PQSOL.encode()
    PCAS50_BYTE: bytes = NMEAHeader.PCAS50.encode()
    PQTMTAR_BYTE: bytes = NMEAHeader.PQTMTAR.encode()
    PSTMDRPVA_BYTE: bytes = NMEAHeader.PSTMDRPVA.encode()
    PQTMDRPVA_BYTE: bytes = NMEAHeader.PQTMDRPVA.encode()
    PQTMVEHATT_BYTE: bytes = NMEAHeader.PQTMVEHATT.encode()
    HEADINGA_BYTE: bytes = NMEAHeader.HEADINGA.encode()


class Default:
    KEEP_DECIMAL_DIGIT: int = 3
    LOC_DECIMAL_DIGIT: int = 11
    PERCENT_DECIMAL_DIGIT: int = 3

    DEFAULT_NAN: float = np.nan
    LAT_DEFAULT_VALUE: float = 0.0
    LNG_DEFAULT_VALUE: float = 0.0
    HGT_DEFAULT_VALUE: float = 0.0
    ALT_DEFAULT_VALUE: float = 0.0


sys_type = {
    "$GPGSV": "gps",
    "$GBGSV": "bds",
    "$GLGSV": "glo",
    "$GAGSV": "gal",
    "$BDGSV": "bds",
    "$GQGSV": "qzs",
    "$GIGSV": "irn",
}

gp_sys = {
    "1": "l1",  # GPS-L1 C/A
    "2": "l1",  # GPS-L1 P(Y)
    "3": "l1",  # GPS-L1 M
    "4": "l2",  # GPS-L2 P(Y)
    "5": "l2",  # GPS-L2C-M
    "6": "l2",  # GPS-L2C-L
    "7": "l5",  # GPS-L5-I
    "8": "l5",  # GPS-L5-Q
}

gb_sys = {
    "1": "b1i",  # BD-B1I
    "3": "b1c",  # BD-B1C
    "5": "b2a",  # BD-B2a
    "6": "b2b",  # BD-B2b
    "8": "b3i",  # BD-B3I
    "B": "b2i",  # BD-B2I
}

gl_sys = {
    "1": "g1",  # GL-G1 C/A
    "2": "g1",  # GL-G1 P
    "3": "g2",  # GL-G2 C/A
    "4": "g2",  # GL-G2 P
}

ga_sys = {
    "1": "e5a",  # GAL-E5a
    "2": "e5b",  # GAL-E5b
    "5": "e6",  # GAL-E6
    "7": "e1",  # GAL-L1-BC
}

gq_sys = {
    "1": "q1",  # QZS-L1 C/A
    "5": "q2",  # QZS-L2CM
    "6": "q2",  # QZS-L2CL
    "7": "q5",  # QZS-L5I
    "8": "q5",  # QZS-L5Q
}
gi_sys = {
    "1": "i5",  # IRNSS-L5I
}

# sat_label_list1 = [DictKey.GPGSV, DictKey.GBGSV, DictKey.GLGSV, DictKey.GAGSV, DictKey.BDGSV_2]
sys_label_list = list(sys_type.values())
sat_sys_list = list(sys_type.keys())

sys_list = ["gps", "bds", "glo", "gal", "qzs"]
sat_sys = {
    sat_sys_list[0]: gp_sys,
    sat_sys_list[1]: gb_sys,
    sat_sys_list[2]: gl_sys,
    sat_sys_list[3]: ga_sys,
    sat_sys_list[4]: gb_sys,
    sat_sys_list[5]: gq_sys,
    sat_sys_list[6]: gi_sys,
}

freq_list = ["l1", "l2", "l5"]

sat_freq_combinations = (
    ("gps", "l1"),
    ("gps", "l2"),
    ("gps", "l5"),
    ("bds", "b1i"),
    ("bds", "b1c"),
    ("bds", "b2a"),
    ("bds", "b2b"),
    ("bds", "b3i"),
    ("bds", "b2i"),
    ("glo", "g1"),
    ("glo", "g2"),
    ("gal", "e5a"),
    ("gal", "e5b"),
    ("gal", "e6"),
    ("gal", "e1"),
    ("qzs", "q1"),
    ("qzs", "q2"),
    ("qzs", "q5"),
    ("irn", "i5"),
)

_freq_list = [f"{sat_sys}_{sat_freq}" for sat_sys, sat_freq in sat_freq_combinations]
_cnt_list = [f"{sat_sys}_{sat_freq}_cnt" for sat_sys, sat_freq in sat_freq_combinations]
_sum_list = [f"{sat_sys}_{sat_freq}_sum" for sat_sys, sat_freq in sat_freq_combinations]
_max_list = [f"{sat_sys}_{sat_freq}_max" for sat_sys, sat_freq in sat_freq_combinations]
_min_list = [f"{sat_sys}_{sat_freq}_min" for sat_sys, sat_freq in sat_freq_combinations]

filter_list = _freq_list + _cnt_list
snr_list = filter_list + _sum_list + _max_list + _min_list

gsa_sys_id = {
    "1": "gps",
    "2": "glo",
    "3": "gal",
    "4": "bds",
    "5": "qzs",
    "6": "irn",
}

__all__ = [
    "NMEAHeaderByte",
    "Default",
    "sys_type",
    "gp_sys",
    "gb_sys",
    "gl_sys",
    "ga_sys",
    "sys_list",
    "sys_label_list",
    "sat_sys_list",
    "sat_freq_combinations",
    "freq_list",
    "snr_list",
    "gsa_sys_id",
]
