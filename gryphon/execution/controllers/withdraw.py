import termcolor as tc
import time

from gryphon.lib import session 
from gryphon.lib.exchange.exchange_factory import make_exchange_data_from_key, make_exchange_from_key
from gryphon.lib.logger import get_logger
from gryphon.lib.money import Money
from gryphon.lib.models.transaction import Transaction

logger = get_logger(__name__)


def transaction_complete(exchange_name, currency):
    db = session.get_a_trading_db_mysql_session()
    try:
        exchange_data = make_exchange_data_from_key(exchange_name, db)
        tr = db.query(Transaction).filter_by(exchange=exchange_data).filter_by(_amount_currency=currency).filter_by(transaction_status=Transaction.IN_TRANSIT).order_by(Transaction.time_created).first()
        if tr:
            tr.complete()
            session.commit_mysql_session(db)
            if tr.transaction_type == Transaction.DEPOSIT:
                action = "deposit to"
            elif tr.transaction_type == Transaction.WITHDRAWL:
                action = "withdrawal from"
            logger.info(tc.colored("Recorded %s %s %s" % (tr.amount, action, exchange_name), "green"))
        else:
            logger.info(tc.colored("No Transaction of that currency found", "red"))
    finally:
        db.remove()
    

def withdraw_fiat(exchange_name, target_exchange_name, amount_str, deposit_amount_str, transaction_details):
    db = session.get_a_trading_db_mysql_session()
    try:
        exchange_data = make_exchange_data_from_key(exchange_name, db)
        target_exchange_data = make_exchange_data_from_key(target_exchange_name, db)
        amount = Money.loads(amount_str)
        if deposit_amount_str:
            deposit_amount = Money.loads(deposit_amount_str)
            exchange_data.record_fiat_withdrawal(target_exchange_data, amount, deposit_amount=deposit_amount, transaction_details=transaction_details)
        else:
            exchange_data.record_fiat_withdrawal(target_exchange_data, amount, transaction_details=transaction_details)
            
        session.commit_mysql_session(db)
        logger.info(tc.colored("Recorded %s withdrawal from %s" % (amount, exchange_name), "green"))
    finally:
        db.remove()

def withdraw(exchange_name, target_exchange_name, amount_str):
    db = session.get_a_trading_db_mysql_session()
    try:
        exchange_data = make_exchange_data_from_key(exchange_name, db)
        target_exchange_data = make_exchange_data_from_key(target_exchange_name, db)
        target_exchange = make_exchange_from_key(target_exchange_name)
        amount = Money.loads(amount_str)
        
        addr = target_exchange.current_deposit_address
        exchange_data.record_withdrawal(target_exchange_data, amount, addr)
        session.commit_mysql_session(db)
        logger.info(tc.colored("Recorded %s withdrawal from %s" % (amount, exchange_name), "green"))
    finally:
        db.remove()
