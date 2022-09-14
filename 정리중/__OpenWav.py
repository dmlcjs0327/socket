import pyaudio
import wave
""" .wav 음성 파일 재생 """
""" 라즈베리파이 기기에서 스피커로 재생 """

name = input("Audio name : ")

class AudioFile:
    chunk = 1024
    
    def __init__(self, file):
        """ Init audio stream """
        self.wf = wave.open(file, 'rb')
        self.p = pyaudio.PyAudio()
        self.stream = self.p.open(format = self.p.get_format_from_width(self.wf.getsampwidth()),
                                  channels = self.wf.getnchannels(),
                                  rate = self.wf.getframerate(),
                                  output = True
                            )
    def play(self):
        data = self.wf.readframes(self.chunk)
        while data != b'':
            self.stream.write(data)
            data = self.wf.readframes(self.chunk)
    def close(self):
        self.stream.close()
        self.p.terminate()
        
a = AudioFile(name+'.wav') # 파일이름 + .wav 파일 재생
a.play()
a.close