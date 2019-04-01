import numpy as np
import time

sampleData = open('sampleData.txt','r').read()
splitData = sampleData.split('\n')

date,closep,highp,lowp,openp,volume = np.loadtxt(splitData,
                                                 delimiter=',',
                                                 unpack=True)



def ExpMovingAverage(values, window):
    weights = np.exp(np.linspace(-1., 0., window))
    weights /= weights.sum()
    a =  np.convolve(values, weights, mode='full')[:len(values)]
    a[:window] = a[window]
    return a

def EFI(d,c,v,tf):
    efi = []

    x = 1
    while x < len(d):
        forceIndex = (c[x] - c[x-1]) * v[x]
        print forceIndex
        efi.append(forceIndex)
        x+=1
    efitf = ExpMovingAverage(efi,tf)

    return d[1:], efitf

efix,efiy = EFI(date,closep,volume,14)
