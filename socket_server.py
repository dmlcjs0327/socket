import time
import threading 
import socket as s
#https://docs.python.org/ko/3/library/socket.html


# 하드코딩 구간
ip = '' #소켓통신을 할 대상기기의 IP (''로 둘 경우, 모든 host를 의미 / 단, 이 경우 send 대신 sendto로 addr를 명시해줘야 함)
port = 201701 #임의 지정 (1024 ~ 49151에서 사용할 것)
send_data = '여기에 보낼 데이터를 입력하세요.'
interval = 1 #송수신할 시간간격(sec)
data_size = 1024 #전송받을 데이터 크기

server_socket = s.socket(s.AF_INET, s.SOCK_DGRAM) #IPv4, UDP 프로토콜 방식의 소켓 객체 생성
server_socket.bind(('',port)) #해당 ip/port에 대해 소켓 객체를 연결
server_socket.listen(1) #연결을 허용할 client의 수

'''
=======================================참고===============================
socket(): 소켓을 생성하는 함수
    SOCKET socket(int family=AF_INET,int type=SOCK_STREAM,int proto=0);
    실패 시: -1(SOCKET_ERROR) 반환
    family: 네트워크 주소 체계
        #define AF_INET       2         //IPv4
        #define AF_INET6      23        //IPv6
    type: 소켓 타입
        #define SOCK_STREAM   1         //스트림 , TCP 프롤토콜의 전송 방식
        #define SOCK_DGRAM    2         //데이터 그램, UDP 프로토콜의 전송 방식
        #define SOCK_RAW      3         //RAW 소켓, 가공하지 않은 소켓
    proto: 프로토콜
        #define IPPROTO_TCP   6         //TCP 프로토콜
        #define IPPROTO_UDP   17        //UDP 프로토콜
        #define IPPROTO_RAW   255       //RAW
==========================================================================
'''

# 데이터를 전송받을 함수
def recv():
    global client_socket
    recv_list = list()
    while True: 
        try: recv_list.append(client_socket.recv(data_size).decode('utf-8')) #한번에 수신할 최대 데이터양을 param으로 지정 가능/2의 거듭제곱 입력
        except Exception: break
    return "".join(recv_list)

def main_func():
        print("[연결 시도 중...]")
        client_socket, client_addr = server_socket.accept() #연결된 client의 소켓 객체, client의 주소를 반환
        
        print("[연결 성공 with {}]".format(client_addr))
        recv_data = recv() #client로부터 데이터를 받음 
        
        print("[수신된 데이터 with {}]".format(client_addr))
        print(recv_data)
        
        print("\n[송신할 데이터]")
        print(send_data)
        
        client_socket.send(send_data.encode('utf-8')) #연결된 client에게 데이터를 전송
        print("\n[데이터 송신 완료]")
        
        time.sleep(interval) #잠시 대기 후 송수신 (오버헤드를 줄이기 위함)


err_cnt = 0
while True:
    try:
        #recvThread create
        recvThread = threading.Thread(target=main_func) #recv함수를 실행할 때마다 별도의 스레드를 생성 후 실행
        recvThread.start()
        
    except:
        print("error! retry! (try cnt: {}sec)".format(err_cnt))
        time.sleep(1)
        
        err_cnt += 1
        if err_cnt > 15:
            print("에러가 15초 이상 수정되지 않았습니다. 연결을 중단합니다.")
            server_socket.close()
            break
        
print("server를 중지합니다.")

    