from MOTer import MOTer
import cv2 as cv

video = 1
cap = cv.VideoCapture(video)
moter = MOTer()
tracker = moter.tracker
while(1):
    ret, frame = cap.read()
    tframe = moter.frametrack(frame)
    cv.imshow("MOT", tframe)
    cv.waitKey(1)

