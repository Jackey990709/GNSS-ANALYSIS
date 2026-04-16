from src.libs.ubx.ubx_types import *
from src.libs import bytes2int, str2int


def calc_cksum(content: bytes):
    ck_a, ck_b = 0, 0
    for char in content:
        ck_a += char
        ck_a &= 0xFF
        ck_b += ck_a
        ck_b &= 0xFF

    return bytes((ck_a, ck_b))


class UbxStruct:
    def __init__(self, len_bytes, payload, cksum):
        self.len_bytes: bytes = len_bytes
        self.payload: bytes = payload
        self.cksum: bytes = cksum
        self.decode_data: dict = {}
        self.hdr: bytes = b"\x0d\x03"
        self.struct: dict[str, str] = {
            "ch": U1,
            "flag": X1,
            "count": U2,
            "wnR": U2,
            "wnF": U2,
            "towMsR": U4,
            "towSubMsR": U4,
            "towMsF": U4,
            "towSubMsF": U4,
            "accEst": U4,
        }

    def decode(self):
        decode_dict = {}
        ck_sum = calc_cksum(self.hdr + self.len_bytes + self.payload)
        if ck_sum == self.cksum:
            offset = 0
            for key, value in self.struct.items():
                length = str2int(value)
                data = bytes2int(self.payload[offset : offset + length])
                if "X" in value:
                    decode_dict[key] = f"{data:0>2X}"
                else:
                    decode_dict[key] = data

                offset += length

        return decode_dict
