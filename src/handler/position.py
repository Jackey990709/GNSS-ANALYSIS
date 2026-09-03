from __future__ import annotations

from collections import defaultdict
from datetime import datetime
import json
import logging
import os
import warnings
from pathlib import Path
from threading import Event
from typing import Any, Optional, TYPE_CHECKING, Union

from src.libs.nmea.headinga import HEADINGAParser
from src.libs.nmea.pcas50 import PCAS50Parser
from src.libs.nmea.pqsol import PQSOLParser
from src.libs.nmea.pqtmdrprva import PQTMDRPVAParser
from src.libs.nmea.pqtmtar import PQTMTARParser
from src.libs.nmea.pqtmvehatt import PQTMVEHATTParser
from src.libs.nmea.pqtmvel import PQTMVELParser
from src.libs.nmea.pstmdrprva import PSTMDRPVAParser

if TYPE_CHECKING:
    from PySide6.QtWidgets import QCheckBox
import numpy as np
import pandas as pd
from src.libs.jsreport import JsReport
from src.libs.nmea import NMEAHeaderByte, gsa_sys_id, snr_list
from src.util import percentiles

from src import HandleItem, Point
from src.handler import *
from src.handler.pos import PosProcessor
from src.libs.nmea import (
    Default,
    NMEAHeader,
    sys_label_list,
    sat_freq_combinations,
)
from src.libs.nmea.gga import GGAParser
from src.libs.nmea.gsa import GSAParser
from src.libs.nmea.gsv import GSVParser
from src.libs.nmea.rmc import RMCParser
from src.libs.nmea.base import _NMEABase
from src.libs.report import Report
from src.util import utils
from src.util.logger import logger
from src.util.const import File
from src.util.param import (
    cep_keys,
    position_index_list,
)

logger = logging.getLogger(__name__)

threshold = 100  # CN0门限


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


def _filter_empty_sections(
    _index: list[str], result_dict: dict[str, list]
) -> tuple[list[str], dict[str, list]]:
    """剔除全空的数据段（如 6-DR、PQTMVEL、Roll/Pitch/Heading 无数据时整段为 NaN）。"""
    df_result = pd.DataFrame(result_dict, index=_index)

    def _remove_section(
        keep_mask: list[bool], check_slice: slice, section_start: int
    ) -> None:
        """若 check_slice 内的数据行全部为 NaN，则将整段（section_start 到 check_slice.stop）标记为 False。"""
        section_data = df_result.iloc[check_slice]
        if not section_data.empty and section_data.isna().all().all():
            for j in range(section_start, check_slice.stop):
                keep_mask[j] = False

    def _find_next_blank(start: int) -> int:
        j = start
        while j < len(_index) and _index[j] != "":
            j += 1
        return j

    keep_mask = [True] * len(_index)

    # ── 1. Px Accuracy 段 ──────────────────────────────────────────
    for i, label in enumerate(_index):
        if label == "" and i + 1 < len(_index) and _index[i + 1].endswith(" Accuracy:"):
            data_end = _find_next_blank(i + 2)
            _remove_section(keep_mask, slice(i + 2, data_end), i)

    # ── 2. PQTMVEL 段 ─────────────────────────────────────────────
    for i, label in enumerate(_index):
        if label == "" and i + 1 < len(_index) and _index[i + 1] == "PQTMVEL Result:":
            data_end = _find_next_blank(i + 2)
            _remove_section(keep_mask, slice(i + 2, data_end), i)

    # ── 3. Heading 段 ──────────────────────────────────────────────
    for i, label in enumerate(_index):
        if (
            label == ""
            and i + 1 < len(_index)
            and _index[i + 1] == "Roll/Pitch/Heading Result:"
        ):
            data_end = _find_next_blank(i + 2)
            _remove_section(keep_mask, slice(i + 2, data_end), i)

    if all(keep_mask):
        return _index, result_dict
    new_index = [idx for idx, keep in zip(_index, keep_mask) if keep]
    new_result = {
        k: [v for v, keep in zip(vals, keep_mask) if keep]
        for k, vals in result_dict.items()
    }
    return new_index, new_result


class PositionAttr:
    def __init__(
        self,
        point: Union[Point, str] = "",
        top_n: int = 5,
        elev: int = 0,
        threshold: int = 0,
        fix_threshold: float = 0.1,
    ):
        self.point = point
        self.top_n = top_n
        self.elev = elev
        self.threshold = threshold  # CN0门限
        self.fixed_threshold = fix_threshold  # 固定解可用精度门限

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
        self._is_pos320 = False
        self.is_long_test = False  # 标记是否为长时间测试，影响报告生成逻辑

        # {file: [...51列]} 存储 long test 报告每文件数据
        self.long_test_data: dict[str, Union[list, str]] = {}
        self.remark = ""  # long test 报告备注信息

    def create(self):
        self.df_datas.clear()

        if not self.filepath:
            return

        if (self.action >> 1) & 1 and self.is_moving:
            self.js_report = JsReport(self.scenes)
            self.customer_path = os.path.join(self.filepath, "cReport")
            os.makedirs(self.customer_path, exist_ok=True)

        if self.action & 1:
            # if self.is_moving:
            #     self.result_path = os.path.join(self.filepath, "report", "all")
            # else:
            #     self.result_path = os.path.join(self.filepath, "report")
            self.result_path = os.path.join(self.filepath, "report", "all")

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

        self.position_dict = {k: [] for k in POSITION_DICT_KEYS}

        if self.is_moving:
            # 动态增加PQTMVEL解析
            self.position_dict.update({k: [] for k in POSITION_MOVING_DICT_KEYS})

        for sat_sys, freq in sat_freq_combinations:
            if (used_label := f"{sat_sys}_used") not in self.position_dict:
                self.position_dict[used_label] = []
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

            if std_mode:
                # 计算平均坐标值
                lat_mean, lng_mean, hgt_mean = self._calculate_mean_coordinate(df)
                self.point = Point(lat=lat_mean, lng=lng_mean, hgt=hgt_mean)

            self._calc_static_data(df, freq)
            if self.scenes:
                self.df_datas[file]["calc"] = df
                self.df_datas[file]["freq"] = freq

            if self.result_path:
                write_to_file(
                    df[EXPORT_COLUMNS + ["mis_seconds"]],
                    self.data_path,
                    f"{file[:-4]}{File.CALC_FILE_EXT}",
                )

            self._gen_result(
                result_dict,
                file[:-4],
                df,
                freq,
                df_expect,
                df_valid,
                checksum_fail=_NMEABase.total_failed,
                nmea_missing=_NMEABase.total_missing,
            )

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

        self.gen_split_report()

        Report.finalize_workbooks()

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
        skiprows, length = self.check_file_type()
        if self._is_pos320:
            df_ref = self._generate_pos_dateframe(
                self.point, skiprows=skiprows, length=length
            )
        else:
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

        df_ref = df_ref.rename(columns=RENAME_COLUMNS, errors="ignore")
        df_ref.drop(
            columns=snr_list + DROP_COLUMNS,
            inplace=True,
            errors="ignore",
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
                    df[
                        REF_COLUMNS
                        + EXPORT_COLUMNS
                        + ["heading_err", "2d_err", "3d_err"]
                    ],
                    self.data_path,
                    f"{file[:-4]}{File.CALC_FILE_EXT}",
                )

            self._gen_result(
                result_dict,
                file[:-4],
                df,
                freq,
                df_expect,
                df_valid,
                checksum_fail=_NMEABase.total_failed,
                nmea_missing=_NMEABase.total_missing,
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

        Report.finalize_workbooks()

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
            (
                check_file.text()  # type: ignore[union-attr]
                if callable(getattr(check_file, "text", None))
                else check_file
            )
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

    def _calc_static_data(self, df: pd.DataFrame, freq: float):
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
        df["yaw_delta"] = df["yaw"].round(3)

        pitch_mean = df["pitch"].mean()
        roll_mean = df["roll"].mean()
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", "Mean of empty slice")
            # 计算航向平均值，航向平均值需要考虑角度的环绕问题，使用向量平均法计算
            heading_mean = (
                np.degrees(
                    np.arctan2(
                        np.nanmean(np.sin(np.radians(df["heading"]))),
                        np.nanmean(np.cos(np.radians(df["heading"]))),
                    )
                )
                % 360
            )
        df["pitch_delta"] = abs(df["pitch"] - pitch_mean).round(5)
        df["roll_delta"] = angle_diff(df["roll"], roll_mean).round(5)
        df["heading_delta"] = angle_diff(df["heading"], heading_mean).round(5)
        with warnings.catch_warnings():
            warnings.filterwarnings("ignore", "Mean of empty slice")
            rms_pitch = np.sqrt(np.nanmean(df["pitch"] ** 2))
            rms_roll = np.sqrt(np.nanmean(df["roll"] ** 2))
            rms_heading = np.sqrt(np.nanmean(df["heading"] ** 2))
        df["rms_pitch_delta"] = abs(df["pitch"] - rms_pitch).round(5)
        df["rms_roll_delta"] = angle_diff(df["roll"], rms_roll).round(5)
        df["rms_heading_delta"] = angle_diff(df["heading"], rms_heading).round(5)
        df["mis_seconds"] = (
            df.index.to_series().diff().dt.total_seconds().fillna(np.nan) * freq
        )
        # df_utc_time["utc_date_time"].diff().dt.total_seconds() * 1000

        # # 计算内符合精度
        # if std_mode:
        #     df["std_distance"] = df["distance"]
        # else:
        #     *_, df["std_distance"] = utils.calculate_data(
        #         df["lat"], df["lng"], df["hgt"], lat_mean, lng_mean, hgt_mean
        #     )

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
        df["speed_delta"] = abs(df["speed"] - df["ref_speed"]).round(5)
        df["yaw_delta"] = angle_diff(df["yaw"], df["ref_yaw"]).round(5)
        df["pitch_delta"] = abs(df["pitch"] - df["ref_pitch"]).round(5)
        df["roll_delta"] = angle_diff(df["roll"], df["ref_roll"]).round(5)
        df["heading_delta"] = angle_diff(df["heading"], df["ref_heading"]).round(5)

        # 计算PQTMVEL数据
        # | PQTMVEL <Heading> - POS <Heading> | = HeadingErr
        df["heading_err"] = angle_diff(df["p_heading"], df["ref_heading"]).round(5)

        # | <GrdSpd>–√(〖<Vel-N>〗^2+〖<Vel-E>〗^2 )| = 2DErr
        df["2d_err"] = abs(
            df["p_grdspd"] - np.sqrt(df["p_veln"] ** 2 + df["p_vele"] ** 2)
        ).round(5)

        # |<Spd> –√(〖<Vel-N>〗^2+〖<Vel-E>〗^2+〖<Vel-D>〗^2 )| =3DErr
        df["3d_err"] = abs(
            df["p_spd"]
            - np.sqrt(df["p_veln"] ** 2 + df["p_vele"] ** 2 + df["p_veld"] ** 2)
        ).round(5)

        if self._is_pos320:
            df["veln_delta"] = abs(df["p_veln"] - df["ref_veln"]).round(5)
            df["vele_delta"] = abs(df["p_vele"] - df["ref_vele"]).round(5)
            df["veld_delta"] = abs(df["p_veld"] - df["ref_veld"]).round(5)
        else:
            df["veln_delta"] = np.nan
            df["vele_delta"] = np.nan
            df["veld_delta"] = np.nan

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

    def _generate_pos_dateframe(self, file, skiprows=0, length=0):
        df = pd.read_csv(
            file,
            sep=r"\s+",
            header=0,
            skiprows=range(skiprows),
            encoding="utf-8",
            encoding_errors="ignore",
        )

        if length == 11:
            df.columns = POS320_COLUMNS

        elif length == 21:
            df.columns = HP100_COLUMNS

        else:
            return pd.DataFrame()

        # GPS 时间转 UTC（拆分星期和秒，避免大数纳秒精度丢失）
        GPS_EPOCH = datetime(1980, 1, 6)
        LEAP_SECONDS = 18
        df["utc_date_time"] = (
            pd.to_datetime(GPS_EPOCH)
            + pd.to_timedelta(df["week"].astype(int) * 7, unit="D")
            + pd.to_timedelta(df["gpstime"] - LEAP_SECONDS, unit="s")
        ).astype("datetime64[us]")
        df.drop_duplicates(subset=["utc_date_time"], keep="first", inplace=True)
        df.set_index("utc_date_time", inplace=True)
        df["speed"] = np.sqrt(df["ref_veln"] ** 2 + df["ref_vele"] ** 2)
        df["yaw"] = df["heading"]
        df["label"] = "1"
        return df

    def check_file_type(self) -> tuple[int, int]:
        skiprows = 0
        self._is_pos320 = False
        with open(
            self.point, "r", encoding="utf-8", errors="ignore"  # pyright: ignore
        ) as f:
            for line in f:
                skiprows += 1
                if "Roll         Pitch       Heading" in line:
                    self._is_pos320 = True
                    length = len(line.split())
                    return skiprows, length
                elif "Pitch          Roll       Azimuth" in line:
                    self._is_pos320 = True
                    length = len(line.split())
                    return skiprows + 1, length
        return 0, 0

    def _handle_nmea(self, file_path, error_dict, is_ttff, callback, start_flag=False):
        _NMEABase.reset_stats()

        # 读取必备句子配置（必须在 _check_rmc_first 之前，避免 NMEAHeader 被变异）
        required_json = Path(__file__).parents[2] / "settings.json"
        if required_json.exists():
            with open(required_json, "r", encoding="utf-8") as f:
                required_sentence = set(json.load(f).get("required_sentence", []))
        else:
            required_sentence = {
                NMEAHeaderByte.RMC_BYTE.decode(),
                NMEAHeaderByte.GGA_BYTE.decode(),
                # NMEAHeaderByte.VTG_BYTE.decode(),
                # NMEAHeaderByte.GLL_BYTE.decode(),
            }

        # 确定主要处理的数据类型
        main_type = "rmc" if self._check_rmc_first(file_path) else "gga"

        # 设置处理标志
        main_flag = False
        gsa_flag = False
        gsv_flag = False

        # 初始化临时字典
        gsv_cn0_temp_dict: dict = init_temp_gsv()
        gsa_temp_dict: defaultdict[str, float] = defaultdict(float)

        main_utc_time = ""
        self.init_data()
        prev_total_failed = 0
        epoch_missing = required_sentence.copy()

        with open(file_path, "rb") as f:
            for line in f:
                if self.stop_event and self.stop_event.is_set():
                    break

                if line.startswith(b"[LOGGA,"):
                    continue

                line_upper = line.upper()
                update_error_dict(line_upper, error_dict, self.error_list)

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
                        _NMEABase.counting = True

                if start_flag:
                    # 处理主要类型数据（RMC或GGA）
                    if nmea_flag:
                        if main_flag:
                            if gsv_flag:
                                gsv_cn0_temp_dict = self._handle_gsv(
                                    gsv_cn0_temp_dict, main_utc_time
                                )

                            if gsa_flag:
                                self._handle_gsa(gsa_temp_dict)

                            # 记录前一历元的checksum fail次数
                            fail_count = _NMEABase.total_failed - prev_total_failed
                            self.position_dict["checksum"][-1] = fail_count
                            prev_total_failed = _NMEABase.total_failed

                            # 累加前一历元的NMEA缺失句子数
                            _NMEABase.total_missing += len(epoch_missing)

                        self.init_data(True)
                        # 新历元从全集开始，移除当前首句
                        epoch_missing = required_sentence.copy()
                        epoch_missing.discard(
                            NMEAHeaderByte.RMC_BYTE.decode()
                            if main_type == "rmc"
                            else NMEAHeaderByte.GGA_BYTE.decode()
                        )

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
                            self.position_dict["alt"][-1] = parser.alt
                            self.position_dict["sep"][-1] = parser.sep
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
                        gsv_flag = True

                    # 处理另一个类型的数据（如果是RMC则处理GGA，反之亦然）
                    elif (
                        NMEAHeaderByte.GGA_BYTE in line
                        if main_type == "rmc"
                        else NMEAHeaderByte.RMC_BYTE in line
                    ):
                        err_code, decode_line = utils.decode_line(line)
                        if main_type == "rmc":  # 当前主要类型是RMC，处理GGA数据
                            parser = GGAParser(decode_line, error_code=err_code)
                            epoch_missing.discard(NMEAHeaderByte.GGA_BYTE.decode())
                            self.position_dict["gga_time"][-1] = parser.utc_time
                            self.position_dict["label"][-1] = parser.fix_label
                            self.position_dict["satellites"][-1] = parser.satellites
                            self.position_dict["lat"][-1] = parser.lat
                            self.position_dict["lng"][-1] = parser.lng
                            self.position_dict["alt"][-1] = parser.alt
                            self.position_dict["sep"][-1] = parser.sep
                            self.position_dict["hgt"][-1] = parser.hgt
                            self.position_dict["delay"][-1] = parser.delay
                        else:  # 当前主要类型是GGA，处理RMC数据
                            parser = RMCParser(decode_line, error_code=err_code)
                            epoch_missing.discard(NMEAHeaderByte.RMC_BYTE.decode())
                            self.position_dict["utc_date_time"][
                                -1
                            ] = parser.utc_date_time
                            self.position_dict["speed"][-1] = parser.speed
                            self.position_dict["yaw"][-1] = parser.yaw

                    # 处理GSA数据
                    elif NMEAHeaderByte.GSA_BYTE in line:
                        err_code, decode_line = utils.decode_line(line)
                        gsa = GSAParser(decode_line, error_code=err_code)
                        if gsa.sys_id and gsa.sys_id in gsa_sys_id:
                            key = gsa_sys_id[gsa.sys_id]
                            gsa_temp_dict[key] += gsa.sat_count

                        if not gsa_flag:
                            self.position_dict["pdop"][-1] = gsa.pdop
                            self.position_dict["hdop"][-1] = gsa.hdop
                            self.position_dict["vdop"][-1] = gsa.vdop
                            gsa_flag = True

                    # elif NMEAHeaderByte.VTG_BYTE in line:
                    #     err_code, decode_line = utils.decode_line(line)
                    #     vtg = VTGParser(decode_line, error_code=err_code)
                    #     self.position_dict["cog"][-1] = vtg.cog
                    #     self.position_dict["knot"][-1] = vtg.knot
                    #     self.position_dict["kmph"][-1] = vtg.kmph
                    # 记录VTG/GLL句子出现过（NMEA完整性校验）
                    elif NMEAHeaderByte.VTG_BYTE in line:
                        epoch_missing.discard(NMEAHeaderByte.VTG_BYTE.decode())
                    elif NMEAHeaderByte.GLL_BYTE in line:
                        epoch_missing.discard(NMEAHeaderByte.GLL_BYTE.decode())
                    # 处理GSV数据
                    elif NMEAHeaderByte.GSV_BYTE in line and gsv_flag:
                        self._handle_gsv_dict(gsv_cn0_temp_dict, line)
                    elif NMEAHeaderByte.PCAS50_BYTE in line:
                        err_code, decode_line = utils.decode_line(line)
                        parser = PCAS50Parser(decode_line, error_code=err_code)
                        self.position_dict["pitch"][-1] = parser.pitch
                        self.position_dict["roll"][-1] = parser.roll
                        self.position_dict["heading"][-1] = parser.heading
                    elif NMEAHeaderByte.PQSOL_BYTE in line:
                        err_code, decode_line = utils.decode_line(line)
                        parser = PQSOLParser(decode_line, error_code=err_code)
                        self.position_dict["pitch"][-1] = parser.pitch
                        self.position_dict["roll"][-1] = parser.roll
                        self.position_dict["heading"][-1] = parser.heading
                    elif NMEAHeaderByte.PQTMDRPVA_BYTE in line:
                        err_code, decode_line = utils.decode_line(line)
                        parser = PQTMDRPVAParser(decode_line, error_code=err_code)
                        self.position_dict["pitch"][-1] = parser.pitch
                        self.position_dict["roll"][-1] = parser.roll
                        self.position_dict["heading"][-1] = parser.heading
                    elif NMEAHeaderByte.PQTMTAR_BYTE in line:
                        err_code, decode_line = utils.decode_line(line)
                        parser = PQTMTARParser(decode_line, error_code=err_code)
                        self.position_dict["h_status"][-1] = parser.status
                        self.position_dict["pitch"][-1] = parser.pitch
                        self.position_dict["roll"][-1] = parser.roll
                        self.position_dict["heading"][-1] = parser.heading
                    elif NMEAHeaderByte.PQTMVEHATT_BYTE in line:
                        err_code, decode_line = utils.decode_line(line)
                        parser = PQTMVEHATTParser(decode_line, error_code=err_code)
                        self.position_dict["pitch"][-1] = parser.pitch
                        self.position_dict["roll"][-1] = parser.roll
                        self.position_dict["heading"][-1] = parser.heading
                    elif NMEAHeaderByte.PSTMDRPVA_BYTE in line:
                        err_code, decode_line = utils.decode_line(line)
                        parser = PSTMDRPVAParser(decode_line, error_code=err_code)
                        self.position_dict["pitch"][-1] = parser.pitch
                        self.position_dict["roll"][-1] = parser.roll
                        self.position_dict["heading"][-1] = parser.heading
                    elif NMEAHeaderByte.HEADINGA_BYTE in line:
                        err_code, decode_line = utils.decode_line(line)
                        parser = HEADINGAParser(decode_line)
                        self.position_dict["heading"][-1] = parser.heading
                        self.position_dict["pitch"][-1] = parser.pitch
                    elif self.is_moving and NMEAHeaderByte.PQTMVEL_BYTE in line:
                        err_code, decode_line = utils.decode_line(line)
                        parser = PQTMVELParser(decode_line, error_code=err_code)
                        self.position_dict["p_veln"][-1] = parser.vel_n
                        self.position_dict["p_vele"][-1] = parser.vel_e
                        self.position_dict["p_veld"][-1] = parser.vel_d
                        self.position_dict["p_grdspd"][-1] = parser.grdspd
                        self.position_dict["p_spd"][-1] = parser.spd
                        self.position_dict["p_heading"][-1] = parser.heading
                        self.position_dict["p_grdspdacc"][-1] = parser.grdspdacc
                        self.position_dict["p_spdacc"][-1] = parser.spdacc
                        self.position_dict["p_headingacc"][-1] = parser.headingacc

        # 记录最后一个历元的checksum fail次数
        if self.position_dict["checksum"]:
            self.position_dict["checksum"][-1] = (
                _NMEABase.total_failed - prev_total_failed
            )
        # 累加最后一个历元的NMEA缺失句子数
        # _NMEABase.total_missing += len(epoch_missing)
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

    def _handle_gsa(self, gsa_temp_dict):
        for sys, count in gsa_temp_dict.items():
            key = f"{sys}_used"
            self.position_dict[key][-1] = count

        gsa_temp_dict.clear()

    def _handle_gsv_dict(self, gsv_cn0_temp_dict, line):
        err_code, decode_line = utils.decode_line(line)
        gsv = GSVParser(decode_line, error_code=err_code)
        sys_label, freq_label, cn0_list = gsv.decode_gsv(self.elev, self.threshold)
        if sys_label in sys_label_list and cn0_list:
            gsv_cn0_temp_dict[sys_label][freq_label] += cn0_list

    def _handle_dataframe(self, file, error_dict, log_info="", write_file: bool = True):
        if error_dict:
            log_info = f"ERROR统计: <br>{error_dict}<br><br>" + log_info

        if not self.position_dict["utc_date_time"]:
            return None, 0, 0, 1, 1, log_info

        df = pd.DataFrame(self.position_dict)
        df.drop(df.tail(1).index, inplace=True)  # 剔除最后一行数据

        # 转成 DataFrame 后立即释放 position_dict，避免其数据驻留到下一个文件才被 init_data 覆盖
        self.position_dict.clear()

        if self.scenes and write_file:
            # 仅初始化 df_datas[file]
            # self.df_datas.setdefault(file, {"original": df})
            self.df_datas.setdefault(file, {})

        # 计算总卫星数
        df["total_svs"] = df[
            [f"{sys}_{freq}_cnt" for sys, freq in sat_freq_combinations]
        ].sum(axis=1, min_count=1)

        # 计算总CN0
        df["total_cn0"] = df[
            [f"{sys}_{freq}_sum" for sys, freq in sat_freq_combinations]
        ].sum(axis=1, min_count=1)

        # 计算平均CN0
        df["avg_cn0"] = (df["total_cn0"] / df["total_svs"]).round(2)

        if write_file and self.result_path:
            write_to_file(
                df,
                self.data_path,
                f"{file[:-4]}{File.ORIGINAL_FILE_EXT}",
                False,
            )

        fix_total = df.shape[0]

        df, freq, log_info, first_valid_index, _ = format_pd(
            df,
            log_info=log_info,
            label="rmc",
            log_path=os.path.join(self.filepath, "report"),
            file=file,
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

        # TopN CN0 平均值
        all_cn0 = np.concatenate(list(cn0_arrays.values()))
        all_cn0 = all_cn0[~np.isnan(all_cn0)]
        if all_cn0.size >= self.top_n:
            top_cn0 = np.sort(all_cn0)[-self.top_n :]
        else:
            top_cn0 = all_cn0
        self.position_dict["top_cn0"][-1] = (
            round(top_cn0.mean(), 1) if top_cn0.size > 0 else np.nan
        )

        # for freq in freq_list:
        #     total_count = 0
        #     for sat_sys in sys_list:
        #         key = f"{sat_sys}_{freq}"
        #         if key in cn0_arrays:
        #             total_count += cn0_arrays[key][cn0_arrays[key] > threshold].size

        #     self.position_dict[f"{freq}_count"][-1] = total_count

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

        _index = self._get_filtered_index()
        _index, result_dict = _filter_empty_sections(_index, result_dict)
        df_result = pd.DataFrame(result_dict, index=_index)

        for col in df_result.columns:
            df_result[col] = df_result[col].fillna("-")

        if not df_result.empty and result_path:
            sheet_name = "All" if begin_time is None else point
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
                sheet_name=sheet_name,
                is_long_test=self.is_long_test if begin_time is None else False,
                long_test_data=self.long_test_data if begin_time is None else None,
            )
            report.gen_precision_report()

    @staticmethod
    def _extract_cep(desc: pd.Series, decimal: int = 4) -> list:
        """从 describe Series 提取 [50%, 68%, 95%, 99.7%, 99%, max]"""
        return [round(desc[k], decimal) for k in cep_keys] + [desc["max"]]

    def _gen_result(
        self,
        result_dict,
        file,
        df,
        freq,
        df_expect,
        df_valid,
        checksum_fail=np.nan,
        nmea_missing=np.nan,
        collect_long: bool = True,
    ):
        mask = df["label"] != "0"
        if self.is_moving:
            df_speed = df[mask]["speed_delta"]
            df_cog = df[mask]["yaw_delta"]
        else:
            df_speed = df["speed_delta"]
            df_cog = df["yaw_delta"]

        df_hgt_delta = df[mask]["hgt_delta"]

        df_distance: pd.Series = df[mask]["distance"]
        df_distance_3d: pd.Series = df[mask]["distance_3d"]

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
            "df_cog": df_cog,
            "df_satellites": df["satellites"],
            "df_visibled_satellites": df["total_svs"],
            "df_avg_cn0": df["avg_cn0"],
            "df_top_cn0": df["top_cn0"],
            "df_pitch_delta": df["pitch_delta"],
            "df_roll_delta": df["roll_delta"],
            "df_heading_delta": df["heading_delta"],
        }

        if not self.is_moving:
            stats_to_calculate["df_rms_pitch_delta"] = df["rms_pitch_delta"]
            stats_to_calculate["df_rms_roll_delta"] = df["rms_roll_delta"]
            stats_to_calculate["df_rms_heading_delta"] = df["rms_heading_delta"]
        else:
            stats_to_calculate["df_heading_err"] = df["heading_err"]
            stats_to_calculate["df_2d_err"] = df["2d_err"]
            stats_to_calculate["df_3d_err"] = df["3d_err"]
            stats_to_calculate["df_veln_delta"] = df["veln_delta"]
            stats_to_calculate["df_vele_delta"] = df["vele_delta"]
            stats_to_calculate["df_veld_delta"] = df["veld_delta"]

        for label in "01234567":
            stats_to_calculate[f"df_{label}"] = df[df["label"] == label]["distance"]
            if label != "0":
                stats_to_calculate[f"df_{label}_hgt_delta"] = df[df["label"] == label][
                    "hgt_delta"
                ]

        for key, data in stats_to_calculate.items():
            stats_describe[key] = data.describe(percentiles=percentiles).round(4)

        df_dop = df[mask][["pdop", "hdop", "vdop"]]
        fixed_avalible = stats_to_calculate["df_4"][
            stats_to_calculate["df_4"] < self.fixed_threshold
        ].shape[0]
        fixed_available_rate = utils.calc_value(
            stats_to_calculate["df_4"].shape[0], fixed_avalible
        )

        if not self.is_moving:
            if freq == 15:
                df_misseconds = df["mis_seconds"].dropna().round(3)
                # 统计非正常间隔(非1.005/0.93)的误秒个数
                mis_seconds = ((df_misseconds != 1.005) & (df_misseconds != 0.93)).sum()
            else:
                df_misseconds = df["mis_seconds"].dropna()
                # 统计 mis-seconds 含小数个数
                mis_seconds = (df_misseconds % 1.0 != 0).sum()
        else:
            mis_seconds = np.nan

        heading_0_size = df[df["h_status"] == "0"].shape[0]
        heading_4_size = df[df["h_status"] == "4"].shape[0]
        heading_5_size = df[df["h_status"] == "5"].shape[0]

        result_dict[file] = [
            _format_date_time(df.index[0]),
            _format_date_time(df.index[-1]),
            round((df.index[-1] - df.index[0]).total_seconds() / 3600, 1),
            f"{freq}HZ",
            round(df_dop["pdop"].mean(), Default.KEEP_DECIMAL_DIGIT),
            round(df_dop["hdop"].mean(), Default.KEEP_DECIMAL_DIGIT),
            round(df_dop["vdop"].mean(), Default.KEEP_DECIMAL_DIGIT),
            stats_describe["df_satellites"]["mean"].round(1),
            *self._extract_cep(stats_describe["df_satellites"]),
            *self._extract_cep(stats_describe["df_visibled_satellites"]),
            "",
            stats_describe["df_avg_cn0"]["mean"].round(1),
            *self._extract_cep(stats_describe["df_avg_cn0"], decimal=1),
            *self._extract_cep(stats_describe["df_top_cn0"], decimal=1),
            f"{cn0_values['gps_l1']}+{cn0_values['gps_l2']}+{cn0_values['gps_l5']}",
            f"{cn0_values['bds_b1i']}+{cn0_values['bds_b2a']}+{cn0_values['bds_b2b']}",
            f"{cn0_values['bds_b1c']}+{cn0_values['bds_b2i']}+{cn0_values['bds_b3i']}",
            f"{cn0_values['gal_e1']}+{cn0_values['gal_e5a']}+{cn0_values['gal_e5b']}+{cn0_values['gal_e6']}",
            f"{cn0_values['glo_g1']}+{cn0_values['glo_g2']}",
            f"{cn0_values['qzs_q1']}+{cn0_values['qzs_q2']}+{cn0_values['qzs_q5']}",
            f"{cn0_values['irn_i5']}",
            f"{utils.calc_value(df_expect, df_valid)}%({df_valid})",  # 实际定位率
            f"{utils.calc_value(df_expect, stats_to_calculate['df_0'].shape[0])}%({stats_to_calculate['df_0'].shape[0]})",  # 0-未定位比率
            f"{utils.calc_value(df_expect, stats_to_calculate['df_1'].shape[0])}%({stats_to_calculate['df_1'].shape[0]})",  # 1-单点比率
            f"{utils.calc_value(df_expect, stats_to_calculate['df_2'].shape[0])}%({stats_to_calculate['df_2'].shape[0]})",  # 2-差分比率
            f"{utils.calc_value(df_expect, stats_to_calculate['df_3'].shape[0])}%({stats_to_calculate['df_3'].shape[0]})",  # 3-单点比率
            f"{utils.calc_value(df_expect, stats_to_calculate['df_4'].shape[0])}%({stats_to_calculate['df_4'].shape[0]})",  # 4-固定解比率
            f"{utils.calc_value(df_expect, stats_to_calculate['df_5'].shape[0])}%({stats_to_calculate['df_5'].shape[0]})",  # 5-浮点解比率
            f"{utils.calc_value(df_expect, stats_to_calculate['df_6'].shape[0])}%({stats_to_calculate['df_6'].shape[0]})",  # 6-单点比率
            f"{utils.calc_value(df_expect, stats_to_calculate['df_7'].shape[0])}%({stats_to_calculate['df_7'].shape[0]})",  # 7-单点比率
            (
                fixed_available_rate
                if np.isnan(fixed_available_rate)
                else f"{fixed_available_rate}%"
            ),  # 4-固定解可用率
            f"{utils.calc_value(df_expect, heading_0_size)}%({heading_0_size})",  # "0-Heading rate"
            f"{utils.calc_value(df_expect, heading_4_size)}%({heading_4_size})",  # "4-Heading rate"
            f"{utils.calc_value(df_expect, heading_5_size)}%({heading_5_size})",  # "5-Heading rate"
            mis_seconds,  # 误秒数
            nmea_missing,  # Integrity of NMEA
            checksum_fail,
            "",
            file,
            utils.calc_rms(df_distance),
            stats_describe["df_distance"]["std"],  # 1σ
            *self._extract_cep(stats_describe["df_distance"]),
            utils.calc_rms(df_hgt_delta),
            stats_describe["df_hgt_delta"]["std"],  # 1σ
            *self._extract_cep(stats_describe["df_hgt_delta"]),
            utils.calc_rms(stats_to_calculate["df_speed"]),
            *self._extract_cep(stats_describe["df_speed"]),
            utils.calc_rms(stats_to_calculate["df_cog"]),
            *self._extract_cep(stats_describe["df_cog"]),
        ]

        if self.is_moving:
            # 如果HeadingAcc–HeadingErr>0, 则符合要求，计算符合要求的点占所有点的多少
            per_heading = utils.calc_value(
                stats_to_calculate["df_heading_err"].shape[0],
                (df["p_headingacc"] > df["heading_err"]).sum(),
            )

            # 如果 GrdSpdAcc – 2DErr＞0, 则符合要求，计算符合要求的点占所有点的多少
            per_2d = utils.calc_value(
                stats_to_calculate["df_2d_err"].shape[0],
                (df["p_grdspdacc"] > df["2d_err"]).sum(),
            )

            # 如果SpdAcc - 3DErr＞0, 则符合要求，计算符合要求的点占所有点的多少
            per_3d = utils.calc_value(
                stats_to_calculate["df_3d_err"].shape[0],
                (df["p_spdacc"] > df["3d_err"]).sum(),
            )

            result_dict[file].extend(
                [
                    "",
                    file,
                    utils.calc_rms(stats_to_calculate["df_heading_err"]),
                    stats_describe["df_heading_err"]["std"],  # 1σ
                    *self._extract_cep(stats_describe["df_heading_err"]),
                    (f"{per_heading}%" if not np.isnan(per_heading) else per_heading),
                    utils.calc_rms(stats_to_calculate["df_2d_err"]),
                    stats_describe["df_2d_err"]["std"],  # 1σ
                    *self._extract_cep(stats_describe["df_2d_err"]),
                    (f"{per_2d}%" if not np.isnan(per_2d) else per_2d),
                    utils.calc_rms(stats_to_calculate["df_3d_err"]),
                    stats_describe["df_3d_err"]["std"],  # 1σ
                    *self._extract_cep(stats_describe["df_3d_err"]),
                    (f"{per_3d}%" if not np.isnan(per_3d) else per_3d),
                    *self._extract_cep(stats_describe["df_veln_delta"]),
                    *self._extract_cep(stats_describe["df_vele_delta"]),
                    *self._extract_cep(stats_describe["df_veld_delta"]),
                ]
            )
        result_dict[file].extend(
            [
                "",
                file,
                utils.calc_rms(stats_to_calculate["df_roll_delta"]),
                stats_describe["df_roll_delta"]["std"],  # 1σ
                *self._extract_cep(stats_describe["df_roll_delta"]),
                utils.calc_rms(stats_to_calculate["df_pitch_delta"]),
                stats_describe["df_pitch_delta"]["std"],  # 1σ
                *self._extract_cep(stats_describe["df_pitch_delta"]),
                utils.calc_rms(stats_to_calculate["df_heading_delta"]),
                stats_describe["df_heading_delta"]["std"],  # 1σ
                *self._extract_cep(stats_describe["df_heading_delta"]),
            ]
        )

        if not self.is_moving:
            result_dict[file].extend(
                [
                    utils.calc_rms(stats_to_calculate["df_rms_roll_delta"]),
                    stats_describe["df_rms_roll_delta"]["std"],  # 1σ
                    *self._extract_cep(stats_describe["df_rms_roll_delta"]),
                    utils.calc_rms(stats_to_calculate["df_rms_pitch_delta"]),
                    stats_describe["df_rms_pitch_delta"]["std"],  # 1σ
                    *self._extract_cep(stats_describe["df_rms_pitch_delta"]),
                    utils.calc_rms(stats_to_calculate["df_rms_heading_delta"]),
                    stats_describe["df_rms_heading_delta"]["std"],  # 1σ
                    *self._extract_cep(stats_describe["df_rms_heading_delta"]),
                ]
            )

        result_dict[file].extend(
            [
                "",
                file,
                utils.calc_rms(stats_to_calculate["df_1"]),
                *self._extract_cep(stats_describe["df_1"]),
                utils.calc_rms(stats_to_calculate["df_1_hgt_delta"]),
                *self._extract_cep(stats_describe["df_1_hgt_delta"]),
                "",
                file,
                utils.calc_rms(stats_to_calculate["df_2"]),
                *self._extract_cep(stats_describe["df_2"]),
                utils.calc_rms(stats_to_calculate["df_2_hgt_delta"]),
                *self._extract_cep(stats_describe["df_2_hgt_delta"]),
                "",
                file,
                utils.calc_rms(stats_to_calculate["df_4"]),
                *self._extract_cep(stats_describe["df_4"]),
                utils.calc_rms(stats_to_calculate["df_4_hgt_delta"]),
                *self._extract_cep(stats_describe["df_4_hgt_delta"]),
                "",
                file,
                utils.calc_rms(stats_to_calculate["df_5"]),
                *self._extract_cep(stats_describe["df_5"]),
                utils.calc_rms(stats_to_calculate["df_5_hgt_delta"]),
                *self._extract_cep(stats_describe["df_5_hgt_delta"]),
                "",
                file,
                utils.calc_rms(stats_to_calculate["df_6"]),
                *self._extract_cep(stats_describe["df_6"]),
                utils.calc_rms(stats_to_calculate["df_6_hgt_delta"]),
                *self._extract_cep(stats_describe["df_6_hgt_delta"]),
            ]
        )

        if self.is_long_test and collect_long:
            # 直接生成 long_time_report.html 模板 Report-1 的一行（51 列），避免二次解析
            def _lt_fmt(value):
                """NaN/None -> '-'; 数值 round 4 位。"""
                if value is None:
                    return "-"
                try:
                    if pd.isna(value):
                        return "-"
                except (TypeError, ValueError):
                    pass
                if isinstance(value, float):
                    return str(round(value, 4))
                return str(value)

            def get_loc_frozen(loc: pd.DataFrame) -> str:
                """检查经纬度是否冻结（连续2h经纬度都无变化）。"""
                same = loc.eq(loc.shift()).all(axis=1).to_numpy()
                starts = np.flatnonzero(~same)
                ends = np.append(starts[1:] - 1, len(df) - 1)
                timestamps = pd.DatetimeIndex(df.index)
                durations = timestamps[ends] - timestamps[starts]

                return "Fail" if (durations >= pd.Timedelta(hours=2)).any() else "Pass"

            cn0_order = [
                "gps_l1",
                "gps_l5",
                "gps_l2",  # GP_1, GP_8, GP_6
                "glo_g1",
                "glo_g2",  # GL_1, GL_3
                "gal_e1",
                "gal_e5a",
                "gal_e5b",
                "gal_e6",  # GA_7, GA_1, GA_2, GA_5
                "bds_b1i",
                "bds_b1c",
                "bds_b2i",
                "bds_b2a",
                "bds_b2b",
                "bds_b3i",  # GB_1, GB_3, GB_B, GB_5, GB_6, GB_8
                "qzs_q1",
                "qzs_q5",  # GQ_1, GQ_8
                "irn_i5",  # GI_1
            ]
            sat_order = ["gps", "glo", "gal", "bds", "qzs", "irn"]
            # CEP100 取 Max
            cep_values = ["50%", "68%", "95%", "99%", "max"]
            # 卫星数（保留1位小数，NaN显示"-"）、CN0（0置"-"）
            satellites = [
                (
                    _lt_fmt(round(float(df[f"{s}_used"].mean()), 1))
                    if f"{s}_used" in df.columns
                    else "-"
                )
                for s in sat_order
            ]
            cn0 = [
                "-" if (v := cn0_values.get(k, 0.0)) == 0 else _lt_fmt(v)
                for k in cn0_order
            ]
            # RTK Fixed Rate (0~6) 取百分比
            rates = [
                _lt_fmt(
                    utils.calc_value(df_valid, stats_to_calculate[f"df_{i}"].shape[0])
                )
                for i in range(7)
            ]
            # 发生过未定位(0-Unfixed)即视为失锁
            lose_fix = "Fail" if stats_to_calculate["df_0"].shape[0] > 0 else "Pass"
            # 经纬度不更新：出现连续2h经度和纬度都无变化则 Fail
            loc_frozen = get_loc_frozen(df[["lat", "lng"]])

            # Test Date: 起始时间-结束时间
            test_date = (
                f"{pd.Timestamp(df.index[0]):%Y%m%d %H:%M:%S}"
                f"-{pd.Timestamp(df.index[-1]):%Y%m%d %H:%M:%S}"
            )
            self.long_test_data[file] = [
                test_date,  # Test Date
                _lt_fmt(file),  # Module
                _lt_fmt(df_valid),  # Position count
                _lt_fmt(checksum_fail),  # Checksum Error
                lose_fix,  # Lose fix or not
                _lt_fmt(nmea_missing),  # Missing NMEA
                _lt_fmt(mis_seconds),  # Mis-seconds
                *[_lt_fmt(stats_describe["df_distance"][k]) for k in cep_values],
                *[_lt_fmt(stats_describe["df_hgt_delta"][k]) for k in cep_values],
                *satellites,  # 卫星数×6
                *cn0,  # CN0 × 18
                *rates,  # RTK Fixed Rate×7
                _lt_fmt(fixed_available_rate),  # 固定解可用率
                loc_frozen,  # 经纬度不更新
                "",  # Remark
            ]
            if "remark" not in self.long_test_data:
                self.long_test_data["remark"] = self.remark

    def _get_filtered_index(self):
        """构建 index 列表，动态模式移除 "From RMS" 条目及空分隔符，同时去除 " From AVG" 后缀。"""
        _index = [x.format(self.top_n) if "{}" in x else x for x in position_index_list]
        if self.is_moving:
            _index = [
                x
                for i, x in enumerate(_index)
                if "From RMS" not in x
                and not (
                    x == "" and i + 1 < len(_index) and "From RMS" in _index[i + 1]
                )
            ]
            _index = [x.replace(" From AVG", "") for x in _index]
        else:
            try:
                pq_idx = _index.index("PQTMVEL Result:")
                start = pq_idx - 1  # include preceding blank
                end = pq_idx + 1
                while end < len(_index) and _index[end] != "":
                    end += 1
                _index = _index[:start] + _index[end:]  # keep trailing blank
            except ValueError:
                pass
        return _index

    def _gen_nan_result(self, result_dict, file):
        result_dict[file] = [np.nan] * len(self._get_filtered_index())

    def gen_split_report(self):
        for scene in self.scenes:
            begin_time = pd.Timestamp(scene["begin_time"])
            end_time = pd.Timestamp(scene["end_time"])
            result_dict = {}
            result_path: Path = Path(self.result_path) / ".." / scene["name"]
            data_path: Path = result_path / "data"
            data_path.mkdir(parents=True, exist_ok=True)

            for file, data in self.df_datas.items():
                if "calc" not in data:
                    continue

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
                    result_dict,
                    file[:-4],
                    df_scene,
                    freq,
                    df_expect,
                    df_valid,
                    collect_long=False,
                )

            self._gen_report(
                result_path,  # type: ignore
                data_path,  # type: ignore
                result_dict,
                scene["name"],
                begin_time=begin_time,
                end_time=end_time,
            )


try:
    from PySide6.QtCore import QThread, Signal

    class PositionUIProcessor(QThread):
        log_signal = Signal(str)
        end_signal = Signal()

        def __init__(self):
            QThread.__init__(self)
            self.processor = PositionProcessor()

        def check_file(self):
            if isinstance(self.processor.point, str) and not os.path.exists(
                self.processor.point
            ):
                self.log_signal.emit(f"<font color='red'>参考文件不存在</font>")
                return False

            check_list = [
                (
                    check_file.text()  # type: ignore[union-attr]
                    if callable(getattr(check_file, "text", None))
                    else check_file
                )
                for check_file in self.processor.check_list
            ]

            for file in check_list:
                if not os.path.exists(os.path.join(self.processor.filepath, file)):
                    self.log_signal.emit(f"<font color='red'>{file}文件不存在</font>")
                    return False

            return True

        def run(self):
            if not self.check_file():
                self.end_signal.emit()
                return

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

except ImportError:
    pass


class PositionWebProcessor:
    def __init__(self):
        self.processor = PositionProcessor()
        self.processor.callback = print

    def run(self):
        self.processor.create()

        if self.processor.is_moving:
            self.processor.process_moving_data(
                is_ttff=self.processor.is_ttff,
            )
        else:
            self.processor.process_static_data(
                std_mode=self.processor.std_mode,
                is_ttff=self.processor.is_ttff,
            )
