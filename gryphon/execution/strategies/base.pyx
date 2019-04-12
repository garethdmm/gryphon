import ConfigParser
from delorean import Delorean
import pickle
import random
import termcolor as tc

from cdecimal import Decimal, InvalidOperation, ROUND_UP, ROUND_DOWN

from gryphon.lib.configurable_object import ConfigurableObject
from gryphon.lib.exchange.consts import Consts
import gryphon.lib.gryphonfury.positions as positions
from gryphon.lib.logger import get_logger
from gryphon.lib.models.datum import DatumRecorder
from gryphon.lib.models.flag import Flag
from gryphon.lib.models.order import Order
from gryphon.lib.money import Money
from gryphon.lib.session import commit_mysql_session


logger = get_logger(__name__)


MIN_VOLUME_OBFUSCATION = 0.00
MAX_VOLUME_OBFUSCATION = 0.10


class Strategy(ConfigurableObject):
    def __init__(self, db, harness=None, strategy_configuration=None):
        self.db = db
        self.harness = harness

        self._position = None
        self.order_class = Order

        # Configurable properties with defaults only below this line.

        self.volume_currency = 'BTC'

        # How long the strategy pauses between ticks.
        self.tick_sleep = 5

        # Exchanges that the strategy declares it's interested in up-front. It's
        # convenient to have these at startup sometimes.
        self.target_exchanges = []  

        if strategy_configuration:
            self.configure(strategy_configuration)

    def configure(self, strategy_configuration):
        """
        Initialize the strategy's configurable properties based on the configuration
        given to us by the harness, which has already been synthesized from the
        command line and .conf file.
        """
        self.init_configurable('tick_sleep', strategy_configuration)

    def set_up(self):
        """
        In this function do any setup that needs to be done on startup, before we enter
        the tick-loop, that may not be appropriate in the constructor.
        """
        pass

    def pre_tick(self):
        self._max_position = None

        # This is necessary because _position functions as an in-tick cache, so this
        # line clears that cache from last tick. Could also be done in post_tick.
        self._position = None

    def tick(self, order_book, eaten_orders):
        raise NotImplementedError

    def post_tick(self, tick_count):
        pass

    def is_complete(self):
        """
        Strategies can signal to their runners that they are "finished". This isn't
        usually relevant for continuous-trading strategies like a market maker, but is
        very useful for execution strategies, for instance.
        """
        return False

    @property
    def actor(self):
        """
        The strategy's 'actor' is how orders and trades are associated with the
        strategy in the database. As a consequence, if two strategies have the same
        actor, they have the same trade history and position.
        """
        return self.__class__.__name__.upper()

    @property
    def name(self):
        """
        The strategy's 'name' is a less formal identifier for a strategy than it's
        actor, and has nothing to do with the operation of strategies in the framework.
        Use it for things that aren't mission-critical, like to make log messages nice.
        """
        return self.__class__.__name__
   
    @property 
    def position(self):
        if self._position is not None:
            return self._position

        # Currently we just default to assuming the class's actor is it's classname,
        # but we'll improve this shortly.

        self._position = positions.fast_position(
            self.db,
            volume_currency=self.volume_currency,
            actor=self.actor,
        )

        return self._position

