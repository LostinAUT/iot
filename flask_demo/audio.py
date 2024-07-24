import pyaudio
from playsound import playsound
import wave
import os

# 设置录音参数
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
RECORD_SECONDS = 6
AUDIO_DIR = "./audio/"
AUDIO_PREFIX = "output"
AUDIO_EXTENSION = ".wav"

# 初始化文件计数器
file_counter = 1

# 检查已有文件，找到最大的文件编号
existing_files = os.listdir(AUDIO_DIR)
max_counter = 0
for file_name in existing_files:
    if file_name.startswith(AUDIO_PREFIX) and file_name.endswith(AUDIO_EXTENSION):
        try:
            counter = int(file_name[len(AUDIO_PREFIX):-len(AUDIO_EXTENSION)])
            if counter > max_counter:
                max_counter = counter
        except ValueError:
            pass

file_counter = max_counter + 1

# 生成文件名
WAVE_OUTPUT_FILENAME = f"{AUDIO_DIR}{AUDIO_PREFIX}{file_counter:03d}{AUDIO_EXTENSION}"

# 初始化PyAudio
p = pyaudio.PyAudio()

# 打开音频流
stream = p.open(format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK)

print("开始录音...")

# 开始录音
frames = []
for i in range(0, int(RATE / CHUNK * RECORD_SECONDS)):
    data = stream.read(CHUNK)
    frames.append(data)

print("录音结束.")
print(WAVE_OUTPUT_FILENAME)

# 关闭音频流
stream.stop_stream()
stream.close()
p.terminate()

# 将录音保存到WAV文件
wf = wave.open(WAVE_OUTPUT_FILENAME, 'wb')
wf.setnchannels(CHANNELS)
wf.setsampwidth(p.get_sample_size(FORMAT))
wf.setframerate(RATE)
wf.writeframes(b''.join(frames))
wf.close()

# 播放录音
# playsound(WAVE_OUTPUT_FILENAME)

# 清理
# os.remove(WAVE_OUTPUT_FILENAME)

# 更新文件计数器
file_counter += 1
