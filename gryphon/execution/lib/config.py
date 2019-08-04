from __future__ import print_function
from six.moves.configparser import RawConfigParser

from gryphon.lib.logger import get_logger

logger = get_logger(__name__)


def get_config_var(filepath, section, key):
    print(filepath)

    config = RawConfigParser()
    config.read(filepath)
    section_dict = dict(config.items('live'))

    return section_dict[key]
