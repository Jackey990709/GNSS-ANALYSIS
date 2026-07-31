import os

import numpy as np
import pandas as pd

from src.util import utils


def nav_log_info(nav_log, log_info, temp_log_info, file, callback):
    if temp_log_info:
        log_info += (
            f'<p style="color:blue"><b><a name="{file}">{file}异常信息：</a></b></p>'
            + temp_log_info
        )
        nav_log += f'<p><a href="#{file}">{file}异常信息</a></p>'

    return nav_log, log_info


def update_error_dict(line: bytes, error_dict: dict, error_list: list[bytes]):
    for err in error_list:
        if err in line:
            err_str = line.strip().decode(errors="ignore").strip()
            error_dict[err_str] = error_dict.get(err_str, 0) + 1
            break


def print_error_info(error_dict: dict, callback):
    for err in error_dict.keys():
        callback(f'<font color="red">检测到{err}异常</font>')


def handle_log_info(log_info: str, temp_log_info: str, df: pd.DataFrame) -> str:
    if df is None:
        log_info += f"{temp_log_info}<br>"
    else:
        if not df.empty:
            log_info += f"{temp_log_info}<br>"
            if isinstance(df, pd.Series):
                for e in df:
                    log_info += f"{e}<br>"

            if isinstance(df, pd.DataFrame):
                for e in df.iterrows():
                    log_info += f"{e}<br>"
            log_info += f"<br>"
    return log_info


def get_duplicate_e_info(df, e="utc_date_time"):
    if not df[e].is_unique:
        data1 = df[e].drop_duplicates(keep=False)
        data2 = df[e].drop_duplicates(keep="first")
        return pd.concat([data1, data2]).drop_duplicates(keep=False)
    return pd.Series([], dtype="object")


def format_pd(
    df: pd.DataFrame, log_info: str = "", label: str = "ksxt", handle_log=True
):
    df.dropna(subset=["utc_date_time"], inplace=True)
    # df_log = get_duplicate_e_info(df)
    # if handle_log:
    #     log_info = handle_log_info(log_info, f"{label}语句重复输出:", df_log)

    df = df.drop_duplicates(subset=["utc_date_time"], keep="first")
    df.reset_index(inplace=True)  # 重置索引，解决丢数/重复数据导致的索引不连续
    # df = df.copy()
    first_valid_index = df["utc_date_time"].first_valid_index()
    last_valid_index = df["utc_date_time"].last_valid_index()
    df["utc_date_time"] = pd.to_datetime(df["utc_date_time"])
    freq = utils.get_freq(df["utc_date_time"].to_numpy())
    # log_info = _handle_time_continuity(df, freq, log_info)
    df.set_index("utc_date_time", inplace=True)

    return df, freq, log_info, first_valid_index, last_valid_index


def get_expect_valid_value(
    df: pd.DataFrame,
    freq,
    df_total,
    first_valid_index,
    last_valid_index,
    label="heading",
) -> tuple[int, int]:
    df_expect = 0
    try:
        df_expect = (
            ((df.index[-1] - df.index[0]).total_seconds()) * freq
            + 1
            + first_valid_index
            + df_total
            - last_valid_index
            - 1
        )
    except IndexError:
        ...

    return df_expect, df[label].dropna().size


def write_to_file(df: pd.DataFrame, result_path: str, filename, index=True):
    try:
        if not index:
            df.to_csv(os.path.join(result_path, filename), index=index)
        else:
            if "index" in df.columns:
                df.drop(columns=["index"]).to_csv(
                    os.path.join(result_path, filename), index=index
                )
            else:
                df.to_csv(os.path.join(result_path, filename))
    except PermissionError:
        # with open(
        #     os.path.join("\\".join(result_path.split("\\")[:-1]), "debug.txt"), "a"
        # ) as f:
        #     f.write(traceback.format_exc())
        raise Exception


def angle_diff(value, ref):
    """计算两个角度之间的最小绝对差值（0~180°），处理 360° 跨零。"""
    # 如果 | POS_Heading – DUT_Heading | > 180°
    # 则 | POS_Heading – DUT_Heading | - 360°再取绝对值，得到HeadingErr

    diff = abs(value - ref)
    return np.where(diff <= 180, diff, 360 - diff)
