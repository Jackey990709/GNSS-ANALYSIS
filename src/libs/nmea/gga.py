from src import NMEAHeader
from src.libs.nmea.base import NMEAParser

from . import Default


class GGAParser(NMEAParser):
    def __init__(self, *args, **kwargs):
        super(GGAParser, self).__init__(*args, chars=NMEAHeader.GGA, **kwargs)
        _gga_split = self.nmea_split

        try:
            self._lat_degree_mins = _gga_split[2]
        except IndexError:
            self._lat_degree_mins = Default.DEFAULT_NAN

        try:
            self._lng_degree_mins = _gga_split[4]
        except IndexError:
            self._lng_degree_mins = Default.DEFAULT_NAN

        try:
            self._ns = _gga_split[3]
        except IndexError:
            self._ns = Default.DEFAULT_NAN

        try:
            self._ew = _gga_split[5]
        except IndexError:
            self._ew = Default.DEFAULT_NAN

        try:
            self._utc_time_str = _gga_split[1] or ""
        except IndexError:
            self._utc_time_str = ""

        try:
            self._utc_time = _gga_split[1] or Default.DEFAULT_NAN
            float(self._utc_time)
        except (IndexError, ValueError):
            self._utc_time = Default.DEFAULT_NAN

        try:
            self._lat = self.change_loc_format(_gga_split[2], _gga_split[3])
        except IndexError:
            self._lat = Default.DEFAULT_NAN

        try:
            self._lng = self.change_loc_format(_gga_split[4], _gga_split[5], 3)
        except IndexError:
            self._lng = Default.DEFAULT_NAN

        try:
            self._hgt = _gga_split[9] or Default.DEFAULT_NAN
        except IndexError:
            self._hgt = Default.DEFAULT_NAN

        try:
            self._alt = _gga_split[11] or 0
        except IndexError:
            self._alt = Default.DEFAULT_NAN

        try:
            self._fix_label = _gga_split[6] or "0"
        except IndexError:
            self._fix_label = "0"

        try:
            self._satellites = _gga_split[7] or Default.DEFAULT_NAN
        except IndexError:
            self._satellites = Default.DEFAULT_NAN

        try:
            self._delay = _gga_split[13] or Default.DEFAULT_NAN
        except IndexError:
            self._delay = Default.DEFAULT_NAN

    @property
    def utc_time(self):
        return self._utc_time

    @property
    def utc_time_str(self):
        return self._utc_time_str

    @property
    def lat(self):
        return self._lat

    @property
    def lng(self):
        return self._lng

    @property
    def hgt(self):
        try:
            return round(
                float(self._hgt) + float(self._alt), Default.KEEP_DECIMAL_DIGIT
            )
        except ValueError:
            return Default.DEFAULT_NAN

    @property
    def fix_label(self):
        return self._fix_label

    @property
    def satellites(self):
        try:
            return float(self._satellites)
        except ValueError:
            return Default.DEFAULT_NAN

    @property
    def delay(self):
        return self._delay

    @staticmethod
    def change_loc_format(loc, azimuth, dot=2):
        try:
            degree = (
                round(
                    float(loc[:dot]) + float(loc[dot:]) / 60,
                    Default.LOC_DECIMAL_DIGIT,
                )
                if loc
                else Default.DEFAULT_NAN
            )
        except ValueError:
            degree = Default.DEFAULT_NAN

        if azimuth == "E" or azimuth == "N":
            return degree
        elif azimuth == "W" or azimuth == "S":
            return -degree
        else:
            return Default.DEFAULT_NAN

    @property
    def lat_degree_mins(self):
        return self._lat_degree_mins

    @property
    def lng_degree_mins(self):
        return self._lng_degree_mins

    @property
    def ns(self):
        return self._ns

    @property
    def ew(self):
        return self._ew
