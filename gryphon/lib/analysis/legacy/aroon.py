import numpy as np
import time

sampleData = open('sampleData.txt','r').read()
splitData = sampleData.split('\n')

date,closep,highp,lowp,openp,volume = np.loadtxt(splitData,
                                                 delimiter=',',
                                                 unpack=True)

def aroon(tf):

    AroonUp = []
    AroonDown = []
    AroonDate = []

    x = tf
    #Through some sorcery, we can actually 1 liner this
    while x < len(date):

        #print highp[x]
        #  19, -  since we wanna know how many days SINCE
        # then we create the list with the x-20 to x... then we
        # convert to list since its a numpy array.
        # then we do a .index to find out where the max is at in the list.

        Aroon_Up = tf-(highp[x-(tf-1):x].tolist().index(max(highp[x-(tf-1):x])))
        Aroon_Down = tf-(lowp[x-(tf-1):x].tolist().index(min(lowp[x-(tf-1):x])))

        AroonUp.append(Aroon_Up)
        AroonDown.append(Aroon_Down)
        AroonDate.append(date[x])

        x+=1
    return AroonDate,AroonUp,AroonDown

aroon(20)
