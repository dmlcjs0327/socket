""" 영상 폴더 내 최대 영상 개수 초과 시 오래된 영상부터 하나씩 지움 """
""" 저장공간 확보 목적 """

import glob
import os
import time
def Remove_Movie():
    Max_Movies = 10 # 영상 폴더 내 최대 영상 개수

    list_of_files = glob.glob('/home/kangmugu/Movies/*.mp4') # * means all if need specific format then *.csv

    oldest_file = min(list_of_files, key=os.path.getctime)
    if len(list_of_files) > Max_Movies:
        os.remove(oldest_file)
        pass