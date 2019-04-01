"""
Functions for calculating different versions of the sharpe ratio, defined roughly as the
ratio of the excess returns of an asset to it's standard deviation.

https://en.wikipedia.org/wiki/Sharpe_ratio
"""

import numpy as np
import pandas as pd

def calculate_sharpe_ratio(series, annualize_by_factor=None):
    """
    Given a raw pandas value/prices series calculate the sharpe ratio of the log
    returns with a risk-free rate of 0. This is an unrealistic assumption but we'll
    use it for now.
    """

    # Convert raw prices into log returns.
    log_prices = np.log(series)
    log_returns = log_prices - log_prices.shift(1)

    raw_sharpe = np.mean(log_returns) / np.std(log_returns)

    if annualize_by_factor is not None:
        return raw_sharpe*np.sqrt(annualize_by_factor)
    else:
        return raw_sharpe
