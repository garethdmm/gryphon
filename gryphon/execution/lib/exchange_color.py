import termcolor as tc


EXCHANGE_COLORS = {
    "BITSTAMP": lambda t: tc.colored(t, "green"),
    "COINBASE": lambda t: tc.colored(t, "blue"),
    "KRAKEN": lambda t: tc.colored(t, "cyan"),
    "CAVIRTEX": lambda t: tc.colored(t, "red"),
    "QUADRIGA": lambda t: tc.colored(t, "yellow"),
    "BITFINEX": lambda t: tc.colored(t, attrs=['bold']),
    "ITBIT": lambda t: tc.colored(t, "magenta"),
    "OKCOIN": lambda t: tc.colored(t, "red", attrs=['bold']),
}


def exchange_color(text, exchange_name):
    try:
        colored_text = EXCHANGE_COLORS[exchange_name](text)
    except:
        colored_text = text
    return colored_text


def legend():
    output = ""
    for exchange_name in EXCHANGE_COLORS:
        output += exchange_color(exchange_name, exchange_name) + "  "
    return output
