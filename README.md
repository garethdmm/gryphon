
![alttext](gryphon/dashboards/static/img/gryphon-logo-blue@3x.png)

# Gryphon Trading Framework
**Gryphon** is an open source software platform for building and running algorithmic trading strategies in cryptocurrency markets. It was built by Tinker, one of the earliest cryptocurrency trading companies, and has traded billions in volume to date.


-----------------

| **`Documentation`** | **`Build`** |
|---------|--------|
| [![Documentation](https://img.shields.io/badge/api-reference-blue.svg)](https://gryphon.readthedocs.io/en/latest/) | [![Build Status](https://travis-ci.com/TinkerWork/gryphon.svg?branch=master)](https://travis-ci.com/TinkerWork/gryphon) |
| [![Documentation Status](https://readthedocs.org/projects/gryphon/badge/?version=latest)](https://gryphon.readthedocs.io/en/latest/?badge=latest) |  |

## What's included

Gryphon is both a software library that can be integrated into other projects, and an application suite for running trading strategies and operating a trading business. How you use Gryphon depends on your goals. Some highlights are:

Library Highlights:
* Exchange integrations ~ Because cryptocurrency exchanges all have their own API specifications, quirks, and issues, Gryphon includes a set of wrappers that conform these exchange APIs to a single reliable interface.
* Common strategy operations ~ In a given strategy class, like market making or arbitrage, there are some operations that are very frequent. Gryphon includes building-block libraries that make designing new strategies simpler.

Application suite:

* Execution environment ~ run from the command line as `gryphon-execute`, this is app runs strategies and includes some other utility functions that are commonly used in day-to-day operation of a trading business.
* Gryphon Data Service ~ a standalone app for listening to market data and events at high frequency. GDS can be used in advanced installations of gryphon to massively speed up tick speeds. GDS can also archive the data it receives, over time building up large datasets which can be used for machine learning or other analysis techniques.
* Dashboards ~ run from the command line as `gryphon-dashboards`, this is a web server that connects to your trading database to help you visualize the activity of your trading strategies and understand the health of your trading business.


## Installation

The gryphon library can be installed directly through pip.

```shell
$ pip install gryphon-framework
```

To use gryphon for trading, there are extra install steps to set up the execution environment. See this page for details: [Installing Gryphon](https://gryphon-docs-test.readthedocs.io/en/latest/).

If you are going to extend or modify gryphon, we recommend downloading the codebase and installing through pip with the `-e` flag.

## Usage

### Credentials and environment variables

When using Gryphon sensitive credentials like API keys never leave your machine. Instead, gryphon applications read credentials from a `.env` file stored in the directory they are launched from. `.env` files are simple lists of key-value pairs,

The .env entries for an exchange like Coinbase look something like this.

```
COINBASE_BTC_USD_API_KEY=[YOUR KEY]
COINBASE_BTC_USD_API_SECRET=[YOUR SECRET]
COINBASE_BTC_USD_API_PASSPHRASE=[YOUR PASSPHRASE]
```

Depending on the features you wish to use and the exchanges you wish to trade on, you'll need to have certain entries in your .env file. You can read the [.env appendix](https://gryphon-framework.readthedocs.io/en/latest) to find out which you will need.


### Run a built-in strategy

Once you have followed the execution tools install steps [here](https://gryphon-framework.readthedocs.io/en/latest). You can use the gryphon execution environment to run strategies. Gryphon ships with a few simple built-in strategies. These aren't designed for serious trading but can be useful for testing and learning the framework.

One such strategy is called 'Simple Marketmaking'. It can be run as follows:

```shell
$ gryphon-execute strategy simple_mm --builtin [--execute]
```

If you don't include the `--execute` flag, the strategy runs in test-mode, and won't place any orders on exchanges. This is a feature of the execution environment, not the strategy, so this flag works with every strategy you run or build on gryphon. Only use the `--execute` flag when you're ready to run or test a strategy with real money.

### Write and run your first strategy

Gryphon has a lot of building-block libraries that make common tasks quite simple. For example, we can use the gryphon arbitrage library to write a simple arbitrage strategy in only three major function calls.

```python
from gryphon.execution.strategies.base import Strategy
import gryphon.lib.arbitrage as arb


class GeminiCoinbaseArbitrage(Strategy):
    def tick(self):
        cross = arb.get_crosses(
            self.harness.gemini_btc_usd.get_orderbook(),
            self.harness.coinbase_btc_usd.get_orderbook(),
        )

        executable_volume = arb.get_executable_volume(
            cross,
            self.coinbase_btc_usd.get_balance(),
            self.gemini_btc_usd.get_balance(),
        )

        if cross and executable_volume:
            self.harness.gemini_btc_usd.market_order(cross.volume, 'BID')
            self.harness.coinbase_btc_usd.market_order(cross.volume, 'ASK')
```

Copy this code into a python file named 'arbitrage.py' in the same directory as your .env file, and you can run it in test mode with `gryphon-execute strategy arbitrage`.

Notice how much functionality is in play here: `gryphon-execute` sets up the environment that strategies run in and orchestrates the tick-by-tick operation, the exchange integrations for Coinbase and Gemini abstract away all the implementation details of working with those APIs into simple semantic function calls, and the arbitrage library simplifies some complex calculations into just two function calls.


## Contribution guidelines

**We use [GitHub issues](https://gryphon-framework.readthedocs.io/en/latest) for
tracking requests and bugs.**

**See the [development roadmap](https://trello.com/b/0HQI8KE9/engineering) trello board for more ideas about how you can contribute.**


## For more information

* [Gryphon Website](https://www.gryphonframework.org)
participate.

