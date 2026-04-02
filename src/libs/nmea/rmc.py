from datetime import datetime

from src import NMEAHeader
from src.libs.nmea.base import NMEAParser

from . import Default


class RMCParser(NMEAParser):
    def __init__(self, *args, **kwargs):
        super(RMCParser, self).__init__(*args, chars=NMEAHeader.RMC, **kwargs)
        _rmc_split = self.nmea_split

        try:
            self._utc_date = _rmc_split[9] or Default.DEFAULT_NAN
            float(self._utc_date)
        except (IndexError, ValueError):
            self._utc_date = Default.DEFAULT_NAN

        try:
            self._utc_time = _rmc_split[1] or Default.DEFAULT_NAN
            float(self._utc_time)
        except (IndexError, ValueError):
            self._utc_time = Default.DEFAULT_NAN

        try:
            self._utc_time_str = _rmc_split[1] or ""
        except IndexError:
            self._utc_time_str = ""

        try:
            self._speed = _rmc_split[7] or Default.DEFAULT_NAN
        except IndexError:
            self._speed = Default.DEFAULT_NAN

        try:
            self._yaw = float(_rmc_split[8])
        except (IndexError, ValueError):
            self._yaw = Default.DEFAULT_NAN

    @property
    def utc_time(self):
        return self._utc_time

    @property
    def utc_time_str(self):
        return self._utc_time_str

    @property
    def utc_date(self):
        return self._utc_date

    @property
    def utc_date_time(self):
        """
        :return: utc日期时间格式, 2007-09-08T04:22:09.800
        """
        if isinstance(self.utc_date, str) and len(self.utc_date) != 6:
            return Default.DEFAULT_NAN

        if self.utc_date and self.utc_time:
            try:
                ptime = datetime.strptime(
                    f"{self.utc_date}{self.utc_time}", "%d%m%y%H%M%S.%f"
                )
                return ptime.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3]
            except ValueError:
                pass
        return Default.DEFAULT_NAN

    @property
    def speed(self):
        """
        :return: 速度, 单位m/s
        """
        try:
            return round(
                float(self._speed) * 1.852 * 1000 / 3600,
                Default.KEEP_DECIMAL_DIGIT,
            )
        except ValueError:
            return Default.DEFAULT_NAN

    @property
    def yaw(self):
        return self._yaw
