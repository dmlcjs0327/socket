import RPi.GPIO as GPIO
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import board
import busio
import picamera
import sys
import pyaudio
import wave
import numpy as np
from datetime import datetime
from time import sleep 
from time import time
from curses.ascii import isdigit #문자열이 숫자로 구성되었는지 확인하는 함수
import threading 
import socket as s
import cv2
import os
import urllib.request
import glob


#========================================목차===========================================

# 드래그 후 ctrl+F로 검색하여 바로가기

# 1) 하드코딩 구간
# 2) 전역변수 선언 구간
# 3) 센서변수 선언 구간
# 4) 함수 선언 구간
# 5) 스레드 선언 구간
# 6) 실행 구간



#======================================== 1) 하드코딩 구간 ===========================================

ip = '' #소켓통신을 할 대상기기의 IP (''로 둘 경우, 모든 host를 의미 / 단, 이 경우 send 대신 sendto로 addr를 명시해줘야 함)
port = 3022 #사용할 포트 / 1024 ~ 49151에서 임의지정
interval = 2 #송수신할 시간간격(sec)
sensor_interval = 0.1 #센서 값 입력의 주기
sensor_thres = 0.6 #10개의 센서 입력값 중 1이 7개 이상인 경우만 실행
data_size = 1024 #전송받을 데이터 크기(bytes)
siren_file = "test.wav"
directory_picture = '/home/kangmugu/CAMPictures/' #캡처한 사진을 저장할 경로
directory_movie = '/home/kangmugu/Movies/' #모션감지 영상을 저장할 경로
url_stream = "http://192.168.24.11:8081/?action=stream" #동영상 스트림 url



#======================================== 2) 전역변수 선언 구간 ======================================

_message_queue = [] #출력할 메세지를 저장하는 큐
is_end = False #전체 프로그램 종료를 의미

humity_target = 30 #목표 습도
humity_real = -1   #실제 습도

water_motor_err = False #수위모터에 에러가 있는지 (0기본, 1에러)
cooler_motor_err = False #스프링쿨러에 에러가 있는지 (0기본, 1에러)
cooler_motor_on = False

siren_option = None #경보에 대한 정보
capture_option = None #영상을 캡처하여 저장/전송할 주기
motor_option = None #모터 강제 작동

motion_detected = None #모션 감지 여부

server_socket = None #서버 소켓 객체
client_socket = None #클라이언트 소켓 객체
client_addr =  None #클라이언트 주소
socket_is_initialized = False #소켓이 생성되었는지를 저장하는 변수
socket_is_connected = False #소켓이 연결되었는지를 저장하는 변수
connect_is_run = False

connect_err = False #thread_connect가 비정상적으로 종료되었는지
receive_err = False #thread_receive가 비정상적으로 종료되었는지
send_err = False #thread_send가 비정상적으로 종료되었는지
video_send_err = False #thread_video_send가 비정상적으로 종료되었는지
picture_send_err = False #thread_picture_send가 비정상적으로 종료되었는지
sound_send_err = False #thread_sound_send가 비정상적으로 종료되었는지
motion_err = False #thread_motion이 비정상적으로 종료되었는지

camera = picamera.PiCamera() #웹캠(식물 전방 카메라)
camera.resolution = (1920, 1080) #해상도 설정



#======================================== 3) 센서 선언 구간 ========================================

I2C = busio.I2C(board.SCL, board.SDA) #습도 센서를 위한 i2c
ads = ADS.ADS1115(I2C) #습도 센서를 위한 ads

WL1 = 17 #저수 하단 핀
WL2 = 27 #저수 상단 핀

ENA_T = 16 #저수 펌프 가동/정지 핀
IN1_T = 20 #저수 펌프 정방향 회전 설정 핀
IN2_T = 21 #저수 펌프 역방향 회전 설정 핀

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



#======================================== 4) 함수 선언 구간 ========================================

#출력할 message를 queue에 넣는 함수
#=> 각 thread가 동시에 출력을 할 경우, 메세지가 끊겨서 출력될 수 있다
#=> 이를 방지하기 위해, 메세지 queue에 메세지들을 넣고, 한 스레드가 담당하여 출력한다.

#출력할 메세지와 기록 시간을 queue에 저장하는 함수
def append_message(msg):
    global _message_queue
    global is_end
    cur_time = datetime.now().strftime("%Y/%m/%d %H:%M:%S")
    msg2 = "{} {}".format(cur_time,msg)
    try:
        if not is_end:_message_queue.append(msg2)
        else: print(msg2)
    except:
        print(msg2)


# 모터 제어 함수
def pump(run, dic1, dic2, ENA, IN1, IN2):
    GPIO.output(ENA, run)
    GPIO.output(IN1, dic1)
    GPIO.output(IN2, dic2)


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

    global water_motor_err #수위모터에 에러가 있는지(bool)
    global cooler_motor_err #스프링쿨러에 에러가 있는지(bool)

    global siren_option #경보에 대한 정보
    global capture_option #영상을 캡처하여 저장/전송할 주기
    global motor_option

    global connect_err #thread_connect가 비정상적으로 종료되었는지
    global receive_err #thread_receive가 비정상적으로 종료되었는지
    global send_err #thread_send가 비정상적으로 종료되었는지
    global video_send_err #thread_video_send가 비정상적으로 종료되었는지
    global picture_send_err #thread_picture_send가 비정상적으로 종료되었는지
    global sound_send_err #thread_sound_send가 비정상적으로 종료되었는지
    global cooler_motor_on

    global motion_detected

    msg="""[_main] 
    <현재 습도>
    -목표 습도: {}
    -실제 습도: {}
    -캡처 정보: {}
    -사이렌 정보: {}
    -모터 정보: {}
    -쿨러 정보: {}
    -모션 감지: {}
    """.format(humity_target, humity_real, capture_option, siren_option, motor_option, cooler_motor_on, motion_detected)
    append_message(msg)


#시스템 메세지를 출력하는 함수
def print_message():
    global _message_queue
    
    state_message()
    
    print("\n".join(_message_queue))
    print()
    

def avg(lst): #평균 계산
    return sum(lst)/len(lst)


class MyException(Exception):

    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg+" "+super().__str__()



#======================================== 5) 스레드 선언 구간 ======================================

#스레드에서 실행할 함수명은 앞에 _를 붙였음

#소켓 연결용 스레드(단기)
def _connect():
    global is_end
    global connect_err
    global server_socket
    global client_socket
    global client_addr
    global socket_is_initialized
    global socket_is_connected
    global connect_is_run
    
    if connect_is_run or is_end: return #프로그램이 끝났거나 이미 connect가 실행 중이면, 바로 종료
    
    connect_is_run = True
    connect_err = False
    append_message("[_connect] <시작>")
    
    if not socket_is_initialized: #소켓이 생성되지 않은 경우
        socket_is_initialized = True
        server_socket = s.socket(s.AF_INET, s.SOCK_STREAM) #IPv4, TCP 프로토콜 방식의 소켓 객체 생성

        #소켓 생성 시도
        try:
            server_socket.bind(('',port)) #해당 ip/port에 대해 소켓 객체를 연결
            server_socket.listen(10) #연결을 허용할 client의 수
            append_message("[_connect] 소켓 new 생성 성공")

        except Exception:
            append_message("[_connect] 소켓 new 생성 실패..")
            socket_is_initialized = False
            server_socket.close() #서버소켓을 닫고
            socket_is_connected = False
            connect_err = True
            return

        #소켓 연결 시도
        try:
            socket_is_connected = True
            append_message("[_connect] 소켓 연결 시도 중...")
            client_socket, client_addr = server_socket.accept() #연결될 때까지 대기
            append_message("[_connect] 소켓 연결 성공 with {}".format(client_addr))

        except Exception as e:
            socket_is_connected = False
            append_message("[_connect] 에러: {}".format(e))
            connect_err = True


    else: #소켓이 생성된 경우
        if not socket_is_connected: #연결이 되지 않은 경우
            server_socket.close() #서버소켓을 닫고
            append_message("[_connect] 소켓 닫기")

            #소켓 생성 시도
            try:
                server_socket.bind(('',port)) #해당 ip/port에 대해 소켓 객체를 연결
                server_socket.listen(10) #연결을 허용할 client의 수
                append_message("[_connect] 소켓 new 생성 성공")

            except Exception:
                append_message("[_connect] 소켓 new 생성 실패..")
                socket_is_initialized = False
                server_socket.close() #서버소켓을 닫고
                socket_is_connected = False
                connect_err = True
                return

            #소켓 연결 시도
            try:
                socket_is_connected = True
                append_message("[_connect] 소켓 연결 시도 중...")
                client_socket, client_addr = server_socket.accept() #연결될 때까지 대기
                append_message("[_connect] 소켓 연결 성공 with {}".format(client_addr))

            except Exception as e:
                socket_is_connected = False
                append_message("[_connect] 에러: {}".format(e))
                connect_err = True

        else: #연결이 된 경우
            append_message("[_connect] 이미 연결이 되어 있습니다")

    print("[_connect] <종료>")
    connect_is_run = False

thread_connect = threading.Thread(target=_connect)
thread_connect.daemon = True #main thread가 종료되면 같이 종료


#안드로이드의 연락을 받는 스레드(유지)
def _receive():
    global is_end
    global receive_err
    global server_socket
    global client_socket
    global client_addr
    global data_size
    global interval
    global humity_target
    global siren_option
    global capture_option
    global motor_option
    global socket_is_connected
    wait_cnt = 0 # 대기횟수

    append_message("[_receive] <시작>")
    receive_err = False
    
    while not is_end:
        wait_cnt = 0
        try: 
            #소켓 연결이 안 된 경우
            while not socket_is_connected: 
                append_message("[_receive] 소켓 연결을 대기합니다")
                sleep(interval)
                wait_cnt += 1
                
                if wait_cnt > 0:
                    append_message("[_receive] 소켓이 연결되지 않습니다")
                    receive_err = True
                    break

            recv_data = client_socket.recv(data_size).decode('utf-8') #받을 때까지 대기
            append_message("[_receive] 수신: {}".format(recv_data))
            
            tmp = []
            n = 0
            for data in recv_data:
                if data != "," and isdigit(data):
                    n = n*10 + int(data)
                else:
                    tmp.append(n)
                    n = 0
            tmp.append(n)
            tmp = tmp[2:]
            append_message("[_receive] 변환 data: {}".format(tmp))

            #[습도,경보,캡처] 형식으로 데이터를 전송받음
            try:
                humity_target = int(tmp[0]) #0~100 사이의 수로 구성
                siren_option = int(tmp[1]) #"siren" 또는 "tts 읽을 문장"으로 구성
                motor_option = int(tmp[2])
                capture_option = int(tmp[3]) #숫자1 숫자2.. 로 구성
            except:
                pass

            sleep(interval) #잠시 대기 후 송수신 (오버헤드를 줄이기 위함)
            
        except Exception as e: 
            socket_is_connected = False
            receive_err = True
            append_message("[_receive] 에러: {}".format(e))
            break
            
    append_message("[_receive] <종료>")

thread_receive = threading.Thread(target=_receive)
thread_receive.daemon = True #main thread가 종료되면 같이 종료


#안드로이드에게 연락을 보내는 스레드(유지)
def _send(): #send_data: 보낼 메세지(str)
    global is_end
    global send_err
    global client_socket
    global interval
    global humity_real
    global water_motor_err
    global cooler_motor_err
    global motion_detected
    global socket_is_connected
    wait_cnt = 0 # 대기횟수
    motion_detected_send_cnt = 0 #모션감지 정보를 보낸 횟수

    append_message("[_send] <시작>")
    send_err = False

    while not is_end:
        try:
            #소켓 연결이 안 된 경우
            while not socket_is_connected: 
                append_message("[_receive] 소켓 연결을 대기합니다")
                sleep(interval)
                wait_cnt += 1
                
                if wait_cnt > 0:
                    append_message("[_receive] 소켓이 연결되지 않습니다")
                    send_err = True
                    break

            #[습도,T이상,S이상,모션감지]
            send_data = "{},{},{},{}".format(humity_real, int(water_motor_err), int(cooler_motor_err), int(motion_detected))
            
            if motion_detected: 
                motion_detected_send_cnt += 1
                if motion_detected_send_cnt > 2:
                    motion_detected = False
                    motion_detected_send_cnt = 0

            append_message("[_send] 송신: {}".format(send_data))
            client_socket.send(send_data.encode('utf-8')) #연결된 client에게 데이터를 전송
            append_message("[_send] 송신 완료")
            
            sleep(interval) #잠시 대기 후 송수신 (오버헤드를 줄이기 위함)
        
        except Exception as e:
            socket_is_connected = False
            send_err = True
            append_message("[_send] 에러: {}".format(e))
    
    append_message("[_send] <종료>")

thread_send = threading.Thread(target=_send)
thread_send.daemon = True #main thread가 종료되면 같이 종료


#안드로이드에게 영상을 보내는 스레드(단기)
def _video_send(send_data):
    append_message("[_video_send] <종료>")
    pass

thread_video_send = threading.Thread(target=_video_send)
thread_video_send.daemon = True


#센서에게 소리를 보내는 스레드(단기)
def _sound_send():
    global is_end
    global siren_option
    global sound_send_err
    chunk = 1024 #스피터에 전달할 정보량

    sound_send_err = False

    while not is_end:
        try:
            if siren_option == 1:
                append_message("[_sound_send] 동작")
                wf = wave.open(siren_file, 'rb') #사운드파일 객체
                p = pyaudio.PyAudio() #스피커 객체
                stream = p.open(format = p.get_format_from_width(wf.getsampwidth()), 
                                channels = wf.getnchannels(), 
                                rate = wf.getframerate(), 
                                output = True)
                data = wf.readframes(chunk)
                while data != b'':
                    stream.write(data)
                    data = wf.readframes(chunk)
                stream.stop_stream()
                stream.close()
                p.terminate()
                append_message("[_sound_send] 동작 완료")
                sleep(0.5)
            
        except Exception as e:
            sound_send_err = True
            append_message("[_sound_send] 에러 발생")
            break
        
thread_sound_send = threading.Thread(target=_sound_send)
thread_sound_send.daemon = True #main thread가 종료되면 같이 종료


# 센서 조정용 스레드_저수탱크(유지)
def _sensor_water():
    global is_end
    global humity_real
    global humity_target
    global water_motor_err
    global cooler_motor_err
    global motor_option
    global sensor_interval
    global sensor_thres
    
    water_bottom_list = [] #저수탱크 하단 센서값을 저장할 리스트
    water_top_list = [] #저수탱크 상단 센서값을 저장할 리스트
    
    water_level_bottom_cnt = 0 #물높이가 최저가 될 때마다 +1
    
    water_motor_on = False #모터가 켜져있는지 확인하는 변수
    
    append_message("[_sensor] <시작>")
    
    while not is_end:
        #저수탱크 모터 조정 파트
        try:
            water_level_bottom = GPIO.input(WL1) #저수탱크 하단 센서
            water_bottom_list.append(water_level_bottom)
            
            water_level_top = GPIO.input(WL2) #저수탱크 상단 센서
            water_top_list.append(water_level_top)

            if len(water_bottom_list) == 10: #센서값을 10개 모은 경우에 수행
                water_level_bottom = 1 if avg(water_bottom_list)>sensor_thres else 0 #평균값 추출
                water_level_top = 1 if avg(water_top_list)>sensor_thres else 0 #평균값 추출

                water_bottom_list = []
                water_top_list = []

                if water_level_bottom == 0: #저수탱크 하단에 물이 없으면
                    if not water_motor_on:#모터가 꺼져있으면
                        pump(1, 1, 0, ENA_T, IN1_T, IN2_T) #모터 작동
                        water_motor_on = True
                        append_message("[_sensor] 저수탱크 모터 작동")
                    else: #모터가 켜져있으면
                        water_level_bottom_cnt+=1 #물이 없는 상태 카운트
                        if water_level_bottom_cnt > 200: raise MyException("모터가 켜져있는데 물이 안 차오름") #20초 초과 시 에러

                elif water_level_top == 1: #저수탱크 상단에 물이 있으면
                    if water_motor_on: #모터가 켜져있으면
                        pump(0, 0, 0, ENA_T, IN1_T, IN2_T) #모터 중지
                        water_motor_on = False
                        append_message("[_sensor] 저수탱크 모터 중지")
                else:
                    water_level_bottom_cnt = 0 #카운트 초기화
                    water_motor_err = False
            
        except Exception as e:
            water_motor_err = True #에러가 발생했다고 체크
            append_message("[_sensor] 저수탱크 에러 발생: {}".format(e))
        
        finally: sleep(sensor_interval)
    
    pump(0, 0, 0, ENA_T, IN1_T, IN2_T)
    append_message("[_sensor] <종료>")

thread_sensor_water = threading.Thread(target=_sensor_water)
thread_sensor_water.daemon = True #main thread가 종료되면 같이 종료


# 센서 조정용 스레드_스프링쿨러(유지)
def _sensor_humity():
    global is_end
    global humity_real
    global humity_target
    global water_motor_err
    global cooler_motor_err
    global motor_option
    global interval
    global sensor_thres
    
    humity_low_cnt = 0 #습도가 낮을 때마다 +1
    
    cooler_motor_on = False #모터가 켜져있는지 확인하는 변수
    
    append_message("[_sensor] <시작>")
    
    while not is_end:

        #스프링쿨러 조정 파트
        try:
            adcValue = AnalogIn(ads, ADS.P1).value #0~1023
            humity_real = 64-int(adcValue/1023)

            if motor_option == 1:
                if not cooler_motor_on: #모터가 꺼져있으면
                    pump(1, 0, 1, ENA_S, IN1_S, IN2_S)
                    cooler_motor_on = True
                    append_message("[_sensor] 스프링쿨러 강제 작동")
                    
            else:
                if humity_real < humity_target: #습도가 목표치보다 낮은데
                    if not cooler_motor_on: #모터가 꺼져있으면
                        pump(1, 0, 1, ENA_S, IN1_S, IN2_S) #스프링쿨러 작동
                        cooler_motor_on = True
                        append_message("[_sensor] 스프링쿨러 작동")
                    
                    else: #모터가 켜져있으면
                        humity_low_cnt+=1
                        if humity_low_cnt > 10: raise MyException("모터가 켜져있는데 습도가 안 오름") #20초 초과 시 에러
                        
                else : #습도가 목표치보다 높은데
                    humity_low_cnt = 0
                    if not cooler_motor_on: #모터가 켜져있으면
                        pump(0, 0, 0, ENA_S, IN1_S, IN2_S) #스프링쿨러 중지
                        cooler_motor_on = False
                        append_message("[_sensor] 스프링쿨러 중지")
            
            cooler_motor_err = False

        except Exception as e:
            cooler_motor_err = True #에러가 발생했다고 체크
            append_message("[_sensor] 스프링쿨러 에러 발생: {}".format(e))

        sleep(interval)
        
    append_message("[_sensor] <종료>")

thread_sensor_humity = threading.Thread(target=_sensor_humity)
thread_sensor_humity.daemon = True #main thread가 종료되면 같이 종료

        
#동작 감지용 스레드(유지)
def _motion():
    global is_end
    global url_stream
    global motion_detected
    global motion_err

    motion_err = False
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
        sleep(interval)
                        
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
    
    try:
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
                motion_detected = True
                
                #저장된 파일을 전송하는 코드 추가 요망!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
                
            a = b
            b = c
            
            if cv2.waitKey(1) & 0xFF == 27: break
            remove_movie() #오래된 영상 제거

    except Exception as e:
        append_message("[_motion] 에러: {}".format(e))
        motion_err = True

    os.system('sudo killall mjpg_streamer')
    append_message("[_motion] <종료>")

thread_motion = threading.Thread(target=_motion)
thread_motion.daemon = True #main thread가 종료되면 같이 종료



#======================================== 6) 실행 구간 ============================================
print("[_main] <시작>")

thread_connect.start()
sleep(interval//2)

thread_receive.start()
thread_send.start()
thread_sensor_water.start()
thread_sensor_humity.start()
thread_sound_send.start()
thread_motion.start()

try:
    while not is_end:
        #thread_connect가 정상 작동했는지 확인
        if connect_err:
            append_message("[_main] _connect 에러가 발생했습니다. 재시도합니다..")
            thread_connect.start()
        
        #thread_receive가 정상 작동했는지 확인
        if receive_err:
            append_message("[_main] _receive 에러가 발생했습니다. 재시도합니다..")
            thread_connect.start()
            thread_receive.start()
        
        #thread_send가 정상 작동했는지 확인
        if send_err:
            append_message("[_main] _send 에러가 발생했습니다. 재시도합니다..")
            thread_connect.start()
            thread_send.start()    
                
        #thread_picture_send가 정상 작동했는지 확인
        if picture_send_err:
            append_message("[_main] _picture_send 에러가 발생했습니다. 재시도합니다..")
                    
        #thread_sound_send가 정상 작동했는지 확인
        if sound_send_err:
            append_message("[_main] _sound_send 에러가 발생했습니다. 재시도합니다..")
            thread_sound_send.start()

        #thread_motion이 정상작동했는지 확인
        if motion_err:
            append_message("[_main] _motion 에러가 발생했습니다. 재시도합니다..")
            thread_sound_send.start()

        print_message()
        sleep(interval)
        
except Exception as e:
    print("[_main] 서버를 중단합니다:",e)
    is_end = True 
        
print("[_main] <종료>")
pump(0, 0, 0, ENA_T, IN1_T, IN2_T) #모터 중지
pump(0, 0, 0, ENA_S, IN1_S, IN2_S) #스프링쿨러 중지

if socket_is_initialized: 
    server_socket.close()
sys.exit(0)




                