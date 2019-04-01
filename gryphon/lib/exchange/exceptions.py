"""
A collection of exceptions to handle regular failures from exchange APIs.
"""

class ExchangeException(Exception):
    pass

    
class CancelOrderNotFoundError(ExchangeException):
    pass


class InsufficientFundsError(ExchangeException):
    pass


class MinimumOrderSizeError(ExchangeException):
    pass


class NonceError(ExchangeException):
    pass


class NoEffectOrderCancelledError(ExchangeException):
    pass


class ExchangeAPIFailureException(ExchangeException):
    def __init__(self, exchange, response=None, message=''):
        if response != None and message:
            raise ValueError('Only specify one of response and message')

        if message:
            error_message = message
        else:
            error_message = 'No response' if response == None else response.text

        message = '[%s] %s' % (exchange.name, error_message)

        super(ExchangeAPIFailureException, self).__init__(message)
        self.exchange = exchange
        self.response = response


class ExchangeAPIErrorException(ExchangeException):
    def __init__(self, exchange, message):
        super_message = '[%s] %s' % (exchange.name, message)
        super(ExchangeAPIErrorException, self).__init__(super_message)
        self.exchange = exchange
        self.message = message


class CachedOrderbookFailure(ExchangeException):
    def __init__(self, exchange, message):
        super_message = '[%s] %s' % (exchange.name, message)
        super(CachedOrderbookFailure, self).__init__(super_message)


class ExchangeNotIntegratedError(ExchangeException):
    """
    This exception is used to indicate that the user is trying to trade on an exchange
    that Gryphon doesn't know about or hasn't been integrated.
    """
    def __init__(self, exchange_name):
        message = """Gryphon does not have an integration for the exchange named %s. Maybe you forgot to qualify the exchange name with its trading pair, like BITSTAMP_BTC_USD, or maybe Gryphon just doesn\'t support that exchange.""" % exchange_name

        super(ExchangeNotIntegratedError, self).__init__(message)

