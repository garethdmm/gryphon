
def trade_size(data_set):
    volumes = [t.volume for t in data_set]
    return sum(volumes) / len(volumes)
