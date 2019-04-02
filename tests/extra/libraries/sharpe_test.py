import pyximport; pyximport.install()
import gryphon.lib; gryphon.lib.prepare()

import datetime
import unittest

import mock
import numpy as np
import pandas as pd
import sure

import gryphon.lib.analysis.sharpe as sharpe


class TestSharpe(unittest.TestCase):
    def setUp(self):
        self.series = pd.Series(
            range(1, 24),
            index=[datetime.datetime(2015, 1, 1, i) for i in range(1,24)],
        )

    def tearDown(self):
        pass

    def test_basic(self):
        s = sharpe.calculate_sharpe_ratio(self.series, annualize_by_factor=24*365)
        s.should.equal(np.float64(89.671800634636767))

    def test_probabilistic(self):
        """
        Sharpe ratio of a normal(0,1) variable should be zero, since it's mean is
        close to zero and the std deviation is 1.
        """

        log_returns = pd.Series(np.random.normal(0, 1, 10000))
        s = sharpe.calculate_sharpe_ratio(log_returns)
        s = abs(s)

        self.assertTrue(s < 0.01)

