import logging

from src import NMEAHeader
from src.libs.nmea.base import NMEAParser
from . import Default

logger = logging.getLogger(__name__)


def check_value(value):
    return value
    # return DefaultConst.DEFAULT_NAN if value == 127.0 else value


class GSAParser(NMEAParser):
    def __init__(self, *args, **kwargs):
        super(GSAParser, self).__init__(*args, chars=NMEAHeader.GSA, **kwargs)
        _gsa_split = self.nmea_split

        try:
            self._sat_count = 12 - _gsa_split[3:15].count("")
        except (IndexError, ValueError):
            self._sat_count = Default.DEFAULT_NAN

        try:
            self._pdop = float(_gsa_split[15])
        except (IndexError, ValueError):
            self._pdop = Default.DEFAULT_NAN

        try:
            self._hdop = float(_gsa_split[16])
        except (IndexError, ValueError):
            self._hdop = Default.DEFAULT_NAN

        try:
            if len(_gsa_split) == 18:
                self._vdop = float(_gsa_split[17].split("*")[0])
            else:
                self._vdop = float(_gsa_split[17])
        except (IndexError, ValueError):
            self._vdop = Default.DEFAULT_NAN

        try:
            if len(_gsa_split) == 19:
                self._sys_id = _gsa_split[18].split("*")[0]
            else:
                self._sys_id = ""
        except (IndexError, ValueError):
            self._sys_id = ""

    @property
    def sat_count(self):
        return self._sat_count

    @property
    def pdop(self):
        return check_value(self._pdop)

    @property
    def hdop(self):
        return check_value(self._hdop)

    @property
    def vdop(self):
        return check_value(self._vdop)

    @property
    def sys_id(self):
        return self._sys_id
