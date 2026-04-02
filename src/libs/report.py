import asyncio
import os
from pathlib import Path
import re
import shutil
from typing import Any, Optional
import aiofiles
from jinja2 import Environment, PackageLoader
from matplotlib import pyplot as plt
import numpy as np
import pandas as pd
from openpyxl.styles import Font, Alignment, Border, Side

from src import Point
from src.util.const import File, LocalPath
from src.libs.nmea import filter_list

DEFAULT_NULL_VALUE = ""

plt.rcParams["font.family"] = "SimHei"
plt.rcParams["axes.unicode_minus"] = False

TIME_UNIT = "ms"
FIX_LABEL = "定位符"

loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

write_file_task_list: list = []


async def wait_write_file_task_done_async():
    if write_file_task_list:
        await asyncio.gather(*write_file_task_list)
        write_file_task_list.clear()


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
    env = Environment(loader=PackageLoader("res", "templates"))
    # 注册自定义过滤器
    env.filters["clean_id"] = clean_id
    return env


def _format_index(df):
    pattern = re.compile(r"[ T\-:]")
    return [pattern.sub("", element)[4:] for element in df.index.to_list()]


class Report:
    def __init__(
        self,
        df_result: pd.DataFrame,
        folder_path: str,
        data_path: str,
        point: Point,
        nav_log: str,
        log_info: str,
        check_list: list[str],
        is_moving: bool = False,
        is_ttff: bool = False,
        begin_time: Optional[pd.Timestamp] = None,
        end_time: Optional[pd.Timestamp] = None,
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

        self.csv_path = Path(folder_path) / ("../all/data" if begin_time else "data")

    def gen_precision_report(self):
        self.copy_assets_to_folder(LocalPath.ASSETS_PATH)

        self._get_precision_data()

        env = _load_package()
        chart_tempate = env.get_template("chart.html")

        self._gen_excel_task()

        self._gen_task(
            env.get_template("report.html"),
            "report.html",
            title="Report",
            point=self.point,
            nav_log=self.nav_log,
            log_info=self.log_info,
            table_data=self.df_result.to_html(table_id="table_id"),
        )

        self._gen_task(
            chart_tempate,
            "RTK时延.html",
            plot=True,
            title="RTK delay",
            plot_item="delay",
            description="<p>统计GGA中RTK时延</p>",
            test_datas=self.__dict__.get("_delay", {}),
        )
        self._gen_task(
            chart_tempate,
            "卫星数.html",
            plot=True,
            title="Satellites",
            plot_item="satellites",
            description="<p>统计GGA中卫星个数</p>",
            test_datas=self.__dict__.get("_satellites", {}),
        )
        self._gen_task(
            chart_tempate,
            "时间连续性.html",
            plot=True,
            plot_item=TIME_UNIT,
            title="Time Continuity",
            description=f"<p>统计RMC时间连续性，单位为{TIME_UNIT}</p>",
            test_datas=self.__dict__.get("_time", {}),
        )
        self._gen_task(
            chart_tempate,
            "GPS_CN0.html",
            title="GPS CN0",
            test_datas=self.__dict__.get("_gps", {}),
        )
        self._gen_task(
            chart_tempate,
            "BDS_1_CN0.html",
            title="BDS CN0",
            test_datas=self.__dict__.get("_bds_1", {}),
        )
        self._gen_task(
            chart_tempate,
            "BDS_2_CN0.html",
            title="BDS CN0",
            test_datas=self.__dict__.get("_bds_2", {}),
        )
        self._gen_task(
            chart_tempate,
            "GAL_CN0.html",
            title="GAL CN0",
            test_datas=self.__dict__.get("_gal", {}),
        )
        self._gen_task(
            chart_tempate,
            "GLO_CN0.html",
            title="GLO CN0",
            test_datas=self.__dict__.get("_glo", {}),
        )
        self._gen_task(
            chart_tempate,
            "速度误差.html",
            plot=True,
            title="Speed",
            plot_item="speed",
            description="<p>统计RMC中速度误差</p>",
            test_datas=self.__dict__.get("_speed", {}),
        )
        self._gen_task(
            chart_tempate,
            "水平误差2D.html",
            title="所有解误差",
            description="<p>统计所有解水平/高程误差</p>",
            test_datas=self.__dict__.get("_precision", {}),
        )
        self._gen_task(
            chart_tempate,
            "DOP值.html",
            title="DOP",
            description="<p>统计GSA语句中DOP值</p>",
            test_datas=self.__dict__.get("_dop", {}),
        )
        self._gen_task(
            chart_tempate,
            "固定解误差.html",
            title="固定解误差",
            description="<p>统计固定解水平/高程误差</p>",
            test_datas=self.__dict__.get("_fix_precision", {}),
        )
        self._gen_task(
            chart_tempate,
            "定位标识符.html",
            title="定位标识符",
            description="<p>统计GGA中定位标识符</p>",
            test_datas=self.__dict__.get("_label", {}),
        )

        loop.run_until_complete(wait_write_file_task_done_async())

    def copy_assets_to_folder(self, assets_path: Path):
        target_path = Path(self.folder_path)

        # 如果目标目录不存在，创建它
        target_path.mkdir(parents=True, exist_ok=True)

        # 复制整个目录树
        shutil.copytree(assets_path, target_path / "assets", dirs_exist_ok=True)
        shutil.copy(LocalPath.TEMPLATE_PATH / "index.html", target_path)

    def _get_precision_data(self):
        gps_dict: dict[str, Any] = {}
        bds_1_dict: dict[str, Any] = {}
        bds_2_dict: dict[str, Any] = {}
        gal_dict: dict[str, Any] = {}
        glo_dict: dict[str, Any] = {}
        dop_dict: dict[str, Any] = {}
        label_dict: dict[str, Any] = {}
        delay_dict: dict[str, Any] = {}
        satellites_dict: dict[str, Any] = {}
        time_dict: dict[str, Any] = {}
        speed_dict: dict[str, Any] = {}
        precision_dict: dict[str, Any] = {}
        fix_precision_dict: dict[str, Any] = {}

        for file in self.check_list:
            try:
                df = pd.read_csv(
                    os.path.join(
                        self.csv_path, file[:-4] + f"{File.ORIGINAL_FILE_EXT}"
                    ),
                    low_memory=False,
                )

                df_utc_time = self._format_utc_time(df)
                if self.begin_time and self.end_time:
                    df.index = pd.to_datetime(df.index, errors="coerce")
                    df = df[(df.index >= self.begin_time) & (df.index <= self.end_time)]
                    df.index = df.index.astype(str)
                    # df = df.loc[self.begin_time : self.end_time]

                df_delay = df["delay"].fillna(DEFAULT_NULL_VALUE)
                df_satellites = df["satellites"].fillna(DEFAULT_NULL_VALUE)
                df_label = df["label"].fillna(DEFAULT_NULL_VALUE)

                df_snr = df[filter_list]

                delay_dict[file] = [
                    _format_index(df_delay),
                    {"delay": df_delay.to_list()},
                ]
                satellites_dict[file] = [
                    _format_index(df_satellites),
                    {"satellites": df_satellites.to_list()},
                ]

                label_dict[file] = [
                    _format_index(df_label),
                    {"label": df_label.to_list()},
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

            except FileNotFoundError:
                delay_dict[file] = [[], []]
                satellites_dict[file] = [[], []]
                label_dict[file] = [[], []]
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

            try:
                file_path = os.path.join(
                    self.csv_path, file[:-4] + f"{File.CALC_FILE_EXT}"
                )

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
                    {"speed": df_speed.to_list()},
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
                            "水平精度": df_distance["distance"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "法向精度": df_distance["hgt_delta"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]
                    fix_precision_dict[file] = [
                        _format_index(df_4_distance),
                        {
                            "水平精度": df_4_distance["distance"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "法向精度": df_4_distance["hgt_delta"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
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
                            "水平精度": df_distance["distance"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "法向精度": df_distance["hgt_delta"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]
                    fix_precision_dict[file] = [
                        _format_index(df_4_distance),
                        {
                            "水平精度": df_4_distance["distance"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                            "法向精度": df_4_distance["hgt_delta"]
                            .fillna(DEFAULT_NULL_VALUE)
                            .to_list(),
                        },
                    ]
            except FileNotFoundError:
                speed_dict[file] = [[], []]
                precision_dict[file] = [[], []]
                fix_precision_dict[file] = [[], []]

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
                "_label": label_dict,
                "_satellites": satellites_dict,
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

    async def _write_file(self, filename, template, kwargs=None):
        if kwargs is None:
            kwargs = {}

        async with aiofiles.open(
            os.path.join(self.data_path, filename), encoding="utf-8", mode="w"
        ) as f:
            await f.write(template.render(**kwargs))

    async def _write_file_async(self, filename, template, **kwargs):
        await self._write_file(filename, template, kwargs)

    def _start_task(self, template, filename, plot=True, **kwargs):
        if plot:
            self._plot_png(filename[:-5], **kwargs)
        task = loop.create_task(self._write_file_async(filename, template, **kwargs))
        write_file_task_list.append(task)

    def _gen_task(self, template, filename, plot=False, **kwargs):
        self._start_task(template, filename, plot, **kwargs)

    def _gen_excel_task(self):
        task = loop.create_task(self._gen_excel())
        write_file_task_list.append(task)

    def _plot_png(self, filename, **kwargs):
        plot_data = kwargs["test_datas"]
        title = kwargs["title"]
        num = len(plot_data.keys())
        canvas_size = calc_canvas_size(num)

        fig = plt.figure(constrained_layout=True)
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
        plt.close(fig)

    async def _gen_excel(self):
        with pd.ExcelWriter(
            os.path.join(self.folder_path, "report.xlsx"), engine="openpyxl"
        ) as writer:
            self.df_result.to_excel(writer, sheet_name="Report")

            # 获取工作表对象
            worksheet = writer.sheets["Report"]

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
            for row in worksheet.iter_rows(min_row=1, max_row=worksheet.max_row):
                for cell in row:
                    cell.font = data_font
                    cell.border = border
                    if cell.column_letter == "A":
                        cell.alignment = left_alignment
                    else:
                        cell.alignment = right_alignment

            # 自动调整列宽
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = (max_length + 2) * 1.2
                worksheet.column_dimensions[column_letter].width = adjusted_width
