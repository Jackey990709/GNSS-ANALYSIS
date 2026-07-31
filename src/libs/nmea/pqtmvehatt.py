from src import NMEAHeader
from src.libs.nmea import Default
from src.libs.nmea.base import CustomNMEAParser


class PQTMVEHATTParser(CustomNMEAParser):
    def __init__(self, *args, **kwargs):
        super(PQTMVEHATTParser, self).__init__(
            *args, chars=NMEAHeader.PQTMVEHATT, **kwargs
        )
        _pqtm_split = self.nmea_split

        try:
            self._pitch = float(_pqtm_split[4])
        except (IndexError, ValueError):
            self._pitch = Default.DEFAULT_NAN

        try:
            self._roll = float(_pqtm_split[3])
        except (IndexError, ValueError):
            self._roll = Default.DEFAULT_NAN

        try:
            self._heading = float(_pqtm_split[5])
        except (IndexError, ValueError):
            self._heading = Default.DEFAULT_NAN

    @property
    def pitch(self):
        return self._pitch

    @property
    def roll(self):
        return self._roll

    @property
    def heading(self):
        return self._heading
