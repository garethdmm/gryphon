import numpy as np
from cdecimal import Decimal


def ExpMovingAverage(values, timestamps, window_time=300):
    assert len(values) == len(timestamps)
    ema = []
    values = list(values)
    values.reverse()
    timestamps = list(timestamps)
    timestamps.reverse()
    for i in range(len(timestamps)):
        noted_timestamp = timestamps[i]
        relevant_values = []
        relevant_timestamps = []
        for j in range(len(timestamps)):
            
            index = j+i
            if index > len(timestamps)-1:
                break 
            elif noted_timestamp - timestamps[index] < window_time:
                relevant_values.append(values[index])
                relevant_timestamps.append(noted_timestamp - timestamps[index])
            else:
                break
            
        weights = np.exp([ (Decimal(1)/ Decimal(1+ts)) for ts in relevant_timestamps])
        weights = [w/sum(weights) for w in weights]
        
        weighted_value = 0
        for i in range(len(relevant_values)):
            rv = relevant_values[i]
            weight = weights[i]
            weighted_value += rv*weight
        ema.append(weighted_value)
    ema.reverse()
    return ema
