import json
import os
import io as _io
from copy import copy
from datetime import datetime
from pathlib import Path
import re
import shutil
import warnings
from typing import Any, Optional
from jinja2 import Environment, PackageLoader
from matplotlib import pyplot as plt
from matplotlib.dates import date2num, DateFormatter, AutoDateLocator
import numpy as np
import openpyxl
import pandas as pd
from openpyxl.styles import Font, Alignment, Border, Side, PatternFill
from openpyxl.utils import get_column_letter
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl.chart import BarChart, Reference
from openpyxl.chart.series import SeriesLabel
from openpyxl.chart.label import DataLabelList
from openpyxl.chart.shapes import GraphicalProperties
from openpyxl.drawing.line import LineProperties
from openpyxl.chart.axis import ChartLines

from src import Point
from src.util import HA, VA
from src.util.const import File, LocalPath
from src.util.logger import logger
from src.libs.nmea import filter_list, sys_list

DEFAULT_NULL_VALUE = ""
FAIL_FILL = PatternFill(start_color="FFC7CE", end_color="FFC7CE", fill_type="solid")

warnings.filterwarnings(
    "ignore", message="Conditional Formatting extension is not supported"
)

plt.rcParams["font.family"] = "SimHei"
plt.rcParams["axes.unicode_minus"] = False

TIME_UNIT = "ms"
FIX_LABEL = "定位符"


def _fill(
    ws,
    col,
    row,
    df,
    label,
    fname,
    percentage: bool = False,
    pass_fail: bool = False,
    pass_fail_count: bool = False,
):
    """从 df_result 取值填入模板单元格，并处理百分比或 Pass/Fail 状态。"""
    try:
        v = df.loc[label, fname]
        if pd.isna(v) or v in ("-", "", np.nan):
            val = "NA"
        elif isinstance(v, str):
            # 处理 "75.5%(100)" 格式 → 数值
            import re as _re

            m = _re.match(r"([\d.]+)", v)
            val = float(m.group(1)) if m else v
        else:
            val = round(v, 4) if isinstance(v, float) else v
    except (KeyError, TypeError, ValueError):
        val = "NA"
    cell = ws[f"{col}{row}"]

    if val == "NA":
        cell.value = val
    elif pass_fail:
        cell.value = "Pass" if val == 0 else f"Fail-{val}%"
        if "Fail" in cell.value:
            cell.fill = FAIL_FILL
    elif pass_fail_count:
        cell.value = "Pass" if val == 0 else f"Fail-{val}"
        if "Fail" in cell.value:
            cell.fill = FAIL_FILL
    elif percentage and isinstance(val, (int, float)):
        cell.value = val / 100
        cell.number_format = "0.00%"
    else:
        cell.value = val


def _fill_nth(
    ws,
    col,
    row,
    df,
    label,
    fname,
    nth: int = 0,
    percentage: bool = False,
    pass_fail: bool = False,
    pass_fail_count: bool = False,
):
    """从 df_result 获取第 nth 次出现的 label 值填入模板。用于处理重复 index label (如 Confidence Coefficient)。"""
    try:
        matches = df[df.index == label]
        v = matches.iloc[nth][fname]
        if pd.isna(v) or v in ("-", "", np.nan):
            val = "NA"
        elif isinstance(v, str):
            import re as _re

            m = _re.match(r"([\d.]+)", v)
            val = float(m.group(1)) if m else v
        else:
            val = round(v, 4) if isinstance(v, float) else v
    except (IndexError, KeyError, TypeError, ValueError):
        val = "NA"
    cell = ws[f"{col}{row}"]
    if pass_fail:
        cell.value = "Pass" if val == 0 else f"Fail-{val}%"
        if "Fail" in cell.value:
            cell.fill = FAIL_FILL
    elif pass_fail_count:
        cell.value = "Pass" if val == 0 else f"Fail-{val}"
        if "Fail" in cell.value:
            cell.fill = FAIL_FILL
    elif percentage and isinstance(val, (int, float)):
        cell.value = val / 100
        cell.number_format = "0.000%"
    else:
        cell.value = val


def calc_canvas_size(m):
    m_sqrt = np.sqrt(m)
    m_sqrt_int = int(m_sqrt)
    if m_sqrt > m_sqrt_int:
        m_sqrt_int += 1
    return m_sqrt_int


def clean_id(value):
    """
    自定义Jinja2过滤器，用于清理字符串以生成有效的HTML ID
    """
    # 确保输入是字符串
    value = str(value)
    # 替换特殊字符
    value = (
        value.replace(".", "")
        .replace("#", "")
        .replace(",", "")
        .replace("+", "")
        .replace("-", "")
        .replace("(", "（")
        .replace(")", "）")
    )

    return "id_" + value


def _load_package() -> Environment:
    if not hasattr(_load_package, "_env"):
        env = Environment(loader=PackageLoader("res", "templates"))
        env.filters["clean_id"] = clean_id
        _load_package._env = env
    return _load_package._env


def _format_index(df):
    pattern = re.compile(r"[ T\-:]")
    return [pattern.sub("", element)[4:] for element in df.index.to_list()]


def _copy_template_sheet(template_ws, target_wb, title: str):
    """Add a worksheet that retains the static report template's layout."""
    target_ws = target_wb.create_sheet(title=title)

    for row in template_ws.iter_rows():
        for source_cell in row:
            target_cell = target_ws[source_cell.coordinate]
            target_cell.value = source_cell.value
            if source_cell.has_style:
                target_cell._style = copy(source_cell._style)
            if source_cell.hyperlink:
                target_cell._hyperlink = copy(source_cell.hyperlink)
            if source_cell.comment:
                target_cell.comment = copy(source_cell.comment)

    for merged_range in template_ws.merged_cells.ranges:
        target_ws.merge_cells(str(merged_range))

    for key, dimension in template_ws.column_dimensions.items():
        target_ws.column_dimensions[key] = copy(dimension)
    for key, dimension in template_ws.row_dimensions.items():
        target_ws.row_dimensions[key] = copy(dimension)

    target_ws.sheet_format = copy(template_ws.sheet_format)
    target_ws.sheet_properties = copy(template_ws.sheet_properties)
    target_ws.page_margins = copy(template_ws.page_margins)
    target_ws.page_setup = copy(template_ws.page_setup)
    target_ws.print_options = copy(template_ws.print_options)
    target_ws.freeze_panes = template_ws.freeze_panes
    target_ws.sheet_view.showGridLines = template_ws.sheet_view.showGridLines

    return target_ws


class Report:
    _excel_timestamp: str = ""
    _open_wbs: dict[str, Any] = {}
    _template_fills: dict[str, dict[int, Any]] = {}

    def __init__(
        self,
        df_result: pd.DataFrame,
        folder_path: str,
        data_path: str = "",
        point: Point = Point(0, 0, 0),
        nav_log: str = "",
        log_info: str = "",
        check_list: list[str] = [],
        is_moving: bool = False,
        is_ttff: bool = False,
        begin_time: Optional[pd.Timestamp] = None,
        end_time: Optional[pd.Timestamp] = None,
        sheet_name: str = "All",
        is_long_test: bool = False,
        long_test_data: Optional[dict] = None,
    ):
        self.df_result = df_result
        self.folder_path = folder_path
        self.data_path = data_path
        self.point = point
        self.nav_log = nav_log
        self.log_info = log_info
        self.check_list = check_list
        self.is_moving = is_moving
        self.is_ttff = is_ttff
        self.begin_time = begin_time
        self.end_time = end_time
        self.sheet_name = sheet_name
        if self.sheet_name == "All":
            Report._excel_timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.is_long_test = is_long_test
        self.long_test_data = long_test_data or {}
        self.excel_timestamp = Report._excel_timestamp

        self.csv_path = Path(folder_path) / ("../all/data" if begin_time else "data")

    @classmethod
    def finalize_workbooks(cls):
        """保存并关闭所有缓存的 workbook，处理完毕后清空缓存。"""
        for key, wb in list(cls._open_wbs.items()):
            try:
                wb.save(key)
            except PermissionError:
                base, ext = os.path.splitext(key)
                counter = 1
                while True:
                    alt_path = f"{base}_副本{counter}{ext}"
                    if not os.path.exists(alt_path):
                        break
                    counter += 1
                wb.save(alt_path)
                logger.warning(f"Excel 文件被占用，已保存到备份: {alt_path}")
            finally:
                wb.close()
        cls._open_wbs.clear()
        cls._template_fills.clear()

    def gen_precision_report(self):
        self.copy_assets_to_folder(LocalPath.ASSETS_PATH)
        env = _load_package()

        # 先处理依赖 df_result / long_test_data 的报表生成
        self._gen_excel()

        if self.is_long_test:
            self._gen_long_time_report()

        self._gen_dynamic_template() if self.is_moving else self._gen_static_template()

        self._gen_task(
            env.get_template("report.html"),
            "report.html",
            title="Report",
            point=self.point,
            nav_log=self.nav_log,
            log_info=self.log_info,
            table_data=self.df_result.to_html(table_id="table_id"),
        )

        # 释放已用完的大内存对象
        del self.df_result
        del self.long_test_data

        # 再处理精度数据（基于 check_list 从文件读取，不依赖 df_result）
        self._get_precision_data()
        chart_tempate = env.get_template("chart.html")
        chart_double_y_tempate = env.get_template("chart-double-y.html")

        self._gen_task(
            chart_tempate,
            "rtk_delay.html",
            plot=True,
            title="RTK Delay",
            plot_item="delay",
            description="<p>统计GGA中RTK时延</p>",
            test_datas=self.__dict__.pop("_delay", {}),
        )
        self._gen_task(
            chart_tempate,
            "satellites_trend.html",
            plot=True,
            title="Satellites Trend",
            plot_item="satellites",
            description="<p>统计GGA中卫星个数</p>",
            test_datas=self.__dict__.pop("_satellites", {}),
        )
        self._gen_task(
            chart_double_y_tempate,
            "time_continuity.html",
            plot=True,
            plot_item=TIME_UNIT,
            title="Time Continuity",
            description=f"<p>统计RMC时间连续性，单位为{TIME_UNIT}</p>",
            test_datas=self.__dict__.pop("_time", {}),
        )
        self._gen_task(
            chart_tempate,
            "gps_cn0.html",
            title="GPS CN0",
            test_datas=self.__dict__.pop("_gps", {}),
        )
        self._gen_task(
            chart_tempate,
            "bds1_cn0.html",
            title="BDS CN0",
            test_datas=self.__dict__.pop("_bds_1", {}),
        )
        self._gen_task(
            chart_tempate,
            "bds2_cn0.html",
            title="BDS CN0",
            test_datas=self.__dict__.pop("_bds_2", {}),
        )
        self._gen_task(
            chart_tempate,
            "gal_cn0.html",
            title="GAL CN0",
            test_datas=self.__dict__.pop("_gal", {}),
        )
        self._gen_task(
            chart_tempate,
            "glo_cn0.html",
            title="GLO CN0",
            test_datas=self.__dict__.pop("_glo", {}),
        )
        self._gen_task(
            chart_tempate,
            "qzss_cn0.html",
            title="QZSS CN0",
            test_datas=self.__dict__.pop("_qzss", {}),
        )
        self._gen_task(
            chart_tempate,
            "irnss_cn0.html",
            title="IRNSS CN0",
            test_datas=self.__dict__.pop("_irnss", {}),
        )
        self._gen_task(
            chart_tempate,
            "svs_used_trend.html",
            title="SVs Used",
            test_datas=self.__dict__.pop("_svs_used", {}),
        )
        self._gen_task(
            chart_double_y_tempate,
            "sog_trend.html",
            title="SOG Trend",
            plot_item="sog",
            description="<p>统计RMC中速度误差</p>",
            test_datas=self.__dict__.pop("_speed", {}),
        )
        self._gen_task(
            chart_double_y_tempate,
            "accuracy_trend.html",
            title="Accuracy Trend",
            description="<p>统计所有解水平/高程误差</p>",
            test_datas=self.__dict__.pop("_precision", {}),
        )
        self._gen_task(
            chart_tempate,
            "dop_trend.html",
            title="DOP Trend",
            description="<p>统计GSA语句中DOP值</p>",
            test_datas=self.__dict__.pop("_dop", {}),
        )
        self._gen_task(
            chart_double_y_tempate,
            "fix_accuracy_trend.html",
            title="Fix Accuracy Trend",
            description="<p>统计固定解水平/高程误差</p>",
            test_datas=self.__dict__.pop("_fix_precision", {}),
        )
        self._gen_task(
            chart_tempate,
            "cog_trend.html",
            title="COG trend",
            description="<p>统计RMC中航向角变化</p>",
            test_datas=self.__dict__.pop("_cog", {}),
        )
        self._gen_task(
            chart_double_y_tempate,
            "alt_sep_trend.html",
            title="MSL Alt/GEO Sep trend",
            description="<p>统计GGA中高度和大地水准面分离变化</p>",
            test_datas=self.__dict__.pop("_alt_sep", {}),
        )
        self._gen_task(
            chart_double_y_tempate,
            "float_accuracy_trend.html",
            title="Float Accuracy Trend",
            description="<p>统计浮点解水平/高程误差</p>",
            test_datas=self.__dict__.pop("_float_precision", {}),
        )

        self._gen_task(
            chart_tempate,
            "pqtmvel_trend.html",
            title="PQTMVEL Trend",
            test_datas=self.__dict__.pop("_pqtmvel", {}),
        )
        if self.is_moving:
            self._gen_task(
                chart_double_y_tempate,
                "gps_l1_h.html",
                title="GPS L1 H",
                test_datas=self.__dict__.pop("_gps_l1_h", {}),
            )

            self._gen_task(
                chart_double_y_tempate,
                "gps_l1_v.html",
                title="GPS L1 V",
                test_datas=self.__dict__.pop("_gps_l1_v", {}),
            )

        # 图表数据已写入文件，提前释放实例所有属性
        plt.close("all")
        self.__dict__.clear()

    def _gen_long_time_report(self):
        """Long-time test: long_test_data 已是 Report-1 的行数组，直接收集生成 JS，不做二次解析。"""
        remark = self.long_test_data.pop("remark", "")
        rows = [d for d in self.long_test_data.values() if isinstance(d, list)]
        env = _load_package()
        out_dir = str(Path(self.folder_path).parents[2])
        js_path = os.path.join(out_dir, "report_data.js")
        html_path = os.path.join(out_dir, "long_time_report.html")

        # 若 out_dir 下已有 html 和 js，则把本次行追加到已有 report1 末尾；否则创建新的
        existing: list = []
        if os.path.exists(js_path) and os.path.exists(html_path):
            try:
                with open(js_path, encoding="utf-8") as f:
                    js_text = f.read()
                start = js_text.find("{")
                end = js_text.rfind("}")
                if start != -1 and end != -1 and end > start:
                    existing = json.loads(js_text[start : end + 1]).get("report1", [])
            except (ValueError, OSError):
                existing = []

        # 追加去重：以 test_date（每行第1列）作为去重键，已存在则不重复添加
        existing_keys = {"".join(r) for r in existing if isinstance(r, list) and r}
        for r in rows:
            key = "".join(r)
            if key not in existing_keys:
                existing.append(r)
                existing_keys.add(key)
        report_data = {"report1": existing, "report2": []}
        with open(js_path, encoding="utf-8", mode="w") as f:
            # 数据量可能很大，用 iterencode 流式写入避免一次性构建大字符串导致内存溢出
            f.write("var reportData = ")
            for chunk in json.JSONEncoder(ensure_ascii=False).iterencode(report_data):
                f.write(chunk)
            f.write(";")

        if not os.path.exists(html_path):
            self._write_file(
                "long_time_report.html",
                env.get_template("long_time_report.html"),
                kwargs={"remark": remark},
                write_path=out_dir,
            )

    def copy_assets_to_folder(self, assets_path: Path, copy_index: bool = True):
        target_path = Path(self.folder_path)

        # 如果目标目录不存在，创建它
        target_path.mkdir(parents=True, exist_ok=True)

        # 复制整个目录树
        shutil.copytree(assets_path, target_path / "assets", dirs_exist_ok=True)
        if copy_index:
            shutil.copy(LocalPath.TEMPLATE_PATH / "index.html", target_path)

    def _gen_static_template(self):
        """将静态测试结果填入 static.xlsx 模板，与 report.xlsx 同目录、加时间戳、分场景"""
        sheet_title = self.sheet_name or "All"
        out_dir = os.path.dirname(self.folder_path)
        out_path = Path(out_dir) / f"{self.excel_timestamp}_Static_Report.xlsx"
        key = str(out_path.resolve())

        wb = Report._open_wbs.get(key)
        if wb is None:
            wb = openpyxl.load_workbook(LocalPath.STATIC_TEMPLATE)
            Report._open_wbs[key] = wb

        if sheet_title in wb.sheetnames:
            del wb[sheet_title]
        template_wb = openpyxl.load_workbook(LocalPath.STATIC_TEMPLATE)
        template_ws = template_wb.active
        assert template_ws is not None
        _copy_template_sheet(template_ws, wb, sheet_title)
        template_wb.close()

        ws = wb[sheet_title]

        df = self.df_result
        files = [c for c in df.columns if not str(c).startswith("_")]  # 排除辅助列
        n_dut = len(files)
        max_length = 0

        e16_fill = ws["E16"].fill
        for i, fname in enumerate(files):
            col = get_column_letter(i + 6)  # F=6, G=7, ...
            cell = ws[f"{col}16"]
            cell.value = fname  # DUT name
            cell.fill = copy(e16_fill)

            # Horizontal accuracy rows 17-21
            _fill(ws, col, 17, df, "Positional Accuracy CEP50(m)", fname)
            _fill(ws, col, 18, df, "Positional Accuracy CEP68(m)", fname)
            _fill(ws, col, 19, df, "Positional Accuracy CEP95(m)", fname)
            _fill(ws, col, 20, df, "Positional Accuracy CEP99(m)", fname)
            _fill(ws, col, 21, df, "Positional Accuracy Max(m)", fname)

            # Constellation row 22: fill system names only, in a fixed order.
            # Either BDS signal group is sufficient to mark BDS as available.
            constellation_keys = (
                ("GPS", ("GPS Avg(L1+L2+L5)",)),
                (
                    "BDS",
                    ("BDS Avg(B1I+B2A+B2B)", "BDS Avg(B1C+B2I+B3I)"),
                ),
                ("GAL", ("GAL Avg(E1+E5A+E5B+E6)",)),
                ("GLO", ("GLO Avg(G1+G2)",)),
                ("QZSS", ("QZSS Avg(Q1+Q2+Q5)",)),
                ("IRNSS", ("IRNSS Avg(I5)",)),
            )
            available_constellations = []
            for constellation, keys in constellation_keys:
                for key in keys:
                    try:
                        value = df.loc[key, fname]
                        value_text = str(value).strip()
                        if pd.notna(value) and value_text not in ("-", ""):
                            # CN0 can be a single number or a value per frequency,
                            # e.g. "33.8+0.0+0.0". All-zero values mean no system.
                            cn0_values = [
                                float(item.strip()) for item in value_text.split("+")
                            ]
                            if any(cn0 != 0 for cn0 in cn0_values):
                                available_constellations.append(constellation)
                                break
                    except (KeyError, TypeError, ValueError):
                        pass
            constellation_text = "+".join(available_constellations)
            ws[f"{col}22"] = constellation_text
            max_length = max(
                max_length,
                len(str(fname)),
                len(constellation_text),
            )

            # Average CN0 & Satellites
            _fill(ws, col, 23, df, "All CN0 Avg", fname)
            _fill(ws, col, 24, df, "Parsed Satellites Avg", fname)

            # Vertical accuracy rows 25-29
            _fill(ws, col, 25, df, "Altitude Accuracy CEP50(m)", fname)
            _fill(ws, col, 26, df, "Altitude Accuracy CEP68(m)", fname)
            _fill(ws, col, 27, df, "Altitude Accuracy CEP95(m)", fname)
            _fill(ws, col, 28, df, "Altitude Accuracy CEP99(m)", fname)
            _fill(ws, col, 29, df, "Altitude Accuracy Max(m)", fname)

            # Lose fix / Missing NMEA
            _fill(ws, col, 30, df, "0-Unfixed rate", fname, pass_fail=True)
            _fill(ws, col, 31, df, "Integrity of NMEA", fname, pass_fail_count=True)
            _fill(ws, col, 32, df, "Mis-Seconds", fname, pass_fail_count=True)
            _fill(ws, col, 33, df, "ChecksumError Count", fname, pass_fail_count=True)

            # Fixed / Float / DGPS / GPS rates (rows 34-37)
            for row, label in (
                (34, "4-Fixed rate"),
                (35, "5-Float rate"),
                (36, "2-DGPS rate"),
                (37, "1-GPS rate"),
            ):
                _fill(ws, col, row, df, label, fname, percentage=True)

            # Fixed availability (row 38)
            _fill(ws, col, 38, df, "Fixed availability", fname, percentage=True)

        # 所有 DUT 数据列等宽；宽度取 Sample 与 Constellation 中最长的内容并留出边距。
        if n_dut > 0:
            data_column_width = max_length + 5
            for i in range(n_dut):
                ws.column_dimensions[get_column_letter(i + 6)].width = data_column_width

        # Excel 的默认网格线不会在打印或部分查看器中显示；为数据表添加实际边框，
        # 使指标列和各 DUT 列之间始终有清晰的分割线。
        if n_dut > 0:
            table_border = Side(style="thin", color="000000")
            for row in ws.iter_rows(
                min_row=16,
                max_row=38,
                min_col=5,  # 指标名称列 E
                max_col=5 + n_dut,
            ):
                for cell in row:
                    cell.border = Border(
                        left=table_border,
                        right=table_border,
                        top=table_border,
                        bottom=table_border,
                    )

        # ---- 添加柱状图 ----
        if n_dut > 0:
            data_start_col = 6  # F
            data_end_col = data_start_col + n_dut - 1

            chart = BarChart()
            chart.type = "bar"
            chart.title = "Static Performance Test Report"
            chart.title.overlay = False  # type: ignore
            chart.grouping = "clustered"
            chart.style = 10
            chart.width = 16
            chart.height = 18
            chart.gapWidth = 50

            # 水平柱状图: y_axis=数值轴(底部/值), x_axis=分类轴(左侧/文件名)
            chart.x_axis.title = None
            chart.x_axis.delete = False
            chart.x_axis.tickLblPos = "low"
            # 关闭 Y 轴（数值轴）竖向网格线
            chart.y_axis.majorGridlines = ChartLines(
                spPr=GraphicalProperties(ln=LineProperties(noFill=True))
            )
            chart.y_axis.minorGridlines = ChartLines(
                spPr=GraphicalProperties(ln=LineProperties(noFill=True))
            )

            # 图例位置
            chart.legend.position = "t"
            chart.legend.overlay = False

            # 数据标签
            chart.dLbls = DataLabelList()
            chart.dLbls.showVal = True  # type: ignore[assignment]
            chart.dLbls.showCatName = False  # type: ignore[assignment]
            chart.dLbls.showSerName = False  # type: ignore[assignment]
            chart.dLbls.position = "outEnd"  # type: ignore[assignment]

            # 分类轴（DUT 名称）
            cats = Reference(
                ws, min_col=data_start_col, max_col=data_end_col, min_row=16, max_row=16
            )

            # 用 add_data + 手动设 tx 来确保 series 标题正确
            series_config = [
                (17, "CEP50(m)"),
                (18, "CEP68(m)"),
                (19, "CEP95(m)"),
                (21, "Maximum(m)"),
            ]
            for row_num, series_name in series_config:
                data_ref = Reference(
                    ws,
                    min_col=data_start_col,
                    max_col=data_end_col,
                    min_row=row_num,
                    max_row=row_num,
                )
                chart.add_data(data_ref, from_rows=True, titles_from_data=False)
                s = chart.series[-1]
                s.tx = SeriesLabel(v=series_name)
            chart.set_categories(cats)

            # openpyxl type stub: anchor is optional; runtime accepts (chart, cell)
            ws.add_chart(chart, "B16")  # type: ignore[call-arg]

        # ---- 水平误差趋势图 ----
        precision_data = self.__dict__.get("_precision", {})
        if precision_data:
            try:
                fig, ax = plt.subplots(figsize=(10, 4), dpi=100)
                fig.suptitle("2D Position Error Trend", fontsize=12, fontweight="bold")

                for fname in files:
                    entry = precision_data.get(fname)
                    if not entry or not entry[0] or not entry[1]:
                        continue
                    data_vals = entry[1].get(HA, [])
                    if not data_vals:
                        continue
                    vals = [v if v != DEFAULT_NULL_VALUE else np.nan for v in data_vals]

                    # parse time strings (MMddHHmmSS.fff) → datetime for UTC alignment
                    time_dt = []
                    for ts in entry[0]:
                        dt = datetime.strptime(
                            ts if "." in ts else ts + ".0", "%m%d%H%M%S.%f"
                        )
                        time_dt.append(dt)

                    ax.plot(
                        date2num(time_dt),
                        vals,
                        label=fname,
                        linewidth=0.8,
                        alpha=0.8,
                    )

                ax.xaxis.set_major_formatter(DateFormatter("%H:%M:%S"))
                ax.xaxis.set_major_locator(AutoDateLocator())
                ax.set_xlabel("UTC Time")
                ax.set_ylabel("Horizontal Error (m)")
                if ax.get_legend_handles_labels()[0]:
                    ax.legend(
                        loc="lower center",
                        bbox_to_anchor=(0.5, -0.35),
                        ncol=min(len(files), 4),
                        fontsize=8,
                    )
                ax.grid(True, linestyle=":", alpha=0.4)
                fig.tight_layout()

                img_buf = _io.BytesIO()
                fig.savefig(img_buf, format="png", dpi=120, bbox_inches="tight")
                plt.close(fig)
                img_buf.seek(0)

                from openpyxl.drawing.image import Image

                img = Image(img_buf)
                img.width = 1100
                img.height = 600
                ws.add_image(img, "B41")
            except Exception:
                logger.warning("Failed to generate trend chart", exc_info=True)

    def _gen_dynamic_template(self):
        """将动态测试结果填入 Dynamic_Report.xlsx 模板，所有 section 写在同一个 sheet 内。"""
        TEMPLATE_ROW = 18
        sheet_title = "Dynamic"
        out_dir = os.path.dirname(self.folder_path)
        out_path = Path(out_dir) / f"{self.excel_timestamp}_Dynamic_Report.xlsx"
        key = str(out_path.resolve())

        wb = Report._open_wbs.get(key)
        if wb is None:
            wb = openpyxl.load_workbook(LocalPath.DYNAMIC_TEMPLATE)
            ws = wb.active
            assert ws is not None
            ws.title = sheet_title

            # 根据最长文件名设置 C 列（Module）列宽
            fnames = [c for c in self.df_result.columns if not str(c).startswith("_")]
            max_name_len = max((len(name) for name in fnames), default=0)
            ws.column_dimensions["C"].width = max(max_name_len + 5, 10)

            # 清除模板中 row 18-19 的占位合并和占位数据
            for m in list(ws.merged_cells.ranges):
                s = str(m)
                if str(TEMPLATE_ROW) in s and ("B" in s or "AE" in s or "BH" in s):
                    ws.unmerge_cells(s)
            for row in range(TEMPLATE_ROW, ws.max_row + 1):
                for col in range(1, ws.max_column + 1):
                    ws.cell(row, col).value = None

            section_start = TEMPLATE_ROW
            Report._open_wbs[key] = wb
            template_fills = {
                col: copy(ws.cell(TEMPLATE_ROW, col).fill)
                for col in range(2, ws.max_column + 1)
            }
            Report._template_fills[key] = template_fills
        else:
            ws = wb[sheet_title]
            last_row = TEMPLATE_ROW - 1
            for row in range(TEMPLATE_ROW, ws.max_row + 1):
                if ws[f"C{row}"].value is not None:
                    last_row = row
            section_start = last_row + 2
            template_fills = Report._template_fills[key]

        self._write_dynamic_section(ws, section_start, TEMPLATE_ROW, template_fills)

    def _write_dynamic_section(
        self, ws, section_start: int, template_row: int, template_fills: dict
    ):
        """将一个 section 的 DUT 数据写入工作表的指定起始行。"""
        scene_name = self.sheet_name
        df = self.df_result
        files = [c for c in df.columns if not str(c).startswith("_")]
        n_dut = min(len(files), 8)

        # 复制 template_row 的样式到本 section 各行，fill 使用初次加载时保存的原始填充
        for i in range(n_dut):
            row = section_start + i
            for col in range(2, ws.max_column + 1):
                src = ws.cell(template_row, col)
                dst = ws.cell(row, col)
                if src.has_style:
                    dst.font = copy(src.font)
                    dst.fill = copy(template_fills[col])
                    dst.border = copy(src.border)
                    dst.alignment = copy(src.alignment)
                    dst.number_format = src.number_format
                    dst.protection = copy(src.protection)
            # 复制行高
            src_dim = ws.row_dimensions.get(template_row)
            if src_dim and src_dim.height:
                ws.row_dimensions[row].height = src_dim.height

        # B: scene name — extract position count from Total rate value
        pos_count = "XXXX"
        try:
            total_rate_val = df.loc["Total rate", files[0]]
            if isinstance(total_rate_val, str):
                m = re.search(r"\((\d+)\)", total_rate_val)
                if m:
                    pos_count = m.group(1)
        except (KeyError, IndexError):
            pass
        ws[f"B{section_start}"] = f"{scene_name}\n[Position count:{pos_count}]"

        for i, fname in enumerate(files[:n_dut]):
            row = section_start + i

            # C: DUT name
            ws[f"C{row}"] = fname

            # D: Lose fix rate (Pass/Fail: 0=Pass)
            _fill(ws, "D", row, df, "0-Unfixed rate", fname, pass_fail=True)

            # E: Integrity of NMEA — ChecksumError count
            _fill(ws, "E", row, df, "Integrity of NMEA", fname, pass_fail_count=True)

            # F-I: Rate columns (percentage)
            for col_letter, label in (
                ("F", "4-Fixed rate"),
                ("G", "5-Float rate"),
                ("H", "2-DGPS rate"),
                ("I", "1-GPS rate"),
            ):
                _fill(ws, col_letter, row, df, label, fname, percentage=True)

            # J: Fixed availability
            _fill(ws, "J", row, df, "Fixed availability", fname, percentage=True)

            # K-O: Horizontal CEP
            for col_letter, label in (
                ("K", "Positional Accuracy CEP50(m)"),
                ("L", "Positional Accuracy CEP68(m)"),
                ("M", "Positional Accuracy CEP95(m)"),
                ("N", "Positional Accuracy CEP99(m)"),
                ("O", "Positional Accuracy Max(m)"),
            ):
                _fill(ws, col_letter, row, df, label, fname)

            # P-T: Vertical CEP
            for col_letter, label in (
                ("P", "Altitude Accuracy CEP50(m)"),
                ("Q", "Altitude Accuracy CEP68(m)"),
                ("R", "Altitude Accuracy CEP95(m)"),
                ("S", "Altitude Accuracy CEP99(m)"),
                ("T", "Altitude Accuracy Max(m)"),
            ):
                _fill(ws, col_letter, row, df, label, fname)

            # U-Y: Speed CEP
            for col_letter, label in (
                ("U", "SOG CEP50(m/s)"),
                ("V", "SOG CEP68(m/s)"),
                ("W", "SOG CEP95(m/s)"),
                ("X", "SOG CEP99(m/s)"),
                ("Y", "SOG Max(m/s)"),
            ):
                _fill(ws, col_letter, row, df, label, fname)

            # Z-AD: COG CEP
            for col_letter, label in (
                ("Z", "COG CEP50(°)"),
                ("AA", "COG CEP68(°)"),
                ("AB", "COG CEP95(°)"),
                ("AC", "COG CEP99(°)"),
                ("AD", "COG Max(°)"),
            ):
                _fill(ws, col_letter, row, df, label, fname)

            # AG-AK: VEL_N Speed Error
            for col_letter, label in (
                ("AG", "VEL-N CEP50(m/s)"),
                ("AH", "VEL-N CEP68(m/s)"),
                ("AI", "VEL-N CEP95(m/s)"),
                ("AJ", "VEL-N CEP99(m/s)"),
                ("AK", "VEL-N Max(m/s)"),
            ):
                _fill(ws, col_letter, row, df, label, fname)

            # AL-AP: VEL_E Speed Error
            for col_letter, label in (
                ("AL", "VEL-E CEP50(m/s)"),
                ("AM", "VEL-E CEP68(m/s)"),
                ("AN", "VEL-E CEP95(m/s)"),
                ("AO", "VEL-E CEP99(m/s)"),
                ("AP", "VEL-E Max(m/s)"),
            ):
                _fill(ws, col_letter, row, df, label, fname)

            # AQ-AU: VEL_D Speed Error
            for col_letter, label in (
                ("AQ", "VEL-D CEP50(m/s)"),
                ("AR", "VEL-D CEP68(m/s)"),
                ("AS", "VEL-D CEP95(m/s)"),
                ("AT", "VEL-D CEP99(m/s)"),
                ("AU", "VEL-D Max(m/s)"),
            ):
                _fill(ws, col_letter, row, df, label, fname)

            # AV-AZ: 2D Velocity Error
            for col_letter, label in (
                ("AV", "2D Velocity CEP50(m/s)"),
                ("AW", "2D Velocity CEP68(m/s)"),
                ("AX", "2D Velocity CEP95(m/s)"),
                ("AY", "2D Velocity CEP99(m/s)"),
                ("AZ", "2D Velocity Max(m/s)"),
            ):
                _fill(ws, col_letter, row, df, label, fname)

            # BA-BE: 3D Velocity Error
            for col_letter, label in (
                ("BA", "3D Velocity CEP50(m/s)"),
                ("BB", "3D Velocity CEP68(m/s)"),
                ("BC", "3D Velocity CEP95(m/s)"),
                ("BD", "3D Velocity CEP99(m/s)"),
                ("BE", "3D Velocity Max(m/s)"),
            ):
                _fill(ws, col_letter, row, df, label, fname)

            # BF: 2D_Spd confidence (nth=1)
            _fill_nth(ws, "BF", row, df, "Confidence Coefficient", fname, nth=1)

            # BG: 3D_Spd confidence (nth=2)
            _fill_nth(ws, "BG", row, df, "Confidence Coefficient", fname, nth=2)

        # Merge B, AE, BH columns for this section
        section_end = section_start + n_dut - 1
        if n_dut > 1:
            for col_letter in ("B", "AE", "BH"):
                ws.merge_cells(f"{col_letter}{section_start}:{col_letter}{section_end}")

    def _get_precision_data(self):
        gps_dict: dict[str, Any] = {}
        bds_1_dict: dict[str, Any] = {}
        bds_2_dict: dict[str, Any] = {}
        gal_dict: dict[str, Any] = {}
        glo_dict: dict[str, Any] = {}
        dop_dict: dict[str, Any] = {}
        delay_dict: dict[str, Any] = {}
        satellites_dict: dict[str, Any] = {}
        time_dict: dict[str, Any] = {}
        cog_dict: dict[str, Any] = {}
        speed_dict: dict[str, Any] = {}
        precision_dict: dict[str, Any] = {}
        fix_precision_dict: dict[str, Any] = {}
        gps_l1_h: dict[str, Any] = {}
        gps_l1_v: dict[str, Any] = {}
        alt_sep_dict: dict[str, Any] = {}
        qzss_dict: dict[str, Any] = {}
        irnss_dict: dict[str, Any] = {}
        svs_used_dict: dict[str, Any] = {}
        float_precision_dict: dict[str, Any] = {}
        pqtmvel_dict: dict[str, Any] = {}

        for file in self.check_list:
            file = os.path.splitext(file)[0]
            try:
                usecols = (
                    [
                        "delay",
                        "satellites",
                        "alt",
                        "sep",
                        "label",
                        "pdop",
                        "hdop",
                        "vdop",
                        "utc_date_time",
                    ]
                    + ([f"{_sys}_used" for _sys in sys_list])
                    + filter_list
                )
                if self.is_ttff:
                    usecols.append("header")

                df = pd.read_csv(
                    os.path.join(self.csv_path, file + f"{File.ORIGINAL_FILE_EXT}"),
                    low_memory=False,
                    usecols=usecols,
                )

                df_utc_time = self._format_utc_time(df)
                if self.begin_time and self.end_time:
                    df.index = pd.to_datetime(df.index, errors="coerce")
                    df = df[(df.index >= self.begin_time) & (df.index <= self.end_time)]
                    df.index = df.index.astype(str)

                    df_utc_time = df_utc_time[
                        (df_utc_time["utc_date_time"] >= self.begin_time)
                        & (df_utc_time["utc_date_time"] <= self.end_time)
                    ]

                df_delay = df["delay"].fillna(DEFAULT_NULL_VALUE)
                df_satellites = df["satellites"].fillna(DEFAULT_NULL_VALUE)
                # df_label = df["label"].fillna(DEFAULT_NULL_VALUE)
                df_snr = df[filter_list]

                delay_dict[file] = [
                    _format_index(df_delay),
                    {"delay": df_delay.to_list()},
                ]
                satellites_dict[file] = [
                    _format_index(df_satellites),
                    {"satellites": df_satellites.to_list()},
                ]
                time_dict[file] = [
                    _format_index(df_utc_time),
                    {
                        TIME_UNIT: df_utc_time["delta"]
                        .fillna(DEFAULT_NULL_VALUE)
                        .to_list(),
                        FIX_LABEL: df_utc_time["label"]
                        .fillna(DEFAULT_NULL_VALUE)
                        .to_list(),
                    },
                ]

                df_alt_sep = df[["alt", "sep"]].fillna(DEFAULT_NULL_VALUE)
                alt_sep_dict[file] = [
                    _format_index(df_alt_sep),
                    {
                        "MSL Alt": df_alt_sep["alt"].to_list(),
                        "GEO Sep": df_alt_sep["sep"].to_list(),
                    },
                ]

                df_svs_used = df[[f"{_sys}_used" for _sys in sys_list]]
                svs_used_str = df_svs_used.index.str
                df_svs_used = df_svs_used[
                    svs_used_str.endswith(".00") | svs_used_str.endswith(".000")
                ].fillna(DEFAULT_NULL_VALUE)
                svs_used_dict[file] = [
                    _format_index(df_svs_used),
                    {
                        f"{_sys}_used": df_svs_used[f"{_sys}_used"].to_list()
                        for _sys in sys_list
                    },
                ]

                df.loc[df["label"] == 0, ["pdop", "hdop", "vdop"]] = np.nan
                df_dop = df[["pdop", "hdop", "vdop"]]
                df_dop_index_str = df_dop.index.str
                df_dop = df_dop[
                    df_dop_index_str.endswith(".00") | df_dop_index_str.endswith(".000")
                ]

                dop_dict[file] = [
                    _format_index(df_dop),
                    {
                        "PDOP": df_dop["pdop"].fillna(DEFAULT_NULL_VALUE).to_list(),
                        "HDOP": df_dop["hdop"].fillna(DEFAULT_NULL_VALUE).to_list(),
                        "VDOP": df_dop["vdop"].fillna(DEFAULT_NULL_VALUE).to_list(),
                    },
                ]

                if df_snr is not None:
                    df_index_str = df_snr.index.str
                    df_snr = df_snr[
                        df_index_str.endswith(".00") | df_index_str.endswith(".000")
                    ]
                    df_snr.fillna(np.nan, inplace=True)
                    axis = _format_index(df_snr)

                    gps_dict[file] = [
                        axis,
                        {
                            "L1": df_snr["gps_l1"].fillna(DEFAULT_NULL_VALUE).to_list(),
                            "L2": df_snr["gps_l2"].fillna(DEFAULT_NULL_VALUE).to_list(),
                            "L5": df_snr["gps_l5"].fillna(DEFAULT_NULL_VALUE).to_list(),
                            "L1_COUNT": df_snr["gps_l1_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "L2_COUNT": df_snr["gps_l2_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "L5_COUNT": df_snr["gps_l5_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]

                    bds_1_dict[file] = [
                        axis,
                        {
                            "B1I": df_snr["bds_b1i"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "B2a": df_snr["bds_b2a"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "B2b": df_snr["bds_b2b"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "B1I_COUNT": df_snr["bds_b1i_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "B2a_COUNT": df_snr["bds_b2a_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "B2b_COUNT": df_snr["bds_b2b_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]

                    bds_2_dict[file] = [
                        axis,
                        {
                            "B1C": df_snr["bds_b1c"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "B2I": df_snr["bds_b2i"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "B3I": df_snr["bds_b3i"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "B1C_COUNT": df_snr["bds_b1c_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "B2I_COUNT": df_snr["bds_b2i_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "B3I_COUNT": df_snr["bds_b3i_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]

                    gal_dict[file] = [
                        axis,
                        {
                            "E1": df_snr["gal_e1"].fillna(DEFAULT_NULL_VALUE).to_list(),
                            "E5a": df_snr["gal_e5a"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "E5b": df_snr["gal_e5b"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "E6": df_snr["gal_e6"].fillna(DEFAULT_NULL_VALUE).to_list(),
                            "E1_COUNT": df_snr["gal_e1_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "E5a_COUNT": df_snr["gal_e5a_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "E5b_COUNT": df_snr["gal_e5b_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "E6_COUNT": df_snr["gal_e6_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]

                    glo_dict[file] = [
                        axis,
                        {
                            "G1": df_snr["glo_g1"].fillna(DEFAULT_NULL_VALUE).to_list(),
                            "G2": df_snr["glo_g2"].fillna(DEFAULT_NULL_VALUE).to_list(),
                            "G1_COUNT": df_snr["glo_g1_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "G2_COUNT": df_snr["glo_g2_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]
                    qzss_dict[file] = [
                        axis,
                        {
                            "Q1": df_snr["qzs_q1"].fillna(DEFAULT_NULL_VALUE).to_list(),
                            "Q2": df_snr["qzs_q2"].fillna(DEFAULT_NULL_VALUE).to_list(),
                            "Q5": df_snr["qzs_q5"].fillna(DEFAULT_NULL_VALUE).to_list(),
                            "Q1_COUNT": df_snr["qzs_q1_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "Q2_COUNT": df_snr["qzs_q2_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "Q5_COUNT": df_snr["qzs_q5_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]
                    irnss_dict[file] = [
                        axis,
                        {
                            "I5": df_snr["irn_i5"].fillna(DEFAULT_NULL_VALUE).to_list(),
                            "I5_COUNT": df_snr["irn_i5_cnt"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]

            except FileNotFoundError:
                delay_dict[file] = [[], []]
                satellites_dict[file] = [[], []]
                time_dict[file] = [
                    [],
                    {
                        TIME_UNIT: [],
                        FIX_LABEL: [],
                    },
                ]
                gps_dict[file] = [[], {}]
                bds_1_dict[file] = [[], {}]
                bds_2_dict[file] = [[], {}]
                gal_dict[file] = [[], {}]
                glo_dict[file] = [[], {}]
                dop_dict[file] = [[], {}]
                # speed_dict[file] = [[], {}]
                # cog_dict[file] = [[], {}]
                alt_sep_dict[file] = [[], {}]
                qzss_dict[file] = [[], {}]
                irnss_dict[file] = [[], {}]
                svs_used_dict[file] = [[], {}]

            try:
                file_path = os.path.join(self.csv_path, file + f"{File.CALC_FILE_EXT}")

                df = pd.read_csv(file_path, low_memory=False)
                if df.empty:
                    raise FileNotFoundError
                df.drop_duplicates(subset=["utc_date_time"], keep="first", inplace=True)
                df.dropna(subset=["utc_date_time"], inplace=True)
                df.set_index("utc_date_time", inplace=True)
                if self.begin_time and self.end_time:
                    df.index = pd.to_datetime(df.index, errors="coerce")
                    df = df[(df.index >= self.begin_time) & (df.index <= self.end_time)]
                    df.index = df.index.astype(str)
                df_speed = df["speed_delta"].fillna(DEFAULT_NULL_VALUE)
                speed_dict[file] = [
                    _format_index(df_speed),
                    {"SOG Accuracy": df_speed.to_list()},
                ]
                df_cog = df[["yaw_delta"]].fillna(DEFAULT_NULL_VALUE)
                cog_dict[file] = [
                    _format_index(df_cog),
                    {"COG Accuracy": df_cog["yaw_delta"].to_list()},
                ]

                if self.is_moving:
                    df_distance = df[["label", "ref_label", "distance", "hgt_delta"]]
                    df_4_distance = df.loc[
                        df["label"] == 4,
                        ["label", "ref_label", "distance", "hgt_delta"],
                    ]
                    precision_dict[file] = [
                        _format_index(df_distance),
                        {
                            HA: df_distance["distance"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            VA: df_distance["hgt_delta"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]
                    fix_precision_dict[file] = [
                        _format_index(df_4_distance),
                        {
                            HA: df_4_distance["distance"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            VA: df_4_distance["hgt_delta"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]

                    df_5_distance = df.loc[df["label"] == 5, ["distance", "hgt_delta"]]
                    float_precision_dict[file] = [
                        _format_index(df_5_distance),
                        {
                            HA: df_5_distance["distance"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            VA: df_5_distance["hgt_delta"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]
                    df_gps_l1 = df[["gps_l1", "distance", "hgt_delta"]]
                    df_gps_index_str = df_gps_l1.index.str
                    df_gps_l1 = df_gps_l1[
                        df_gps_index_str.endswith(".00")
                        | df_gps_index_str.endswith(".000")
                    ]
                    gps_l1_h[file] = [
                        _format_index(df_gps_l1),
                        {
                            "gps_l1": df_gps_l1["gps_l1"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "distance": df_gps_l1["distance"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]
                    gps_l1_v[file] = [
                        _format_index(df_gps_l1),
                        {
                            "gps_l1": df_gps_l1["gps_l1"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "hgt_delta": df_gps_l1["hgt_delta"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]
                    df_pqtmvel = df[["heading_err", "2d_err", "3d_err"]].fillna(
                        DEFAULT_NULL_VALUE
                    )
                    pqtmvel_dict[file] = [
                        _format_index(df_pqtmvel),
                        {
                            "heading_err": df_pqtmvel["heading_err"].to_list(),
                            "2d_err": df_pqtmvel["2d_err"].to_list(),
                            "3d_err": df_pqtmvel["3d_err"].to_list(),
                        },
                    ]
                else:
                    df_distance = df[["label", "distance", "hgt_delta"]]
                    df_4_distance = df.loc[
                        df["label"] == 4, ["label", "distance", "hgt_delta"]
                    ]
                    precision_dict[file] = [
                        _format_index(df_distance),
                        {
                            HA: df_distance["distance"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            VA: df_distance["hgt_delta"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]
                    fix_precision_dict[file] = [
                        _format_index(df_4_distance),
                        {
                            HA: df_4_distance["distance"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            VA: df_4_distance["hgt_delta"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]

                    df_5_distance = df.loc[df["label"] == 5, ["distance", "hgt_delta"]]
                    float_precision_dict[file] = [
                        _format_index(df_5_distance),
                        {
                            HA: df_5_distance["distance"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            VA: df_5_distance["hgt_delta"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]
                    pqtmvel_dict[file] = [
                        [],
                        {"heading_err": [], "2d_err": [], "3d_err": []},
                    ]
            except FileNotFoundError:
                speed_dict[file] = [[], []]
                precision_dict[file] = [[], []]
                fix_precision_dict[file] = [[], []]
                gps_l1_h[file] = [[], []]
                gps_l1_v[file] = [[], []]
                cog_dict[file] = [[], []]
                float_precision_dict[file] = [[], []]
                pqtmvel_dict[file] = [[], []]

        self.__dict__.update(
            {
                "_delay": delay_dict,
                "_time": time_dict,
                "_speed": speed_dict,
                "_precision": precision_dict,
                "_fix_precision": fix_precision_dict,
                "_gps": gps_dict,
                "_bds_1": bds_1_dict,
                "_bds_2": bds_2_dict,
                "_gal": gal_dict,
                "_glo": glo_dict,
                "_dop": dop_dict,
                "_satellites": satellites_dict,
                "_gps_l1_h": gps_l1_h,
                "_gps_l1_v": gps_l1_v,
                "_cog": cog_dict,
                "_alt_sep": alt_sep_dict,
                "_qzss": qzss_dict,
                "_irnss": irnss_dict,
                "_svs_used": svs_used_dict,
                "_float_precision": float_precision_dict,
                "_pqtmvel": pqtmvel_dict,
            }
        )

    def _format_utc_time(self, df: pd.DataFrame):
        if df.empty:
            raise FileNotFoundError

        df.drop_duplicates(subset=["utc_date_time"], keep="first", inplace=True)
        df.dropna(subset=["utc_date_time"], inplace=True)

        if df.empty:
            raise FileNotFoundError

        columns_needed = ["utc_date_time"]
        if "label" in df.columns:
            columns_needed.append("label")

        if self.is_ttff:
            columns_needed.extend(["header"])

        df_utc_time = df[columns_needed].copy()
        df_utc_time["index"] = df_utc_time["utc_date_time"]
        df_utc_time["utc_date_time"] = pd.to_datetime(df_utc_time["utc_date_time"])
        df_utc_time["delta"] = df_utc_time["utc_date_time"].diff().dt.total_seconds() * 1000  # type: ignore

        if self.is_ttff:
            df_utc_time.loc[df["header"] == 1, "delta"] = np.nan

        df_utc_time.set_index("index", drop=False, inplace=True)
        df_utc_time.index.name = ""

        df.set_index("utc_date_time", inplace=True)

        return df_utc_time[1:]

    def _write_file(
        self, filename, template, kwargs=None, write_path: Optional[str] = None
    ):
        if kwargs is None:
            kwargs = {}

        with open(
            os.path.join(write_path or self.data_path, filename),
            encoding="utf-8",
            mode="w",
        ) as f:
            f.write(template.render(**kwargs))

    def _write_file_with_js(self, filename, template, **kwargs):
        # 将大量 test_datas 写入独立 JS 文件，按端口逐个序列化避免内存溢出
        print(f"Generating JS {filename} ...")
        if "test_datas" in kwargs:
            data_filename = filename.replace(".html", ".js")
            js_dir = os.path.join(self.folder_path, "assets", "js")
            os.makedirs(js_dir, exist_ok=True)
            data_path = os.path.join(js_dir, data_filename)
            data = kwargs["test_datas"]
            with open(data_path, encoding="utf-8", mode="w") as f:
                f.write("var reportData = {")
                first = True
                for port_name, port_data in data.items():
                    if not first:
                        f.write(",")
                    first = False
                    f.write(json.dumps(port_name, ensure_ascii=False) + ":")
                    f.write(json.dumps(port_data, ensure_ascii=False, default=str))
                f.write("};")
            kwargs.pop("test_datas")
            kwargs["data_file"] = os.path.relpath(data_path, self.data_path)
        self._write_file(filename, template, kwargs)

    def _gen_task(self, template, filename, plot=False, **kwargs):
        print(f"Generating {filename} ...")
        if plot:
            self._plot_png(filename[:-5], **kwargs)
        self._write_file_with_js(filename, template, **kwargs)

    def _plot_png(self, filename, **kwargs):
        print(f"Generating PNG {filename} ...")
        plot_data = kwargs["test_datas"]
        title = kwargs["title"]
        num = len(plot_data.keys())
        canvas_size = calc_canvas_size(num)

        fig = plt.figure(constrained_layout=True)
        try:
            fig.suptitle(title)

            for idx, (key, value) in enumerate(plot_data.items(), 1):
                ax = fig.add_subplot(canvas_size, canvas_size, idx)

                # 处理数据，将默认空值替换为np.nan
                if isinstance(value[1], list):
                    processed_data = [
                        e if e != DEFAULT_NULL_VALUE else np.nan for e in value[1]
                    ]
                else:
                    plot_item = kwargs["plot_item"]
                    processed_data = [
                        e if e != DEFAULT_NULL_VALUE else np.nan
                        for e in value[1][plot_item]
                    ]

                ax.plot(processed_data)
                ax.set_title(key, fontsize=9)
            fig.set_size_inches(12, 6)
            plt.savefig(os.path.join(self.data_path, f"{filename}.png"))
        finally:
            plt.close(fig)

    def _gen_excel(self):
        excel_path = os.path.join(
            os.path.dirname(self.folder_path),
            f"{self.excel_timestamp}_Report.xlsx",
        )
        key = str(Path(excel_path).resolve())

        wb = Report._open_wbs.get(key)
        if wb is None:
            wb = openpyxl.Workbook()
            # 删除默认空白 sheet
            if "Sheet" in wb.sheetnames:
                del wb["Sheet"]
            Report._open_wbs[key] = wb

        # 如果 sheet 已存在则删除后重建
        if self.sheet_name in wb.sheetnames:
            del wb[self.sheet_name]
        ws = wb.create_sheet(self.sheet_name)

        # 将 DataFrame 写入工作表
        for r_idx, row in enumerate(
            dataframe_to_rows(self.df_result, index=True, header=True), 1
        ):
            for c_idx, value in enumerate(row, 1):
                ws.cell(row=r_idx, column=c_idx, value=value)

        # 设置数据字体格式
        data_font = Font(name="Microsoft YaHei", size=10)
        left_alignment = Alignment(horizontal="left", vertical="center")
        right_alignment = Alignment(horizontal="right", vertical="center")

        border = Border(
            left=Side(style="thin"),
            right=Side(style="thin"),
            top=Side(style="thin"),
            bottom=Side(style="thin"),
        )

        # 应用数据样式
        for row in ws.iter_rows(min_row=1, max_row=ws.max_row):
            for cell in row:
                cell.font = data_font
                cell.border = border
                if cell.column_letter == "A":
                    cell.alignment = left_alignment
                else:
                    cell.alignment = right_alignment

        # 自动调整列宽
        for column in ws.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = (max_length + 2) * 1.2
            ws.column_dimensions[column_letter].width = adjusted_width

    def gen_pps_report(self):
        self.copy_assets_to_folder(LocalPath.ASSETS_PATH, copy_index=False)
        pps_datas, time_datas = self.gen_pps_data()

        env = _load_package()
        chart_template = env.get_template("chart.html")

        self._gen_excel()

        self._gen_task(
            chart_template,
            "pps_chart.html",
            title="授时精度",
            chart_js="./assets/js/echarts.min.js",
            test_datas=pps_datas,
        )
        self._gen_task(
            chart_template,
            "time_chart.html",
            title="时间连续性",
            chart_js="./assets/js/echarts.min.js",
            test_datas=time_datas,
        )

        plt.close("all")
        self.__dict__.clear()

    def gen_pps_data(self):
        pps_datas, time_datas = {}, {}
        for file in self.check_list:
            try:
                df = pd.read_csv(
                    os.path.join(self.folder_path, file[:-4] + f"_pps{File.EXT_FILE}"),
                    low_memory=False,
                )

                df_utc_time = self._format_utc_time(df)

                df_pps = df["pps_delta"].fillna(DEFAULT_NULL_VALUE)

                time_datas[file] = [
                    _format_index(df_pps),
                    {"time": df_utc_time["delta"].fillna(DEFAULT_NULL_VALUE).to_list()},
                ]
                pps_datas[file] = [_format_index(df_pps), {"pps": df_pps.to_list()}]
            except FileNotFoundError:
                time_datas[file] = [[], []]
                pps_datas[file] = [[], []]

        return pps_datas, time_datas
