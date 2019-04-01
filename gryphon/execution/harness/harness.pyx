# -*- coding: utf-8 -*-
"""
The Harness is the execution context we provide to Strategies for them to interact with
the outside world. This allows us to provide a level of robustness and simplicity of
interface that would be strictly impossible if strategies were to interact directly with
exchanges themselves.

Adding this level of abstraction is useful for other purposes, too. Sometimes, you'll
want your strategies to run in a context that isn't the real world, such as during
backtesting. For this, you can write another harness (so long as it conforms to the same
interface), and reimplement the interface functions in a different way.
"""

from sets import Set
import termcolor as tc
import time

from cdecimal import ROUND_UP, ROUND_DOWN
from delorean import Delorean
from sqlalchemy.orm import joinedload

from gryphon.execution.lib import auditing
from gryphon.execution.harness.exchange_coordinator import ExchangeCoordinator
from gryphon.lib import configuration as config_lib
from gryphon.lib.configurable_object import ConfigurableObject
from gryphon.lib.exchange import exchange_factory
from gryphon.lib.exchange.retry import exchange_retry
from gryphon.lib.exchange.consts import Consts
from gryphon.lib.exchange.exceptions import CancelOrderNotFoundError
from gryphon.lib.logger import get_logger
from gryphon.lib.models.datum import DatumRecorder
from gryphon.lib.models.order import Order
from gryphon.lib.models.trade import Trade
from gryphon.lib.money import Money
from gryphon.lib.session import commit_mysql_session
from gryphon.lib.util.profile import tick_profile

logger = get_logger(__name__)

ORDERBOOK_DELAY_SAMPLE_SIZE = 10


class Harness(ConfigurableObject):
    def __init__(self, db, configuration):
        self.db = db

        self.strategy = None

        # Configurables.
        self.execute = False
        self.emerald = False
        self.audit = False
        self.audit_tick = 100
        self.audit_types = []

        if configuration:
            self.configure(configuration)

        self.initialize_coordinators(configuration)

    def configure(self, configuration):
        self.init_configurable('execute', configuration['platform'])
        self.init_configurable('emerald', configuration['platform'])
        self.init_configurable('audit', configuration['platform'])
        self.init_configurable('audit_tick', configuration['platform'])
        self.init_configurable('audit_types', configuration['platform'])

        if type(self.audit_types) is str:
            if self.audit_types.lower() == 'all':
                self.audit_types = auditing.ALL_AUDITS
            else:
                self.audit_types = config_lib.parse_configurable_as_list(
                    self.audit_types,
                )

    def initialize_coordinators(self, configuration):
        """
        The harness has an exchange connection for every gryphon integrated exchange.
        Only those exchanges which have an initialized ledger and proper credentials
        will be 'tradable', or able to access authenticated endpoints. You can tell
        which exchanges are tradable by looking at harness.tradable_exchanges.
        """

        self.exchanges = []

        for exchange_name in exchange_factory.ALL_EXCHANGE_KEYS:
            api_wrapper_class = exchange_factory.get_api_wrapper_class_by_name(
                exchange_name,
            )

            exchange_coordinator = ExchangeCoordinator(
                api_wrapper_class(configuration=configuration),
                self.db,
                self,
            )

            setattr(self, exchange_name.lower(), exchange_coordinator)

            self.exchanges.append(exchange_coordinator)

        self.log('The following exchanges will be tradable: %s' % (
            [e.name for e in self.tradable_exchanges],
        ))

    def exchange_from_key(self, exchange_name):
        return self._exchange_dict[exchange_name.lower()]

    @property
    def _exchange_dict(self):
        return {e.name.lower(): e for e in self.exchanges}

    @property
    def tradable_exchanges(self):
        """
        A tradable exchange is one for which we have an initialized ledger in the db
        (a row in the Exchange table), and which has a working api connection.
        """
        return [e for e in self.exchanges if e.is_tradable]

    @property
    def non_tradable_exchanges(self):
        """
        A tradable exchange is one for which we have an initialized ledger in the db
        (a row in the Exchange table), and which has a working api connection.
        """
        return [e for e in self.exchanges if not e.is_tradable]

    @property
    def active_exchanges(self):
        """
        Active exchanges are those that have had trading activity since the last audit,
        which means we have to run consolidate_ledger() for them every tick.
        """
        return [e for e in self.exchanges if e.is_active]

    @property
    def auditable_exchanges(self):
        """
        Auditable exchanges are those that we'll run audits on, either because they've
        had trading activity on them or because the strategy listed them in
        target_exchanges. Only tradable exchanges are auditable.
        """
        return [
            e for e in self.tradable_exchanges
            if e.is_active or e.name in self.strategy.target_exchanges
        ]

    ## Tick code-path functions. ##

    def tick(self):
        """
        Consolidate the ledgers and the tick the strategy.
        """

        self.pre_tick_algo()

        current_orders = self.consolidate_ledgers()

        self.pre_tick_logging(current_orders)

        self.tick_algo(current_orders)

    @tick_profile
    def pre_tick_algo(self):
        self.strategy.pre_tick()

    @tick_profile
    def tick_algo(self, current_orders):
        self.strategy.tick(current_orders)

    def post_tick(self, tick_count):
        self.strategy.post_tick(tick_count)

    def sleep_time_to_next_tick(self):
        # Is tick a property of the strategy or of the platform...
        # It can be a property of the strategy and still a built-in argument.
        return self.strategy.tick_sleep

    def pre_tick_logging(self, current_orders):
        self.log_position()
        self.log_balances()
        self.log_orders(current_orders)

    def consolidate_ledgers(self):
        """
        Make sure that our ledger agrees with the exchange's state for each exchange
        that we've been making trades on.
        """

        current_orders = {}

        for exchange in self.active_exchanges:
            exchange_current_orders = exchange.consolidate_ledger()
            current_orders[exchange.name] = exchange_current_orders

        return current_orders

    ## Harness Interface Functions. ##

    def strategy_complete(self):
        return self.strategy.is_complete()

    ## Accounting and auditing functions. ##

    @exchange_retry()
    def wind_down(self):
        self.log('Winding Down')

        self.log('Cancelling All Open Orders')

        for exchange in self.auditable_exchanges:
            exchange.cancel_all_open_orders()

        time.sleep(10)

        self.log('Consolidating Ledgers')

        current_orders = self.consolidate_ledgers()

        # All orders should have been cancelled by now.
        assert all([len(orders) == 0 for orders in current_orders.values()])

    ##  Logging functions. ##

    def log(self, format_string, string_args=None, color=None, log_level='info'):
        """
        This function simply attaches the date and colours to a log message, and then
        dispatches to the appropriate logger function.
        """
        timestamp = unicode(Delorean().datetime.strftime('%d/%m/%y %H:%M:%S %Z'))

        result_string = u'[%s] (%s) %s' % (
            self.strategy.name if self.strategy else 'HARNESS_SETUP',
            timestamp,
            format_string,
        )

        if string_args != None:
            result_string = result_string % string_args

        if color:
            result_string = tc.colored(result_string, color)

        if log_level == 'info':
            logger.info(result_string)
        elif log_level == 'debug':
            logger.debug(result_string)
        elif log_level == 'error':
            logger.error(result_string)
        elif log_level == 'critical':
            logger.critical(result_string)

    def log_position(self):
        volume_position = self.strategy.position
        self.log('Open position: %s', volume_position, 'magenta')

    def log_balances(self):
        volume_currency = self.strategy.volume_currency

        self.log('Available balances:', color='magenta')

        for exchange in self.auditable_exchanges:
            volume_balance = exchange.exchange_account.balance[volume_currency]
            price_balance = exchange.exchange_account.balance[exchange.currency]

            self.log(
                '  %s: %s %s',
                (exchange.name, volume_balance, price_balance),
                'magenta',
            )

        # We currently only support lines-of-credit for Bitcoin.
        if self.strategy.volume_currency == 'BTC' and False:
            btc_credit_limit = self.strategy.exchange.btc_credit_limit

            if btc_credit_limit > 0:
                self.log(
                    'With Credit: %s',
                    (volume_balance + btc_credit_limit),
                    'magenta',
                )

    def log_orders(self, current_orders):
        """
        TODO: Let strategies overload this function somehow so they can give their own
        representation of the open order state (e.g. get our [asks][fv][bids] display
        back for market making strats.
        """

        self.log('Open Orders:', color='cyan')

        for exchange_name, exchange_orders in current_orders.items():
            self.log('  %s' % exchange_name, color='cyan')

            bids = [o for o in exchange_orders if o['mode'] == Consts.BID]
            asks = [o for o in exchange_orders if o['mode'] == Consts.ASK]
            bids.sort(key=lambda o: o['price'], reverse=True)
            asks.sort(key=lambda o: o['price'], reverse=True)

            for ask in asks:
                self.log(
                    '\tAsk : %.2f   %.4f',
                    (ask['price'].amount, ask['volume_remaining'].amount),
                    'cyan',
                )

            for bid in bids:
                self.log(
                    '\tBid : %.2f   %.4f',
                    (bid['price'].amount, bid['volume_remaining'].amount),
                    'cyan',
                )

    def log_trade(self, fiat_change, volume_change):
        """
        Log trades as we account for them. TODO: This function has recently been moved
        into ExchangeCoordinator, where it has access to the specific order information,
        so we could rewrite this function to print out more specific info than just
        the relative position change.
        """

        # No trades happened.
        if volume_change == Money('0', self.strategy.volume_currency):
            return

        price_per_unit_volume = abs(fiat_change) / abs(volume_change).amount

        if volume_change > 0:  # Bought tokens.
            self.log(
                'Bought %s at a price of %s',
                (abs(volume_change), abs(fiat_change)),
                'green',
            )
        elif volume_change < 0:  # Sold tokens.
            self.log(
                'Sold %s at a price of %s',
                (abs(volume_change), abs(fiat_change)),
                'green',
            )

    # Auditing functions.

    def full_audit(self, wind_down=True):
        if wind_down:
            self.wind_down()

        for exchange in self.auditable_exchanges:
            exchange.audit(self.audit_types)

