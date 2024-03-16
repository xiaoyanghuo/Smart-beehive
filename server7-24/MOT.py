import cv2 as cv
import numpy as np
import onnxruntime as ort
from scipy.optimize import linear_sum_assignment
import time


from deep_sort import nn_matching
from deep_sort.detection import Detection
from deep_sort.tracker import Tracker

# 模型数据后处理

def drawbox(boxinfo, frame):
    # imgshape = frame.shape
    color = [(0,0,255),(0,255,0),(255,0,0),(255,255,0)]
    a = int(boxinfo[0] - 0.5*boxinfo[2])
    b = int(boxinfo[0] + 0.5*boxinfo[2])
    c = int(boxinfo[1] - 0.5*boxinfo[3])
    d = int(boxinfo[1] + 0.5*boxinfo[3])
    L = [boxinfo[4], boxinfo[5], boxinfo[6], boxinfo[7], boxinfo[8]]
    color_index = L.index(max(L))
    # cv.rectangle(frame,  (c, a),(d, b), color[color_index], 1)
    cv.circle(frame, (c, a), 10, color[color_index])


def drawtrack(track,frame,flag):
    bbox = track.to_tlwh()
    ID = track.track_id
    a = int(bbox[0])
    b = int(bbox[0] + bbox[2])
    c = int(bbox[1])
    d = int(bbox[1] + bbox[3])
    color = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (255, 255, 0)]
    print("track.features",track.features)
    if flag:
        cv.rectangle(frame, (c, a),(d, b), color[track.bug_class], 1)#int(track.features[0][0])
        cv.rectangle(frame, (c, a), (d, b), color[track.bug_class], 1)  # int(track.features[0][0])
        cv.putText(frame, str(track.track_id)+' '+str(track.confirmed_id)+' '+str(track.hits),(c,a)
                   , cv.FONT_HERSHEY_SIMPLEX, 0.75, color[track.bug_class], 1)
    else:
        cv.rectangle(frame, (c, a), (d, b), (255,255,255), 1)  # int(track.features[0][0])
        cv.putText(frame, str(track.track_id) + ' ' + str(track.confirmed_id) + ' ' + str(track.hits), (c, a)
                   , cv.FONT_HERSHEY_SIMPLEX, 0.75, (255,255,255), 1)


def padding(frame):
    imgshape = frame.shape
    if imgshape[0]>imgshape[1]:
        pframe = cv.resize(frame,(int(640/imgshape[0]*imgshape[1]), 640))
        pad = 640-int(640/imgshape[0]*imgshape[1])
        ret = cv.copyMakeBorder(frame, 0, 0,pad//2, pad//2+pad%2,  cv.BORDER_CONSTANT, value=(255,255,255))
        w = 0
        h = pad//2
    elif imgshape[0]<imgshape[1]:
        pframe = cv.resize(frame,(640, int(640/imgshape[1]*imgshape[0])))
        pad = 640-int(640/imgshape[1]*imgshape[0])
        ret = cv.copyMakeBorder(pframe,pad//2, pad//2+pad%2, 0, 0,  cv.BORDER_CONSTANT, value=(255,255,255))
        w = pad//2
        h = 0

    return h,w,ret


def non_max_suppression(boxes, max_bbox_overlap, scores=None):
    # ROI就是(x,y,w,h)
    # boxes中装的就是多个ROI，scores装着对应的分数
    # max_bbox_overlap超过这个值，可以抑制这个框。
    if len(boxes) == 0:
        return []
    boxes = boxes.astype(np.float64)
    pick = []
    x1 = boxes[:, 0]-boxes[:, 2]//2
    y1 = boxes[:, 1]-boxes[:, 3]//2
    x2 = boxes[:, 0]+boxes[:, 2]//2
    y2 = boxes[:, 1]+boxes[:, 3]//2
    area = (x2 - x1 + 1) * (y2 - y1 + 1)
    if scores is not None:
        idxs = np.argsort(scores)
    else:
        idxs = np.argsort(y2)
    while len(idxs) > 0:
        last = len(idxs) - 1#最大值
        i = idxs[last]#最大下标
        pick.append(i)#加入输出
        xx1 = np.maximum(x1[i], x1[idxs[:last]]) #np.maximum(array1, array2)：逐位比较array1和array2，并输出两者的最大值。
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)
        overlap = (w * h) / area[idxs[:last]]
        idxs = np.delete(
            idxs, np.concatenate(
                ([last], np.where(overlap > max_bbox_overlap)[0])))#删去最大下标以及小值
    print(pick)
    return pick


ort_session = ort.InferenceSession("last-wasp2.onnx", providers=['CPUExecutionProvider'])

video = "http://admin:admin@10.58.7.39:8081/video"
video = 1
print("get video")
cap =cv.VideoCapture(video)
print("video found")

# save information
index1 = 0

max_cosine_distance=0.2
nn_budget=None
# ret, frame = cap.read()
# if not ret:
#     print("Can't receive frame (stream end?). Exiting ...")
#     exit()
metric = nn_matching.NearestNeighborDistanceMetric(
   "cosine", max_cosine_distance, nn_budget)#使用余弦指标的最近邻距离度量结果
tracker = Tracker(metric)#输入metric距离度量器，以获取跟踪器
results = [] #初始化结果数组

while 1:
    ret, frame = cap.read()
    if not ret:
        print("Can't receive frame (stream end?). Exiting ...")
        break
    _,_,tframe = padding(frame)
    pframe = cv.cvtColor(tframe, cv.COLOR_BGR2RGB)
    pframe = cv.resize(pframe,(640, 640))/255
    pframe = np.swapaxes(pframe, 0, 2)
    pframe = np.expand_dims(pframe, axis=0)
    results = ort_session.run(None,{"images": pframe.astype(np.float32)},)
    res = results[0].transpose(0,2,1).copy()
    confidence = res[0, :, 4:9]
    boxnos , _ = np.where(confidence>0.4)

    #frame = cv.resize(frame,(640, 640))
    boxes = []
    scores = []
    boxinfos = []

    for boxno in boxnos:
        scores.append(np.max(res[0,boxno,4:9]))
        boxes.append(res[0,boxno,0:4])
        boxinfos.append(res[0,boxno,:])
    pick = non_max_suppression(np.array(boxes), 0.4,np.array(scores))



    finalboxinfos = []
    for idx in pick:
        finalboxinfos.append(boxinfos[idx])
    #every line:  cx,cy,w,h,con0,con1,con2,con3




    #构造符合接口的detections类列表
    detections = []
    for boxinfo in finalboxinfos:
        a = int(boxinfo[0] - 0.5 * boxinfo[2])
        b = int(boxinfo[0] + 0.5 * boxinfo[2])
        c = int(boxinfo[1] - 0.5 * boxinfo[3])
        d = int(boxinfo[1] + 0.5 * boxinfo[3])
        L = [boxinfo[4],boxinfo[5],boxinfo[6],boxinfo[7],boxinfo[8]]
        box = [a,c,boxinfo[2],boxinfo[3]]
        score = max(L)
        bug_class = int(L.index(max(L)))
        detections.append(Detection(box, score, [bug_class], bug_class))# bug_class
        drawbox(boxinfo, tframe)
    print(detections)

    tracker.predict()#使用获得的卡尔曼滤波器进行预测
    tracker.update(detections)#使用新获得的检测框来更新状态

    print(tracker.tracks)
    for track in tracker.tracks:
         if not track.is_confirmed() or track.time_since_update > 1:
             drawtrack(track,tframe,False)
             continue
         drawtrack(track,tframe,True)

    cv.putText(tframe, str(tracker.bugs_out), (320, 60), cv.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 1)
    cv.putText(tframe, str(tracker.bugs_in), (320, 580), cv.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 1)
    #drawbox(, tframe)
    cv.imshow("a", tframe)

    key = cv.waitKey(2)
    if key == ord('q'):
        break
    elif key == ord('/'):
        cv.waitKey(0)
cap.release()
cv.destroyAllWindows()




        # cv.imsave("frame"+str(index1),frame)
        # with open("detections"+str(index1),'w') as tf:
        # 	write()





