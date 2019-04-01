"""
A library that makes it easy to read from .conf files.
"""

import argparse
from collections import defaultdict
import ConfigParser
import StringIO

from cdecimal import Decimal, InvalidOperation

from gryphon.lib.money import Money


def read_config_from_file(config_filename):
    """
    Take a filename in the current working directory and read the configuration therin
    into a dictionary object.

    Section titles of the form [x:y] are parsed into sub-dictionaries under the key x.
    """
    parser = ConfigParser.RawConfigParser()
    parser.read(config_filename)

    configuration = parse_sections(parser)

    return configuration


def _get_parser_for_string_config(string_config):
    """
    This should only be used for unit testing.
    """
    buf = StringIO.StringIO(string_config)
    parser = ConfigParser.ConfigParser()
    parser.readfp(buf)

    return parser


def parse_sections(parser):
    configuration = defaultdict(lambda: {})

    for section_name in parser.sections():
        if ':' in section_name:
            parent_section_name = section_name[:section_name.index(':')]
            subsection_name = section_name[section_name.index(':') + 1:]

            configuration[parent_section_name][subsection_name] = dict(
                parse_section_items(parser.items(section_name)),
            )
        else:
            configuration[section_name] = dict(
                parse_section_items(parser.items(section_name)),
            )

    return configuration


def parse_section_items(items):
    """
    Parse values in the configuration file into object types intelligently.
    """
    parsed_items = []

    for item in items:
        parsed_items.append((item[0], parse_configurable_value(item[1])))

    return parsed_items


def parse_configurable_as_list(value):
    """
    For string values with commas in them, try to parse the value as a list.
    """
    if ',' in value:
        return [token.strip() for token in value.split(',') if token]
    else:
        return [value]


def parse_configurable_value(value):
    """
    Simple function to parse a setting specified either in a .conf file or from the
    command line.
    """
    if value is None:
        return None
    if type(value) is bool:
        return value
    elif value == 'yes':
        return True
    elif value == 'no':
        return False
    else:
        try:
            return Money.loads(value)
        except ValueError:
            try:
                return Decimal(value)
            except InvalidOperation:
                pass

        return value


def dict_update_override(dicta, dictb):
    """
    This
        i) does add None's from b if k is not in a.
        ii) does not override a valid value in a with a None from b
        iii) does override a valid value in a with a valid value from b
    """
    dicta.update(
        {k: v for k, v in dictb.iteritems() if v or (k not in dicta)}
    )

