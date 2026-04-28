from datetime import datetime
import logging
import os
from pathlib import Path
from threading import Event
from typing import Any, Optional, Union
from PySide6.QtCore import QThread, Signal
from PySide6.QtWidgets import QCheckBox
import numpy as np
import pandas as pd
from src.libs.jsreport import JsReport
from src.libs.nmea import NMEAHeaderByte, freq_list, snr_list
from src.util.param import percentiles

from src import HandleItem, Point
from src.handler import (
    format_pd,
    get_expect_valid_value,
    update_error_dict,
    nav_log_info,
    print_error_info,
    write_to_file,
)
from src.handler.pos import PosProcessor
from src.libs.nmea import (
    Default,
    NMEAHeader,
    sys_list,
    sys_label_list,
    sat_freq_combinations,
)
from src.libs.nmea.gga import GGAParser
from src.libs.nmea.gsa import GSAParser
from src.libs.nmea.gsv import GSVParser
from src.libs.nmea.rmc import RMCParser
from src.libs.report import Report
from src.util import utils
from src.util.logger import logger
from src.util.const import File
from src.util.param import (
    PERCENT_50,
    PERCENT_68,
    PERCENT_95,
    PERCENT_99,
    position_index_list,
)

logger = logging.getLogger(__name__)

threshold = 20  # CN0门限

EXPORT_COLUMNS: list = [
    "label",
    "lat",
    "lng",
    "hgt",
    "speed",
    "E",
    "N",
    "U",
    "distance_3d",
    "distance",
    "hgt_delta",
    "speed_delta",
]

REF_COLUMNS: list = [
    "ref_label",
    "ref_lat",
    "ref_lng",
    "ref_hgt",
    "ref_speed",
]


def init_temp_gsv():
    gsv_cn0_temp_dict = {}
    for sat_sys, freq in sat_freq_combinations:
        gsv_cn0_temp_dict.setdefault(sat_sys, {}).setdefault(freq, [])

    return gsv_cn0_temp_dict


def get_cn0_numpy(m: list) -> np.ndarray:
    y = np.array(m)
    return y[~np.isnan(y)]


def calc_mean(m: np.ndarray) -> float:
    return np.nan if m.size == 0 else round(m.mean(), 1)


def _format_date_time(value) -> str:
    loc = str(value).rfind(".")
    return str(value) if loc == -1 else str(value)[:loc]


class PositionAttr:
    def __init__(self, point: Union[Point, str] = ""):
        self.point = point

        self.result_path: str = ""
        self.filepath: str = ""
        self.utc_date: Optional[str] = None
        self.error_list: list = []
        self.is_moving: bool = False
        self.ref_file: str = ""
        self.fix_mode: int = 0
        self.std_mode: bool = False
        self.is_ttff: bool = False
        self.prefix_list: list = []
        self.check_list: list[Union[str, QCheckBox]] = []
        self.point: Union[Point, str] = point
        self.data_path = ""
        self.scenes: list = []
        self.customer_path: str = ""
        self.df_datas: dict[str, dict[str, Any]] = {}

        self.js_report: Optional[JsReport] = None
        self.action: int = HandleItem.INTERNAL

        self.stop_event: Optional[Event] = None

    def create(self):
        if not self.filepath:
            return

        if (self.action >> 1) & 1 and self.is_moving:
            self.js_report = JsReport(self.scenes)
            self.customer_path = os.path.join(self.filepath, "cReport")
            os.makedirs(self.customer_path, exist_ok=True)

        if self.action & 1:
            if self.is_moving:
                self.result_path = os.path.join(self.filepath, "report", "all")
            else:
                self.result_path = os.path.join(self.filepath, "report")

            self.data_path = os.path.join(self.result_path, "data")
            os.makedirs(self.data_path, exist_ok=True)


class PositionProcessor(PositionAttr):
    def __init__(self, point: Union[Point, str] = ""):
        self.callback: Any = None
        super().__init__(point)

        self.position_dict: dict[str, list] = {}
        # self.init_data()

    def init_data(self, init: bool = False):
        if init:
            for key, item in self.position_dict.items():
                item.append("0" if key == "label" else Default.DEFAULT_NAN)

            return

        self.position_dict = {
            "utc_date_time": [],
            "gga_time": [],
            "label": [],
            "satellites": [],
            "lat": [],
            "lng": [],
            "hgt": [],
            "delay": [],
            "pdop": [],
            "hdop": [],
            "vdop": [],
            "speed": [],
            "header": [],
            "yaw": [],
            "l1_count": [],
            "l2_count": [],
            "l5_count": [],
        }
        for sat_sys, freq in sat_freq_combinations:
            self.position_dict[f"{sat_sys}_{freq}"] = []
            self.position_dict[f"{sat_sys}_{freq}_cnt"] = []
            self.position_dict[f"{sat_sys}_{freq}_sum"] = []
            self.position_dict[f"{sat_sys}_{freq}_max"] = []
            self.position_dict[f"{sat_sys}_{freq}_min"] = []

    def process_static_data(
        self,
        std_mode=False,
        is_ttff=False,
    ):
        result_dict: dict[str, list] = {}
        log_info = nav_log = ""

        self.check_list: list[str] = self._normalize_check_list()

        for file in self.check_list:
            if self.stop_event and self.stop_event.is_set():
                return

            self.print_msg(f"开始处理文件: {file}")

            df, _, df_valid, df_expect, freq, temp_log = self._generate_dateframe(
                file,
                is_ttff=is_ttff,
            )
            if df is None or df.empty:
                nav_log, log_info = nav_log_info(
                    nav_log, log_info, temp_log, file, self.callback
                )
                self._gen_nan_result(result_dict, file[:-4])
                continue

            # 计算平均坐标值
            lat_mean, lng_mean, hgt_mean = self._calculate_mean_coordinate(df)

            if std_mode:
                self.point = Point(lat=lat_mean, lng=lng_mean, hgt=hgt_mean)

            self._calc_static_data(df, lat_mean, lng_mean, hgt_mean, std_mode)

            if self.result_path:
                write_to_file(
                    df[EXPORT_COLUMNS],
                    self.data_path,
                    f"{file[:-4]}{File.CALC_FILE_EXT}",
                )

            self._gen_result(result_dict, file[:-4], df, freq, df_expect, df_valid)

            nav_log, log_info = nav_log_info(
                nav_log, log_info, temp_log, file, self.callback
            )

            # self.js_report.gen_scene_result(df, self.customer_path, freq, file[:-4])

            self.print_msg(f"文件处理完成: {file}")

        self.print_msg(f"生成报告中...")
        # self.gen_customer_report()

        desc = "(内符合坐标)" if std_mode else ""
        self._gen_report(
            self.result_path,
            self.data_path,
            result_dict,
            f"{self.point}({desc})",
            nav_log,
            log_info,
            is_ttff=is_ttff,
        )

        self.print_msg(f"报告生成完成")

    def process_moving_data(
        self,
        callback=print,
        is_ttff=False,
    ):
        result_dict: dict[str, list] = {}
        log_info = nav_log = ""

        self.check_list: list[str] = self._normalize_check_list()

        self.print_msg(f"开始处理参考: {self.point}")

        df_ref, *_ = self._generate_dateframe(self.point, write_file=False)

        if df_ref is None or df_ref.empty:
            self.print_msg('<font color="red">参考无效！</font>')
            return

        if self.fix_mode != 0:
            df_ref = df_ref[df_ref["label"] == "4"]

        if df_ref.empty:
            self.print_msg(
                '<font color="red">参考无效，没有选择的定位类型数据！</font>'
            )
            return

        if self.js_report:
            self.js_report.gen_scene_result(
                df_ref,
                self.customer_path,
                action=(self.action >> 1) & 1,
                callback=self.print_msg,
            )

        df_ref = df_ref.rename(
            columns={
                "label": "ref_label",
                "lat": "ref_lat",
                "lng": "ref_lng",
                "hgt": "ref_hgt",
                "speed": "ref_speed",
            }
        )
        df_ref.drop(
            columns=snr_list
            + [
                "gga_time",
                "vdop",
                "hdop",
                "pdop",
                "delay",
                "satellites",
                "header",
                "yaw",
                "l1_count",
                "l2_count",
                "l5_count",
            ],
            inplace=True,
        )

        self.print_msg("参考处理完成")

        for file in self.check_list:
            if self.stop_event and self.stop_event.is_set():
                return

            self.print_msg(f"开始处理文件: {file}")

            df, *_, freq, temp_log_info = self._generate_dateframe(
                file,
                callback,
            )

            if df is None or df.empty:
                nav_log, log_info = nav_log_info(
                    nav_log, log_info, temp_log_info, file, callback
                )
                self._gen_nan_result(result_dict, file[:-4])
                continue

            df = pd.concat([df, df_ref], axis=1, join="inner")
            if df.empty:
                nav_log, log_info = nav_log_info(
                    nav_log, log_info, temp_log_info, file, callback
                )
                self._gen_nan_result(result_dict, file[:-4])
                continue

            self._calc_moving_data(df)

            df_total = df.shape[0]
            freq_concat = utils.get_freq(df.index.to_numpy())
            df_expect, df_valid = get_expect_valid_value(
                df,
                freq_concat,
                df_total,
                0,
                last_valid_index=df.shape[0] - 1,
                label="distance",
            )

            if self.scenes:
                self.df_datas[file]["calc"] = df
                self.df_datas[file]["freq"] = freq_concat

            if self.result_path:
                write_to_file(
                    df[EXPORT_COLUMNS + REF_COLUMNS],
                    self.data_path,
                    f"{file[:-4]}{File.CALC_FILE_EXT}",
                )

            self._gen_result(
                result_dict, file[:-4], df, freq, df_expect, df_valid, True
            )
            nav_log, log_info = nav_log_info(
                nav_log, log_info, temp_log_info, file, callback
            )

            if self.js_report:
                self.js_report.gen_scene_result(
                    df,
                    self.customer_path,
                    freq_concat,
                    file[:-4],
                    (self.action >> 1) & 1,
                    callback=self.print_msg,
                )

            self.print_msg(f"文件处理完成: {file}")

        self.print_msg("生成报告中...")

        self.gen_customer_report()

        self._gen_report(
            self.result_path,
            self.data_path,
            result_dict,
            self.point,
            nav_log,
            log_info,
            is_ttff=is_ttff,
        )

        self.gen_split_report()

        self.print_msg("报告生成完成")

    def gen_customer_report(self):
        if not ((self.action >> 1) & 1) or not self.js_report:
            return

        self.js_report.write_to_js(self.customer_path)
        self.js_report.plot_cep_graph(self.customer_path)
        self.js_report.gen_track_file(self.customer_path)

    def print_msg(self, msg: str):
        if self.callback == print:
            msg = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f')} {msg}"
        self.callback(msg)

    def _normalize_check_list(self) -> list[str]:
        """标准化检查列表, 处理QCheckBox对象"""
        check_list = [
            check_file.text() if isinstance(check_file, QCheckBox) else check_file
            for check_file in self.check_list
        ]

        if self.scenes and self.js_report:
            self.js_report.init_report_data(check_list)

        return check_list

    def _calculate_mean_coordinate(self, df: pd.DataFrame) -> tuple:
        """计算坐标平均值"""
        if df[df["label"] == "4"]["lat"].size / df["lat"].size > 0.1:
            lat_mean = df[df["label"] == "4"]["lat"].mean()
            lng_mean = df[df["label"] == "4"]["lng"].mean()
            hgt_mean = df[df["label"] == "4"]["hgt"].mean()
        else:
            df_mean = df[df["label"].str.contains("1|2|4|5")]
            lat_mean = df_mean["lat"].mean()
            lng_mean = df_mean["lng"].mean()
            hgt_mean = df_mean["hgt"].mean()

        return lat_mean, lng_mean, hgt_mean

    def _calc_static_data(
        self,
        df: pd.DataFrame,
        lat_mean: float,
        lng_mean: float,
        hgt_mean: float,
        std_mode: bool,
    ):
        """计算ENU坐标系和各种距离"""
        # 计算ENU坐标系

        # assert isinstance(self.point, Point)
        df["E"], df["N"], df["U"], df["distance_3d"], df["distance"] = (
            utils.calculate_data(
                df["lat"],
                df["lng"],
                df["hgt"],
                self.point.lat,  # type: ignore
                self.point.lng,  # type: ignore
                self.point.hgt,  # type: ignore
            )
        )

        # 计算高度差和速度差
        df["hgt_delta"] = abs(df["hgt"] - self.point.hgt).round(3)  # type: ignore
        df["speed_delta"] = df["speed"].round(3)
        df["std_hgt_delta"] = abs(df["hgt"] - hgt_mean).round(3)

        # 计算内符合精度
        if std_mode:
            df["std_distance"] = df["distance"]
        else:
            *_, df["std_distance"] = utils.calculate_data(
                df["lat"], df["lng"], df["hgt"], lat_mean, lng_mean, hgt_mean
            )

    def _calc_moving_data(self, df):
        df["E"], df["N"], df["U"], df["distance_3d"], df["distance"] = (
            utils.calculate_data(
                df["lat"],
                df["lng"],
                df["hgt"],
                df["ref_lat"],
                df["ref_lng"],
                df["ref_hgt"],
            )
        )

        if self.fix_mode != 0:
            df = df[df["ref_label"] == "4"]

        df["hgt_delta"] = abs(df["hgt"] - df["ref_hgt"]).round(3)
        df["speed_delta"] = abs(df["speed"] - df["ref_speed"]).round(3)

    def _generate_dateframe(
        self,
        file,
        callback=None,
        log_info="",
        write_file=True,
        is_ttff=False,
    ):
        if not write_file:
            file_path = file
            file = file.split("\\")[-1]
        else:
            file_path = os.path.join(self.filepath, file)

        error_dict = {}

        self._handle_nmea(file_path, error_dict, is_ttff, callback)

        return self._handle_dataframe(file, error_dict, log_info, write_file)

    def _handle_nmea(self, file_path, error_dict, is_ttff, callback, start_flag=False):
        # 确定主要处理的数据类型
        main_type = "rmc" if self._check_rmc_first(file_path) else "gga"

        # 设置处理标志
        main_flag = False
        gsa_flag = False
        gsv_flag = False

        # 初始化临时字典
        gsv_cn0_temp_dict: dict = init_temp_gsv()

        header = 0
        header_count = 0
        main_utc_time = ""
        self.init_data()

        with open(file_path, "rb") as f:
            for line in f:
                if self.stop_event and self.stop_event.is_set():
                    break

                line_upper = line.upper()
                update_error_dict(line_upper, error_dict, self.error_list)

                for prefix in self.prefix_list:
                    if prefix in line_upper:
                        header = 1
                        if not is_ttff:
                            header_count += 1
                        break

                nmea_flag = (
                    NMEAHeaderByte.RMC_BYTE in line
                    if main_type == "rmc"
                    else NMEAHeaderByte.GGA_BYTE in line
                )

                # 检查是否开始处理
                if not start_flag and nmea_flag:
                    err_code, decode_line = utils.decode_line(line)
                    parser = (
                        RMCParser(decode_line, error_code=err_code)
                        if main_type == "rmc"
                        else GGAParser(decode_line, error_code=err_code)
                    )
                    if not start_flag and isinstance(parser.utc_time, str):
                        start_flag = True

                if start_flag:
                    # 处理主要类型数据（RMC或GGA）
                    if nmea_flag:
                        if main_flag and gsv_flag:
                            gsv_cn0_temp_dict = self._handle_gsv(
                                gsv_cn0_temp_dict, main_utc_time
                            )

                        self.init_data(True)

                        err_code, decode_line = utils.decode_line(line)
                        # 设置主要类型数据
                        if main_type == "rmc":
                            parser = RMCParser(decode_line, error_code=err_code)
                            self.position_dict["utc_date_time"][
                                -1
                            ] = parser.utc_date_time
                            self.position_dict["speed"][-1] = parser.speed
                            self.position_dict["yaw"][-1] = parser.yaw
                        else:  # GGA
                            parser = GGAParser(decode_line, error_code=err_code)
                            self.position_dict["gga_time"][-1] = parser.utc_time
                            self.position_dict["label"][-1] = parser.fix_label
                            self.position_dict["satellites"][-1] = parser.satellites
                            self.position_dict["lat"][-1] = parser.lat
                            self.position_dict["lng"][-1] = parser.lng
                            self.position_dict["hgt"][-1] = parser.hgt
                            self.position_dict["delay"][-1] = parser.delay

                        main_utc_time = parser.utc_time

                        main_flag = True
                        gsa_flag = False
                        gsv_flag = (
                            True
                            if parser.utc_time_str.endswith(".00")
                            or parser.utc_time_str.endswith(".000")
                            else False
                        )

                        self.position_dict["header"][-1] = header

                        if not np.isnan(float(main_utc_time)):
                            header = 0

                    # 处理另一个类型的数据（如果是RMC则处理GGA，反之亦然）
                    elif (
                        NMEAHeaderByte.GGA_BYTE in line
                        if main_type == "rmc"
                        else NMEAHeaderByte.RMC_BYTE in line
                    ):
                        err_code, decode_line = utils.decode_line(line)
                        if main_type == "rmc":  # 当前主要类型是RMC，处理GGA数据
                            parser = GGAParser(decode_line, error_code=err_code)
                            self.position_dict["gga_time"][-1] = parser.utc_time
                            self.position_dict["label"][-1] = parser.fix_label
                            self.position_dict["satellites"][-1] = parser.satellites
                            self.position_dict["lat"][-1] = parser.lat
                            self.position_dict["lng"][-1] = parser.lng
                            self.position_dict["hgt"][-1] = parser.hgt
                            self.position_dict["delay"][-1] = parser.delay
                        else:  # 当前主要类型是GGA，处理RMC数据
                            parser = RMCParser(decode_line, error_code=err_code)
                            self.position_dict["utc_date_time"][
                                -1
                            ] = parser.utc_date_time
                            self.position_dict["speed"][-1] = parser.speed
                            self.position_dict["yaw"][-1] = parser.yaw

                    # 处理GSA数据
                    elif NMEAHeaderByte.GSA_BYTE in line:
                        if not gsa_flag:
                            err_code, decode_line = utils.decode_line(line)
                            gsa = GSAParser(decode_line, error_code=err_code)
                            self.position_dict["pdop"][-1] = gsa.pdop
                            self.position_dict["hdop"][-1] = gsa.hdop
                            self.position_dict["vdop"][-1] = gsa.vdop
                            gsa_flag = True

                    # 处理GSV数据
                    elif NMEAHeaderByte.GSV_BYTE in line and gsv_flag:
                        self._handle_gsv_dict(gsv_cn0_temp_dict, line)

        if not is_ttff and header_count:
            error_dict["重启"] = header_count
        print_error_info(error_dict, callback)

    def _check_rmc_first(self, file_path: str) -> bool:
        logger.info("start check rmc first")
        result_list = []
        NMEAHeader.RMC, NMEAHeader.GGA = "RMC,", "GGA,"
        is_gnrmc, is_gprmc, is_gngga, is_gpgga = [False] * 4

        with open(file_path, "rb") as f:
            for line in f:
                if len(result_list) > 3600:
                    break

                if not is_gnrmc and NMEAHeaderByte.GNRMC_BYTE in line:
                    is_gnrmc = True
                elif not is_gprmc and NMEAHeaderByte.GPRMC_BYTE in line:
                    is_gprmc = True
                elif not is_gngga and NMEAHeaderByte.GNGGA_BYTE in line:
                    is_gngga = True
                elif not is_gpgga and NMEAHeaderByte.GPGGA_BYTE in line:
                    is_gpgga = True

                if NMEAHeaderByte.RMC_BYTE in line or NMEAHeaderByte.GGA_BYTE in line:
                    err_code, decode_line = utils.decode_line(line)
                    if NMEAHeaderByte.RMC_BYTE in line:
                        parser = RMCParser(decode_line, error_code=err_code)
                        label = "rmc"
                    else:
                        parser = GGAParser(decode_line, error_code=err_code)
                        label = "gga"
                    if isinstance(parser.utc_time, str):
                        result_list.append({label: parser.utc_time})

        if is_gnrmc:
            NMEAHeader.RMC = NMEAHeader.GNRMC
        elif is_gprmc:
            NMEAHeader.RMC = NMEAHeader.GPRMC

        if is_gngga:
            NMEAHeader.GGA = NMEAHeader.GNGGA
        elif is_gpgga:
            NMEAHeader.GGA = NMEAHeader.GPGGA

        for i in range(len(result_list) - 1):
            current_item: dict = result_list[i]
            next_item: dict = result_list[i + 1]

            current_key: str = list(current_item.keys())[0]
            next_key: str = list(next_item.keys())[0]

            if current_key == next_key:
                continue

            if current_item[current_key] != next_item[next_key]:
                continue

            if current_key == "rmc":
                return True
            break

        return False

    def _handle_gsv(self, gsv_cn0_temp_dict, utc_time):
        self._set_cn0_value(gsv_cn0_temp_dict)

        # if (
        #     isinstance(utc_time, float)
        #     or utc_time.endswith(".00")
        #     or utc_time.endswith(".000")
        # ):
        #     logger.debug(f"{gsv_cn0_temp_dict}")
        #     gsv_cn0_temp_dict = {
        #         item: {"l1": [], "l2": [], "l5": []} for item in sys_label_list
        #     }

        return init_temp_gsv()

    def _handle_gsv_dict(self, gsv_cn0_temp_dict, line):
        err_code, decode_line = utils.decode_line(line)
        gsv = GSVParser(decode_line, error_code=err_code)
        sys_label, freq_label, cn0_list = gsv.decode_gsv()
        if sys_label in sys_label_list and cn0_list:
            gsv_cn0_temp_dict[sys_label][freq_label] += cn0_list

    def _handle_dataframe(self, file, error_dict, log_info="", write_file: bool = True):
        if error_dict:
            log_info = f"ERROR统计: <br>{error_dict}<br><br>" + log_info

        if not self.position_dict["utc_date_time"]:
            return None, 0, 0, 1, 1, log_info

        df = pd.DataFrame(self.position_dict)
        df.drop(df.tail(1).index, inplace=True)  # 剔除最后一行数据

        if self.scenes and write_file:
            self.df_datas.setdefault(file, {"original": df})

        if write_file and self.result_path:
            write_to_file(
                df,
                self.data_path,
                f"{file[:-4]}{File.ORIGINAL_FILE_EXT}",
                False,
            )

        fix_total = df.shape[0]

        df, freq, log_info, first_valid_index, _ = format_pd(
            df, log_info=log_info, label="rmc"
        )

        fix_expect, fix_valid = get_expect_valid_value(
            df, freq, fix_total, first_valid_index, df.shape[0] - 1, "lat"
        )

        # gen pos and position file
        if write_file and self.result_path:
            pos = PosProcessor(self.data_path, file, df)
            pos.start()

        return df, fix_total, fix_valid, fix_expect, freq, log_info

    def _set_cn0_value(self, gsv_cn0_temp_dict):
        # 预计算所有CN0数组
        cn0_arrays = {}
        for sys, freq in sat_freq_combinations:
            cn0_arrays[f"{sys}_{freq}"] = get_cn0_numpy(gsv_cn0_temp_dict[sys][freq])

        for sys, freq in sat_freq_combinations:
            key = f"{sys}_{freq}"
            cn0_array = cn0_arrays[key]
            if cn0_array.size > 0:
                self.position_dict[key][-1] = round(cn0_array.mean(), 1)
                self.position_dict[f"{key}_sum"][-1] = cn0_array.sum()
                self.position_dict[f"{key}_cnt"][-1] = len(cn0_array)
                self.position_dict[f"{key}_max"][-1] = cn0_array.max()
                self.position_dict[f"{key}_min"][-1] = cn0_array.min()
            else:
                self.position_dict[key][-1] = np.nan
                self.position_dict[f"{key}_sum"][-1] = np.nan
                self.position_dict[f"{key}_cnt"][-1] = np.nan
                self.position_dict[f"{key}_max"][-1] = np.nan
                self.position_dict[f"{key}_min"][-1] = np.nan

        for freq in freq_list:
            total_count = 0
            for sat_sys in sys_list:
                key = f"{sat_sys}_{freq}"
                if key in cn0_arrays:
                    total_count += cn0_arrays[key][cn0_arrays[key] > threshold].size

            self.position_dict[f"{freq}_count"][-1] = total_count

    def _gen_report(
        self,
        result_path: str,
        data_path: str,
        result_dict,
        point,
        nav_log="",
        log_info="",
        is_ttff=False,
        begin_time: Optional[pd.Timestamp] = None,
        end_time: Optional[pd.Timestamp] = None,
    ):
        if not (self.action & 1):
            return

        df_result = pd.DataFrame(result_dict, index=position_index_list)
        for col in df_result.columns:
            df_result[col] = df_result[col].fillna("-")

        if not df_result.empty and result_path:
            report = Report(
                df_result,
                result_path,
                data_path,
                point,
                nav_log,
                log_info,
                self.check_list,
                self.is_moving,
                is_ttff=is_ttff,
                begin_time=begin_time,
                end_time=end_time,
            )
            report.gen_precision_report()

    def _gen_result(
        self,
        result_dict,
        file,
        df,
        freq,
        df_expect,
        df_valid,
        is_moving=False,
    ):
        if "std_distance" not in df.keys():
            is_moving = True

        if is_moving:
            hgt_delta_mask = (df["label"].isin(["1", "2", "4", "5", "7"])) & (
                df["ref_label"] != "0"
            )
            df_speed = df[(df["label"].isin(["1", "2", "4", "5", "7"]))]["speed_delta"]
        else:
            hgt_delta_mask = df["label"] != "0"
            df_speed = df["speed_delta"]

        df_hgt_delta = df[hgt_delta_mask]["hgt_delta"]

        distance_mask: pd.Series = df["label"].str.contains("1|2|4|5|7")
        df_distance: pd.Series = df[distance_mask]["distance"]
        df_distance_3d: pd.Series = df[distance_mask]["distance_3d"]

        cn0_data = {}
        for sat_sys, sat_freq in sat_freq_combinations:
            cn0_data[f"{sat_sys}_{sat_freq}"] = df[f"{sat_sys}_{sat_freq}"].mean()

        # 处理NaN值
        cn0_values: dict[str, float] = {}
        for key, value in cn0_data.items():
            cn0_values[key] = round(value, 1) if not np.isnan(value) else 0.0

        # 生成统计描述
        stats_describe: dict[str, pd.Series] = {}
        stats_to_calculate: dict[str, pd.Series] = {
            "df_distance": df_distance,
            "df_hgt_delta": df_hgt_delta,
            "df_distance_3d": df_distance_3d,
            "df_speed": df_speed,
        }

        for label in ["1", "2", "4", "5"]:
            stats_to_calculate[f"df_{label}"] = df[df["label"] == label]["distance"]
            stats_to_calculate[f"df_{label}_hgt_delta"] = df[df["label"] == label][
                "hgt_delta"
            ]

        df_0 = df[df["label"] == "0"]["distance"]

        for key, data in stats_to_calculate.items():
            stats_describe[key] = data.describe(percentiles=percentiles)

        df_dop = df[df["label"].str.contains("1|2|4|5")]

        result_dict[file] = [
            _format_date_time(df.index[0]),
            _format_date_time(df.index[-1]),
            round((df.index[-1] - df.index[0]).total_seconds() / 3600, 1),
            f"{freq}HZ",
            round(df["satellites"].mean(), 2),
            f"{cn0_values['gps_l1']}+{cn0_values['gps_l2']}+{cn0_values['gps_l5']}",
            f"{cn0_values['bds_b1i']}+{cn0_values['bds_b2a']}+{cn0_values['bds_b2b']}",
            f"{cn0_values['bds_b1c']}+{cn0_values['bds_b2i']}+{cn0_values['bds_b3i']}",
            f"{cn0_values['gal_e1']}+{cn0_values['gal_e5a']}+{cn0_values['gal_e5b']}+{cn0_values['gal_e6']}",
            f"{cn0_values['glo_g1']}+{cn0_values['glo_g2']}",
            round(df_dop["pdop"].mean(), Default.KEEP_DECIMAL_DIGIT),
            round(df_dop["hdop"].mean(), Default.KEEP_DECIMAL_DIGIT),
            round(df_dop["vdop"].mean(), Default.KEEP_DECIMAL_DIGIT),
            utils.calc_value(df_expect, df_valid),  # 实际定位率
            utils.calc_value(df_expect, df_0.shape[0]),  # 未定位比率
            utils.calc_value(
                df_expect, stats_to_calculate["df_1"].shape[0]
            ),  # 单点比率
            utils.calc_value(
                df_expect, stats_to_calculate["df_2"].shape[0]
            ),  # 差分比率
            utils.calc_value(
                df_expect, stats_to_calculate["df_4"].shape[0]
            ),  # 固定解比率
            utils.calc_value(
                df_expect, stats_to_calculate["df_5"].shape[0]
            ),  # 浮点解比率
            "",
            file,
            utils.calc_rms(df_distance),
            (
                np.nan
                if is_moving
                else round(df["std_distance"].std(), Default.KEEP_DECIMAL_DIGIT)
            ),  # 内符合精度
            round(
                stats_describe["df_distance"][PERCENT_50], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_distance"][PERCENT_68], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_distance"][PERCENT_95], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_distance"][PERCENT_99], Default.KEEP_DECIMAL_DIGIT
            ),
            round(stats_describe["df_distance"]["max"], Default.KEEP_DECIMAL_DIGIT),
            utils.calc_rms(df_hgt_delta),
            (
                np.nan
                if is_moving
                else round(
                    stats_describe["df_hgt_delta"]["std"], Default.KEEP_DECIMAL_DIGIT
                )
            ),
            round(
                stats_describe["df_hgt_delta"][PERCENT_50], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_hgt_delta"][PERCENT_68], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_hgt_delta"][PERCENT_95], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_hgt_delta"][PERCENT_99], Default.KEEP_DECIMAL_DIGIT
            ),
            round(stats_describe["df_hgt_delta"]["max"], Default.KEEP_DECIMAL_DIGIT),
            utils.calc_rms(df_speed),
            round(stats_describe["df_speed"][PERCENT_50], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_speed"][PERCENT_68], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_speed"][PERCENT_95], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_speed"][PERCENT_99], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_speed"]["max"], Default.KEEP_DECIMAL_DIGIT),
            "",
            file,
            utils.calc_rms(df_distance_3d),
            round(
                stats_describe["df_distance_3d"][PERCENT_50], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_distance_3d"][PERCENT_68], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_distance_3d"][PERCENT_95], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_distance_3d"][PERCENT_99], Default.KEEP_DECIMAL_DIGIT
            ),
            round(stats_describe["df_distance_3d"]["max"], Default.KEEP_DECIMAL_DIGIT),
            "",
            file,
            utils.calc_rms(stats_to_calculate["df_4"]),
            round(stats_describe["df_4"][PERCENT_50], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_4"][PERCENT_68], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_4"][PERCENT_95], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_4"][PERCENT_99], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_4"]["max"], Default.KEEP_DECIMAL_DIGIT),
            utils.calc_value(
                stats_to_calculate["df_4"].shape[0],
                stats_to_calculate["df_4"][stats_to_calculate["df_4"] <= 0.025].shape[
                    0
                ],
            ),
            utils.calc_value(
                stats_to_calculate["df_4"].shape[0],
                stats_to_calculate["df_4"][
                    (stats_to_calculate["df_4"] > 0.025)
                    & (stats_to_calculate["df_4"] <= 0.1)
                ].shape[0],
            ),
            utils.calc_value(
                stats_to_calculate["df_4"].shape[0],
                stats_to_calculate["df_4"][
                    (stats_to_calculate["df_4"] > 0.1)
                    & (stats_to_calculate["df_4"] <= 0.2)
                ].shape[0],
            ),
            utils.calc_value(
                stats_to_calculate["df_4"].shape[0],
                stats_to_calculate["df_4"][
                    (stats_to_calculate["df_4"] > 0.2)
                    & (stats_to_calculate["df_4"] <= 1)
                ].shape[0],
            ),
            utils.calc_value(
                stats_to_calculate["df_4"].shape[0],
                stats_to_calculate["df_4"][
                    (stats_to_calculate["df_4"] > 1)
                    & (stats_to_calculate["df_4"] <= 10)
                ].shape[0],
            ),
            utils.calc_value(
                stats_to_calculate["df_4"].shape[0],
                stats_to_calculate["df_4"][(stats_to_calculate["df_4"] > 10)].shape[0],
            ),
            utils.calc_rms(stats_to_calculate["df_4_hgt_delta"]),
            round(
                stats_describe["df_4_hgt_delta"][PERCENT_50], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_4_hgt_delta"][PERCENT_68], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_4_hgt_delta"][PERCENT_95], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_4_hgt_delta"][PERCENT_99], Default.KEEP_DECIMAL_DIGIT
            ),
            round(stats_describe["df_4_hgt_delta"]["max"], Default.KEEP_DECIMAL_DIGIT),
            utils.calc_value(
                stats_to_calculate["df_4_hgt_delta"].shape[0],
                stats_to_calculate["df_4_hgt_delta"][
                    stats_to_calculate["df_4_hgt_delta"] <= 0.05
                ].shape[0],
            ),
            utils.calc_value(
                stats_to_calculate["df_4_hgt_delta"].shape[0],
                stats_to_calculate["df_4_hgt_delta"][
                    (stats_to_calculate["df_4_hgt_delta"] > 0.05)
                    & (stats_to_calculate["df_4_hgt_delta"] <= 0.2)
                ].shape[0],
            ),
            utils.calc_value(
                stats_to_calculate["df_4_hgt_delta"].shape[0],
                stats_to_calculate["df_4_hgt_delta"][
                    stats_to_calculate["df_4_hgt_delta"] > 0.2
                ].shape[0],
            ),
            "",
            file,
            utils.calc_rms(stats_to_calculate["df_1"]),
            round(stats_describe["df_1"][PERCENT_50], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_1"][PERCENT_68], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_1"][PERCENT_95], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_1"][PERCENT_99], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_1"]["max"], Default.KEEP_DECIMAL_DIGIT),
            utils.calc_rms(stats_to_calculate["df_1_hgt_delta"]),
            round(
                stats_describe["df_1_hgt_delta"][PERCENT_50], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_1_hgt_delta"][PERCENT_68], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_1_hgt_delta"][PERCENT_95], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_1_hgt_delta"][PERCENT_99], Default.KEEP_DECIMAL_DIGIT
            ),
            round(stats_describe["df_1_hgt_delta"]["max"], Default.KEEP_DECIMAL_DIGIT),
            "",
            file,
            utils.calc_rms(stats_to_calculate["df_5"]),
            round(stats_describe["df_5"][PERCENT_50], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_5"][PERCENT_68], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_5"][PERCENT_95], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_5"][PERCENT_99], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_5"]["max"], Default.KEEP_DECIMAL_DIGIT),
            utils.calc_rms(stats_to_calculate["df_5_hgt_delta"]),
            round(
                stats_describe["df_5_hgt_delta"][PERCENT_50], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_5_hgt_delta"][PERCENT_68], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_5_hgt_delta"][PERCENT_95], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_5_hgt_delta"][PERCENT_99], Default.KEEP_DECIMAL_DIGIT
            ),
            round(stats_describe["df_5_hgt_delta"]["max"], Default.KEEP_DECIMAL_DIGIT),
            "",
            file,
            utils.calc_rms(stats_to_calculate["df_2"]),
            round(stats_describe["df_2"][PERCENT_50], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_2"][PERCENT_68], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_2"][PERCENT_95], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_2"][PERCENT_99], Default.KEEP_DECIMAL_DIGIT),
            round(stats_describe["df_2"]["max"], Default.KEEP_DECIMAL_DIGIT),
            utils.calc_rms(stats_to_calculate["df_2_hgt_delta"]),
            round(
                stats_describe["df_2_hgt_delta"][PERCENT_50], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_2_hgt_delta"][PERCENT_68], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_2_hgt_delta"][PERCENT_95], Default.KEEP_DECIMAL_DIGIT
            ),
            round(
                stats_describe["df_2_hgt_delta"][PERCENT_99], Default.KEEP_DECIMAL_DIGIT
            ),
            round(stats_describe["df_2_hgt_delta"]["max"], Default.KEEP_DECIMAL_DIGIT),
        ]

    def _gen_nan_result(self, result_dict, file):
        result_dict[file] = [np.nan] * len(position_index_list)

    def gen_split_report(self):
        for scene in self.scenes:
            begin_time = pd.Timestamp(scene["begin_time"])
            end_time = pd.Timestamp(scene["end_time"])
            result_dict = {}
            result_path: Path = Path(self.result_path) / ".." / scene["name"]
            data_path: Path = result_path / "data"
            data_path.mkdir(parents=True, exist_ok=True)

            for file, data in self.df_datas.items():
                df = data["calc"]
                freq = data["freq"]
                df_scene = df[(df.index >= begin_time) & (df.index <= end_time)]
                if df_scene.empty:
                    self._gen_nan_result(result_dict, file)
                    continue

                df_expect, df_valid = get_expect_valid_value(
                    df_scene,
                    freq,
                    df_scene.shape[0],
                    0,
                    last_valid_index=df_scene.shape[0] - 1,
                    label="distance",
                )
                self._gen_result(
                    result_dict, file[:-4], df_scene, freq, df_expect, df_valid, True
                )

            self._gen_report(
                result_path,  # type: ignore
                data_path,  # type: ignore
                result_dict,
                scene["name"],
                begin_time=begin_time,
                end_time=end_time,
            )


class PositionUIProcessor(QThread):
    log_signal = Signal(str)
    end_signal = Signal()

    def __init__(self):
        QThread.__init__(self)
        self.processor = PositionProcessor()

    def run(self):
        self.processor.create()
        self.processor.callback = self.log_signal.emit

        if self.processor.is_moving:
            self.processor.process_moving_data(
                is_ttff=self.processor.is_ttff,
            )
        else:
            self.processor.process_static_data(
                std_mode=self.processor.std_mode,
                is_ttff=self.processor.is_ttff,
            )
        self.end_signal.emit()


class PositionWebProcessor:
    def __init__(self):
        self.processor = PositionProcessor()

    def run(self):
        self.processor.create()
        self.processor.callback = print

        if self.processor.is_moving:
            self.processor.process_moving_data(
                is_ttff=self.processor.is_ttff,
            )
        else:
            self.processor.process_static_data(
                std_mode=self.processor.std_mode,
                is_ttff=self.processor.is_ttff,
            )
