from curses.ascii import isdigit
import time
import os
import threading 
import socket as s
#https://docs.python.org/ko/3/library/socket.html


# 하드코딩 구간
ip = '' #소켓통신을 할 대상기기의 IP (''로 둘 경우, 모든 host를 의미 / 단, 이 경우 send 대신 sendto로 addr를 명시해줘야 함)
port = 3022 #임의 지정 (1024 ~ 49151에서 사용할 것)
interval = 2 #송수신할 시간간격(sec)
data_size = 1024 #전송받을 데이터 크기

# server_socket = s.socket(s.AF_INET, s.SOCK_DGRAM) #IPv4, UDP 프로토콜 방식의 소켓 객체 생성
server_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
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

# 전역변수
humity_in = 50 # 어플리케이션이 요청한 습도
humity_out = 50 # 실제 습도
water_in = 50 # 어플리케이션이 요청한 물높이
water_out = 50 # 실제 물높이

connection_btn = False


def connect():
    global server_socket
    global client_socket
    global client_addr
    global connection_btn
    
    while True:
        try: 
            print("[연결 시도 중...]")
            client_socket, client_addr = server_socket.accept() #연결된 client의 소켓 객체, client의 주소를 반환
            print("[연결 성공 with {}]".format(client_addr))
            connection_btn = True
            break
            
        except Exception as e: 
            print("<connect error>:",e)
            time.sleep(interval)
            err_cnt += 1
            if err_cnt > 15:
                print("에러가 15초 이상 수정되지 않았습니다. 연결을 중단합니다.")   
                break
    

# thread에서 구동할 함수
def socket_receiver():
    print("<socket_receiver> 시작")
    global server_socket
    global client_socket
    global client_addr
    global data_size
    global humity_in
    global water_in
    global interval
    global connection_btn
    err_cnt = 0
    
    while True:
        try: 
            recv_data = client_socket.recv(data_size).decode('utf-8') #한번에 수신할 최대 데이터양을 param으로 지정 가능/받을 때까지 대기
            
            print("<socket_receiver> 수신된 데이터 with {}:".format(client_addr),end=" ")
            print(recv_data)
            
            tmp = list()
            n = 0
            for data in recv_data:
                if data != "," and isdigit(data):
                    n = n*10 + int(data)
                else:
                    tmp.append(n)
                    n = 0
            tmp.append(n)
            tmp = tmp[2:]
                

            recv_data = tmp
            #데이터 처리 후 저장
            
            print("<socket_receiver> test: {}. tmp[0]: {},  tmp[1]: {}".format(recv_data, recv_data[0], recv_data[1]))
                        
            humity_in = int(recv_data[0])
            water_in = int(recv_data[1])
            print("<socket_receiver> 갱신 완료. 목표습도: {},  목표높이: {}".format(humity_in, water_in))
            
            
            time.sleep(interval) #잠시 대기 후 송수신 (오버헤드를 줄이기 위함)
            
        except Exception as e: 
            if connection_btn:
                print("<socket_receiver> 에러:",e)
                connection_btn = False
                time.sleep(interval)
                err_cnt += 1
                if err_cnt > 15: break
                
            else:
                print("<socket_receiver> 연결 대기중")
                connect()
                time.sleep(interval*2)
            
    print("<socket_receiver> 에러가 15초 이상 수정되지 않았습니다. 연결을 중단합니다.")   
    server_socket.close()
            


def socket_sender(send_data):
    global client_socket
    global connection_btn
    err_cnt = 0
    
    while True:
        try:
            print("<socket_sender> 송신할 데이터:",end=" ")
            print(send_data)
        
            client_socket.send(send_data.encode('utf-8')) #연결된 client에게 데이터를 전송
            print("<socket_sender> 데이터 송신 완료")
            break
        
        except Exception as e:
            if connection_btn:
                print("<socket_sender> 에러:",e)
                connection_btn = False
                time.sleep(interval)
                err_cnt += 1
                if err_cnt > 15: break
                
            else:
                print("<socket_sender> 연결 대기중")
                time.sleep(interval*2)



def controller():
    print("<controller> 시작")
    global humity_in
    global humity_out
    global water_in
    global water_out
    
    while True:
        humity_val = humity_out - humity_in
        water_val = water_out - water_in
        
        if humity_val > 0: humity_out -= 1
        elif humity_val < 0: humity_out += 1 
        
        if water_val > 0: water_out -= 1
        elif water_val < 0: water_out += 1 
        
        time.sleep(1)
        

def test():
    print("<test> 시작")
    global water_out
    global humity_out
    
    while True:
        time.sleep(5)
        water_out += 3
        humity_out += 3


def print_state():
    global humity_in
    global humity_out
    global water_in
    global water_out
    
    print("<현재 상태>")
    print("목표 습도:",humity_in)
    print("실제 습도:",humity_out)
    print("목표 높이:",water_in)
    print("실제 높이:",water_out)

# 테스트=====================================================================================================================

# 5초마다 물높이와 습도가 1씩 증가하는 상황을 가정함

connectThread = threading.Thread(target=connect) 
connectThread.start()
connectThread.join() # 스마트폰과 연결이 되어야 이후 내용을 진행

recvThread = threading.Thread(target=socket_receiver) 
recvThread.start()

testThread = threading.Thread(target=test) 
testThread.start()

controllThread = threading.Thread(target=controller) 
controllThread.start()


while True:
    try:
        # os.system('cls' if os.name in ('nt', 'dos') else 'clear')
        send_data = "{},{}".format(humity_out,water_out)
        socket_sender(send_data)
        print_state()
        time.sleep(interval)
        
    except Exception as e:
        print("<main> 에러:",e)
        server_socket.close()
        break
        
print("<main> server를 중지합니다.")

    