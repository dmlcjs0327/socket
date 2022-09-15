

from socket import *
import os
import sys
import os

clientSock = socket(AF_INET, SOCK_STREAM)
clientSock.connect(('203.255.57.106', 3033))

print('connect success.')
filename = str(input('file name: '))
clientSock.sendall(filename.encode('utf-8'))

data = clientSock.recv(1024)
data_transferred = 0

if not data:
    print('file %s is not in server' %filename)
    sys.exit()

nowdir = os.getcwd()
with open(nowdir+"\\"+"new_"+filename, 'wb') as f: 
    try:
        while data: 
            f.write(data) #
            data_transferred += len(data)
            data = clientSock.recv(1024) 
    except Exception as ex:
        print(ex)
print('file %s load clear. size %d' %(filename, data_transferred))