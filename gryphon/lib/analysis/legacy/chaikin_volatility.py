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


def percentChange(startPoint,currentPoint):
    return((float(currentPoint)-startPoint)/abs(startPoint))*100.00


def chaikinVolCalc(emaUsed,periodsAgo):

    chaikin_volatility = []
    highMlow = []
    x = 0
    while x < len(date):
        hml = highp[x]-lowp[x]
        highMlow.append(hml)
        x += 1

    print len(date)
    print len(highMlow)
    highMlowEMA = ExpMovingAverage(highMlow,emaUsed)
    print len(highMlowEMA)
    y = emaUsed + periodsAgo

    while y < len(date):
        cvc = percentChange(highMlow[y-periodsAgo],highMlow[y])
        chaikin_volatility.append(cvc)
        y+=1

    print len(date[emaUsed+periodsAgo:])
    
    return date[emaUsed+periodsAgo:], chaikin_volatility
        


chaikinVolCalc(10,10)
