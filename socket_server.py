import time
import threading 
import socket as s
#https://docs.python.org/ko/3/library/socket.html


# �ϵ��ڵ� ����
ip = '' #��������� �� ������� IP (''�� �� ���, ��� host�� �ǹ� / ��, �� ��� send ��� sendto�� addr�� �������� ��)
port = 201701 #���� ���� (1024 ~ 49151���� ����� ��)
send_data = '���⿡ ���� �����͸� �Է��ϼ���.'
interval = 1 #�ۼ����� �ð�����(sec)
data_size = 1024 #���۹��� ������ ũ��

server_socket = s.socket(s.AF_INET, s.SOCK_DGRAM) #IPv4, UDP �������� ����� ���� ��ü ����
server_socket.bind(('',port)) #�ش� ip/port�� ���� ���� ��ü�� ����
server_socket.listen(1) #������ ����� client�� ��

'''
=======================================����===============================
socket(): ������ �����ϴ� �Լ�
    SOCKET socket(int family=AF_INET,int type=SOCK_STREAM,int proto=0);
    ���� ��: -1(SOCKET_ERROR) ��ȯ
    family: ��Ʈ��ũ �ּ� ü��
        #define AF_INET       2         //IPv4
        #define AF_INET6      23        //IPv6
    type: ���� Ÿ��
        #define SOCK_STREAM   1         //��Ʈ�� , TCP ���������� ���� ���
        #define SOCK_DGRAM    2         //������ �׷�, UDP ���������� ���� ���
        #define SOCK_RAW      3         //RAW ����, �������� ���� ����
    proto: ��������
        #define IPPROTO_TCP   6         //TCP ��������
        #define IPPROTO_UDP   17        //UDP ��������
        #define IPPROTO_RAW   255       //RAW
==========================================================================
'''

# �����͸� ���۹��� �Լ�
def recv():
    global client_socket
    recv_list = list()
    while True: 
        try: recv_list.append(client_socket.recv(data_size).decode('utf-8')) #�ѹ��� ������ �ִ� �����;��� param���� ���� ����/2�� �ŵ����� �Է�
        except Exception: break
    return "".join(recv_list)

def main_func():
        print("[���� �õ� ��...]")
        client_socket, client_addr = server_socket.accept() #����� client�� ���� ��ü, client�� �ּҸ� ��ȯ
        
        print("[���� ���� with {}]".format(client_addr))
        recv_data = recv() #client�κ��� �����͸� ���� 
        
        print("[���ŵ� ������ with {}]".format(client_addr))
        print(recv_data)
        
        print("\n[�۽��� ������]")
        print(send_data)
        
        client_socket.send(send_data.encode('utf-8')) #����� client���� �����͸� ����
        print("\n[������ �۽� �Ϸ�]")
        
        time.sleep(interval) #��� ��� �� �ۼ��� (������带 ���̱� ����)


err_cnt = 0
while True:
    try:
        #recvThread create
        recvThread = threading.Thread(target=main_func) #recv�Լ��� ������ ������ ������ �����带 ���� �� ����
        recvThread.start()
        
    except:
        print("error! retry! (try cnt: {}sec)".format(err_cnt))
        time.sleep(1)
        
        err_cnt += 1
        if err_cnt > 15:
            print("������ 15�� �̻� �������� �ʾҽ��ϴ�. ������ �ߴ��մϴ�.")
            server_socket.close()
            break
        
print("server�� �����մϴ�.")

    