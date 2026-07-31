import logging


from src import NMEAHeader
from src.libs.nmea.base import NMEAParser
from . import sat_sys, sys_type

logger = logging.getLogger(__name__)

sys_symbol_dict = {
    "$GPGSV": "G",
    "$GBGSV": "C",
    "$GAGSV": "E",
    "$GLGSV": "R",
}


MAX_CN0_VALUE = 60


class GSVParser(NMEAParser):
    def __init__(self, *args, **kwargs):
        super(GSVParser, self).__init__(*args, chars=NMEAHeader.GSV, **kwargs)

    def decode_gsv(self, elev, threshold):
        logger.debug(f"decode line: {self.line.strip()}")

        if not self.check_sum():
            return "", "", []

        temp_line = self.line.replace("*", ",")  # 将星号替换为逗号
        line_split = temp_line.split(",")

        if line_split[0] not in sys_type:
            return "", "", []

        if len(line_split[4:]) % 4 == 2:  # NMEA4.1
            signal_id, gsv_data = line_split[-2], line_split[4:-2]
        else:  # NMEA4.0
            gsv_data = line_split[4:-1]
            signal_id = "6" if line_split == "$GAGSV" else "1"

        length = len(gsv_data)
        if length % 4 != 0 or length < 4 or length > 16:
            logger.debug(f"gsv line format error: {self.line.strip()}")
            return "", "", []

        try:
            freq_label = sat_sys[line_split[0]][signal_id]
        except KeyError:
            if signal_id == "0":
                freq_label = "L1"
            else:
                logger.debug(f"sys label not in the memory: {self.line.strip()}")
                return "", "", []

        result: dict[str, list] = {}

        i = 0
        if freq_label not in result:
            result[freq_label] = []
        freq_list = result[freq_label]

        while i < length:
            try:
                elev_value = float(gsv_data[i + 1])
                cn0_value = float(gsv_data[i + 3])
                if cn0_value == 0.0 or cn0_value < threshold:
                    raise ValueError  # 剔除CN0为0或低于阈值的值
                if elev_value < elev:
                    raise ValueError  # 剔除仰角低于阈值的值
                freq_list.append(cn0_value)
            except ValueError:
                ...
            i += 4
        logger.debug(f"{line_split[0]}, {freq_label}, {result[freq_label]}")

        return sys_type[line_split[0]], freq_label.lower(), result[freq_label]
