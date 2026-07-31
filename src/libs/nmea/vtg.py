import logging

from src import NMEAHeader
from src.libs.nmea.base import NMEAParser
from . import Default

logger = logging.getLogger(__name__)


class VTGParser(NMEAParser):
    def __init__(self, *args, **kwargs):
        super(VTGParser, self).__init__(*args, chars=NMEAHeader.VTG, **kwargs)
        _vtg_split = self.nmea_split

        try:
            self._cog = float(_vtg_split[1])
        except (IndexError, ValueError):
            self._cog = Default.DEFAULT_NAN

        try:
            self._knot = float(_vtg_split[5])
        except (IndexError, ValueError):
            self._knot = Default.DEFAULT_NAN

        try:
            self._kmph = float(_vtg_split[7])
        except (IndexError, ValueError):
            self._kmph = Default.DEFAULT_NAN

    @property
    def cog(self):
        return self._cog

    @property
    def knot(self):
        return self._knot

    @property
    def kmph(self):
        return self._kmph
