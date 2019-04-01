import numpy as np
import time

sampleData = open('sampleData.txt','r').read()
splitData = sampleData.split('\n')

date,closep,highp,lowp,openp,volume = np.loadtxt(splitData, delimiter=',',unpack=True)

def standard_deviation(tf,prices):

    sd = []
    sddate = []
    x = tf
   ######
    while x <= len(prices):
        array2consider = prices[x-tf:x]
        standev = array2consider.std()
        sd.append(standev)
        sddate.append(date[x])
        x+=1
    return sddate,sd

def bollinger_bands(mult,tff):
    bdate = []
    topBand = []
    botBand = []
    midBand = []

    x = tff

    while x < len(date):
        curSMA = movingaverage(closep[x-tff:x],tff)[-1]

        d,curSD = standard_deviation(tff,closep[0:tff])

        curSD = curSD[0]

        #print curSD
        #print curSMA

        TB = curSMA + (curSD*mult)
        BB = curSMA - (curSD*mult)
        D = date[x]

        bdate.append(D)
        topBand.append(TB)
        botBand.append(BB)
        midBand.append(curSMA)

        x+=1

    return bdate,topBand,botBand,midBand

d,tb,bb,mb = bollinger_bands(2,20)
