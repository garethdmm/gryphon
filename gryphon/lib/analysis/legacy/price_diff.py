from decimal import Decimal
from collections import defaultdict
def price_diff(fundamental_values, timestamps, window_time=300):
    assert len(timestamps) == len(fundamental_values)
    
    fundamental_values = list(fundamental_values)
    fundamental_values.reverse()
    timestamps = list(timestamps)
    timestamps.reverse()
    
    price_diffs = []
    for i in range(len(timestamps)):
        curr_fv = fundamental_values[i]
        curr_ts = timestamps[i]
        lookback_index = 0
        for j in range(len(timestamps)):
            index = i + j
            if index > len(timestamps)-1:
                break
            if curr_ts - timestamps[index] > window_time:
                lookback_index = index
                break
        if lookback_index == 0:
            price_diff = Decimal('0')
        else:
            price_diff = (abs(fundamental_values[lookback_index] - curr_fv) / fundamental_values[lookback_index])
        price_diffs.append(price_diff)
    price_diffs.reverse()
    return price_diffs

def price_diff_rolling_average(fund_vals, fund_val_timestamps, window_time=60, rolling_period=86400):
    price_diffs = price_diff(fund_vals, fund_val_timestamps, window_time)
    
    price_diffs = list(price_diffs)
    price_diffs.reverse()
    timestamps = list(fund_val_timestamps)
    timestamps.reverse()
    
    price_diff_averages = []
    matched_timestamps = []
    for i in range(len(timestamps)):
        current_timestamp = timestamps[i]
        
        lookback_index= 0
        for j in range((len(fund_val_timestamps))):
            index = i + j
            if index > len(timestamps) -1:
                break
            if current_timestamp - timestamps[index] > rolling_period:
                lookback_index = index
                break
        if lookback_index != 0:
            ts = timestamps[i]
            relevant_list = price_diffs[i:lookback_index]
            if relevant_list:
                a = sum(relevant_list) / len(relevant_list)
            else:
                a = Decimal('0')
            price_diff_averages.append(a)
        matched_timestamps.append(current_timestamp)
    price_diff_averages.reverse()
    return matched_timestamps, price_diff_averages


def price_diff_compare(fund_vals, fund_val_timestamps, alt_fund_vals, alt_fund_val_timestamps, window_time=50):
    assert len(fund_vals) == len(fund_val_timestamps) and len(alt_fund_vals) == len(alt_fund_val_timestamps)
    price_diffs = price_diff(fund_vals, fund_val_timestamps, window_time)
    alt_price_diffs = price_diff(alt_fund_vals, alt_fund_val_timestamps, window_time)
    timeline = defaultdict(dict)
    for i in range(len(fund_val_timestamps)):
        ts = fund_val_timestamps[i]
        timeline[ts]['fund']=price_diffs[i]
    
    current_price_diff = price_diffs[0]
    for i in range(len(alt_fund_val_timestamps)):
        ts = alt_fund_val_timestamps[i]
        timeline[ts]['alt'] = alt_price_diffs[i]
    
    diffs = {}
    current_alt = 0
    current_fund = 0
    for ts, val in timeline.iteritems():
        if 'alt' in val:
            current_alt = val['alt']
        if 'fund' in val:
            current_fund = val['fund']
        
        diffs[ts] = abs(current_alt - current_fund)
            #timetstamps, diffs
    sorted_timestamps = sorted(diffs, key=lambda key: key)  
    return sorted_timestamps, [diffs[ts] for ts in sorted_timestamps]
