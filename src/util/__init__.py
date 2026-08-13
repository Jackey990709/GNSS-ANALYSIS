prefix_list: list = ["MXT E", "devicename", "Starting GNSS", "UC6580I R2000"]
error_list: list = [
    "ERROR_TRAP",
    "CHECKIMU_RST",
    "hard fault",
    "FWINVALID",
    "start addr",
    "mepc",
    "watchdog",
]

HA = "Positional Accuracy"
VA = "Altitude Accuracy"


# cep_keys = ["50%", "68%", "95%", "99%"]
# percentiles = [0.50, 0.68, 0.95, 0.99]
# cep_list = ["CEP50", "CEP68", "CEP95", "CEP99", "Max"]
cep_keys = ["50%", "68%", "95%", "99%", "99.7%"]
percentiles = [0.50, 0.68, 0.95, 0.99, 0.997]
cep_list = ["CEP50", "CEP68", "CEP95", "CEP99", "CEP99.7", "Max"]
rms_cep_list = ["RMS"] + cep_list
rms_sigma_cep_list = ["RMS", "1σ"] + cep_list

describe_list = ["99%", "99.7%", "95%", "68%", "50%"]
PERCENT_50 = describe_list[-1]
PERCENT_68 = describe_list[-2]
PERCENT_95 = describe_list[-3]
PERCENT_99 = describe_list[-4]
PERCENT_997 = describe_list[-5]

__all__ = [
    "prefix_list",
    "error_list",
    "HA",
    "VA",
    "cep_keys",
    "percentiles",
    "cep_list",
    "rms_cep_list",
    "rms_sigma_cep_list",
    "PERCENT_50",
    "PERCENT_68",
    "PERCENT_95",
    "PERCENT_997",
    "PERCENT_99",
]
