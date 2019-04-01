import numpy as np
import time

sampleData = open('sampleData.txt','r').read()
splitData = sampleData.split('\n')

date,closep,highp,lowp,openp,volume = np.loadtxt(splitData,
                                                 delimiter=',',
                                                 unpack=True)

def HHLL(d,c,tf):
    hh = []
    ll = []
    x = tf

    while x < len(d):
        consHigh = c[x-tf:x]
        consLow = c[x-tf:x]

        HighestHigh = max(consHigh)
        LowestLow = min(consLow)

        hh.append(HighestHigh)
        ll.append(LowestLow)

        x+=1
        
    #print hh
    return d,hh,ll
    
HHLL(date,closep,5)
