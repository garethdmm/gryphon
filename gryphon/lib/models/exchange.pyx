# -*- coding: utf-8 -*-
import copy
import json
import uuid

from delorean import parse
from sqlalchemy import Column, Integer, Unicode, Numeric, PickleType
from sqlalchemy import or_, and_
from sqlalchemy import func
from sqlalchemy.ext.mutable import Mutable
from sqlalchemy.orm import relationship, reconstructor, Session
from sqlalchemy.types import TypeDecorator, UnicodeText

from gryphon.lib import gryphon_json_serialize
from gryphon.lib.exchange.exchange_factory import make_exchange_from_key
from gryphon.lib.logger import get_logger
from gryphon.lib.models.base import Base
from gryphon.lib.models.order import Order
from gryphon.lib.models.trade import Trade
from gryphon.lib.models.transaction import Transaction
from gryphon.lib.money import Money

logger = get_logger(__name__)

metadata = Base.metadata


class JSONEncodedMoneyDict(TypeDecorator):
    """
    This class handles storage and retrieval of certain data in the database,
    specifically dictionaries wherein all keys are Money objects. This is used in
    conjuction with MutableDict below to store balance information for exchange accounts
    and a few other things.
    """

    impl = UnicodeText(length=2**31)

    def load_json_money_dict(self, value):
        d = json.loads(value)

        for key, value in d.items():
            d[key] = Money.loads(value)

        return d

    def process_bind_param(self, value, dialect):
        if value is not None:
            value = json.dumps(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = self.load_json_money_dict(value)
        return value


class MutableDict(Mutable, dict):
    """
    Used in conjunction with JSONMoneyDict as above, the MutableDict constructor is
    called when we load the mutable columns. This calls coerce(cls, key, value), where
        cls ~ is the Class of the column (Balance, Position, Target0,
        key ~ is the name of the column
        value ~ is the result that's been parsed by JSONEncodedMoneyDict.

    This is all based on sqlalchemy documentation here:
        https://docs.sqlalchemy.org/en/latest/orm/extensions/mutable.html

    The examples for MutableDict have a strange control flow to them that I don't
    understand, but the result that we want is for these to be available as their proper
    Balance/Position/Target classes when we load them, and this can be achieved just by
    doing return cls(value) in the coerce method.
    """
    @classmethod
    def coerce(cls, key, value):
        if isinstance(value, dict) and cls in [Balance, Position, Target]:
            return cls(value)
        else:
            # This will error.
            return Mutable.coerce(key, value)

    def __delitem(self, key):
        dict.__delitem__(self, key)
        self.changed()

    def __setitem__(self, key, value):
        dict.__setitem__(self, key, value)
        self.changed()

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, state):
        self.update(self)


class Balance(MutableDict):
    def __missing__(self, key):
        value = self[key] = Money(0, key)
        return value

    def __add__(self, other):
        # Make a deep copy of self. copy.deepcopy() is 4x slower than this
        # because we know the exact structure and don't have to watch for recursions
        result = self.__class__()
        for currency, m in self.iteritems():
            result[currency] = Money(m.amount, m.currency)

        if isinstance(other, Balance):
            all_currencies = list(set(self.keys() + other.keys()))
            for c in all_currencies:
                result[c] += other[c]
        elif isinstance(other, Money):
            result[other.currency] += other
        else:
            raise ValueError('Can only add Money and Balance objects')
        return result

    def __neg__(self):
        result = self.__class__()
        for currency, balance in self.iteritems():
            result[currency] = -balance
        return result

    def __sub__(self, other):
        return self + (-other)

    def fiat(self):
        currencies = self.keys()

        non_btc_currencies = [c for c in currencies if c != 'BTC']
        if len(non_btc_currencies) > 1:
            raise ValueError('Balance has more than one fiat currency')
        elif len(non_btc_currencies) < 1:
            return None

        fiat_currency = non_btc_currencies[0]
        return self[fiat_currency]

    def total_usd_value(self, date=None):
        total_usd_value = Money(0, 'USD')
        for currency, balance in self.iteritems():
            total_usd_value += balance.to('USD', date=date)
        return total_usd_value


class Position(Balance):
    pass


class Target(Balance):
    pass


class Exchange(Base):
    __tablename__ = 'exchange'

    exchange_id = Column(Integer, primary_key=True)
    unique_id = Column(Unicode(64), nullable=False)
    name = Column(Unicode(64), nullable=False)

    position = Column(Position.as_mutable(JSONEncodedMoneyDict))
    target = Column(Target.as_mutable(JSONEncodedMoneyDict))
    balance = Column(Balance.as_mutable(JSONEncodedMoneyDict))

    _multi_position_cache = Column('multi_position_cache', Numeric(precision=24, scale=14))

    # lazy=dynamic makes this behave like a query
    transactions = relationship('Transaction', cascade='all,delete-orphan', backref='exchange', lazy='dynamic')

    def __init__(self, name):
        self.unique_id = unicode(uuid.uuid4().hex)
        self.name = name
        self.position = Position()
        self.target = Target()
        self.balance = Balance()
        self.multi_position_cache = Money(0, 'BTC')

    @reconstructor
    def init_on_load(self):
        if not self.position:
            self.position = Position()
        if not self.target:
            self.target = Target()
        if not self.balance:
            self.balance = Balance()

    def __unicode__(self):
        return u'[EXCHANGE: %s] Position: %s Target: %s Balance: %s' % (
           self.name, self.position, self.target, self.balance)

    def __repr__(self):
        return self.to_json()

    def to_json(self):
        return json.dumps({
            'name': self.name,
            'exchange_id': self.exchange_id,
            'unique_id': self.unique_id,
            'position': self.position,
            'target': self.target,
            'balance': self.balance,
        }, ensure_ascii=False)

    @property
    def multi_position_cache(self):
        return Money(self._multi_position_cache, 'BTC')

    @multi_position_cache.setter
    def multi_position_cache(self, value):
        if value.currency != 'BTC':
            raise ValueError('multi_position_cache must be a BTC Money object')
        self._multi_position_cache = value.amount

    def record_fiat_withdrawal(self, target_exchange_data, withdrawal_amount, deposit_amount=None, transaction_details={}):
        if deposit_amount:
            logger.info('deposit amount: %s' % deposit_amount)
            if deposit_amount.currency != withdrawal_amount.currency:
                exchange_rate = str(withdrawal_amount.amount / deposit_amount.amount)
                transaction_details.update({'exchange_rate': exchange_rate})

        withdrawal_fee = None
        source_exchange = make_exchange_from_key(self.name)
        # We don't have exchange objects for bank accounts (BMO_USD, BMO_CAD)
        if source_exchange:
            withdrawal_fee = source_exchange.fiat_withdrawal_fee(withdrawal_amount)
            # assumes that fees are taken out of the withdrawal amount instead of the balance
            withdrawal_amount -= withdrawal_fee

        withdrawal = Transaction(Transaction.WITHDRAWL, Transaction.IN_TRANSIT, withdrawal_amount, self, transaction_details, fee=withdrawal_fee)
        withdrawal.complete()

        if deposit_amount is None:
            deposit_amount = withdrawal_amount

        deposit_fee = None
        target_exchange = make_exchange_from_key(target_exchange_data.name)
        if target_exchange:
            deposit_fee = target_exchange.fiat_deposit_fee(deposit_amount)

        deposit = Transaction(Transaction.DEPOSIT, Transaction.IN_TRANSIT, deposit_amount, target_exchange_data, transaction_details, fee=deposit_fee)

        return (deposit, withdrawal)

    def record_withdrawal(self, target_exchange_data, amount, deposit_address='', transaction_hash='', exchange_withdrawal_id=''):
        details = {}
        if deposit_address:
            details['deposit_address'] = deposit_address
        if transaction_hash:
            details['transaction_hash'] = transaction_hash
        if exchange_withdrawal_id:
            details['exchange_withdrawal_id'] = exchange_withdrawal_id

        exchange = make_exchange_from_key(self.name)
        withdrawal_fee = exchange.withdrawal_fee
        deposit = Transaction(Transaction.DEPOSIT, Transaction.IN_TRANSIT, amount, target_exchange_data, details)
        withdrawl = Transaction(Transaction.WITHDRAWL, Transaction.IN_TRANSIT, amount, self, details, fee=withdrawal_fee)
        withdrawl.complete()
        return (deposit, withdrawl)

    def pending_deposits(self, currency=None):
        query = self.transactions.filter(Transaction.transaction_type == Transaction.DEPOSIT).filter(Transaction.transaction_status == Transaction.IN_TRANSIT)
        if currency:
            query = query.filter(Transaction._amount_currency == currency)
        return query.all()

    def combinations_of_all_lengths(self, items):
        result = []
        from itertools import combinations
        for comb_length in range(1, len(items) + 1):
            combs = combinations(items, comb_length)
            result += combs
        return result

    def deposit_landed(self, amount_changed, tolerance=0):
        expected_deposits = self.pending_deposits(amount_changed.currency)
        possible_combinations = self.combinations_of_all_lengths(expected_deposits)
        for c in possible_combinations:
            total_amount = 0
            for deposit in c:
                total_amount += deposit.amount
                if deposit.fee:
                    total_amount -= deposit.fee
            # we found a combination of deposits which match the amount changed
            # this should have a tolerance
            if abs(total_amount - amount_changed) <= tolerance:
                for deposit in c:
                    deposit.complete()

                deposit_ids = [int(d.transaction_id) for d in c]
                logger.info('Deposits %s for %s match up to the %s change in balance' % (deposit_ids, total_amount, amount_changed))
                return True
        return False

    @property
    def full_balance(self):
        in_transit_transactions = self.pending_deposits()

        in_transit_balance = copy.deepcopy(self.balance)
        for tr in in_transit_transactions:
            in_transit_balance[tr.amount.currency] += tr.amount
        return in_transit_balance

    @property
    def trades(self):
        session = Session.object_session(self)

        return session.query(Trade)\
            .join(Order)\
            .filter(Order._exchange_name.in_(self.all_pair_names))

    def ledger(self, start_time, end_time, currency=None):
        """
        Load the most recent <limit> entries in the ledger (Trades or Transactions).

        Can filter to only entries which affect a specific <currency>.
        """
        from gryphon.lib import assets

        if start_time and start_time < assets.EARLIEST_CORRECT_LEDGER_DATE:
            raise ValueError(
                'start_time must be later than %s' % (
                    assets.EARLIEST_CORRECT_LEDGER_DATE,
                ))

        if end_time and end_time < assets.EARLIEST_CORRECT_LEDGER_DATE:
            raise ValueError(
                'end_time must be later than %s' % assets.EARLIEST_CORRECT_LEDGER_DATE,
            )

        trades_query = self.trades\
            .order_by(Trade.time_created.desc())

        if currency:
            trades_query = trades_query.filter(
                or_(
                    Trade._price_currency == currency,
                    Trade._volume_currency == currency,
                    Trade._fee_currency == currency,
                ),
            )

        if start_time:
            trades_query = trades_query.filter(Trade.time_created > start_time)

        if end_time:
            trades_query = trades_query.filter(Trade.time_created <= end_time)

        trades = trades_query.all()

        transactions_query = self.transactions\
            .filter(Transaction.transaction_status == Transaction.COMPLETED)\
            .order_by(Transaction.time_completed.desc())

        if currency:
            transactions_query = transactions_query.filter(
                or_(
                    Transaction._amount_currency == currency,
                    Transaction._fee_currency == currency,
                ),
            )

        if start_time:
            transactions_query = transactions_query.filter(or_(
                and_(
                    Transaction.time_completed != None,
                    Transaction.time_completed > start_time,
                ),
                and_(
                    Transaction.time_completed == None,
                    Transaction.time_created > start_time,
                ),
            ))

        if end_time:
            # We include transactions in the ledger based on when they were completed,
            # not created. This is an issue because we only started recording
            # time_completed on 2015-10-08. So for these pre-time_completed transactions
            # we use their time_created instead.
            transactions_query = transactions_query.filter(or_(
                and_(
                    Transaction.time_completed != None,
                    Transaction.time_completed <= end_time,
                ),
                and_(
                    Transaction.time_completed == None,
                    Transaction.time_created <= end_time,
                ),
            ))

        transactions = transactions_query.all()

        def sort_key(t):
            if isinstance(t, Trade):
                return t.time_created
            elif isinstance(t, Transaction):
                if t.time_completed:
                    return t.time_completed
                else:
                    return t.time_created

        entries = sorted(trades + transactions, key=sort_key, reverse=True)

        return entries

    @property
    def all_pair_names(self):
        # Just a hack until we migrate the db.

        if self.name == 'GEMINI':
            return [self.name, 'GEMINI_ETH_USD']
        else:
            return [self.name]

    def ledger_balance(self, start_time=None, end_time=None, include_pending=False):
        from gryphon.lib import assets
        session = Session.object_session(self)

        return assets.ledger_balance(
            session,
            start_time=start_time,
            end_time=end_time,
            include_pending=include_pending,
            exchange_names=self.all_pair_names,
        )
