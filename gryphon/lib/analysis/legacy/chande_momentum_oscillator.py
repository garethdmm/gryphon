import numpy as np
import time

sampleData = open('sampleData.txt','r').read()
splitData = sampleData.split('\n')

date,closep,highp,lowp,openp,volume = np.loadtxt(splitData,
                                                 delimiter=',',
                                                 unpack=True)


def cmo(prices,tf):

    CMO = []
    x = tf
    while x < len(date):
        considerationPrices = prices[x-tf:x]
        #print considerationPrices

        upSum = 0
        downSum = 0

        y = 1
        
        while y < tf:
            curPrice = considerationPrices[y]
            prevPrice = considerationPrices[y-1]

            if curPrice >= prevPrice:
                upSum+= (curPrice-prevPrice)

            else:
                downSum += (prevPrice-curPrice)

            y+=1

        #print upSum
        #print downSum
        curCMO = ((upSum-downSum)/(upSum+float(downSum)))*100.00
        #print curCMO
        CMO.append(curCMO)
        
        x+=1

    return date[tf:],CMO

cmo(closep,10)
