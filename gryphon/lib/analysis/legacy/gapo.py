import numpy as np
import time
import math

sampleData = open('sampleData.txt','r').read()
splitData = sampleData.split('\n')

date,closep,highp,lowp,openp,volume = np.loadtxt(splitData,
                                                 delimiter=',',
                                                 unpack=True)

def GAPO(d,h,l,tf):
    gapo = []
    x = tf

    while x < len(d):
        consHigh = h[x-tf:x]
        consLow = l[x-tf:x]

        HighestHigh = max(consHigh)
        LowestLow = min(consLow)

        gapos = ( (math.log(HighestHigh - LowestLow)) /
                  math.log(tf))

        print gapos
        gapo.append(gapos)
        x+=1
    return d[tf:],gapo

GAPO(date,highp,lowp,14)
