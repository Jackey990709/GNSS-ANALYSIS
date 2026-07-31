from src import NMEAHeader
from src.libs.nmea import Default
from src.libs.nmea.base import CustomNMEAParser


class PQTMTARParser(CustomNMEAParser):
    def __init__(self, *args, **kwargs):
        super(PQTMTARParser, self).__init__(*args, chars=NMEAHeader.PQTMTAR, **kwargs)
        _pqtm_split = self.nmea_split

        try:
            self._status = _pqtm_split[3]
        except IndexError:
            self._status = Default.DEFAULT_NAN

        try:
            self._pitch = float(_pqtm_split[6])
        except (IndexError, ValueError):
            self._pitch = Default.DEFAULT_NAN

        try:
            self._roll = float(_pqtm_split[7])
        except (IndexError, ValueError):
            self._roll = Default.DEFAULT_NAN

        try:
            self._heading = float(_pqtm_split[8])
        except (IndexError, ValueError):
            self._heading = Default.DEFAULT_NAN

    @property
    def status(self):
        return self._status

    @property
    def pitch(self):
        return self._pitch

    @property
    def roll(self):
        return self._roll

    @property
    def heading(self):
        return self._heading
