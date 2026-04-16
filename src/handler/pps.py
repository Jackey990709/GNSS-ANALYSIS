from datetime import datetime
from io import BufferedReader
import logging
import os
from typing import Any, Union
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QCheckBox
import numpy as np
import pandas as pd
from src.handler import write_to_file
from src.libs import bytes2int, read_bytes

from src.libs.nmea.rmc import RMCParser
from src.libs.report import Report
from src.libs.ubx.ubx import UbxStruct
from src.util.const import File
from src.util.param import (
    PERCENT_50,
    PERCENT_68,
    PERCENT_95,
    PERCENT_99,
    pps_index_list,
    percentiles,
)
from src.util.utils import calc_rms


logger = logging.getLogger(__name__)


def calc_sec(ms, ns) -> float:
    return round(ms / 1e3 + ns / 1e9, 10)


class PPSAttr:
    def __init__(self):
        self.result_path: str = ""
        self.filepath: str = ""
        self.edge_type: int = 1  # 1 raise, 0 fall
        self.check_list: list[Union[str, QCheckBox]] = []

    def create(self):
        if not self.filepath:
            return

        self.result_path = os.path.join(self.filepath, "pps_result")
        os.makedirs(self.result_path, exist_ok=True)


class PPSProcessor(PPSAttr):
    def __init__(self):
        self.callback: Any = None

    def process_data(self):
        result_dict: dict[str, list] = {}
        self.check_list: list[str] = [
            check_file.text() if isinstance(check_file, QCheckBox) else check_file
            for check_file in self.check_list
        ]

        for file in self.check_list:
            self.print_msg(f"开始处理文件: {file}")

            df = self._generate_pps_pd(file)

            if df is None or df.empty:
                self._gen_nan_result(result_dict, file[:-4])
                continue

            edge_str = "secR" if self.edge_type else "secF"
            df["secInt"] = df[edge_str].round(0)
            df["pps_delta"] = (df[edge_str] - df["secInt"]) * 1e9

            write_to_file(
                df, self.result_path, f"{file[:-4]}_pps{File.EXT_FILE}", False
            )

            self._gen_result_dict(result_dict, file[:-4], df)

            self.print_msg(f"文件处理完成: {file}")

        self.print_msg(f"生成报告中...")
        self._gen_report(result_dict)
        self.print_msg(f"报告生成完成")

    def _generate_pps_pd(self, file):
        pps_dict = {
            "utc_date_time": [],
            "ch": [],
            "flag": [],
            "count": [],
            "wnR": [],
            "secR": [],
            "wnF": [],
            "secF": [],
            "accEst": [],
        }

        self._handle_file(file, pps_dict)

        if not pps_dict["utc_date_time"]:
            return None

        return pd.DataFrame(pps_dict)

    def _handle_file(self, file, pps_dict):
        logger.debug(f"handle file: {file}")
        start_flag = False

        with open(os.path.join(self.filepath, file), "rb") as f:
            decode_msg, utc_date_time = None, None
            while True:
                try:
                    hdr1 = read_bytes(f, 1)
                    if hdr1 == b"\xb5":
                        decode_msg = self.handle_pps_data(f)
                        if not decode_msg:
                            continue

                        start_flag = True

                        for value in pps_dict.values():
                            value.append(np.nan)

                        if decode_msg and decode_msg["flag"].strip() != "0":
                            secR = calc_sec(
                                decode_msg["towMsR"], decode_msg["towSubMsR"]
                            )
                            secF = calc_sec(
                                decode_msg["towMsF"], decode_msg["towSubMsF"]
                            )
                            pps_dict["ch"][-1] = decode_msg["ch"]
                            pps_dict["flag"][-1] = decode_msg["flag"]
                            pps_dict["count"][-1] = decode_msg["count"]
                            pps_dict["wnR"][-1] = decode_msg["wnR"]
                            pps_dict["secR"][-1] = secR
                            pps_dict["wnF"][-1] = decode_msg["wnF"]
                            pps_dict["secF"][-1] = secF
                            pps_dict["accEst"][-1] = decode_msg["accEst"]

                    if start_flag and hdr1 == b"\x24":
                        utc_date_time = self.hand_rmc_data(f)
                        if utc_date_time is None:
                            continue

                        pps_dict["utc_date_time"][-1] = utc_date_time

                except EOFError:
                    break

    def handle_pps_data(self, f: BufferedReader):
        # if (
        #     read_bytes(f, 1) != b"\x62"
        #     or read_bytes(f, 1) != b"\x0d"
        #     or read_bytes(f, 1) != b"\x03"
        # ):
        #     return None

        header = read_bytes(f, 3)

        if header[0] != 0x62 and header[1] != 0x0D and header[2] != 0x03:
            return None

        len_bytes = read_bytes(f, 2)
        length = bytes2int(len_bytes)
        if length == 0:
            return None

        payload = read_bytes(f, length)
        ck_sum = read_bytes(f, 2)

        ubx = UbxStruct(len_bytes, payload, ck_sum)

        return ubx.decode()

    def hand_rmc_data(self, f: BufferedReader):
        # if read_bytes(f, 1) != b"\x47" or read_bytes(f, 1) != b"\x4e":
        #     return None

        header = read_bytes(f, 5)

        if header != b"\x47\x4e\x52\x4d\x43":
            if header[0] == 0x47:
                l = f.readline()
            return None

        # if read_bytes(f, 3) != b"\x52\x4d\x43":
        #     return None

        line = "$GNRMC" + f.readline().strip().decode()
        rmc = RMCParser(line, error_code=False)

        return rmc.utc_date_time

    def _gen_report(self, result_dict):
        df_result = pd.DataFrame(result_dict, index=pps_index_list)
        for col in df_result.columns:
            df_result[col] = df_result[col].fillna("-")

        if not df_result.empty and self.result_path:
            report = Report(
                df_result,
                self.result_path,
                data_path=self.result_path,
                check_list=self.check_list,
            )
            report.gen_pps_report()

    def _gen_result_dict(self, result_dict, file, df):
        df_delta = df["pps_delta"]
        df_describe = df_delta.apply(abs).describe(percentiles=percentiles)
        # peak_to_peak_value = df_delta.max() - df_delta.min()

        result_dict[file] = [
            round(df_delta.mean(), 5),
            # round(df_delta.std(), 5),
            calc_rms(df_delta),
            round(df_describe[PERCENT_50], 3),
            round(df_describe[PERCENT_68], 3),
            round(df_describe[PERCENT_95], 3),
            round(df_describe[PERCENT_99], 3),
        ]

    def _gen_nan_result(self, result_dict, file):
        result_dict[file] = [np.nan] * len(pps_index_list)

    def print_msg(self, msg: str):
        if self.callback == print:
            msg = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')} {msg}"
        self.callback(msg)


class PPSUIProcessor(QThread):
    log_signal = Signal(str)
    end_signal = Signal()

    def __init__(self):
        QThread.__init__(self)
        self.processor = PPSProcessor()

    def run(self):
        self.processor.create()
        self.processor.callback = self.log_signal.emit

        self.processor.process_data()
        self.end_signal.emit()


class PPSWebProcessor:
    def __init__(self):
        self.processor = PPSProcessor()

    def run(self):
        self.processor.create()
        self.processor.callback = print

        self.processor.process_data()
