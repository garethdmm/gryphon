import logging
import os

import selenium
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from gryphon.lib.logger import get_logger
from gryphon.lib.models.transaction import Transaction
from gryphon.lib.money import Money
from gryphon.lib.scrapers.base import Scraper
from gryphon.lib.time_parsing import parse

logger = get_logger(__name__)


class BMOScraper(Scraper):
    def __init__(self):
        self.is_ready = False
        self.account_data = []

    def load_transactions(self, account_num):
        """
        Loads the transactions page for each account, and adds them to self.account_data
        """
        self.load()

        logger.debug('transactions')

        for account_idx, account in enumerate(self.account_data):
            if account['account_number'] == account_num:
                # account_idx and account now match the account_num we passed in
                break

        # this is a bit fragile, but chances are if BMO changes their JS framework
        # they'll also change the page layout/markup and this whole scraper will break
        path = '/onlinebanking/OLB/fin/acc/adt/accountDetailsInit?mode=confirmation'
        js = "goto('%s',{inquiryAccountIndex:'%d'})" % (path, account_idx)
        self.driver.execute_script(js)

        transactions = self.get_transactions_from_page(account)

        return transactions

    def get_transactions_from_page(self, account):
        """
        Parses out records from a transactions page.

        Assumes the driver has already navigated to a transactions page.
        """
        logger.debug('get_transactions_from_page')

        account_num = account['account_number']
        account_currency = account['balance'].currency

        self.wait_for_text_on_page('Transaction History')
        self.wait_for_text_on_page('Balance Forward')

        # We need to look for the specific account number because the wait_for_text checks above
        # can match on the transactions page we were previously on
        logger.debug('waiting for account number to match %s' % account_num)
        WebDriverWait(self.driver, 10).until(EC.text_to_be_present_in_element((By.CSS_SELECTOR, '.bodyCopy .cardNumber'), account_num))

        transaction_selector = '#ccChequingTransactionTable tbody tr'
        transaction_els = self.driver.find_elements_by_css_selector(transaction_selector)
        transaction_els.pop(0) # drop the Balance Forward row

        transactions = []

        for el in transaction_els:
            date = el.find_element_by_css_selector('td:nth-child(1)').text
            code = el.find_element_by_css_selector('td:nth-child(2)').text
            description = el.find_element_by_css_selector('td:nth-child(3)').text
            raw_debit = el.find_element_by_css_selector('td:nth-child(4)').text
            raw_credit = el.find_element_by_css_selector('td:nth-child(5)').text
            raw_balance = el.find_element_by_css_selector('td:nth-child(6)').text

            if raw_debit and raw_credit:
                raise Exception('Only one of debit and credit fields should be present')
            elif not raw_debit and not raw_credit:
                raise Exception('One of debit and credit fields should be present')
            elif raw_debit:
                debit = self.string_to_money(raw_debit + ' ' + account_currency)
                amount = debit
                transaction_type = Transaction.WITHDRAWL
            elif raw_credit:
                credit = self.string_to_money(raw_credit + ' ' + account_currency)
                amount = credit
                transaction_type = Transaction.DEPOSIT

            balance = self.string_to_money(raw_balance + ' ' + account_currency)

            timestamp = int(parse(date).epoch)

            transactions.append({
                'timestamp': timestamp,
                'description': description,
                'amount': amount,
                'type': transaction_type,
                # 'code': code,
                # 'balance': balance,
            })

        return transactions

    # Step-by-step Functions

    def load(self):
        if self.is_ready:
            return

        self.driver = webdriver.PhantomJS()
        self.driver.set_window_size(1024, 768)
        self.driver.get('https://www1.bmo.com/onlinebanking/cgi-bin/netbnx/NBmain?product=5')

        self.sign_in()

        self.save_account_data()
        return self.account_data

    def sign_in(self):
        logger.debug('sign_in')
        self.wait_for_text_on_page('Sign in to Online Banking')
        self.screenshot('sign_in')

        card_field = self.css('#siBankCard')
        card_field.send_keys(os.environ['BMO_CARD_NUMBER'])

        password_field = self.css('#regSignInPassword')
        password_field.send_keys(os.environ['BMO_PASSWORD'])

        self.screenshot('sign_in_filled')

        try:
            continue_btn = self.css('[widgetid="btnBankCardContinue"] [role="button"]')
        except selenium.common.exceptions.NoSuchElementException:
            continue_btn = self.css('[widgetid="btnBankCardContinueNoCache1"] [role="button"]')

        continue_btn.click()

        self.wait_for_text_on_page('Challenge Question', 'My Accounts')

        if self.text_on_page('Challenge Question'):
            self.challenge_question()
        elif self.text_on_page('My Accounts'):
            self.accounts()

    def challenge_question(self):
        logger.debug('challenge_question')
        self.wait_for_text_on_page('Challenge Question')
        self.screenshot('challenge_question')

        security_question = self.css('#lblregSecurityQuestion').text.lower()

        if 'cousin' in security_question:
            security_answer = os.environ['BMO_SECURITY_COUSIN']
        elif 'sibling' in security_question:
            security_answer = os.environ['BMO_SECURITY_SIBLING']
        elif 'born' in security_question:
            security_answer = os.environ['BMO_SECURITY_CITY']
        else:
            logger.info(self.page_source())
            raise Exception('Don\'t recognize security question: "%s"' % security_question)

        logger.debug('Answering "%s" with "%s"' % (security_question, security_answer))

        security_answer_field = self.css('#signInSecurityQuestion')
        security_answer_field.send_keys(security_answer)

        self.screenshot('challenge_question_filled')

        continue_btn = self.css('[widgetid="btnContinue"] [role="button"]')
        continue_btn.click()

        self.accounts()

    def accounts(self):
        logger.debug('accounts')

        self.wait_for_text_on_page('My Accounts')

        self.screenshot('accounts')

    def save_account_data(self):
        logger.debug('save_account_data')

        account_selector = '#BankAccounts tr td.tableContainer table tr'
        account_els = self.driver.find_elements_by_css_selector(account_selector)

        for el in account_els:
            account_num = el.find_element_by_css_selector('.accountNumber').text
            raw_balance = el.find_element_by_css_selector('.summaryBalance.totals').text

            balance = self.string_to_money(raw_balance)

            account = {
                'account_number': account_num,
                'balance': balance,
            }
            self.account_data.append(account)

        self.is_ready = True

    # Helper Functions

    def wait_for_text_on_page(self, *texts):
        ecs = []

        logger_text = ' OR '.join(['"%s"' % t for t in texts])
        logger.debug('waiting until body contains %s' % logger_text)

        for text in texts:
            ec = EC.text_to_be_present_in_element((By.CSS_SELECTOR, 'body'), text)
            ecs.append(ec)

        try:
            WebDriverWait(self.driver, 10).until(AnyEc(*ecs))
        except selenium.common.exceptions.TimeoutException:
            if (self.text_on_page('Service is temporarily unavailable') or
                    self.text_on_page('maintenance')):
                raise Scraper.MaintenanceException()

            logger.info(self.page_text())
            raise selenium.common.exceptions.TimeoutException(
                'Couldn\'t find %s on the page' % logger_text
            )

    def text_on_page(self, text):
        return text in self.page_text()

    def page_text(self):
        return self.driver.find_element_by_css_selector('body').text

    def page_source(self):
        return self.driver.page_source

    def css(self, selector):
        return self.driver.find_element_by_css_selector(selector)

    def screenshot(self, name):
        if logger.level == logging.DEBUG:
            directory = '%s/screenshots' % os.path.dirname(os.path.realpath(__file__))

            if not os.path.exists(directory):
                os.makedirs(directory)

            self.driver.save_screenshot('%s/%s.png' % (directory, name))

    def string_to_money(self, s):
        """
        Handles strings of the format "$77,234.58 USD "
        """
        s = s.strip()
        s = s.replace('$', '')
        parts = s.split(' ')

        if len(parts) != 2:
            raise ValueError('String has too many parts (split on spaces)')

        amount, currency = parts
        return Money(amount, currency)

    def quit(self):
        self.driver.quit()


class AnyEc:
    """
    Use with WebDriverWait to combine expected_conditions in an OR.
    From http://stackoverflow.com/a/16464305/2208702
    """
    def __init__(self, *args):
        self.ecs = args

    def __call__(self, driver):
        for fn in self.ecs:
            try:
                if fn(driver):
                    return True
            except:
                pass


def main():
    scraper = BMOScraper()
    print scraper.load()
    print scraper.load_transactions(os.environ['BMO_USD_ACCOUNT_NUMBER'])
    print scraper.load_transactions(os.environ['BMO_CAD_ACCOUNT_NUMBER'])
    scraper.quit()

if __name__ == '__main__':
    main()
