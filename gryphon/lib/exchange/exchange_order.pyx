from gryphon.lib.money import Money
from gryphon.lib.exchange.consts import Consts

class Order(object):
    __slots__ = ('status', 'exchange', 'order_id', 'price', 'volume', 'type')
    BID = Consts.BID
    ASK = Consts.ASK
    OPEN =u'OPEN'

    CREATED = u'CREATED'
    UNFILLED = u'UNFILLED'
    PARTIALLY_FILLED = u'PARTIALLY_FILLED'
    FILLED = u'FILLED'
    CANCELLED = u'CANCELLED'
    # we use this to flag our orders in an orderbook
    FLAGGED = u'FLAGGED'
    
    
    def  __init__(self, price, volume, exchange, type, order_id=None, status=None):
        self.status = status if status else Order.OPEN
        self.order_id = order_id
        self.price = price
        self.volume = volume
        self.exchange = exchange
        self.type = type

    def __str__(self):
        return (u'[EXCHANGE ORDER] - %s - %s -[%s @ %s] - Status:%s - Order ID:%s' %
            (self.type, self.exchange.name, self.volume, self.price, self.status, self.order_id))

    def __repr__(self):
        return "<" + unicode(self) + ">"

    def __eq__(self, other):
        return (self.order_id == other.order_id and 
            self.price == other.price and 
            self.volume == other.volume and 
            self.type == other.type and
            self.exchange == other.exchange)
            
    def __lt__(self, other):
        return self.price < other.price
    
    def apply_fee(self):
        if self.type == Order.ASK:
            self.price += (self.price * self.exchange.fee)
        elif self.type == Order.BID:
            self.price -= (self.price * self.exchange.fee)
    
    
    @staticmethod
    def scopy(order_to_copy):
        return Order(
            order_to_copy.price,
            order_to_copy.volume,
            order_to_copy.exchange, 
            order_to_copy.type,
            order_to_copy.order_id, 
            order_to_copy.status)

    @staticmethod
    def copy(order_to_copy):
        return Order(
            Money(order_to_copy.price.amount, order_to_copy.price.currency),
            Money(order_to_copy.volume.amount, order_to_copy.volume.currency),
            order_to_copy.exchange, 
            order_to_copy.type,
            order_to_copy.order_id, 
            order_to_copy.status)

