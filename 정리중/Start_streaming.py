""" 라즈베리파이 내에서 실행시켜 스트리밍 프로그램 실행 """
""" 모션 감지 및 녹화 기능도 같이 실행 ( 시작프로그램으로 씀 ) """
import os, sys
os.system('sh mjpg.sh &')
import Motion_Detect as M
M.start()