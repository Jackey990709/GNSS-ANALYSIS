import logging
import re

from src import NMEAHeader
from src.util.logger import logger

logger = logging.getLogger(__name__)


class _NMEABase:
    """Shared base providing nmea_split property and check_sum method."""

    line: str
    check: bool
    total_failed: int = 0
    total_missing: int = 0
    counting: bool = False

    @classmethod
    def reset_stats(cls):
        cls.total_failed = 0
        cls.total_missing = 0
        cls.counting = False

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

        result = format(ck_sum, "02X") == check_sum
        if not result and _NMEABase.counting:
            _NMEABase.total_failed += 1
        return result


class NMEAParser(_NMEABase):
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


class CustomNMEAParser(_NMEABase):
    def __init__(
        self,
        line: str,
        chars: str = NMEAHeader.GGA,
        error_code: bool = False,
        check: bool = True,
    ):
        if error_code:
            if line[0] == "$":
                line = line[:3000]

            regx = r".*([$?].*%s.*\*[0-9A-Z]{2}).*" % chars
            matcher = re.findall(regx, line)
            logger.debug(f"{matcher}")
            line = matcher[0] if matcher else ""

        self.line = line
        self.check = check
