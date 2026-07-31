from src import NMEAHeader
from src.libs.nmea import Default
from src.libs.nmea.base import CustomNMEAParser


class PQTMDRPVAParser(CustomNMEAParser):
    def __init__(self, *args, **kwargs):
        super(PQTMDRPVAParser, self).__init__(
            *args, chars=NMEAHeader.PQTMDRPVA, **kwargs
        )
        _pqtm_split = self.nmea_split

        try:
            self._pitch = float(_pqtm_split[14])
        except (IndexError, ValueError):
            self._pitch = Default.DEFAULT_NAN

        try:
            self._roll = float(_pqtm_split[13])
        except (IndexError, ValueError):
            self._roll = Default.DEFAULT_NAN

        try:
            self._heading = float(_pqtm_split[15].split("*")[0])
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
