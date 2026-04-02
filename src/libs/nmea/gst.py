from src import NMEAHeader
from src.libs.nmea.base import NMEAParser
from . import Default


class GSTParser(NMEAParser):
    def __init__(self, *args, **kwargs):
        super(GSTParser, self).__init__(*args, chars=NMEAHeader.GGA, **kwargs)
        _gst_split = self.nmea_split

        try:
            self._range_rms = float(_gst_split[2])
        except (IndexError, ValueError):
            self._range_rms = Default.DEFAULT_NAN

        try:
            self._std_major = float(_gst_split[3])
        except (IndexError, ValueError):
            self._std_major = Default.DEFAULT_NAN

        try:
            self._std_minor = float(_gst_split[4])
        except (IndexError, ValueError):
            self._std_minor = Default.DEFAULT_NAN

        try:
            self._std_lat = float(_gst_split[6])
        except (IndexError, ValueError):
            self._std_lat = Default.DEFAULT_NAN

        try:
            self._std_lng = float(_gst_split[7])
        except (IndexError, ValueError):
            self._std_lng = Default.DEFAULT_NAN

        try:
            self._std_alt = (
                float(_gst_split[8].split("*")[0])
                if "*" in _gst_split[8]
                else Default.DEFAULT_NAN
            )
        except (IndexError, ValueError):
            self._std_alt = Default.DEFAULT_NAN

    @property
    def range_rms(self):
        return self._range_rms

    @property
    def std_major(self):
        return self._std_major

    @property
    def std_minor(self):
        return self._std_minor

    @property
    def std_lat(self):
        return self._std_lat

    @property
    def std_lng(self):
        return self._std_lng

    @property
    def std_alt(self):
        return self._std_alt
