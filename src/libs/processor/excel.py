import os
from typing import Optional
from openpyxl.styles import PatternFill, Alignment, Side, Border
from openpyxl.utils import get_column_letter
from openpyxl.workbook import Workbook

from src.util.const import ExcelCellLabel
from src.util.const import TTFFSignal as ts


class ExcelName:
    RTK_NAME: str = "%s_rtk"
    TTFF_NAME: str = "%s_ttff"


class ExcelProcessor:
    """TTFF Excel数据写入管理器"""

    def __init__(self):
        # 样式定义
        self.align = Alignment(horizontal="center", vertical="center")
        left, right, top, bottom = [Side(style="thin", color="000000")] * 4
        self.border = Border(left=left, right=right, top=top, bottom=bottom)

    def create_workbook(self) -> Workbook:
        """创建新的Excel工作簿"""
        return Workbook()

    def write_cell(
        self, worksheet, row: int, col: int, value, color: Optional[str] = None
    ):
        """写入单元格数据"""
        cell = worksheet.cell(row, col, value=value)
        cell.alignment = self.align
        cell.border = self.border

        if color:
            cell.fill = PatternFill(fill_type="solid", fgColor=color)

    def write_header_labels(self, worksheet1, worksheet2, cell_labels: list):
        """写入表头标签"""
        for i, label in enumerate(cell_labels, 1):
            self.write_cell(worksheet1, i, 1, label)
            self.write_cell(worksheet2, i, 1, label)

        # 写入标签数量
        self.write_cell(
            worksheet1, len(cell_labels) + 2, 1, ExcelCellLabel.LABEL_NUMBER
        )
        self.write_cell(
            worksheet2, len(cell_labels) + 2, 1, ExcelCellLabel.LABEL_NUMBER
        )

    def write_file_data(
        self,
        worksheet1,
        worksheet2,
        file_name: str,
        col: int,
        start_row: int,
        values: list,
        t_signal,
        fix_unfix_values: list,
        format_values: Optional[list] = None,
    ):
        """写入文件数据

        Args:
            worksheet1: 第一个工作表（写入格式化值）
            worksheet2: 第二个工作表（写入数值）
            file_name: 文件名
            col: 列索引
            start_row: 起始行
            values: 数值列表
            t_signal: 信号类型
            format_values: 格式化值列表（可选，为None时写入values）
        """

        # 写入文件名
        self.write_cell(worksheet1, 1, col, file_name)
        self.write_cell(worksheet1, start_row - 1, col, file_name)
        self.write_cell(worksheet2, 1, col, file_name)
        self.write_cell(worksheet2, start_row - 1, col, file_name)

        display_values = format_values if format_values is not None else values

        # 写入数据值
        row = start_row
        for i, (value, display_value, fix_unfix_value) in enumerate(
            zip(values, display_values, fix_unfix_values), 1
        ):
            if value == -1 or fix_unfix_value > 0:
                self.write_cell(worksheet1, row, col, display_value, "E284A8")
            else:
                self.write_cell(worksheet1, row, col, display_value)

            self.write_cell(worksheet2, row, col, value)
            self.write_cell(worksheet1, row, 1, i)
            self.write_cell(worksheet2, row, 1, i)
            row += 1

    def write_statistics(
        self, worksheet1, worksheet2, col: int, statistics: dict, t_signal
    ):
        """写入统计信息"""
        if t_signal == ts.s1:
            self._write_s1_statistics(worksheet1, worksheet2, col, statistics)
        else:
            self._write_other_statistics(worksheet1, worksheet2, col, statistics)

    def _write_s1_statistics(self, worksheet1, worksheet2, col: int, stats: dict):
        """写入S1信号统计信息"""
        statistics_map = {
            2: stats.get("times_60", 0),
            3: stats.get("times_50_60", 0),
            4: stats.get("times_40_50", 0),
            5: stats.get("times_30_40", 0),
            6: stats.get("times_20_30", 0),
            7: stats.get("times_10_20", 0),
            8: stats.get("times_3_10", 0),
            9: stats.get("times_0_3", 0),
            10: stats.get("times_0", 0),
            11: stats.get("times_fix_unfix", 0),
            12: stats.get("times_utc_is_null", 0),
            13: stats.get("count", 0),
            14: stats.get("average", 0),
            15: stats.get("success_rate", "ERROR"),
        }

        for row, value in statistics_map.items():
            self.write_cell(worksheet1, row, col, value)
            self.write_cell(worksheet2, row, col, value)

    def _write_other_statistics(self, worksheet1, worksheet2, col: int, stats: dict):
        """写入其他信号统计信息"""
        statistics_map = {
            2: stats.get("times_120", 0),
            3: stats.get("times_115_120", 0),
            4: stats.get("times_110_115", 0),
            5: stats.get("times_105_110", 0),
            6: stats.get("times_100_105", 0),
            7: stats.get("times_95_100", 0),
            8: stats.get("times_90_95", 0),
            9: stats.get("times_85_90", 0),
            10: stats.get("times_80_85", 0),
            11: stats.get("times_75_80", 0),
            12: stats.get("times_70_75", 0),
            13: stats.get("times_65_70", 0),
            14: stats.get("times_60_65", 0),
            15: stats.get("times_55_60", 0),
            16: stats.get("times_50_55", 0),
            17: stats.get("times_45_50", 0),
            18: stats.get("times_40_45", 0),
            19: stats.get("times_35_40", 0),
            20: stats.get("times_30_35", 0),
            21: stats.get("times_25_30", 0),
            22: stats.get("times_20_25", 0),
            23: stats.get("times_15_20", 0),
            24: stats.get("times_10_15", 0),
            25: stats.get("times_3_10", 0),
            26: stats.get("times_0_3", 0),
            27: stats.get("times_0", 0),
            28: stats.get("times_fix_float", 0),
            29: stats.get("count", 0),
            30: stats.get("average", 0),
            31: stats.get("success_rate", "ERROR"),
        }

        for row, value in statistics_map.items():
            self.write_cell(worksheet1, row, col, value)
            self.write_cell(worksheet2, row, col, value)

    def adjust_column_width(self, worksheet, col: int, width: int = 24):
        """调整列宽"""
        column_letter = get_column_letter(col)
        worksheet.column_dimensions[column_letter].width = width

    def save_workbook(
        self, workbook: Workbook, result_path: str, excel_name: str, callback=None
    ):
        """保存工作簿"""
        excel_file_path = os.path.join(result_path, excel_name)

        try:
            workbook.save(excel_file_path)
        except PermissionError as e:
            if callback:
                callback(f"文件写入权限错误: {excel_name}")
            raise e
        finally:
            workbook.close()

    def get_excel_name(self, t_signal, label: str, rtk_label: str = "4") -> str:
        """获取Excel文件名"""
        excel_name_prefix = (
            ExcelName.TTFF_NAME if t_signal == ts.s1 else ExcelName.RTK_NAME
        ) % label[:-1]

        return f"{excel_name_prefix}_result.xlsx".lower()
