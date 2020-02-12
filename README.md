
![alttext](gryphon/dashboards/static/img/gryphon-logo-blue-wide.png)
-----------------

**Gryphon** is an open source software platform for building and running algorithmic trading strategies in cryptocurrency markets. It was built by Tinker, one of the earliest cryptocurrency trading companies, and has traded billions in volume to date.



| **`Documentation`** | **`Build`** |
|---------|--------|
| [![Documentation](https://img.shields.io/badge/api-reference-blue.svg)](https://gryphon.readthedocs.io/en/latest/) | [![Build Status](https://travis-ci.com/garethdmm/gryphon.svg?branch=master)](https://travis-ci.com/garethdmm/gryphon) |
| [![Documentation Status](https://readthedocs.org/projects/gryphon/badge/?version=latest)](https://gryphon.readthedocs.io/en/latest/?badge=latest)
 |  |

## What's included

Gryphon is both a software library that can be integrated into other projects, and an application suite for running trading strategies and operating a trading business. How you use Gryphon depends on your goals. Some highlights are:

Library highlights:

* 20+ Exchange pair integrations ~ Gryphon defines a single abstract interface for exchanges, with semantic function calls like `gemini_btc_usd.get_orderbook()`, and integrates 20+ trading pairs on 6 exchanges under that interface. Exchange integrations abstract away all the annoying individual quirks of different exchanges, like rate limits, rounding behaviour, nonces, and undocumented features. This allows the user to write strategies against a single, reliable interface, and focus completely on designing trading behaviour.
* Strategy Building Blocks ~ Common operations, like checking for arbitrage opportunities, are already implemented and tested in for different strategy classes are provided in gryphon's strategy building block libraries. Many common strategy types can be implemented in as few as 3-5 function calls.

Application suite highlights:

* [Strategy Engine](https://gryphon.readthedocs.io/en/latest/usage.html#running-strategies) ~ the primary executable of gryphon loads strategy files and executes them, providing to the strategy developer redundant exchange connections, trade history persistence, monitoring, instrumentation, and lots of other features that make gryphon the easiest way to build and run strategies.
* [Gryphon Data Service](https://gryphon.readthedocs.io/en/latest/data_service.html) ~ a standalone service for ingesting market data and other events at high frequencies. Built using rabbitmq, GDS can be used in advanced installations of gryphon to massively speed up tick speeds or to build up datasets for use in machine learning.
* [Dashboards](https://gryphon.readthedocs.io/en/latest/dashboards.html) ~ a webserver that connects to your trading database to help you visualize the activity of your trading strategies and understand the health of your trading business.

![alttext](gryphon/dashboards/static/img/screenshots_together.png)


## Installation

The gryphon library can be installed directly through pip once [a few prerequisites](https://gryphon.readthedocs.io/en/latest/installation.html) are installed.

```shell
$ pip install gryphon
```

To use gryphon for trading, there are extra install steps to set up the execution engine. See this page for details: [Installing Gryphon](https://gryphon.readthedocs.io/en/latest/installation.html#set-up-the-trading-harness).

If you are going to extend or modify gryphon, we recommend downloading the codebase and installing through pip with the `-e` flag.

## Usage

### Credentials and environment variables

When using Gryphon, sensitive credentials like API keys never leave your machine. Instead, gryphon applications read credentials from a `.env` file stored in the directory they are launched from. `.env` files are simple lists of key-value pairs.

The .env entries for an exchange like Coinbase look something like this.

```
COINBASE_BTC_USD_API_KEY=[YOUR KEY]
COINBASE_BTC_USD_API_SECRET=[YOUR SECRET]
COINBASE_BTC_USD_API_PASSPHRASE=[YOUR PASSPHRASE]
```

Depending on the features you wish to use and the exchanges you wish to trade on, you'll need to have certain entries in your .env file. You can read the [Environment Variable Reference](https://gryphon.readthedocs.io/en/latest/environment.html) to find out which you will need.


### Run a built-in strategy

Once you have followed the strategy engine install steps [here](https://gryphon.readthedocs.io/en/latest/usage.html). You can use the gryphon execution environment to run strategies. Gryphon ships with a few simple built-in strategies. These aren't designed for serious trading but can be useful for testing and learning the framework.

One such strategy is called 'Simple Marketmaking'. It can be run as follows:

```shell
$ gryphon-exec strategy simple_mm --builtin [--execute]
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

Copy this code into a python file named 'arbitrage.py' in the same directory as your .env file, and you can run it in test mode with `gryphon-exec strategy arbitrage`.

Notice how much functionality is in play here: `gryphon-exec` sets up the environment that strategies run in and orchestrates the tick-by-tick operation, the exchange integrations for Coinbase and Gemini abstract away all the implementation details of working with those APIs into simple semantic function calls, and the arbitrage library simplifies some complex calculations into just two function calls.

## Getting Help

If you want help with an issue, there are a few ways to ask:

* Join the [gryphon slack](https://join.slack.com/t/gryphonframework/shared_invite/enQtODUwMTQzMDUyMDE2LWY2ZjdkZWU1YWRiNmQ2MGYzMTQ0YTM2NzZiMjk4MDU0ZGJiZTgxNjdhY2M3ZmEyNWQ2MWI5OGYzMzNkZmNhMzE) to ask a question to the developers
* Report [a bug](https://github.com/garethdmm/gryphon/issues)
* Search or read in [the docs](https://gryphon.readthedocs.io/en/latest/)
* Ask a question on stackoverflow with the tag [‘gryphonframework’](https://stackoverflow.com/questions/tagged/gryphonframework)

The [Gryphon Website](https://www.gryphonframework.org) can also be used as an alternate alternate jumping-off point for users new to Gryphon. 

## Enterprise Support

Enterprise support, custom deployments, strategy development, and other services are available through [Gryphon Labs](http://www.gryphonlabs.co/). If you're a firm interested in using Gryphon, you can [schedule a chat with us](https://calendly.com/gryphonlabs) or contact one of the maintainers directly.

## Contribution guidelines

**We use [GitHub issues](https://github.com/garethdmm/gryphon/issues) for
tracking requests and bugs.**

**See the [Contributing to Gryphon](https://gryphon.readthedocs.io/en/latest/contributing.html) for pull request checklists and ideas about how you can contribute.**



