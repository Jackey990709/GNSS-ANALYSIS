def read_bytes(stream, size):
    data = stream.read(size)

    if len(data) < size:  # EOF
        raise EOFError()

    return data


def bytes2int(v):
    return int.from_bytes(v, "little", signed=False)


def str2int(v) -> int:
    return int(v[1:])
