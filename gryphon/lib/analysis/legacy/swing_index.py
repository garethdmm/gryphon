#November 11th 2013:
open1 = 1286.50
high1 = 1287.70
low1  = 1278.50
close1= 1281.70

#November 12th 2013:
open2 = 1281.80
high2 = 1284.50
low2  = 1260.70
close2= 1266.70

limitMove = 75

def SwingIndex(O1,O2,H1,H2,L1,L2,C1,C2,LM):

    def calc_R(H2,C1,L2,O1,LM):
        x = H2-C1
        y = L2-C1
        z = H2-L2
        print x
        print y
        print z

        if z < x > y:
            print 'x wins!'
            R = (H2-C1)-(.5*(L2-C1))+(.25*(C1-O1))
            print R
            return R
        elif x < y > z:
            print 'y wins!'
            R = (L2-C1)-(.5*(H2-C1))+(.25*(C1-O1))
            print R
            return R

        elif x < z > y:
            print 'z wins!'
            R = (H2-L2)+(.25*(C1-O1))
            print R
            return R


    def calc_K(H2,L2,C1):
        x = H2-C1
        y = L2-C1

        if x > y:
            K=x
            print K
            return K
        elif x < y:
            K=y
            print K
            return K

    L = LM
    R = calc_R(H2,C1,L2,O1,LM)
    K = calc_K(H2,L2,C1)

    SwIn = 50*((C2-C1+(.5*(C2-O2))+(.25*(C1-O1)))/R)*(K/L)
    print '###'
    print SwIn
    



    
SwingIndex(open1,open2,high1,high2,low1,low2,close1,close2,limitMove)
