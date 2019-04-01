import uuid
from gryphon.lib.exchange.base import Exchange
from gryphon.lib.exchange.consts import Consts

class Trade(object):
    __slots__ = ('ask', 'volume', 'trade_id', 'price', 'bid', 'tick')   
    def  __init__(self, price, volume, bid_order, ask_order, trade_id=uuid.uuid4().hex, tick=0):    
         
        self.trade_id = trade_id
        self.bid = bid_order
        self.ask = ask_order
        self.price = price
        self.volume = volume
        self.tick = tick
        
    def __str__(self):
        return (u'[EXCHANGE Trade] - [%s BTC @ %s USD/BTC] - Bid:%s, Ask:%s' % 
            (self.volume, self.price, self.bid.order_id, self.ask.order_id))

    def __repr__(self):
        return "<" + unicode(self) + ">"
    
    @property
    def trade_type(self):
        if self.bid.order_id:
            return Consts.BID
        elif self.ask.order_id:
            return Consts.ASK
        else:
            raise ValueError('We did not participate in this trade so trade_type doesnt mean anything')

