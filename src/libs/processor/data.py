import re
import numpy as np
from typing import Any, Dict, List, Tuple, Optional
from datetime import datetime

from src.util.const import TTFFSignal as ts
from src import NMEAHeader


class TTFFDataProcessor:
    """TTFF 数据处理器"""

    def __init__(
        self,
        ttff_handler_dict: Dict,
        rtk_label: str = "4",
        prefix_list: List[str] = [],
        label: str = NMEAHeader.TTFF_P,
    ):
        self.ttff_handler_dict = ttff_handler_dict
        self.rtk_label = rtk_label
        self.prefix_list = prefix_list or []
        self.label = label

    def extract_all_files_data(self, t_signal, last_ttff_include: bool = False) -> Dict:
        """提取所有文件的数据"""
        extracted_data = {}

        for file in sorted(self.ttff_handler_dict):
            file_data = self.extract_file_data(file, t_signal, last_ttff_include)
            if file_data:
                extracted_data[file] = file_data

        return extracted_data

    def extract_file_data(
        self, file_name: str, t_signal, last_ttff_include: bool = False
    ) -> Optional[Dict]:
        """提取单个文件的数据"""
        file_data = self.ttff_handler_dict.get(file_name)
        if not file_data:
            return None

        ttff_list = file_data["value"]
        prefix_label = file_data["prefix_label"]
        freq = file_data.get("freq", 1)

        # 使用正则表达式分割数据
        regx = re.split(f".*{prefix_label}.*", "".join(ttff_list))

        if len(set(regx[1:-1])) < 2:
            return None

        regx_list = regx[1:] if last_ttff_include else regx[1:-1]

        result = {
            "values": [],
            "format_values": [],
            "fix_unfix_values": [],
            "times_fix_unfix": 0,
            "times_fix_float": 0,
            "times_utc_is_null": 0,
        }

        for m in regx_list:
            if t_signal == ts.s1:
                if self.rtk_label in ["2", "4", "6"]:
                    n, x, fix_time = self.ttff_handler(m, freq)
                    if n >= 0 and fix_time == "":
                        result["times_utc_is_null"] += 1
                    if x > 1:
                        result["times_fix_unfix"] += 1
                        result["fix_unfix_values"].append(1)
                    else:
                        result["fix_unfix_values"].append(0)

                    result["format_values"].append(
                        f"{n}({fix_time}/{x - 1})" if n > 0 else "-1"
                    )
            else:
                n, x, fix_time = self.rtk_handler(m, freq)
                if x > 1:
                    result["times_fix_float"] += 1

            result["values"].append(n)

        return result

    def calculate_statistics(self, values: List[float], t_signal) -> Dict:
        """计算统计信息"""
        if not values:
            return {}

        values_np = np.array(values)
        count = values_np.size
        times_0 = values_np[values_np == -1].size

        stats: dict[str, Any] = {
            "count": count,
            "times_0": times_0,
            "times_0_3": self._count_in_range(values_np, 0, 3),
            "times_3_10": self._count_in_range(values_np, 3, 10),
        }

        if t_signal == ts.s1:
            stats.update(
                {
                    "times_10_20": self._count_in_range(values_np, 10, 20),
                    "times_20_30": self._count_in_range(values_np, 20, 30),
                    "times_30_40": self._count_in_range(values_np, 30, 40),
                    "times_40_50": self._count_in_range(values_np, 40, 50),
                    "times_50_60": self._count_in_range(values_np, 50, 60),
                    "times_60": values_np[values_np >= 60].size,
                }
            )
        else:
            stats.update(
                {
                    "times_10_15": self._count_in_range(values_np, 10, 15),
                    "times_15_20": self._count_in_range(values_np, 15, 20),
                    "times_20_25": self._count_in_range(values_np, 20, 25),
                    "times_25_30": self._count_in_range(values_np, 25, 30),
                    "times_30_35": self._count_in_range(values_np, 30, 35),
                    "times_35_40": self._count_in_range(values_np, 35, 40),
                    "times_40_45": self._count_in_range(values_np, 40, 45),
                    "times_45_50": self._count_in_range(values_np, 45, 50),
                    "times_50_55": self._count_in_range(values_np, 50, 55),
                    "times_55_60": self._count_in_range(values_np, 55, 60),
                    "times_60_65": self._count_in_range(values_np, 60, 65),
                    "times_65_70": self._count_in_range(values_np, 65, 70),
                    "times_70_75": self._count_in_range(values_np, 70, 75),
                    "times_75_80": self._count_in_range(values_np, 75, 80),
                    "times_80_85": self._count_in_range(values_np, 80, 85),
                    "times_85_90": self._count_in_range(values_np, 85, 90),
                    "times_90_95": self._count_in_range(values_np, 90, 95),
                    "times_95_100": self._count_in_range(values_np, 95, 100),
                    "times_100_105": self._count_in_range(values_np, 100, 105),
                    "times_105_110": self._count_in_range(values_np, 105, 110),
                    "times_110_115": self._count_in_range(values_np, 110, 115),
                    "times_115_120": self._count_in_range(values_np, 115, 120),
                    "times_120": values_np[values_np >= 120].size,
                }
            )

        # 计算平均值和成功率
        total_times_np = values_np[values_np != -1]
        total_times = total_times_np.size

        stats["average"] = 0 if total_times == 0 else round(total_times_np.mean(), 1)

        try:
            stats["success_rate"] = f"{round(100 * (1 - times_0 / float(count)), 1)}%"
        except ZeroDivisionError:
            stats["success_rate"] = "ERROR"

        return stats

    def _count_in_range(
        self, values_np: np.ndarray, min_val: float, max_val: float
    ) -> int:
        """计算在指定范围内的数量"""
        return values_np[(values_np >= min_val) & (values_np < max_val)].size

    _TTFF_PATTERN = re.compile(r",E,[1-6],")
    _TTFF_SPLIT_PATTERN = re.compile(r"E,[12456],")
    _FAIL_LABEL = -1.0

    def ttff_handler(self, m: str, freq: int) -> Tuple[float, int, str]:
        """TTFF数据处理"""
        if not self._TTFF_PATTERN.search(m):
            return (self._FAIL_LABEL, 0, "")

        parts = self._TTFF_SPLIT_PATTERN.split(m)
        start_data = parts[0]
        n = start_data.count("\n")  # 统计GGA条数

        fix_time = ""
        if start_data_strip := start_data.strip():
            last_data = start_data_strip.split("\n")[-1]
            if "," in last_data:
                fields = last_data.strip(",").split(",")
                if len(fields) >= 2:
                    fix_time = fields[1]

        x = max((p.count("\n") for p in parts[1:-1]), default=1)

        return (n / freq, x, fix_time)

    def rtk_handler(self, m: str, freq: int) -> Tuple[float, int, str]:
        """RTK数据处理"""
        fix_time = ""
        if m.count(f",E,{self.rtk_label},"):
            m_e_0 = re.split(r",E,[123456],", m)
            m_e_4 = re.split(f",E,{self.rtk_label},", m)
            m_list = m_e_0[0].strip("\n").split("\n")
            if (m_list[-1].strip()) and (m_list[-1].find(",")):
                m_e_0_4 = re.split(f"E,{self.rtk_label},", m)
                n_1_4 = (m_e_0_4[0].count("\n")) - (m_e_0[0].count("\n"))
                fix_time = m_e_0_4[0].split("\n")[-1].strip(",").split(",")[1]
                n_1_4 = n_1_4 / freq
            else:
                n_1_4 = self._FAIL_LABEL

            x = max([e.count("\n") for e in m_e_4[1:-1]]) if m_e_4[1:-1] else 1

            return n_1_4, x, fix_time

        return self._FAIL_LABEL, 0, ""

    @staticmethod
    def get_utc_date_time(utc_time: str) -> str:
        """获取UTC日期时间"""
        try:
            ptime = datetime.strptime(f"010123{utc_time}", "%m%d%y%H%M%S.%f")
            utc_date_time = ptime.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
        except ValueError:
            utc_date_time = ""

        return utc_date_time
