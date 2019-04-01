import numpy as np
import time

sampleData = open('sampleData.txt','r').read()
splitData = sampleData.split('\n')

date,closep,highp,lowp,openp,volume = np.loadtxt(splitData,
                                                 delimiter=',',
                                                 unpack=True)


def movingaverage(values,window):
    weigths = np.repeat(1.0, window)/window
    smas = np.convolve(values, weigths, 'valid')
    return smas # as a numpy array



def EMV(d,c,h,l,o,v,tf):

    x=1
    OnepEMV = []
    while x < len(c):
        movement = ( ((h[x]+l[x])/2) - ((h[x-1]+l[x-1])/2) )
        boxr = ( (v[x]/1000000.00)/ (h[x]-l[x]) )
        OnepEMVs = movement / boxr
        OnepEMV.append(OnepEMVs)
        print OnepEMVs
        x += 1

    tfEMV = movingaverage(OnepEMV,tf)

    print len(tfEMV)
    print len(d[tf:])

    return d[tf:],tfEMV

EMV(date,closep,highp,lowp,openp,volume,14)
