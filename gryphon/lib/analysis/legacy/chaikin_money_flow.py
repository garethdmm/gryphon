import numpy as np
import time

sampleData = open('sampleData.txt','r').read()
splitData = sampleData.split('\n')

date,closep,highp,lowp,openp,volume = np.loadtxt(splitData,
                                                 delimiter=',',
                                                 unpack=True)


def CHMoF(d,c,h,l,o,v,tf):
    CHMF = []
    MFMs = []
    MFVs = []
    x = tf
    while x < len(d):
        PeriodVolume = 0
        volRange = v[x-tf:x]
        for eachVol in volRange:
            PeriodVolume += eachVol

        
        MFM = ((c[x]-l[x])-(h[x]-c[x]))/(h[x]-l[x])

        MFV = MFM*(PeriodVolume)

        MFMs.append(MFM)
        MFVs.append(MFV)
        x+=1

    y = tf
    while y < len(MFVs):
        PeriodVolume = 0
        volRange = v[y-tf:y]
        for eachVol in volRange:
            PeriodVolume += eachVol
            
        consider = MFVs[y-tf:y]
        #print consider
        tfsMFV = 0

        for eachMFV in consider:
            tfsMFV+=eachMFV

        tfsCMF = tfsMFV/PeriodVolume
        CHMF.append(tfsCMF)
        #print tfsCMF
        #time.sleep(555)
        y+=1
    #print len(CHMF)
    #print len(date[tf+tf:])
    return date[tf+tf:],CHMF
    

CHMoF(date,closep,highp,lowp,openp,volume,20)
