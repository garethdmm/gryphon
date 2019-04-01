import prompter
import termcolor as tc

from gryphon.lib.exchange import exchange_factory
from gryphon.lib.logger import get_logger
from gryphon.lib.models.trade import Trade
from gryphon.lib.models.transaction import Transaction
from gryphon.lib.money import Money
from gryphon.lib import session

logger = get_logger(__name__)

def buyback():
    prompt_msg = tc.colored('Did you stop the Coinbase Bot before running this?', 'red')
    bot_stopped = prompter.yesno(prompt_msg)
    if not bot_stopped:
        print tc.colored('Go stop the bot first.', 'red')
        return

    db = session.get_a_trading_db_mysql_session()
    try:
        trades_with_outstanding_fees = db.query(Trade)\
            .filter(Trade.has_outstanding_btc_fee)\
            .all()

        transactions_with_outstanding_fees = db.query(Transaction)\
            .filter(Transaction.has_outstanding_btc_fee)\
            .all()

        coinbase_exchange_data = exchange_factory.make_exchange_data_from_key('COINBASE', db)

        trades_buyback_amount = sum([t.fee for t in trades_with_outstanding_fees])
        transactions_buyback_amount = sum([t.fee for t in transactions_with_outstanding_fees])
        btc_buyback_amount = trades_buyback_amount + transactions_buyback_amount

        print 'Go buy %s on Coinbase (not the exchange)' % btc_buyback_amount

        prompt_msg = 'How much USD did it cost (total including Coinbase Fee): USD'
        raw_usd_cost = prompter.prompt(prompt_msg)
        usd_cost = Money(raw_usd_cost, 'USD')

        withdrawal = Transaction(
            Transaction.WITHDRAWL,
            Transaction.IN_TRANSIT,
            usd_cost,
            coinbase_exchange_data,
            {'notes': 'BTC Fee Buyback'},
        )
        deposit = Transaction(
            Transaction.DEPOSIT,
            Transaction.IN_TRANSIT,
            btc_buyback_amount,
            coinbase_exchange_data,
            {'notes': 'BTC Fee Buyback'},
        )

        withdrawal.complete()
        deposit.complete()

        for trade in trades_with_outstanding_fees:
            trade.fee_buyback_transaction = deposit

        for transaction in transactions_with_outstanding_fees:
            transaction.fee_buyback_transaction = deposit

    finally:
        session.commit_mysql_session(db)
        db.remove()
