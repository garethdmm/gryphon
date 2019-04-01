"""
`gryphon-execute strategy` takes configration parameters both from the commannd line and
from a .conf file. This library is concerned with standardizing the format of the
config dictionary that is passed into the harness, and handling the rules for combining
configuration settings from both sources.

Just a few functions that make our configuration handling cleaner.

The rule is: 
  1) From any source, if something isn't specified explicitly, it is
      left out of the dictionary, or put as None, and any other value from any
      source will override it.
  2) Always specify defaults in code.
  3) At no point is there a any guarantee a setting is in the configuration object.
"""

import ConfigParser
import argparse

from cdecimal import Decimal, InvalidOperation

from gryphon.lib import configuration
from gryphon.lib.money import Money
from gryphon.lib.exchange import exchange_factory


def get_command_line_configuration(known_args, extra_args):
    command_line_configuration = {
        'platform': {
            'strategy': known_args.strategy,
            'config_file': known_args.config_file,
            'builtin': known_args.builtin,
            'heartbeat': known_args.heartbeat,
            'sentry': known_args.sentry,
            'emerald': known_args.emerald,
            'audit': known_args.audit,
            'execute': known_args.execute,
        },
        'strategy': {
            'tick_sleep': configuration.parse_configurable_value(known_args.tick_sleep),
        },
    }

    extra_strategy_configuration = parse_extra_strategy_args(extra_args)

    command_line_configuration['strategy'].update(extra_strategy_configuration)

    return command_line_configuration


def parse_extra_strategy_args(args):
    """
    Turns a list of unknown arguments from the controller into a dictionary. This is
    necessary because the framework doesn't know what argument a strategy might
    require.

    This ONLY supports named arguments, and only supports the syntax '--name name', not
    --name=name.

    There are likely more graceful ways to do this, such as having Strategies know which
    of their properties are configurable and allowing them to register extra arguments,
    but this will do for now.

    TODO:
      - don't print messages from argparse here, just throw an exception or something.
      - the hackery here to support boolean flags (the nargs/const condition) means that
        if you don't give an value for an argument that should have one, no error is
        thrown, and that value is set to 'True'. In most cases this should be caught
        further down the line, but we really should handle it here.
    """

    settings = [x for x in args if x[:2] == '--']
    
    parser = argparse.ArgumentParser()

    for setting_name in settings:
        parser.add_argument(setting_name, action='store', nargs='?', const=True)

    output = vars(parser.parse_args(args))  # Vars turns a Namespace into a dict.

    output = {k: configuration.parse_configurable_value(v) for k, v in output.items()}

    return output


def get_conf_file_configuration(conf_filename, strategy_name):
    """
    If there was a config file specified, load it. If not, look for [strategy_name].conf
    in the current directory. If neither is found just return an initialized 
    configuration object that is otherwise empty.
    """

    if conf_filename is None:
        if strategy_name[-4:] == '.pyx':
            conf_filename = '%s.conf' % strategy_name[:-4]
        else:
            conf_filename = '%s.conf' % strategy_name

    file_configuration = configuration.read_config_from_file(conf_filename)

    standardized_configuration = format_file_config_to_standard(file_configuration)

    return standardized_configuration


def format_file_config_to_standard(file_configuration):
    """
    Regardless of what is in the .conf file, we need to output a dictionary with the
    keys platform, strategy, and exchanges. We also need to correctly categorize any
    exchange configuration settings in the .conf file--specified by a section with the
    same name as an exchange trading pair--under the 'exchanges' key.
    """
    new_configuration = {'platform': {}, 'strategy': {}, 'exchanges': {}}

    for section_name, values in file_configuration.items():
        if section_name in exchange_factory.ALL_EXCHANGE_KEYS:
            new_configuration['exchanges'][section_name] = values
        else:
            new_configuration[section_name] = values

    return new_configuration


def combine_file_and_command_line_config(file_config, command_line_config):
    """
    We have our configuration from the .conf, and we have the configuration from the
    command line. If there are any settings specified in both, take the one from the
    command line.
    """

    final_configuration = file_config.copy()

    configuration.dict_update_override(
        final_configuration['platform'],
        command_line_config['platform'],
    )

    configuration.dict_update_override(
        final_configuration['strategy'],
        command_line_config['strategy'],
    )

    return final_configuration

