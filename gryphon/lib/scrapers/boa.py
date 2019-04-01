import gryphon.lib; gryphon.lib.prepare()

import os

from delorean import Delorean
import ofxclient

from gryphon.lib.logger import get_logger
from gryphon.lib.models.transaction import Transaction
from gryphon.lib.money import Money
from gryphon.lib.scrapers.base import Scraper

logger = get_logger(__name__)


class BoAScraper(Scraper):
    def __init__(self):
        self.statements = {}

    def load(self):
        institution = ofxclient.Institution(
            id='5959',
            org='HAN',
            url='https://eftx.bankofamerica.com/eftxweb/access.ofx',
            username=os.environ['BOA_USERNAME'],
            password=os.environ['BOA_PASSWORD'],
        )

        try:
            institution.authenticate()
        except ValueError as e:
            raise Scraper.MaintenanceException(e)

        account_data = []
        ofx_accounts = institution.accounts()
        for ofx_account in ofx_accounts:
            account_number = ofx_account.number
            statement = ofx_account.statement()

            # save these so that load_transactions can use them
            self.statements[account_number] = statement

            balance = Money(statement.balance, 'USD')

            account = {
                'account_number': account_number,
                'balance': balance,
            }
            account_data.append(account)

        return account_data

    def load_transactions(self, account_num):
        statement = self.statements[account_num]

        transactions = []
        for ofx_transaction in reversed(statement.transactions):

            amount = Money(ofx_transaction.amount, 'USD')
            if amount > 0:
                transaction_type = Transaction.DEPOSIT
            else:
                amount = abs(amount)
                transaction_type = Transaction.WITHDRAWL

            timestamp = int(Delorean(ofx_transaction.date, timezone='UTC').epoch)

            transactions.append({
                'timestamp': timestamp,
                'description': ofx_transaction.payee,
                'amount': amount,
                'type': transaction_type,
                # 'id': ofx_transaction.id,
            })

        return transactions

    def quit(self):
        # BMO Scraper needs to quit phantomjs, so we need it here to preserve a common interface
        pass


def main():
    scraper = BoAScraper()
    print scraper.load()
    print scraper.load_transactions(os.environ['BOA_MAIN_ACCOUNT_NUMBER'])
    scraper.quit()

if __name__ == '__main__':
    main()
