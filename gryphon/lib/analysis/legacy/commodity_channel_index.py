# import numpy as np
# import time
# 
# sampleData  = open('sampleData.txt','r').read()
# 
# splitData = sampleData.split('\n')
# 
# date,closep,highp,lowp,openp,volume = np.loadtxt(splitData,
#                                                  delimiter=',',
#                                                  unpack=True)
# 
# def movingaverage(values,window):
#     weigths = np.repeat(1.0, window)/window
#     smas = np.convolve(values, weigths, 'valid')
#     return smas # as a numpy array
# 
# def CCI(d,c,h,l,o,v,tf,sma):
#     typPrices = []
#     MDar = []
#     cci = []
# 
#     x = 0
#     while x < len(h):
#         tp = (h[x]+l[x]+c[x])/3
# 
#         typPrices.append(tp)
#         x+=1
# 
#     SMATP = movingaverage(typPrices,sma)
# 
#     #print len(SMATP)
#     typPrices = typPrices[sma-1:]
#     #print len(typPrices)
# 
#     y = tf
# 
#     while y < len(SMATP):
#         considerationTP = typPrices[y-tf:y]
#         considerationSMATP = SMATP[y-tf:y]
# 
#         MDs = 0
#         z = 0
#         while z < len(considerationTP):
#             curMD = abs(considerationTP[z]-considerationSMATP[z])
#             MDs += curMD
#             z+=1
#         MD = MDs/tf
#         MDar.append(MD)
# 
#         y+=1
# 
#     #print len(MDar)
#     typPrices = typPrices[14:]
#     SMATP = SMATP[14:]
#     #print len(typPrices)
#     #print len(SMATP)
# 
#     xx = 0
#     while xx < len(SMATP):
#         ccis = (typPrices[xx]-SMATP[xx]) / (0.015 * MDar[xx])
#         cci.append(ccis)
#         xx+=1
# 
#     print len(cci)
#     print len(date[tf+sma-1:])
#     print cci
#     return date[tf+sma-1:],cci
# 
# CCI(date,closep,highp,lowp,openp,volume,14,20)
