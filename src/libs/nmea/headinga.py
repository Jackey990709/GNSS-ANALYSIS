from src.libs.nmea import Default


class HEADINGAParser:
    def __init__(self, line):
        _nmea_split = line.split(",")

        try:
            self._pitch = float(_nmea_split[13])
        except (IndexError, ValueError):
            self._pitch = Default.DEFAULT_NAN

        try:
            self._heading = float(_nmea_split[12])
        except (IndexError, ValueError):
            self._heading = Default.DEFAULT_NAN

    @property
    def pitch(self):
        return self._pitch

    @property
    def heading(self):
        if self._heading > 180:
            return self._heading - 180
        return self._heading + 180
