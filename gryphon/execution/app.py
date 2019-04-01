import pyximport; pyximport.install()

import importlib
import logging
import os
from os.path import join, dirname
import shlex

from cdecimal import Decimal
from cement.core import foundation, controller, handler
from cement.ext.ext_argparse import ArgparseArgumentHandler
from dotenv import load_dotenv

from gryphon.execution.lib import config_helper
from gryphon.lib import environment
from gryphon.lib.logger import get_logger


environment.load_environment_variables()


def turn_on_debug(loggers):
    for logger_name in loggers:
        logger = get_logger(logger_name)
        logger.setLevel(logging.DEBUG)


class ModifiedArgparseArgumentHandler(ArgparseArgumentHandler):
    class Meta:
        label = 'my_argparse'
        ignore_unknown_arguments = True


class GryphonFuryBaseController(controller.CementBaseController):
    """
    The application base controller.
    """

    class Meta:
        label = 'base'

        config_defaults = {
            'strategy': 'Naive',
            'exchange': None,
            'our_orders': False,
            'execute': False,
        }

        arguments = [
            (['strategy'], {
                'action': 'store',
                'help': 'name of strategy',
            }),
            (['-b', '--builtin'], {
                'action': 'store_true',
                'help': 'Whether the strategy name specified refers to a built-in strategy in the Gryphon Framework',
            }),
            (['-X', '--execute'], {
                'action': 'store_true',
                'help': 'execute real trades',
            }),
            (['--heartbeat'], {
                'action': 'store_true',
                'default': None,
                'help': 'heartbeat every tick for monitoring',
            }),
            (['--sentry'], {
                'action': 'store_true',
                'default': None,
                'help': 'log exceptions to a 3rd party service',
            }),
            (['--emerald'], {
                'action': 'store_true',
                'default': None,
                'help': 'look for cached market data in redis vs. polling in-process',
            }),
            (['--audit'], {
                'action': 'store_true',
                'default': None,
                'help': 'whether to run the strategy with audits or not',
            }),
            (['--tick_sleep'], {
                'action': 'store',
                'help': 'How many seconds to sleep between ticks',
            }),
            (['--more-logging'], {
                'action': 'store_true',
                'help': 'extra debug output',
            }),
            (['-c', '--config_file'], {
                'action': 'store',
                'help': 'relative path to the configuration file',
            }),
        ]

    def _parse_strategy_args(self, strat_args):
        """
        Strategy arguments currently come in the form --strat_args [k=v,k2=v2,...].
        This could use some more work for elegance, but this function gives us fairly
        smart parsing of this format, such that complex forms like the following still
        work.

        --strat_args 'exchange=kraken,fundamental_exchanges="kraken,kraken_usd"'
        """
        parsed_args = {}

        if strat_args is not None:
            lexer = shlex.shlex(strat_args, posix=True)
            lexer.whitespace_split = True
            lexer.whitespace = ','

            parsed_args = dict(pair.split('=', 1) for pair in lexer)

        return parsed_args

    @controller.expose()
    def strategy(self):
        if self.app.pargs.more_logging:
            loggers = [
                'requests.packages.urllib3',
                'gryphon.lib.exchange.base',
                'strategies.harness',
                'strategies.base',
            ]

            turn_on_debug(loggers)

        file_configuration = config_helper.get_conf_file_configuration(
            self.app.pargs.config_file,
            self.app.pargs.strategy,
        )

        command_line_configuration = config_helper.get_command_line_configuration(
            self.app.pargs,
            self.app.args.unknown_args, 
        )

        final_configuration = config_helper.combine_file_and_command_line_config(
            file_configuration,
            command_line_configuration,
        )

        from gryphon.execution.live_runner import live_run

        self.app.log.info(
            'Running strategy %s with configuration=%s' % (
            self.app.pargs.strategy,
            final_configuration,
        ))

        live_run(final_configuration)

    @controller.expose()
    def overwatch(self):
        from gryphon.execution.bots import overwatch
        overwatch.watch()

    @controller.expose()
    def shoebox(self):
        from gryphon.execution.bots import shoebox
        shoebox.run()

    @controller.expose()
    def bank(self):
        from gryphon.execution.bots import bank
        bank.run()

    @controller.expose()
    def buyback(self):
        from gryphon.execution.controllers.fee_buyback import buyback
        buyback()

    @controller.expose()
    def balance(self):
        from gryphon.execution.controllers.balance import balance

        exchange_key = self.app.config.get('controller.base', 'exchange')
        balance(exchange_key)

    @controller.expose()
    def winddown(self):
        from gryphon.execution.controllers.wind_down import wind_down

        exchange_key = self.app.config.get('controller.base', 'exchange')
        self.app.config.parse_file('%s.conf' % exchange_key)
        strategy_params = self.app.config.get_section_dict('live')
        execute = self.app.config.get('controller.base', 'execute')
        wind_down(exchange_key, strategy_params, execute)


class OrderBookController(controller.CementBaseController):
    """This controller's commands are 'stacked' onto the base controller."""

    class Meta:
        label = 'orderbook'
        interface = controller.IController
        stacked_on = 'base'
        stacked_type = 'nested'
        description = 'OrderBook Controller'
        arguments = [
            (['exchange'], {
                'action': 'store',
                'help': 'name of exchange',
                'nargs': '?',
            }),
            (['--our-orders'], {'action': 'store_true', 'help': 'highlight our orders'}),
            (['--include-fees'], {'action': 'store_true', 'help': 'include fees in prices'}),
        ]

    @controller.expose(help='show individual or combined orderbooks')
    def default(self):
        from gryphon.execution.controllers.order_book import order_book

        exchange_key = self.app.pargs.exchange
        our_orders = self.app.pargs.our_orders
        include_fees = self.app.pargs.include_fees
        order_book(exchange_key, our_orders, include_fees)


class AuditController(controller.CementBaseController):
    """This controller commands are 'stacked' onto the base controller."""

    class Meta:
        label = 'audit'
        interface = controller.IController
        stacked_on = 'base'
        stacked_type = 'nested'
        description = 'Audit Controller'
        arguments = [
            (['exchange'], {
                'action': 'store',
                'help': 'name of exchange',
                'nargs': '?',
            }),
            (['--more-logging'], {
                'action': 'store_true',
                'help': 'extra debug output',
            }),
        ]

    @controller.expose(help='compare exchange trades to our records')
    def default(self):
        from gryphon.execution.lib.auditing import audit

        exchange_key = self.app.pargs.exchange

        if self.app.pargs.more_logging:
            loggers = ['gryphon.lib.models.exchange', 'utils.audit']
            turn_on_debug(loggers)

        audit(exchange_key)


class ManualController(controller.CementBaseController):
    """This controller commands are 'stacked' onto the base controller."""

    class Meta:
        label = 'manual'
        interface = controller.IController
        stacked_on = 'base'
        stacked_type = 'nested'
        description = 'Manual Controller'
        arguments = [
            (['exchange'], {
                'action': 'store',
                'help': 'name of exchange',
                'nargs': '?',
            }),
            (['order_id'], {'action': 'store', 'help': 'exchange order id to run accounting for'}),
            (['--actor'], {'action': 'store', 'help': 'actor name', 'default': 'Multi'}),
            (['--execute'], {'action': 'store_true', 'help': 'really save to the db'}),
        ]

    @controller.expose(help='run manual accounting on given order id')
    def default(self):
        from gryphon.execution.controllers.manual_accounting import manual_accounting

        exchange_key = self.app.pargs.exchange
        order_id = self.app.pargs.order_id
        actor = self.app.pargs.actor
        execute = self.app.pargs.execute
        manual_accounting(exchange_key, order_id, actor, execute)


class WithdrawController(controller.CementBaseController):
    """This controller commands are 'stacked' onto the base controller."""

    class Meta:
        label = 'withdraw'
        interface = controller.IController
        stacked_on = 'base'
        stacked_type = 'nested'
        description = 'Withdraw Controller'
        arguments = [
            (['exchange'], {
                'action': 'store',
                'help': 'name of exchange',
                'nargs': '?',
            }),
            (['target_exchange'], {
                'action': 'store',
                'help': 'exchange where bitcoins were sent',
            }),
            (['amount'], {
                'action': 'store',
                'help': 'amount as a Money string eg "BTC 10"',
            }),
        ]

    @controller.expose(help='record a withdrawal')
    def default(self):
        from gryphon.execution.controllers.withdraw import withdraw

        exchange_key = self.app.pargs.exchange
        target_exchange_key = self.app.pargs.target_exchange
        amount = self.app.pargs.amount
        withdraw(exchange_key, target_exchange_key, amount)


class WithdrawFiatController(controller.CementBaseController):
    """This controller commands are 'stacked' onto the base controller."""

    class Meta:
        label = 'withdrawfiat'
        interface = controller.IController
        stacked_on = 'base'
        stacked_type = 'nested'
        description = 'Withdraw Fiat Controller'
        arguments = [
            (['exchange'], {
                'action': 'store',
                'help': 'name of exchange',
                'nargs': '?',
            }),
            (['target_exchange'], {
                'action': 'store',
                'help': 'exchange where fiat was sent',
            }),
            (['amount'], {
                'action': 'store',
                'help': 'amount as a Money string eg "USD 100000"',
            }),
            (['external_transaction_id'], {
                'action': 'store',
                'help': 'eg. wire confirmation code',
            }),
            (['destination_amount'], {
                'action': 'store',
                'help': 'expected destination amount (if different than sent amount)',
                'nargs': '?',
            }),
        ]

    @controller.expose(help='record a fiat withdrawal')
    def default(self):
        from gryphon.execution.controllers.withdraw import withdraw_fiat

        exchange_key = self.app.pargs.exchange
        target_exchange_key = self.app.pargs.target_exchange
        amount = self.app.pargs.amount
        destination_amount = self.app.pargs.destination_amount
        external_transaction_id = self.app.pargs.external_transaction_id

        withdraw_fiat(
            exchange_key,
            target_exchange_key,
            amount,
            destination_amount,
            transaction_details={'external_transaction_id': external_transaction_id},
        )


class TransactionCompleteController(controller.CementBaseController):
    """This controller commands are 'stacked' onto the base controller."""

    class Meta:
        label = 'complete'
        interface = controller.IController
        stacked_on = 'base'
        stacked_type = 'nested'
        description = 'Complete Transaction Controller'
        arguments = [
            (['exchange'], {
                'action': 'store',
                'help': 'name of exchange',
                'nargs': '?',
            }),
            (['currency'], {'action': 'store', 'help': ''}),
        ]

    @controller.expose(help='mark a fiat withdrawal as complete')
    def default(self):
        from gryphon.execution.controllers.withdraw import transaction_complete

        exchange_key = self.app.pargs.exchange
        currency = self.app.pargs.currency
        transaction_complete(exchange_key, currency)


class ScriptController(controller.CementBaseController):
    """This controller commands are 'stacked' onto the base controller."""

    class Meta:
        label = 'script'
        interface = controller.IController
        stacked_on = 'base'
        stacked_type = 'nested'
        description = 'Script runner controller'
        arguments = [
            (['script_name'], {
                'action': 'store',
                'help': 'name of the script file in gryphon/execution/scripts',
                'nargs': '?',
            }),
            (['-X', '--execute'], {
                'action': 'store_true',
                'help': 'Run script in live mode, not test mode',
            }),
        ]

    @controller.expose(help='mark a fiat withdrawal as complete')
    def default(self):
        script_name = self.app.pargs.script_name
        execute = self.app.pargs.execute

        path = 'gryphon.execution.scripts.%s' % script_name

        function_name = 'main'  # All script files implement a main function.
        module = importlib.import_module(path)
        main_function = getattr(module, function_name)

        # This function should be renamed.
        script_arguments = config_helper.parse_extra_strategy_args(
            self.app.args.unknown_args,
        )

        main_function(script_arguments=script_arguments, execute=execute)


class GryphonFury(foundation.CementApp):
    class Meta:
        label = 'gryphon-fury'
        base_controller = GryphonFuryBaseController
        arguments_override_config = True

        argument_handler = 'my_argparse'

        # This is where the main config comes from.
        config_files = ['gryphon-fury.conf']

        handlers = [
            ModifiedArgparseArgumentHandler,
            OrderBookController,
            AuditController,
            ManualController,
            WithdrawController,
            WithdrawFiatController,
            TransactionCompleteController,
            ScriptController,
        ]


def main():
    with GryphonFury() as app:
        app.run()

if __name__ == '__main__':
    main()

