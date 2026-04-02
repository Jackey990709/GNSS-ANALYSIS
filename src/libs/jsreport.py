import copy
import json
import logging
import os
import shutil
from typing import Any

from jinja2 import Environment, PackageLoader
import numpy as np
import pandas as pd
from src.libs.nmea import Default
from src.libs.plot import plot_bar, plot_data
from src.util.const import LocalPath
from src.util.param import PERCENT_68, PERCENT_95, PERCENT_99, percentiles, PERCENT_50

logger = logging.getLogger(__name__)

sys_freq_map = (
    ("GPS", "L1"),
    ("GPS", "L2"),
    ("GPS", "L5"),
    ("BEIDOU", "B1I"),
    ("BEIDOU", "B2I"),
    ("BEIDOU", "B1C"),
    ("BEIDOU", "B2a"),
    ("BEIDOU", "B2b"),
    ("BEIDOU", "B3I"),
    ("GLONASS", "G1"),
    ("GLONASS", "G2"),
    ("GALILEO", "E1"),
    ("GALILEO", "E5a"),
    ("GALILEO", "E5b"),
    ("GALILEO", "E6"),
    # ("QZSS", "QZL1"),
    # ("QZSS", "QZL2"),
    # ("QZSS", "QZL5"),
)

sys_map = {
    "GPS": "gps",
    "BEIDOU": "bds",
    "GALILEO": "gal",
    "GLONASS": "glo",
    # "QZSS": "qzs",
}


class JsReport:
    def __init__(self, scenes):
        self.scenes = scenes
        self.report_data = {
            "config": {
                "devices": [],
                "scenes": [],
            },
            "summary": {"scenes": {}},
            "scenes": {},
        }

        self.cep_data: dict[str, Any] = {"axis": [], "scenes": {}}
        self.track_data: dict[str, Any] = {}

    def init_report_data(self, check_list):
        self.report_data["config"]["scenes"] = self.scenes
        device_list = [e[:-4] for e in check_list]
        self.report_data["config"]["devices"] = device_list

        cn0_dict = {
            "GPS": {},
            "BEIDOU": {},
            "GALILEO": {},
            "GLONASS": {},
        }

        for scene in self.scenes:
            self.report_data["summary"]["scenes"][scene["id"]] = {
                device: {} for device in device_list
            }

            self.report_data["scenes"][scene["id"]] = {
                "id": scene["id"],
                "name": scene["name"],
                "device_stats": {
                    device: {"cn0_stats": copy.deepcopy(cn0_dict)}
                    for device in device_list
                },
            }

            self.cep_data["scenes"][scene["name"]] = {
                "horz_cep50": [],
                "horz_cep68": [],
                "horz_cep95": [],
                "horz_cep99": [],
                "horz_cep100": [],
                "vert_cep50": [],
                "vert_cep68": [],
                "vert_cep95": [],
                "vert_cep99": [],
                "vert_cep100": [],
                "speed_cep50": [],
                "speed_cep68": [],
                "speed_cep95": [],
                "speed_cep99": [],
                "speed_cep100": [],
            }

    def gen_scene_result(
        self,
        df: pd.DataFrame,
        folderpath: str,
        freq: int = -1,
        file: str = "Ground Truth",
        action: int = 0,
        callback=print,
    ):
        """freq = -1时，传的为参考文件"""
        if not action:
            return

        if freq != -1:
            self.cep_data["axis"].append(file)

        for scene in self.scenes:
            begin_time = pd.Timestamp(scene["begin_time"])
            end_time = pd.Timestamp(scene["end_time"])

            df_scene = df[(df.index >= begin_time) & (df.index <= end_time)]
            if df_scene.empty:
                callback(
                    f"<font color='red'>{scene['name']} {begin_time} {end_time}场景为空</font>"
                )
                continue

            # if freq != -1:
            #     self._gen_csv_file(df_scene, folderpath, scene, file)

            self.gen_track_data(
                df_scene[df_scene["label"] != "0"], scene["name"], freq, file
            )

            if freq == -1:
                continue

            self.calc_cep(df_scene[df_scene["label"] != "0"], scene["name"])

            total_epochs = (
                int((df_scene.index[-1] - df_scene.index[0]).total_seconds()) * freq + 1
            )
            total_points = df_scene.shape[0]

            for label in ["0", "1", "2", "4", "5", "6", "all"]:
                self.calc_result(
                    df_scene,
                    scene,
                    total_epochs,
                    file,
                    label=label,
                )

            self.calc_quality_counts(
                df_scene, scene["name"], file, total_epochs, total_points
            )
            # logger.warning(f"{self.report_data = }")

            self.plot_error_graph(
                df_scene[df_scene["label"] != "0"],
                folderpath,
                f"{scene['name']}_{file}",
            )

    def _gen_csv_file(self, df: pd.DataFrame, folderpath: str, scene: dict, file: str):
        csv_path = os.path.join(folderpath, "csv")
        os.makedirs(csv_path, exist_ok=True)
        df.to_csv(os.path.join(csv_path, f"{scene['name']}_{file}.csv"))

    def gen_track_data(self, df: pd.DataFrame, scene_name: str, freq: int, file: str):
        df = df.copy()
        df["label"] = df["label"].astype(int)
        df["timestamp"] = pd.Series(df.index).dt.strftime("%H:%M:%S.%f").str[:-4].values
        df.rename(
            columns={"lat": "lat", "lng": "lon", "hgt": "altitude", "label": "quality"},
            inplace=True,
        )

        self.track_data.setdefault(scene_name, []).append(
            {
                "name": file,
                "positions": df[
                    ["lat", "lon", "altitude", "timestamp", "quality"]
                ].to_dict(orient="records"),
                "is_truth": False if freq != -1 else True,
            }
        )

    def gen_track_file(self, folderpath: str):
        track_path = os.path.join(folderpath, "tracks")
        os.makedirs(track_path, exist_ok=True)

        env = Environment(loader=PackageLoader("res", "templates"))
        template = env.get_template("track.html")

        for scene_name, tracks in self.track_data.items():
            with open(
                os.path.join(track_path, f"{scene_name}.json"),
                encoding="utf-8",
                mode="w",
            ) as f:
                f.write(json.dumps({"files": tracks}, indent=2, ensure_ascii=False))

            with open(
                os.path.join(track_path, f"{scene_name}_trajectory.html"),
                encoding="utf-8",
                mode="w",
            ) as f:
                f.write(
                    template.render(
                        initial_data={"files": tracks}, scene_name=scene_name
                    )
                )

        shutil.copy(LocalPath.C_INDEX_FILE, os.path.join(folderpath, f"index.html"))

    def calc_result(
        self,
        df: pd.DataFrame,
        scene: dict,
        total_epochs: int,
        file: str,
        label: str = "all",
    ):
        if label != "all":
            df = df[df["label"] == label]

        if df.empty:
            return

        if label == "all":
            df_cn0 = df[df.index.strftime("%f").str.endswith("000000")]  # type: ignore
            for sat_sys, sat_freq in sys_freq_map:
                self.gen_snr(df_cn0, scene["name"], file, sat_sys, sat_freq)

        points = df.shape[0]
        df = df[df["label"] != "0"]
        df_h_describe = df["distance"].describe(percentiles=percentiles)
        df_v_describe = df["hgt_delta"].describe(percentiles=percentiles)
        df_speed_describe = df["speed_delta"].describe(percentiles=percentiles)

        h_50 = round(df_h_describe[PERCENT_50], Default.KEEP_DECIMAL_DIGIT)
        h_68 = round(df_h_describe[PERCENT_68], Default.KEEP_DECIMAL_DIGIT)
        h_95 = round(df_h_describe[PERCENT_95], Default.KEEP_DECIMAL_DIGIT)
        h_99 = round(df_h_describe[PERCENT_99], Default.KEEP_DECIMAL_DIGIT)
        h_100 = round(df_h_describe["max"], Default.KEEP_DECIMAL_DIGIT)

        v_50 = round(df_v_describe[PERCENT_50], Default.KEEP_DECIMAL_DIGIT)
        v_68 = round(df_v_describe[PERCENT_68], Default.KEEP_DECIMAL_DIGIT)
        v_95 = round(df_v_describe[PERCENT_95], Default.KEEP_DECIMAL_DIGIT)
        v_99 = round(df_v_describe[PERCENT_99], Default.KEEP_DECIMAL_DIGIT)
        v_100 = round(df_v_describe["max"], Default.KEEP_DECIMAL_DIGIT)

        s_50 = round(df_speed_describe[PERCENT_50], Default.KEEP_DECIMAL_DIGIT)
        s_68 = round(df_speed_describe[PERCENT_68], Default.KEEP_DECIMAL_DIGIT)
        s_95 = round(df_speed_describe[PERCENT_95], Default.KEEP_DECIMAL_DIGIT)
        s_99 = round(df_speed_describe[PERCENT_99], Default.KEEP_DECIMAL_DIGIT)
        s_100 = round(df_speed_describe["max"], Default.KEEP_DECIMAL_DIGIT)

        self.report_data["summary"]["scenes"][scene["name"]][file][label] = {
            "points": points,
            "total_epochs": total_epochs,
            "horz_cep50": "-" if np.isnan(h_50) else h_50,
            "horz_cep68": "-" if np.isnan(h_68) else h_68,
            "horz_cep95": "-" if np.isnan(h_95) else h_95,
            "horz_cep99": "-" if np.isnan(h_99) else h_99,
            "horz_cep100": "-" if np.isnan(h_100) else h_100,
            "vert_cep50": "-" if np.isnan(v_50) else v_50,
            "vert_cep68": "-" if np.isnan(v_68) else v_68,
            "vert_cep95": "-" if np.isnan(v_95) else v_95,
            "vert_cep99": "-" if np.isnan(v_99) else v_99,
            "vert_cep100": "-" if np.isnan(v_100) else v_100,
            "speed_cep50": "-" if np.isnan(s_50) else s_50,
            "speed_cep68": "-" if np.isnan(s_68) else s_68,
            "speed_cep95": "-" if np.isnan(s_95) else s_95,
            "speed_cep99": "-" if np.isnan(s_99) else s_99,
            "speed_cep100": "-" if np.isnan(s_100) else s_100,
        }

    def calc_cep(self, df: pd.DataFrame, scene_name: str):
        df_h_describe = df["distance"].describe(percentiles=percentiles)
        df_v_describe = df["hgt_delta"].describe(percentiles=percentiles)
        df_speed_describe = df["speed_delta"].describe(percentiles=percentiles)

        h_50 = round(df_h_describe[PERCENT_50], Default.KEEP_DECIMAL_DIGIT)
        h_68 = round(df_h_describe[PERCENT_68], Default.KEEP_DECIMAL_DIGIT)
        h_95 = round(df_h_describe[PERCENT_95], Default.KEEP_DECIMAL_DIGIT)
        h_99 = round(df_h_describe[PERCENT_99], Default.KEEP_DECIMAL_DIGIT)
        h_100 = round(df_h_describe["max"], Default.KEEP_DECIMAL_DIGIT)

        v_50 = round(df_v_describe[PERCENT_50], Default.KEEP_DECIMAL_DIGIT)
        v_68 = round(df_v_describe[PERCENT_68], Default.KEEP_DECIMAL_DIGIT)
        v_95 = round(df_v_describe[PERCENT_95], Default.KEEP_DECIMAL_DIGIT)
        v_99 = round(df_v_describe[PERCENT_99], Default.KEEP_DECIMAL_DIGIT)
        v_100 = round(df_v_describe["max"], Default.KEEP_DECIMAL_DIGIT)

        s_50 = round(df_speed_describe[PERCENT_50], Default.KEEP_DECIMAL_DIGIT)
        s_68 = round(df_speed_describe[PERCENT_68], Default.KEEP_DECIMAL_DIGIT)
        s_95 = round(df_speed_describe[PERCENT_95], Default.KEEP_DECIMAL_DIGIT)
        s_99 = round(df_speed_describe[PERCENT_99], Default.KEEP_DECIMAL_DIGIT)
        s_100 = round(df_speed_describe["max"], Default.KEEP_DECIMAL_DIGIT)

        self.cep_data["scenes"][scene_name][f"horz_cep50"].append(
            "-" if np.isnan(h_50) else h_50
        )
        self.cep_data["scenes"][scene_name][f"horz_cep68"].append(
            "-" if np.isnan(h_68) else h_68
        )
        self.cep_data["scenes"][scene_name][f"horz_cep95"].append(
            "-" if np.isnan(h_95) else h_95
        )
        self.cep_data["scenes"][scene_name][f"horz_cep99"].append(
            "-" if np.isnan(h_99) else h_99
        )
        self.cep_data["scenes"][scene_name][f"horz_cep100"].append(
            "-" if np.isnan(h_100) else h_100
        )

        self.cep_data["scenes"][scene_name][f"vert_cep50"].append(
            "-" if np.isnan(v_50) else v_50
        )
        self.cep_data["scenes"][scene_name][f"vert_cep68"].append(
            "-" if np.isnan(v_68) else v_68
        )
        self.cep_data["scenes"][scene_name][f"vert_cep95"].append(
            "-" if np.isnan(v_95) else v_95
        )
        self.cep_data["scenes"][scene_name][f"vert_cep99"].append(
            "-" if np.isnan(v_99) else v_99
        )
        self.cep_data["scenes"][scene_name][f"vert_cep100"].append(
            "-" if np.isnan(v_100) else v_100
        )

        self.cep_data["scenes"][scene_name][f"speed_cep50"].append(
            "-" if np.isnan(s_50) else s_50
        )
        self.cep_data["scenes"][scene_name][f"speed_cep68"].append(
            "-" if np.isnan(s_68) else s_68
        )
        self.cep_data["scenes"][scene_name][f"speed_cep95"].append(
            "-" if np.isnan(s_95) else s_95
        )
        self.cep_data["scenes"][scene_name][f"speed_cep99"].append(
            "-" if np.isnan(s_99) else s_99
        )
        self.cep_data["scenes"][scene_name][f"speed_cep100"].append(
            "-" if np.isnan(s_100) else s_100
        )

    def gen_snr(
        self, df: pd.DataFrame, scene_name: str, device, sat_sys: str, sat_freq: str
    ):
        max_value = df[f"{sys_map[sat_sys]}_{sat_freq.lower()}_max"].max()
        min_value = df[f"{sys_map[sat_sys]}_{sat_freq.lower()}_min"].min()
        count_value = df[f"{sys_map[sat_sys]}_{sat_freq.lower()}_cnt"].sum()
        sum_value = df[f"{sys_map[sat_sys]}_{sat_freq.lower()}_sum"].sum()
        avg_value = sum_value / count_value if count_value != 0 else np.nan

        max_value = "-" if np.isnan(max_value) else int(max_value)
        min_value = "-" if np.isnan(min_value) else int(min_value)
        avg_value = "-" if np.isnan(avg_value) else int(avg_value)
        count_value = "-" if count_value == 0 else int(count_value)

        self.report_data["scenes"][scene_name]["device_stats"][device]["cn0_stats"][
            sat_sys
        ][sat_freq] = {
            "avg": avg_value,
            "max": max_value,
            "min": min_value,
            "count": count_value,
        }

    def calc_quality_counts(
        self,
        df: pd.DataFrame,
        scene_name,
        device: str,
        total_epochs: int,
        total_points: int,
    ):
        self.report_data["scenes"][scene_name]["device_stats"][device][
            "quality_counts"
        ] = {
            "0": df[df["label"] == "0"].shape[0],
            "1": df[df["label"] == "1"].shape[0],
            "2": df[df["label"] == "2"].shape[0],
            "4": df[df["label"] == "4"].shape[0],
            "5": df[df["label"] == "5"].shape[0],
            "6": df[df["label"] == "6"].shape[0],
            "all": total_points,
            "total_epochs": total_epochs,
        }

    def plot_error_graph(self, df: pd.DataFrame, folderpath: str, scene_name: str):
        if df.empty:
            return
        horz_error = df["distance"].fillna(np.nan)  # 水平误差数据
        vert_error = df["hgt_delta"].fillna(np.nan)  # 垂直误差数据
        speed_error = df["speed_delta"].fillna(np.nan)  # 速度误差数据
        axis = df.index.to_list()

        image_path = os.path.join(folderpath, "images")
        os.makedirs(image_path, exist_ok=True)

        plot_data(
            os.path.join(image_path, f"{scene_name}_error_curve.png"),
            {
                # "axis": np.array([str(t.time())[:-4] for t in axis]),
                "axis": np.arange(len(axis)),
                "horz_error": horz_error.to_list(),
                "vert_error": vert_error.to_list(),
                "speed_error": speed_error.to_list(),
            },
        )

    def plot_cep_graph(self, folderpath: str):
        axis = self.cep_data["axis"]
        image_path = os.path.join(folderpath, "images")
        os.makedirs(image_path, exist_ok=True)
        for scene_name, scene_data in self.cep_data["scenes"].items():
            for item, data in scene_data.items():
                plot_bar(
                    os.path.join(image_path, f"{scene_name}_{item}_bar.png"),
                    axis,
                    data,
                    f"CEP值 - {item}",
                    "CEP值",
                )

    def write_to_js(self, folderpath: str = "report_data.js"):
        out_str = f"window.reportData = {json.dumps(self.report_data, indent=4, ensure_ascii=False)}"
        data_path = os.path.join(folderpath, "data")
        os.makedirs(data_path, exist_ok=True)
        with open(
            os.path.join(data_path, "report_data.js"), "w", encoding="utf-8"
        ) as f:
            f.write(out_str)

        shutil.copytree(LocalPath.CUSTOMER_PATH, folderpath, dirs_exist_ok=True)
