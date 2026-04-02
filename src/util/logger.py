import logging


# def set_logger(file='log.txt', name='root', level='DEBUG'):
def set_logger(file=None, name='root', level='WARNING'):
    _logger = logging.getLogger(name)
    _logger.setLevel(level)
    BASIC_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    formatter = logging.Formatter(BASIC_FORMAT)

    if file is not None:
        file_handler = logging.FileHandler(file)
        file_handler.setFormatter(formatter)
        _logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    _logger.addHandler(console_handler)

    return _logger


logger = set_logger()
