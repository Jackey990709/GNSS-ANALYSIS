import enum
import os
from pathlib import Path


class ExcelCellLabel:
    LABEL_TTFF: str = "TTFF"
    LABEL_RTK: str = "RTK"
    LABEL_DEVICE: str = "Test Device"
    LABEL_GT_60: str = "大于60秒的次数"
    LABEL_50_60: str = "50~60秒的次数"
    LABEL_40_50: str = "40~50秒的次数"
    LABEL_30_40: str = "30~40秒的次数"
    LABEL_20_30: str = "20~30秒的次数"
    LABEL_10_20: str = "10~20秒的次数"

    LABEL_GT_120: str = "大于120秒的次数"
    LABEL_115_120: str = "115~120秒的次数"
    LABEL_110_115: str = "110~115秒的次数"
    LABEL_105_110: str = "105~110秒的次数"
    LABEL_100_105: str = "100~105秒的次数"
    LABEL_95_100: str = "95~100秒的次数"
    LABEL_90_95: str = "90~95秒的次数"
    LABEL_85_90: str = "85~90秒的次数"
    LABEL_80_85: str = "80~85秒的次数"
    LABEL_75_80: str = "75~80秒的次数"
    LABEL_70_75: str = "70~75秒的次数"
    LABEL_65_70: str = "65~70秒的次数"
    LABEL_60_65: str = "60~65秒的次数"
    LABEL_55_60: str = "55~60秒的次数"
    LABEL_50_55: str = "50~55秒的次数"
    LABEL_45_50: str = "45~50秒的次数"
    LABEL_40_45: str = "40~45秒的次数"
    LABEL_35_40: str = "35~40秒的次数"
    LABEL_30_35: str = "30~35秒的次数"
    LABEL_25_30: str = "25~30秒的次数"
    LABEL_20_25: str = "20~25秒的次数"
    LABEL_15_20: str = "15~20秒的次数"
    LABEL_10_15: str = "10~15秒的次数"
    LABEL_3_10: str = "3~10秒的次数"
    LABEL_0_3: str = "0~3秒的次数"
    LABEL_FIX_SUCCESS_RATE: str = "定位成功率"
    LABEL_AVERAGE: str = "所有次数的平均值"
    LABEL_ABNORMAL_TIMES: str = "异常次数"
    LABEL_NUMBER: str = "序号"
    LABEL_TOTAL_TIMES: str = "测试总次数"
    LABEL_CONVERGE_FAIL_TIMES: str = "未收敛成功的次数"
    LABEL_CONVERGE_AVERAGE: str = "收敛成功平均时长"
    LABEL_CONVERGE_SUCCESS_RATE: str = "收敛成功率"

    LABEL_UNFIX_TIMES: str = "未定位的次数"
    LABEL_FIX_UNFIX_TIMES = "定位不定位的次数"
    LABEL_FIX_FLOAT_TIMES = "跳出固定解次数"
    LABEL_FIX_PPP_TIMES = "跳出PPP次数"
    LABEL_FIX_UTC_NULL = "定位(UTC为空)次数"
    LABEL_UNHEADING_TIMES = "未定向次数"
    LABEL_HEADING_UNHEADING_TIMES = "定向不定向次数"
    LABEL_HEADING_UTC_NULL = "定向(UTC为空)次数"
    LABEL_HEADING_SUCCESS_RATE: str = "定向成功率"


class LocalPath:
    LOCAL_PATH = os.getenv("LOCALAPPDATA", ".")
    LOCAL_FOLDER_PATH = Path(LOCAL_PATH, "tool_settings")
    YAML_FILE = Path(LOCAL_FOLDER_PATH, "settings.yml")

    RES_PATH = Path(os.getcwd(), "res")
    TEMPLATE_PATH = Path(RES_PATH, "templates")
    ASSETS_PATH = Path(TEMPLATE_PATH, "assets")
    CUSTOMER_PATH = Path(TEMPLATE_PATH, "customer")
    C_INDEX_FILE = Path(TEMPLATE_PATH, "cIndex.html")
    REPORT_JSON = Path(os.getcwd(), "REPORT-UTC.json")


class TTFFSignal(enum.Enum):
    s1 = 0  # TTFF
    s2 = 1  # RTK


class File:
    ORIGINAL_FILE_EXT = ".ori.csv"
    CALC_FILE_EXT = ".cal.csv"
