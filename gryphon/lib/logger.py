
import os
import logging
import logging.handlers


def get_logger(name, debug=False):
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(name)
    if debug:
        logger.setLevel(logging.DEBUG)
    if 'SYSLOG_ADDRESS' in os.environ:
        syslog = logging.handlers.SysLogHandler(address=(os.environ['SYSLOG_ADDRESS'], int(os.environ['SYSLOG_PORT'])))
        formatter = logging.Formatter('%(name)s: %(levelname)s %(message)s')
        syslog.setFormatter(formatter)
        logger.addHandler(syslog)
    return logger
