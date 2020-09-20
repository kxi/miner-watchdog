import logging
import sys
import os
from logging.handlers import RotatingFileHandler

def make_logger(stream=sys.stderr, log_file_name=None):
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)

    log_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')

    # stream_handler = logging.StreamHandler(stream=stream)
    # stream_handler.setFormatter(log_formatter)
    # stream_handler.setLevel(logging.INFO)

    file_handler_info = RotatingFileHandler(log_file_name+".log", maxBytes=200000)
    file_handler_info.setFormatter(log_formatter)
    file_handler_info.setLevel(logging.INFO)

    file_handler_critical = RotatingFileHandler(log_file_name+".err", maxBytes=200000)
    file_handler_critical.setFormatter(log_formatter)
    file_handler_critical.setLevel(logging.CRITICAL)


    logger.addHandler(file_handler_info)
    logger.addHandler(file_handler_critical)

    return logger
