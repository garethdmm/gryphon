def standard_deviation(tf,prices):
    sd= []
    sddate = []
    x = tf
    while x <= len(prices):
        array2consider = prices[x-tf:x]
        standev = array2consider.std()
        sd.append(standev)
        sddate.append(date[x])
        x+=1
    return sddate,sd
