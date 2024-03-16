import cv2 as cv
import numpy as np
import os
from MOTer import MOTer
import imageio
import pyodbc
import time
import requests
import socket
import select
import queue

modelpath = 'last-wasp2.onnx'
modelpath = 'finalbest.onnx'
modelpath = 'nju.onnx'

path = 'save/2023-08-17-19-08-57_img(best_effort)/'
# path = 'video/'
# path = 'finalbee/'
path = 'save/2023-08-23-17-49-40_img/'# bee
path = 'save/2023-08-23-17-58-16_img(final)/' # wasp
path = 'save/2023-08-23-17-49-40_img/' # bee
path = 'save/2023-08-17-14-53-34_img/' # ant fly
path = 'save/2023-08-23-18-15-42_img/' #what

framelist0 = os.listdir(path)
framelist0.sort()
print(len(framelist0))
max_length = max([len(filename) for filename in framelist0])
print(max_length)
framelist = []
for i in range(1,max_length+1):
    temp = []
    for filename in framelist0:
        if len(filename) == i:
            temp.append(filename)
            print(filename)
    temp.sort()
    framelist.extend(temp)
# framelist = framelist0
print(len(framelist))

# moter = MOTer()
moter = MOTer(modelpath=modelpath)
tracker = moter.tracker

tframes = []
for i, filename in enumerate(framelist):
    frame = cv.imread(path+filename,cv.IMREAD_COLOR)
    # frame = cv.resize(frame, (frame.shape[1] // 4, frame.shape[0] // 4))
    # frame = cv.rotate(frame, cv.ROTATE_90_CLOCKWISE)
    tframe = moter.frametrack(frame)
    # cv.imwrite('videoframes/'+'tframe'+str(i).rjust(3, '0')+'.jpg', tframe)
    tframes.append(cv.cvtColor(tframe, cv.COLOR_BGR2RGB))
    # cv.imshow("window", frame)
    cv.imshow("window", tframe)

    key = cv.waitKey(1)

cv.destroyAllWindows()