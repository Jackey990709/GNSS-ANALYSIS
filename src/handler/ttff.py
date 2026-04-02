import os
from datetime import datetime

from PySide6.QtCore import QThread, Signal
from typing import Callable

import numpy as np
from openpyxl.workbook import Workbook

from src import NMEAHeader
from src.libs.nmea.gga import GGAParser
from src.util import utils
from src.util.const import ExcelCellLabel
from src.util.const import TTFFSignal as ts

from src.libs.processor.excel import ExcelProcessor
from src.libs.processor.data import TTFFDataProcessor


class SheetName:
    TTFF_RESULT: str = "TTFF_result"
    TTFF_RESULT_DEBUG: str = "TTFF_result_debug"
    RTK_RESULT: str = "RTK_result"
    RTK_RESULT_DEBUG: str = "RTK_result_debug"


class PositionAttr:
    def __init__(self):
        self.folder_path: str = ""
        self.result_path: str = ""
        self.check_list: list[str] = []
        self.prefix_list: list[str] = []
        self.label: str = NMEAHeader.TTFF_P
        self.callback: Callable = print
        self.rtk_label: str = "4"

        self.ttff_handler_dict: dict[str, dict] = {}

    def create(self):
        if not self.folder_path:
            return

        self.result_path = os.path.join(self.folder_path, "ttff")
        os.makedirs(self.result_path, exist_ok=True)


class TTFFProcessor(PositionAttr):
    def __init__(self):
        super().__init__()
        self.excel_manager = ExcelProcessor()

    def process_data(self, last_ttff_include=False):
        for file in self.check_list:
            self.generate_list(file)

        col = 2
        self._create_excel_report(
            ts.s1, col, self._get_ttff_label(), "0", last_ttff_include
        )

        self._create_excel_report(
            ts.s2, col, self._get_rtk_label(), self.rtk_label, last_ttff_include
        )

    def _get_ttff_label(self):
        return [
            ExcelCellLabel.LABEL_DEVICE,
            ExcelCellLabel.LABEL_GT_60,
            ExcelCellLabel.LABEL_50_60,
            ExcelCellLabel.LABEL_40_50,
            ExcelCellLabel.LABEL_30_40,
            ExcelCellLabel.LABEL_20_30,
            ExcelCellLabel.LABEL_10_20,
            ExcelCellLabel.LABEL_3_10,
            ExcelCellLabel.LABEL_0_3,
            ExcelCellLabel.LABEL_UNFIX_TIMES,
            ExcelCellLabel.LABEL_FIX_UNFIX_TIMES,
            ExcelCellLabel.LABEL_FIX_UTC_NULL,
            ExcelCellLabel.LABEL_TOTAL_TIMES,
            ExcelCellLabel.LABEL_AVERAGE,
            ExcelCellLabel.LABEL_FIX_SUCCESS_RATE,
        ]

    def _get_rtk_label(self):
        return [
            ExcelCellLabel.LABEL_DEVICE,
            ExcelCellLabel.LABEL_GT_120,
            ExcelCellLabel.LABEL_115_120,
            ExcelCellLabel.LABEL_110_115,
            ExcelCellLabel.LABEL_105_110,
            ExcelCellLabel.LABEL_100_105,
            ExcelCellLabel.LABEL_95_100,
            ExcelCellLabel.LABEL_90_95,
            ExcelCellLabel.LABEL_85_90,
            ExcelCellLabel.LABEL_80_85,
            ExcelCellLabel.LABEL_75_80,
            ExcelCellLabel.LABEL_70_75,
            ExcelCellLabel.LABEL_65_70,
            ExcelCellLabel.LABEL_60_65,
            ExcelCellLabel.LABEL_50_60,
            ExcelCellLabel.LABEL_50_55,
            ExcelCellLabel.LABEL_45_50,
            ExcelCellLabel.LABEL_40_45,
            ExcelCellLabel.LABEL_35_40,
            ExcelCellLabel.LABEL_30_35,
            ExcelCellLabel.LABEL_25_30,
            ExcelCellLabel.LABEL_20_25,
            ExcelCellLabel.LABEL_15_20,
            ExcelCellLabel.LABEL_10_15,
            ExcelCellLabel.LABEL_3_10,
            ExcelCellLabel.LABEL_0_3,
            ExcelCellLabel.LABEL_CONVERGE_FAIL_TIMES,
            (
                ExcelCellLabel.LABEL_FIX_PPP_TIMES
                if self.rtk_label == "6"
                else ExcelCellLabel.LABEL_FIX_FLOAT_TIMES
            ),
            ExcelCellLabel.LABEL_TOTAL_TIMES,
            ExcelCellLabel.LABEL_CONVERGE_AVERAGE,
            ExcelCellLabel.LABEL_CONVERGE_SUCCESS_RATE,
        ]

    def _create_excel_report(
        self, signal_type, col, labels, rtk_label, last_ttff_include
    ):
        workbook = Workbook()
        ws1 = workbook.active
        ws2 = workbook.create_sheet()

        is_s1 = signal_type == ts.s1

        if not ws1 or not ws2:
            return

        ws1.title = SheetName.TTFF_RESULT_DEBUG if is_s1 else SheetName.RTK_RESULT_DEBUG
        ws2.title = SheetName.TTFF_RESULT if is_s1 else SheetName.RTK_RESULT

        self.handler_data(
            workbook,
            ws1,
            ws2,
            signal_type,
            col,
            labels,
            last_ttff_include=last_ttff_include,
        )

    def generate_list(self, file):
        file_path = os.path.join(self.folder_path, file)
        new_file_name = f"{file[:-4]}_{self.label[:-1].lower()}.txt"

        utc_time_list = []
        prefix_label = ""

        line_list = []
        temp_list = []

        with open(file_path, "rb") as f:
            for line in f:
                err_code, line = utils.decode_line(line)
                line = line.strip()

                if not line:
                    continue

                line_upper = line.upper()

                prefix_label = prefix_label or next(
                    (p for p in self.prefix_list if p in line_upper), ""
                )

                if prefix_label and prefix_label in line_upper:
                    line_list.append(line_upper + "\n")
                    temp_list.append(line_upper + "\n")
                    continue

                if self.label in line:
                    self._process_gga_line(
                        line, err_code, line_list, temp_list, utc_time_list
                    )

        self.write_file(self.result_path, new_file_name, line_list)

        freq = utils.get_freq(utc_time_list, interval=1000)

        self.ttff_handler_dict[file[:-4]] = {
            "value": temp_list,
            "prefix_label": prefix_label,
            "freq": freq,
        }

    def _process_gga_line(
        self, line: str, err_code, line_list: list, temp_list: list, utc_time_list: list
    ):
        gga = GGAParser(line, error_code=err_code)

        utc_time = ""
        if isinstance(gga.utc_time, str):
            utc_time = self.get_utc_date_time(gga.utc_time)
            if utc_time:
                utc_time_list.append(utc_time)

        temp_list.append(f"$GNGGA,{gga.utc_time_str},E,{gga.fix_label},\n")
        line_list.append(line + "\n")

    def handler_data(
        self,
        workbook,
        ws1,
        ws2,
        t_signal,
        col,
        cell_label,
        callback=print,
        last_ttff_include=False,
    ):
        # 初始化数据处理器
        data_processor = TTFFDataProcessor(
            self.ttff_handler_dict, self.rtk_label, self.prefix_list, self.label
        )

        # 写入表头
        self.excel_manager.write_header_labels(ws1, ws2, cell_label)

        value_dict = {}

        for file in sorted(self.ttff_handler_dict):
            # 提取数据
            file_data = data_processor.extract_file_data(
                file, t_signal, last_ttff_include
            )
            if not file_data:
                continue

            # 计算统计信息
            statistics = data_processor.calculate_statistics(
                file_data["values"], t_signal
            )
            statistics.update(
                {
                    "times_fix_unfix": file_data["times_fix_unfix"],
                    "times_fix_float": file_data["times_fix_float"],
                    "times_utc_is_null": file_data["times_utc_is_null"],
                }
            )

            # 写入文件数据
            start_row = 18 if t_signal == ts.s1 else 34
            self.excel_manager.write_file_data(
                ws1,
                ws2,
                file,
                col,
                start_row,
                file_data["values"],
                t_signal,
                file_data["fix_unfix_values"],
                file_data.get("format_values"),
            )

            # 写入统计信息
            self.excel_manager.write_statistics(ws1, ws2, col, statistics, t_signal)

            # 调整列宽
            self.excel_manager.adjust_column_width(ws1, col)
            self.excel_manager.adjust_column_width(ws2, col)

            # 准备返回值
            temp_value_numpy = np.array(file_data["values"])
            temp_value_numpy[temp_value_numpy == -1.0] = np.nan
            value_dict[file] = temp_value_numpy

            col += 1

        # 调整A列宽度
        ws1.column_dimensions["A"].width = 20
        ws2.column_dimensions["A"].width = 16

        # 保存Excel文件
        excel_name = self.excel_manager.get_excel_name(
            t_signal, self.label, self.rtk_label
        )
        self.excel_manager.save_workbook(
            workbook, self.result_path, excel_name, callback
        )

        return value_dict

    def get_utc_date_time(self, utc_time: str) -> str:
        """获取UTC日期时间"""
        try:
            ptime = datetime.strptime(f"010123{utc_time}", "%m%d%y%H%M%S.%f")
            utc_date_time = ptime.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        except ValueError:
            utc_date_time = ""

        return utc_date_time

    def write_file(self, result_path, new_file_name, additional_lines) -> None:
        log_file_path = os.path.join(result_path, new_file_name)
        batch_size = 100
        with open(log_file_path, "w", errors="ignore") as log_file:
            for i in range(0, len(additional_lines), batch_size):
                batch = additional_lines[i : i + batch_size]
                log_file.write("".join(batch))


class TTFFUIProcessor(QThread):
    log_signal = Signal(str)
    end_signal = Signal()

    def __init__(self):
        QThread.__init__(self)
        self.processor = TTFFProcessor()

    def run(self):
        self.processor.create()
        self.processor.callback = self.log_signal.emit

        self.processor.process_data()
        self.end_signal.emit()


class TTFFWebProcessor:
    def __init__(self):
        self.processor = TTFFProcessor()

    def run(self):
        self.processor.create()
        self.processor.callback = print

        self.processor.process_data()
