""" 사진 촬영 기능 """
""" 어플에서 명령을 내리면 이 코드로 촬영이 되는 식으로 되면 좋겠어요 """

import picamera
import datetime



def Capture_Plant():
    now = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    camera = picamera.PiCamera()
    camera.resolution = (1920, 1080)
    camera.capture('/home/kangmugu/CAMPictures/'+now+'.png')


Capture_Plant()