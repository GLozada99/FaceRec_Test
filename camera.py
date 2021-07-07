from cv2 import cv2
import numpy as np
#import os
#os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;udp"
vcap = cv2.VideoCapture("rtsp://gustavo:123456789Gu@10.0.0.121:554/Streaming/Channels/102")
while(1):
    ret, frame = vcap.read()
    if ret == False:
        print("Frame is empty")
        break
    else:
        cv2.imshow('VIDEO', frame)
        cv2.waitKey(1)