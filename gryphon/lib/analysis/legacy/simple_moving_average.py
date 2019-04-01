import numpy as np
from cdecimal import Decimal

def MovingAverage(values, timestamps, window_time=300):
    assert len(values) == len(timestamps)
    ma = []
    values.reverse()
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
        
        weights = [Decimal(1)/len(relevant_values) for a in relevant_values]
        weighted_value = 0
        for i in range(len(relevant_values)):
            rv = relevant_values[i]
            weight = weights[i]
            weighted_value += rv*weight
        ma.append(weighted_value)
    ma.reverse()
    return ma
