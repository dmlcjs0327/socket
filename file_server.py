

from socket import *
from os.path import exists
import sys
import os

serverSock = socket(AF_INET, SOCK_STREAM)
serverSock.bind(('', 3033))
serverSock.listen(10)


print("connect waiting")
connectionSock, addr = serverSock.accept()

print(str(addr), 'connected')

test = connectionSock.recv(1024) 
print('receive data : ', test.decode('utf-8')) 
data_transferred = 0


print("file transportation start")
with open("img1.png", 'rb') as f:
    try:
        data = f.read(1024) 
        while data: 
            data_transferred += connectionSock.send(data) 
            data = f.read(1024) 
    except Exception as ex:
        print(ex)
print("success , size %d" %(data_transferred))