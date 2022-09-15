import RPi.GPIO as GPIO
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import board
import busio
import picamera
from datetime import datetime
from time import sleep 
from time import time
from curses.ascii import isdigit #문자열이 숫자로 구성되었는지 확인하는 함수
import threading 
import socket as s
import cv2
import numpy as np
from datetime import datetime
import urllib.request
import glob
import os


#========================================목차===========================================

# 드래그 후 ctrl+F로 검색하여 바로가기

#1) 하드코딩 구간
#2) 전역변수 선언 구간
#3) 소켓 선언 구간
#4) 센서 선언 구간
#5) 함수 선언 구간
#6) 스레드 선언 구간
#7) 실행 구간



#========================================1) 하드코딩 구간 ===========================================

ip = '' #소켓통신을 할 대상기기의 IP (''로 둘 경우, 모든 host를 의미 / 단, 이 경우 send 대신 sendto로 addr를 명시해줘야 함)
port = 3022 #사용할 포트 / 1024 ~ 49151에서 임의지정
interval = 2 #송수신할 시간간격(sec)
data_size = 1024 #전송받을 데이터 크기(bytes)



#========================================2) 전역변수 선언 구간 ======================================

_message_queue = [] #출력할 메세지를 저장하는 큐
is_end = False #전체 프로그램 종료를 의미

humity_target = 50 #목표 습도
humity_real = -1   #실제 습도

water_moter_err = False #수위모터에 에러가 있는지
cooler_moter_err = False #스프링쿨러에 에러가 있는지

capture_option = None #영상을 캡처하여 저장/전송할 주기

server_socket = None #서버 소켓 객체
client_socket = None #클라이언트 소켓 객체
client_addr =  None #클라이언트 주소
socket_is_connected = False #소켓이 연결되었는지를 저장하는 변수

connect_err = False #thread_connect가 비정상적으로 종료되었는지
receive_err = False #thread_receive가 비정상적으로 종료되었는지
send_err = False #thread_send가 비정상적으로 종료되었는지
video_send_err = False #thread_video_send가 비정상적으로 종료되었는지
picture_send_err = False #thread_picture_send가 비정상적으로 종료되었는지
sound_send_err = False #thread_sound_send가 비정상적으로 종료되었는지

camera = picamera.PiCamera() #웹캠(식물 전방 카메라)
camera.resolution = (1920, 1080) #해상도 설정

directory_picture = '/home/kangmugu/CAMPictures/' #캡처한 사진을 저장할 경로
directory_movie = '/home/kangmugu/Movies/' #모션감지 영상을 저장할 경로
url_stream = "http://192.168.0.194:8081/?action=stream" #동영상 스트림 url



#========================================3) 소켓 선언 구간 ========================================

server_socket = s.socket(s.AF_INET, s.SOCK_STREAM) #IPv4, TCP 프로토콜 방식의 소켓 객체 생성
server_socket.bind(('',port)) #해당 ip/port에 대해 소켓 객체를 연결
server_socket.listen(10) #연결을 허용할 client의 수



#========================================4) 센서 선언 구간 ========================================

I2C = busio.I2C(board.SCL, board.SDA) #습도 센서를 위한 i2c
ads = ADS.ADS1115(I2C) #습도 센서를 위한 ads

WL1 = 17 #저수 하단 핀
WL2 = 27 #저수 상단 핀

ENA_T = 21 #저수 펌프 가동/정지 핀
IN1_T = 20 #저수 펌프 정방향 회전 설정 핀
IN2_T = 16 #저수 펌프 역방향 회전 설정 핀

ENA_S = 13 #스프링쿨러 펌프 가동/정지 핀
IN1_S = 6 #스프링쿨러 펌프 정방향 회전 설정 핀
IN2_S = 5 #스프링쿨러 펌프 역방향 회전 설정 핀

#핀 번호를 참조하는 방식 지정 (BOARD: 보드번호 참조, BCM: 핀번호 참조)
GPIO.setmode(GPIO.BCM) 
GPIO.setwarnings(False) #setwarning false 오류가 뜨는 경우 작성

#GPIO.setup(핀번호, GPIO.IN): 입력핀 설정
GPIO.setup(WL1, GPIO.IN) 
GPIO.setup(WL2, GPIO.IN)

#GPIO.setup(핀번호, GPIO.OUT): 출력핀 설정
GPIO.setup(ENA_T, GPIO.OUT)
GPIO.setup(IN1_T, GPIO.OUT)
GPIO.setup(IN2_T, GPIO.OUT)
GPIO.setup(ENA_S, GPIO.OUT)
GPIO.setup(IN1_S, GPIO.OUT)
GPIO.setup(IN2_S, GPIO.OUT)

#GPIO.output(핀번호, GPIO.LOW): 출력핀에 0V를 내보낼 때 상태 설정
GPIO.output(ENA_T, GPIO.LOW)
GPIO.output(IN1_T, GPIO.LOW)
GPIO.output(IN2_T, GPIO.LOW)
GPIO.output(ENA_S, GPIO.LOW)
GPIO.output(IN1_S, GPIO.LOW)
GPIO.output(IN2_S, GPIO.LOW)



#========================================5) 함수 선언 구간 ========================================

#출력할 message를 queue에 넣는 함수
#=> 각 thread가 동시에 출력을 할 경우, 메세지가 끊겨서 출력될 수 있다
#=> 이를 방지하기 위해, 메세지 queue에 메세지들을 넣고, 한 스레드가 담당하여 출력한다.

#출력할 메세지와 기록 시간을 queue에 저장하는 함수
def append_message(msg):
    global _message_queue
    cur_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    _message_queue.append("{} {}".format(cur_time,msg))


#모터를 회전시키는 함수                     #수정해야함!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
def moter_run(ENA, IN1, IN2, dic): 
    #ENA, IN1, IN2: 회전할 모터
    #dic: 회전방향(True 정방향, False 역방향)

    GPIO.output(ENA, 1) #모터 가동
    GPIO.output(IN1, int(dic))
    GPIO.output(IN2, int(not dic))


#모터를 정지시키는 함수
def moter_stop(ENA, IN1, IN2):
    #ENA, IN1, IN2: 회전할 모터

    GPIO.output(ENA, 0)
    GPIO.output(IN1, 0)
    GPIO.output(IN2, 0)


#웹캠으로 사진을 찍는 함수
def capture_plant():
    global camera
    global directory_picture
    
    now = datetime.now().strftime("%Y%m%d_%H%M%S")
    camera.capture(directory_picture + now+'.png') #해당 경로에 캡처사진 저장


#동영상 스트림이 정상 작동하는지 확인하는 함수
def url_on(url):
    try:
        urllib.request.urlopen(url, timeout=2)
        return True
    except:
        return False


def remove_movie():
    Max_Movies = 10 # 영상 폴더 내 최대 영상 개수
    list_of_files = glob.glob(directory_movie+'*.mp4') # * means all if need specific format then *.csv

    oldest_file = min(list_of_files, key=os.path.getctime)
    if len(list_of_files) > Max_Movies:
        os.remove(oldest_file)


#시스템 전역변수들을 출력하는 함수
def state_message():
    global humity_target #목표 습도(int)
    global humity_real #실제 습도(int)

    global water_moter_err #수위모터에 에러가 있는지(bool)
    global cooler_moter_err #스프링쿨러에 에러가 있는지(bool)

    global capture_option #영상을 캡처하여 저장/전송할 주기

    global connect_err #thread_connect가 비정상적으로 종료되었는지
    global receive_err #thread_receive가 비정상적으로 종료되었는지
    global send_err #thread_send가 비정상적으로 종료되었는지
    global video_send_err #thread_video_send가 비정상적으로 종료되었는지
    global picture_send_err #thread_picture_send가 비정상적으로 종료되었는지
    global sound_send_err #thread_sound_send가 비정상적으로 종료되었는지

    msg="""[_main] 
    <현재 상태>
    -목표 습도: {}
    -실제 습도: {}
    -캡처 주기: {}
    
    <현재 시스템 상태 - 디버깅용>
    -water_moter_err: {}
    -cooler_moter_err: {}
    -connect_err: {}
    -receive_err: {}
    -send_err: {}
    -video_send_err: {}
    -picture_send_err: {}
    -sound_send_err: {}
    """.format(humity_target, humity_real, capture_option,water_moter_err,cooler_moter_err,connect_err,receive_err,send_err,video_send_err,picture_send_err,sound_send_err)
    append_message(msg)


#시스템 메세지를 출력하는 함수
def print_message():
    global _message_queue
    
    state_message()
    
    print("\n".join(_message_queue))
    _message_queue = []
    print()
    


#========================================6) 스레드 선언 구간 ======================================

#스레드에서 실행할 함수명은 앞에 _를 붙였음

#소켓 연결용 스레드(단기)
def _connect():
    global is_end
    global connect_err
    global server_socket
    global client_socket
    global client_addr
    global socket_is_connected
    err_cnt = 0 #에러를 카운트할 변수

    append_message("[_connect] <시작>")
    connect_err = False

    if not is_end and socket_is_connected:
        append_message("[_connect] 소켓이 이미 연결되어 있습니다")
        append_message("[_connect] <종료>")
        return
    
    while not is_end:
        try:
            append_message("[_connect] 연결 시도 중...")
            client_socket, client_addr = server_socket.accept() #연결될 때까지 대기
            append_message("[_connect] 연결 성공 with {}".format(client_addr))
            socket_is_connected = True
            err_cnt = 0
            break
            
        except Exception as e: 
            append_message("[_connect] 에러: {}".format(e))
            sleep(interval) #interval sec만큼 대기
            err_cnt += 1
            if err_cnt > 10:
                append_message("[_connect] 에러가 {}초 이상 수정되지 않았습니다. 연결을 중단합니다.".format(interval*err_cnt))   
                connect_err = True
                break

    append_message("[_connect] <종료>")

thread_connect = threading.Thread(target=_connect)


#안드로이드의 연락을 받는 스레드(유지)
def _receive():
    global is_end
    global receive_err
    global server_socket
    global client_socket
    global client_addr
    global data_size
    global interval
    global socket_is_connected
    global humity_target
    global capture_option
    err_cnt = 0 #에러를 카운트할 변수

    append_message("[_receive] <시작>")
    receive_err = False

    while not is_end:
        try: 
            recv_data = client_socket.recv(data_size).decode('utf-8') #받을 때까지 대기
            append_message("[_receive] 수신: {}".format(recv_data))
            
            s_idx = recv_data.find("[")
            e_idx = recv_data.find("]")

            recv_data = recv_data[s_idx+1:e_idx].split(",")
            #[습도,경보,캡처] 형식으로 데이터를 전송받음

            humity_target = recv_data[0] #0~100 사이의 수로 구성
            siren_option = recv_data[1] #"siren" 또는 "tts 읽을 문장"으로 구성
            capture_option = recv_data[2] #숫자1 숫자2.. 로 구성

            sleep(interval) #잠시 대기 후 송수신 (오버헤드를 줄이기 위함)
            
        except Exception as e: 
            if socket_is_connected: #이미 연결이 되어있다면
                append_message("[_receive] 에러:",e)
                sleep(interval)
                err_cnt += 1

                if err_cnt > 10: 
                    append_message("[_receive] 에러가 {}초 이상 수정되지 않았습니다. 연결을 중단합니다".format(interval*err_cnt))
                    receive_err = True
                    socket_is_connected = False
                    break
                
            else:
                append_message("[_receive] 소켓이 연결되지 않았습니다:",e)
                receive_err = True
                break
            
    append_message("[_receive] <종료>")

thread_receive = threading.Thread(target=_receive)
thread_receive.daemon = True #main thread가 종료되면 같이 종료


#안드로이드에게 연락을 보내는 스레드(유지)
def _send(): #send_data: 보낼 메세지(str)
    global is_end
    global send_err
    global client_socket
    global socket_is_connected
    global humity_real
    global water_moter_err
    global cooler_moter_err
    err_cnt = 0 #에러를 카운트할 변수
    
    
    #[습도,T이상,S이상]
    send_data = "[{},{},{}]".format(humity_real, int(water_moter_err), int(cooler_moter_err))
    
    append_message("[_send] <시작>")
    send_err = False

    while not is_end:
        try:
            append_message("[_send] 송신: {}".format(send_data))
            client_socket.send(send_data.encode('utf-8')) #연결된 client에게 데이터를 전송
            append_message("[_send] 송신 완료")
            
            sleep(interval) #잠시 대기 후 송수신 (오버헤드를 줄이기 위함)
        
        except Exception as e:
            if socket_is_connected: #이미 연결이 되어있다면
                append_message("[_send] 에러:",e)
                sleep(interval)
                err_cnt += 1

                if err_cnt > 10: 
                    append_message("[_send] 에러가 {}초 이상 수정되지 않았습니다. 연결을 중단합니다".format(interval*err_cnt))
                    client_socket.close()
                    server_socket.close()
                    socket_is_connected = False
                    send_err = True
                    break
                
            else:
                append_message("[_send] 소켓이 연결되지 않았습니다:",e)
                send_err = True
                break
    
    append_message("[_send] <종료>")

thread_send = threading.Thread(target=_send)
thread_send.daemon = True


#안드로이드에게 영상을 보내는 스레드(단기)
def _video_send(send_data):
    append_message("[_video_send] <종료>")
    pass

thread_video_send = threading.Thread(target=_video_send)
thread_video_send.daemon = True


#센서에게 소리를 보내는 스레드(단기)
def _sound_send(send_data):
    append_message("[_sound_send] <종료>")
    pass

thread_sound_send = threading.Thread(target=_sound_send)
thread_sound_send.daemon = True


#센서 조정용 스레드(유지)
def _sensor():
    global is_end
    global humity_real
    global humity_target
    global water_moter_err
    global cooler_moter_err
    
    water_level_bottom_cnt = 0 #물높이가 최저가 될 때마다 +1
    humity_low_cnt = 0 #습도가 낮을 때마다 +1
    
    water_moter_on = False #모터가 켜져있는지 확인하는 변수
    cooler_moter_on = False #모터가 켜져있는지 확인하는 변수
    
    append_message("[_sensor] <시작>")

    while not is_end:
        #저수탱크 모터 조정 파트
        try:
            water_moter_err = False
            
            water_level_bottom = GPIO.input(WL1) #저수탱크 하단 센서에서 값을 받아옴
            water_level_top = GPIO.input(WL2) #저수탱크 상단 센서에서 값을 받아옴
            
            if water_level_bottom == 0: #저수탱크 하단에 물이 없으면
                if not water_moter_on: #모터가 꺼져있으면
                    moter_run(ENA_T, IN1_T, IN2_T,True) #모터 작동
                    append_message("[_sensor] 저수탱크 모터 작동")
                
                else: #모터가 켜져있으면
                    water_level_bottom_cnt+=1 #물이 없는 상태 카운트
                    if water_level_bottom_cnt > 10: raise #10회 초과 시 에러처리

            elif water_level_top == 1: #저수탱크 상단에 물이 있으면
                if water_moter_on: #모터가 켜져있으면
                    moter_stop(ENA_T, IN1_T, IN2_T) #모터 중지
                    append_message("[_sensor] 저수탱크 모터 중지")
                    
            else:
                water_level_bottom_cnt = 0 #카운트 초기화
            
        except Exception as e:
            water_moter_err = True #에러가 발생했다고 체크
            append_message("[_sensor] 저수탱크 에러 발생: {}".format(e))

        
        #스프링쿨러 조정 파트
        try:
            cooler_moter_err = False
            
            adcValue = AnalogIn(ads, ADS.P1).value #습도 센서에서 값을 받아옴
            humity_real = 64-int(adcValue/1023) #수정해야함!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            
            if humity_real < humity_target: #습도가 목표치보다 낮으면
                if not cooler_moter_on: #모터가 꺼져있으면
                    moter_run(ENA_S, IN1_S, IN2_S, True) #스프링쿨러 작동
                    append_message("[_sensor] 스프링쿨러 작동")
                    
                else: #모터가 켜져있으면
                    humity_low_cnt+=1 #저습도 상태 카운트
                    if humity_low_cnt > 10: raise #10회 초과 시 에러처리

            else : #그 외엔
                humity_low_cnt = 0 #카운트 초기화
                moter_stop(ENA_S, IN1_S, IN2_S) #스프링쿨러 중지
                append_message("[_sensor] 스프링쿨러 중지")

        except Exception as e:
            cooler_moter_err = True #에러가 발생했다고 체크
            append_message("[_sensor] 스프링쿨러 에러 발생: {}".format(e))

        sleep(interval)
        
    append_message("[_sensor] <종료>")

thread_sensor = threading.Thread(target=_sensor)
thread_sensor.daemon = True


#동작 감지용 스레드(유지)
def _motion():
    global is_end
    global url_stream
    thresh = 25 #문턱값
    max_diff = 300 #차이 허용 최대값
    a, b, c = None, None, None #프레임을 담을 변수
    start_time = None #시작 시간을 저장할 변수
    fourcc = cv2.VideoWriter_fourcc(*'mp4v') #저장 형식
    record = False
    detected = False
    
    append_message("[_motion] <시작>")
    
    os.system('sh mjpg.sh &')
    append_message("[_motion] 스트리밍 프로그램 시작")

    while not is_end and not url_on(url_stream):
        append_message("[_motion] 스트리밍 연결 시도 중..")
        sleep(1)
                        
    cap = cv2.VideoCapture(url_stream)
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    while not is_end and not cap.isOpened():
        cap = cv2.VideoCapture(url_stream)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
    
    append_message("[_motion] 스트리밍 연결 성공")
    ret, a = cap.read()    #ret: 정상적으로 읽어왔는지, a: 읽어온 프레임
    ret, b = cap.read()    
    
    while not is_end and ret:        
        ret, c = cap.read()        
        draw = c.copy()        
        if not ret:            
            ret, c = cap.read()        
            draw = c.copy()         
        
        a_gray = cv2.cvtColor(a, cv2.COLOR_BGR2GRAY) #a 프레임을 흑백으로 색변환     
        b_gray = cv2.cvtColor(b, cv2.COLOR_BGR2GRAY) #b 프레임을 흑백으로 색변환
        c_gray = cv2.cvtColor(c, cv2.COLOR_BGR2GRAY) #c 프레임을 흑백으로 색변환
        
        diff1 = cv2.absdiff(a_gray, b_gray) #a,b에 대한 차이 프레임       
        diff2 = cv2.absdiff(b_gray, c_gray) #b,c에 대한 차이 프레임
        
        ret, diff1_t = cv2.threshold(diff1, thresh, 255, cv2.THRESH_BINARY) #문턱값 미만 픽셀을 0 처리한 프레임      
        ret, diff2_t = cv2.threshold(diff2, thresh, 255, cv2.THRESH_BINARY) #문턱값 미만 픽셀을 0 처리한 프레임        
        
        diff = cv2.bitwise_and(diff1_t, diff2_t) #두 프레임의 각 픽셀에 대한 and 연산        
        
        k = cv2.getStructuringElement(cv2.MORPH_CROSS, (3, 3)) #커널의 형태, 커널의 크기 지정       
        diff = cv2.morphologyEx(diff, cv2.MORPH_OPEN, k) #모폴로지 연산을 통한 노이즈 제거        
        
        diff_cnt = cv2.countNonZero(diff)
        
        if diff_cnt > max_diff:            
            nzero = np.nonzero(diff)            
            cv2.rectangle(draw, #변환 전 이미지 프레임
                        (min(nzero[1]), min(nzero[0])), #diff에서 0이 아닌 값 중 행, 열이 가장 작은 포인트  
                        (max(nzero[1]), max(nzero[0])), #diff에서 0이 아닌 값 중 행, 열이 가장 큰 포인트      
                        (0, 255, 0), #사각형을 그릴 색상 값 
                        2) #thickness            
            
            cv2.putText(draw, "Detected", (10, 30), cv2.FONT_HERSHEY_DUPLEX, 0.5, (0, 0, 255))
            detected = True
            
        movietime = datetime.now().strftime("%Y-%m-%d   %H:%M:%S")
        cv2.putText(draw, movietime, (10, 470), cv2.FONT_HERSHEY_DUPLEX, 0.5, (100, 100, 100))
        cv2.imshow('motion', draw)
        
        now = datetime.now().strftime("%Y%m%d_%H%M%S")

        if detected and not record:
            record = True
            start_time = time()
            video = cv2.VideoWriter(directory_movie +str(now)+ ".mp4", fourcc, 15.0, (draw.shape[1], draw.shape[0]))
            
        if 'video' in locals() and time() > (start_time + 10):
            record = False
            detected = False
            video.release()
            
        if record: 
            append_message("[_motion] <감지>")
            video.write(draw)
            
            #저장된 파일을 전송하는 코드 추가 요망!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
            
        a = b
        b = c
        
        if cv2.waitKey(1) & 0xFF == 27: break
        remove_movie()

    os.system('sudo killall mjpg_streamer')
    append_message("[_motion] <종료>")

thread_motion = threading.Thread(target=_motion)
thread_motion.daemon = True



#========================================7) 실행 구간 ============================================
print("[_main] <시작>")

thread_connect.start()
thread_connect.join()

thread_receive.start()
thread_send.start()
thread_sensor.start()
thread_motion.start()

while not is_end:
    
    #thread_connect가 정상 작동했는지 확인
    if connect_err:
        append_message("[_main] _connect 에러가 발생했습니다. 재시도합니다..")
        try:
            server_socket.close()
            server_socket = s.socket(s.AF_INET, s.SOCK_STREAM) #IPv4, TCP 프로토콜 방식의 소켓 객체 생성
            server_socket.bind(('',port)) #해당 ip/port에 대해 소켓 객체를 연결
            server_socket.listen(10) #연결을 허용할 client의 수
            thread_connect.start()
            thread_connect.join()
            
        except:
            append_message("[_main] _connect 재시도 실패. 서버를 종료합니다.")
            is_end = True
    
    #thread_receive가 정상 작동했는지 확인
    if receive_err:
        try:
            append_message("[_main] _receive 에러가 발생했습니다. 재시도합니다..")
            thread_connect.start()
            thread_connect.join()
            thread_receive.start()
            
        except:
            append_message("[_main] _receive 재시도 실패. 서버를 종료합니다.")
            is_end = True
    
    #thread_send가 정상 작동했는지 확인
    if send_err:
        try:
            append_message("[_main] _send 에러가 발생했습니다. 재시도합니다..")
            thread_connect.start()
            thread_connect.join()
            thread_send.start()
            
        except:
            append_message("[_main] _send 재시도 실패. 서버를 종료합니다.")
            is_end = True
            
    #thread_video_send가 정상 작동했는지 확인
    # if video_send_err:
    #     try:
    #         append_message("[_main] _video_send 에러가 발생했습니다. 재시도합니다..")
    #         pass
        
    #     except:
    #         append_message("[_main] _video_send 재시도 실패.")
            
    #thread_picture_send가 정상 작동했는지 확인
    if picture_send_err:
        try:
            append_message("[_main] _picture_send 에러가 발생했습니다. 재시도합니다..")
            pass
    
        except:
            append_message("[_main] _picture_send 재시도 실패.")
                
    #thread_sound_send가 정상 작동했는지 확인
    # if sound_send_err:
    #     try:
    #         append_message("[_main] _sound_send 에러가 발생했습니다. 재시도합니다..")
    #         pass
        
    #     except:
    #         append_message("[_main] _sound_send 재시도 실패.")
    

    print_message()
    sleep(interval)
        
        
print("[_main] <종료>")




                