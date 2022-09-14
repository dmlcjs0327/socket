""" 스트리밍 중인 웹캠에서 움직임 감지될 시 영상 녹화 기능 """


import cv2
import numpy as np
from datetime import datetime
import time
import urllib.request
import Remove_Oldest_Movie as R

#url에 연결에 성공하면 True, 실패하면 false를 리턴하는 함수
def url_on():
    try:
        urllib.request.urlopen('http://192.168.0.194:8081/?action=stream', timeout=2)
        return True
    except:
        return False

while url_on() == False:
    print("스트리밍 연결 시도 중")
    time.sleep(1.0)
    pass

for i in range(10):
    print(f"=========={10-i}초 후 녹화 기능이 시작됩니다.==========")
    i+=1
    time.sleep(1.0)

thresh = 25
max_diff = 300 

a, b, c = None, None, None 

cap = cv2.VideoCapture("http://192.168.0.194:8081/?action=stream")
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

fourcc = cv2.VideoWriter_fourcc(*'mp4v')
record = False
start_time = time.time()
detected = False
if cap.isOpened():    
    ret, a = cap.read()    #ret(bool): 정상적으로 읽어왔는지, a: 읽어온 프레임
    ret, b = cap.read()    
    while ret:        
        ret, c = cap.read()        
        draw = c.copy()        
        if not ret:            
            break         
        
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

        if detected == True and record == False:
            record = True
            start_time = time.time()
            video = cv2.VideoWriter("/home/kangmugu/Movies/" +str(now)+ ".mp4", fourcc, 15.0, (draw.shape[1], draw.shape[0]))
            
        if 'video' in locals() and time.time() > (start_time + 10):
            record = False
            detected = False
            video.release()
            
        if record == True:
            video.write(draw)
            
        a = b        
        b = c
        
        if cv2.waitKey(1) & 0xFF == 27:            
            break
        R.Remove_Movie()