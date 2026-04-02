import logging
import re

from src import NMEAHeader
from src.util.logger import logger

logger = logging.getLogger(__name__)


class NMEAParser:
    def __init__(
        self,
        line: str,
        chars: str = NMEAHeader.GGA,
        error_code: bool = False,
        check: bool = True,
    ):
        self.chars = chars

        if error_code:
            if line[0] == "$":
                line = line[:3000]

            regx = r".*([$?].*%s.*\*[0-9A-Z]{2}).*" % chars
            matcher = re.findall(regx, line)
            logger.debug(f"{matcher}")
            line = matcher[0] if matcher else ""
        else:
            if len(chars) == 6:
                chars = chars[2:]
            if line[3:7] != chars:
                loc = line.rfind(chars)
                line = line[loc - 3 :] if loc > 3 else ""

        self.line = line
        self.check = check

    @property
    def nmea_split(self):
        _nmea_split = None
        if self.check:
            if self.check_sum():
                _nmea_split = self.line.split(",")
            else:
                _nmea_split = []
        else:
            _nmea_split = self.line.split(",")
        logger.debug(f"split line: {_nmea_split}")

        return _nmea_split

    def check_sum(self) -> bool:
        if "*" not in self.line:
            return False

        content, check_sum = self.line.strip("$#\r\n").split("*", 1)
        ck_sum = 0
        for sub in content:
            ck_sum ^= ord(sub)

        return format(ck_sum, "02X") == check_sum
