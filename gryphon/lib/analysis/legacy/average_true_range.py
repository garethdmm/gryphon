import numpy as np
from exponential_moving_average import ExpMovingAverage


sampleData = open('sampleData.txt','r').read()
splitData = sampleData.split('\n')

date,closep,highp,lowp,openp,volume = np.loadtxt(splitData, delimiter=',',unpack=True)

def TR(d,c,h,l,o,yc):
    x = h-l
    y = abs(h-yc)
    z = abs(l-yc)

    print x
    print y
    print z

    if y <= x >= z:
        TR = x
    elif x <= y >= z:
        TR = y
    elif x <= z >= y:
        TR = z

    print d, TR
    return d, TR

x = 1

TRDates = []
TrueRanges = []

while x < len(date):
    TRDate, TrueRange = TR(date[x],closep[x],highp[x],lowp[x],openp[x],closep[x-1])
    TRDates.append(TRDate)
    TrueRanges.append(TrueRange)
    x+=1



print len(TrueRanges)
ATR = ExpMovingAverage(TrueRanges,14)

print ATR
