import numpy as np
import time

sampleData = open('sampleData.txt','r').read()
splitData = sampleData.split('\n')

date,closep,highp,lowp,openp,volume = np.loadtxt(splitData,
                                                 delimiter=',',
                                                 unpack=True)

def cog(dates,data,tf):

    COG = []
    x = tf
    while x < len(dates):
        consider = data[x-tf:x]
        #print consider
        #print len(consider)

        multipliers = range(1,tf+1)

        topFrac = 0
        botFrac = 0

        reversedOrder = reversed(consider)

        ordered = []
        for eachItem in reversedOrder:
            ordered.append(eachItem)

        #print ordered
        
        for eachM in multipliers:
            addMe = eachM*ordered[eachM-1]

            addMe2 = ordered[eachM-1]
            #print addMe
            topFrac+=addMe
            botFrac+=addMe2

        CeOfGr = -(topFrac/botFrac)

        #print CeOfGr
        COG.append(CeOfGr)
            
            
        #return dates[tf:]    

        #time.sleep()
        x+=1


    return dates[tf:],COG

cog(date,closep,10)
