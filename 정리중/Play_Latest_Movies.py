""" 영상 파일 폴더 내 가장 최근 파일 재생 """

import glob
import os

list_of_files = glob.glob('/home/kangmugu/Movies/*.mp4') # * means all if need specific format then *.csv
latest_file = max(list_of_files, key=os.path.getctime)
print(latest_file)   # 최근 파일 경로 받아옴

""" 여기부터는 라즈리베파이 내부에서 재생하는거라 빼도될거같아요 """
"""
import numpy as np
import cv2 as cv

os.getcwd()

os.chdir('/home/kangmugu/Movies')
os.getcwd()

cap = cv.VideoCapture(latest_file)

width = cap.get(cv.CAP_PROP_FRAME_WIDTH) # 또는 cap.get(3)
height = cap.get(cv.CAP_PROP_FRAME_HEIGHT) # 또는 cap.get(4)
fps = cap.get(cv.CAP_PROP_FPS) # 또는 cap.get(5)
print('프레임 너비: %d, 프레임 높이: %d, 초당 프레임 수: %d' %(width, height, fps))

while cap.isOpened(): # cap 정상동작 확인
    ret, frame = cap.read()
    # 프레임이 올바르게 읽히면 ret은 True
    if not ret:
        print("프레임을 수신할 수 없습니다(스트림 끝?). 종료 중 ...")
        break
    # frame = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)
    cv.imshow('Otter', frame)
    if cv.waitKey(42) == ord('q'):
        break
# 작업 완료 후 해제
cap.release()
cv.destroyAllWindows()
"""