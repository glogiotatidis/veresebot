import sys

import config
import logging

# create logger
logger = logging.getLogger(sys.argv[0])
logger.setLevel(logging.DEBUG)


# create formatter
formatter = logging.Formatter(
    '[%(asctime)s][%(filename)s:%(lineno)s - %(levelname)s - %(funcName)s] %(message)s')


# create console handler and set level to debug
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(formatter)
logger.addHandler(ch)


# create console handler and set level to debug
if getattr(config, 'LOGFILE', False):
    fh = logging.FileHandler(config.LOGFILE)
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(formatter)
    logger.addHandler(fh)
