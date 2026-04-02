CEP50 = "CEP50"
CEP68 = "CEP68"
CEP95 = "CEP95"
CEP99 = "CEP99"

percentiles = [0.99, 0.95, 0.68, 0.50]
describe_list = ["99%", "95%", "68%", "50%"]

PERCENT_50 = describe_list[3]
PERCENT_68 = describe_list[2]
PERCENT_95 = describe_list[1]
PERCENT_99 = describe_list[0]

SCOPE_1 = "<=0.025m"
SCOPE_2 = "0.025~0.1m"
SCOPE_3 = "0.1~0.2m"
SCOPE_4 = "0.2~1m"
SCOPE_5 = "1~10m"
SCOPE_6 = ">10m"
SCOPE_1_5 = "1~5m"
SCOPE_5_10 = "5~10m"
SCOPE_10_ = ">10m"

# 异常定偏
SCOPE_7 = "100~500m"
SCOPE_8 = "500~1000m"
SCOPE_9 = ">=1000m"

# 定位标识符
P1 = "单点解"
P2 = "差分解"
P4 = "固定解"
P5 = "浮点解"
P6 = "推算解"

time_list = [
    "起始时间(UTC)",
    "结束时间(UTC)",
    "测试时间(小时)",
]

"""


"""

position_index_list = time_list + [
    "频率",
    "GGA平均卫星数",
    "GPS Avg(L1+L2+L5)",
    "BDS Avg(B1I+B2A+B2B)",
    "BDS Avg(B1C+B2I+B3I)",
    "GAL Avg(E1+E5A+E5B+E6)",
    "GLO Avg(G1+G2)",
    "PDOP Avg",
    "HDOP Avg",
    "VDOP Avg",
    "实际定位率(%)",
    f"未定位比例(%)",
    f"{P1}定位比例(%)",
    f"{P2}定位比例(%)",
    f"{P4}定位比例(%)",
    f"{P5}定位比例(%)",
    "",
    "所有解统计结果：",
    "水平误差RMS(m)-外符合",
    "水平误差STD(m)-内符合",
    f"水平定位误差{CEP50}(m)",
    f"水平定位误差{CEP68}(m)",
    f"水平定位误差{CEP95}(m)",
    f"水平定位误差{CEP99}(m)",
    "水平定位最大误差(m)",
    "高程误差RMS(m)-外符合",
    "高程误差STD(m)-内符合",
    f"高程定位误差{CEP50}(m)",
    f"高程定位误差{CEP68}(m)",
    f"高程定位误差{CEP95}(m)",
    f"高程定位误差{CEP99}(m)",
    "高程定位最大误差(m)",
    "速度误差RMS(m/s)",
    f"速度定位误差{CEP50}(m)",
    f"速度定位误差{CEP68}(m)",
    f"速度定位误差{CEP95}(m)",
    f"速度定位误差{CEP99}(m)",
    "速度最大误差(m/s)",
    "",
    "三维精度统计结果：",
    "三维误差RMS(m)",
    f"三维误差{CEP50}(m)",
    f"三维误差{CEP68}(m)",
    f"三维误差{CEP95}(m)",
    f"三维误差{CEP99}(m)",
    f"三维最大误差(m)",
    "",
    f"{P4}精度统计结果：",
    f"{P4}水平误差RMS(m)",
    f"{P4}水平误差{CEP50}(m)",
    f"{P4}水平误差{CEP68}(m)",
    f"{P4}水平误差{CEP95}(m)",
    f"{P4}水平误差{CEP99}(m)",
    f"{P4}水平误差最大误差(m)",
    f"{P4}水平精度{SCOPE_1}(%)",
    f"{P4}水平精度{SCOPE_2}(%)",
    f"{P4}水平精度{SCOPE_3}(%)",
    f"{P4}水平精度{SCOPE_4}(%)",
    f"{P4}水平精度{SCOPE_5}(%)",
    f"{P4}水平精度{SCOPE_6}(%)",
    f"{P4}高程误差RMS(m)",
    f"{P4}高程误差{CEP50}(m)",
    f"{P4}高程误差{CEP68}(m)",
    f"{P4}高程误差{CEP95}(m)",
    f"{P4}高程误差{CEP99}(m)",
    f"{P4}高程误差最大误差(m)",
    f"{P4}高程精度<=0.05m(%)",
    f"{P4}高程精度0.05~0.2m(%)",
    f"{P4}高程精度>0.2m(%)",
    "",
    f"{P1}精度统计结果：",
    f"{P1}水平误差RMS(m)",
    f"{P1}水平误差{CEP50}(m)",
    f"{P1}水平误差{CEP68}(m)",
    f"{P1}水平误差{CEP95}(m)",
    f"{P1}水平误差{CEP99}(m)",
    f"{P1}水平误差最大误差(m)",
    f"{P1}高程误差RMS(m)",
    f"{P1}高程误差{CEP50}(m)",
    f"{P1}高程误差{CEP68}(m)",
    f"{P1}高程误差{CEP95}(m)",
    f"{P1}高程误差{CEP99}(m)",
    f"{P1}高程误差最大误差(m)",
    "",
    f"{P5}精度统计结果：",
    f"{P5}水平误差RMS(m)",
    f"{P5}水平误差{CEP50}(m)",
    f"{P5}水平误差{CEP68}(m)",
    f"{P5}水平误差{CEP95}(m)",
    f"{P5}水平误差{CEP99}(m)",
    f"{P5}水平误差最大误差(m)",
    f"{P5}高程误差RMS(m)",
    f"{P5}高程误差{CEP50}(m)",
    f"{P5}高程误差{CEP68}(m)",
    f"{P5}高程误差{CEP95}(m)",
    f"{P5}高程误差{CEP99}(m)",
    f"{P5}高程误差最大误差(m)",
    "",
    f"{P2}精度统计结果：",
    f"{P2}水平误差RMS(m)",
    f"{P2}水平误差{CEP50}(m)",
    f"{P2}水平误差{CEP68}(m)",
    f"{P2}水平误差{CEP95}(m)",
    f"{P2}水平误差{CEP99}(m)",
    f"{P2}水平误差最大误差(m)",
    f"{P2}高程误差RMS(m)",
    f"{P2}高程误差{CEP50}(m)",
    f"{P2}高程误差{CEP68}(m)",
    f"{P2}高程误差{CEP95}(m)",
    f"{P2}高程误差{CEP99}(m)",
    f"{P2}高程误差最大误差(m)",
]


parameters = {"coordinates": {}, "error_list": [], "header_list": []}
