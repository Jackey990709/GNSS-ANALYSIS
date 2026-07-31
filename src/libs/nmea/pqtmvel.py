from src import NMEAHeader
from src.libs.nmea import Default
from src.libs.nmea.base import CustomNMEAParser


class PQTMVELParser(CustomNMEAParser):
    def __init__(self, *args, **kwargs):
        super(PQTMVELParser, self).__init__(*args, chars=NMEAHeader.PQTMVEL, **kwargs)
        _pqtm_split = self.nmea_split

        try:
            self._veln = float(_pqtm_split[3])
        except (IndexError, ValueError):
            self._veln = Default.DEFAULT_NAN

        try:
            self._vele = float(_pqtm_split[4])
        except (IndexError, ValueError):
            self._vele = Default.DEFAULT_NAN

        try:
            self._veld = float(_pqtm_split[5])
        except (IndexError, ValueError):
            self._veld = Default.DEFAULT_NAN

        try:
            self._grdspd = float(_pqtm_split[6])
        except (IndexError, ValueError):
            self._grdspd = Default.DEFAULT_NAN

        try:
            self._spd = float(_pqtm_split[7])
        except (IndexError, ValueError):
            self._spd = Default.DEFAULT_NAN

        try:
            self._heading = float(_pqtm_split[8])
        except (IndexError, ValueError):
            self._heading = Default.DEFAULT_NAN

        try:
            self._grdspdacc = float(_pqtm_split[9])
        except (IndexError, ValueError):
            self._grdspdacc = Default.DEFAULT_NAN

        try:
            self._spdacc = float(_pqtm_split[10])
        except (IndexError, ValueError):
            self._spdacc = Default.DEFAULT_NAN

        try:
            self._headingacc = float(_pqtm_split[11].split("*")[0])
        except (IndexError, ValueError):
            self._headingacc = Default.DEFAULT_NAN

    @property
    def vel_n(self):
        return self._veln

    @property
    def vel_e(self):
        return self._vele

    @property
    def vel_d(self):
        return self._veld

    @property
    def grdspd(self):
        return self._grdspd

    @property
    def spd(self):
        return self._spd

    @property
    def heading(self):
        return self._heading

    @property
    def grdspdacc(self):
        return self._grdspdacc

    @property
    def spdacc(self):
        return self._spdacc

    @property
    def headingacc(self):
        return self._headingacc
