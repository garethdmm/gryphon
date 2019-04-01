
def trade_diff(data_set):
    prices = [t.price for t in data_set]
    diffs = []
    for i in range(len(prices)):
        try:
            diffs.append(abs(prices[i+1] - prices[i]))
        except:
            pass
    return sum(diffs)/len(diffs)
