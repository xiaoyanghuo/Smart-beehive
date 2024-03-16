import cv2 as cv
import numpy as np
import onnxruntime as ort
from deep_sort import nn_matching
from deep_sort.detection import Detection
from deep_sort.tracker import Tracker



class MOTer():
    def __init__(self, modelpath="last-wasp2.onnx", max_cosine_distance=0.01, nn_budget=None,
                 min_confidence=0.1, ):
        self.ort_session = ort.InferenceSession(modelpath, providers=['CPUExecutionProvider'])
        metric = nn_matching.NearestNeighborDistanceMetric(
            "cosine", max_cosine_distance, nn_budget)  # 使用余弦指标的最近邻距离度量结果
        self.tracker = Tracker(metric)  # 输入metric距离度量器，以获取跟踪器
        self.min_confidence = min_confidence
    def frametrack(self,frame,tframe=None ,results=None):
        if tframe == None or results == None:
            tframe, results = preprocess(frame,self.ort_session)
        # 处理推理结果，切换维数轴，batch，特征图，各个框位置+类别置信度
        res = results[0].transpose(0, 2, 1).copy()
        # 置信度数组处理，筛除置信度低于最小阈值的框
        confidence = res[0, :, 4:9]
        boxnos, _ = np.where(confidence > self.min_confidence)
        boxes, scores, boxinfos = [], [], []
        for boxno in boxnos:
            scores.append(np.max(res[0, boxno, 4:9]))
            boxes.append(res[0, boxno, 0:4])
            boxinfos.append(res[0, boxno, :])
        # 输入非极大值抑制
        pick = non_max_suppression(np.array(boxes), 0.2, np.array(scores))

        finalboxinfos = []
        for idx in pick:
            finalboxinfos.append(boxinfos[idx])
        # 结束预处理流程
        # boxinfos every line:  cx,cy,w,h,con0,con1,con2,con3,con4

        # 由boxinfos数组构造符合接口的detections类列表
        detections = []
        for boxinfo in finalboxinfos:
            a = int(boxinfo[0] - 0.5 * boxinfo[2])
            b = int(boxinfo[0] + 0.5 * boxinfo[2])
            c = int(boxinfo[1] - 0.5 * boxinfo[3])
            d = int(boxinfo[1] + 0.5 * boxinfo[3])
            L = [boxinfo[4], boxinfo[5], boxinfo[6], boxinfo[7], boxinfo[8]]
            box = [a, c, boxinfo[2], boxinfo[3]]
            score = max(L)
            bug_class = int(L.index(max(L)))
            if bug_class == 3:
                bug_class = 0
            detections.append(Detection(box, score, [bug_class], bug_class))  # bug_class
            drawbox(boxinfo, tframe)
        # print(detections)
        # 使用跟踪器, detections完成预测更新
        self.tracker.predict()  # 使用获得的卡尔曼滤波器进行预测
        self.tracker.update(detections)  # 使用新获得的检测框来更新状态

        # print(self.tracker.tracks)
        # 对各个track调用打印方法
        for track in self.tracker.tracks:
            if not track.is_confirmed() or track.time_since_update > 1:
                drawtrack(track, tframe, False)
                continue
            drawtrack(track, tframe, True)
        # 打印出入量信息
        bugs_out = [self.tracker.bugs_out[0],self.tracker.bugs_out[1],self.tracker.bugs_out[2],self.tracker.bugs_out[4]]
        bugs_in = [self.tracker.bugs_in[0],self.tracker.bugs_in[1],self.tracker.bugs_in[2],self.tracker.bugs_in[4]]
        cv.putText(tframe, str(bugs_out), (320, 60), cv.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 1)
        cv.putText(tframe, str(bugs_in), (320, 580), cv.FONT_HERSHEY_SIMPLEX, 0.75, (0, 0, 0), 1)
        # cv.imshow("a", tframe)
        return tframe


def drawbox(boxinfo, frame):
    # imgshape = frame.shape
    color = [(0,0,255),(0,255,0),(255,0,0),(0,0,0),(255,255,0)]
    a = int(boxinfo[0] - 0.5*boxinfo[2])
    b = int(boxinfo[0] + 0.5*boxinfo[2])
    c = int(boxinfo[1] - 0.5*boxinfo[3])
    d = int(boxinfo[1] + 0.5*boxinfo[3])
    L = [boxinfo[4], boxinfo[5], boxinfo[6], boxinfo[7], boxinfo[8]]
    color_index = L.index(max(L))
    if color_index == 3:
        color_index = 0
    # cv.rectangle(frame,  (c, a),(d, b), color[color_index], 1)
    # cv.circle(frame, (c, a), 10, color[color_index])
    cv.putText(frame, str(max(L)), (d, b), cv.FONT_HERSHEY_SIMPLEX, 0.75, color[color_index], 2)

def drawtrack(track,frame,flag):
    bbox = track.to_tlwh()
    ID = track.track_id
    a = int(bbox[0])
    b = int(bbox[0] + bbox[2])
    c = int(bbox[1])
    d = int(bbox[1] + bbox[3])
    color = [(0, 0, 255), (0, 255, 0), (255, 0, 0), (0, 0, 0), (255, 255, 0)]
    # print("track.features",track.features)
    if flag:
        cv.rectangle(frame, (c, a), (d, b), color[track.bug_class], 1)#int(track.features[0][0])
        cv.rectangle(frame, (c, a), (d, b), color[track.bug_class], 1)  # int(track.features[0][0])
        cv.putText(frame, str(track.track_id)+' '+str(track.confirmed_id)+' '+str(track.hits),(c,a)
                   , cv.FONT_HERSHEY_SIMPLEX, 0.75, color[track.bug_class], 1)
    else:
        cv.rectangle(frame, (c, a), (d, b), (255,255,255), 1)  # int(track.features[0][0])
        cv.putText(frame, str(track.track_id) + ' ' + str(track.confirmed_id) + ' ' + str(track.hits), (c, a)
                   , cv.FONT_HERSHEY_SIMPLEX, 0.75, (255,255,255), 1)


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
        last = len(idxs) - 1  # 最大值
        i = idxs[last]  # 最大下标
        pick.append(i)  # 加入输出
        xx1 = np.maximum(x1[i], x1[idxs[:last]])  # np.maximum(array1, array2)：逐位比较array1和array2，并输出两者的最大值。
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)
        overlap = (w * h) / area[idxs[:last]]
        idxs = np.delete(
            idxs, np.concatenate(
                ([last], np.where(overlap > max_bbox_overlap)[0])))  # 删去最大下标以及小值
    # print(pick)
    return pick


def padding(frame):
    imgshape = frame.shape
    if imgshape[0]>imgshape[1]:
        pframe = cv.resize(frame,(int(640/imgshape[0]*imgshape[1]), 640))
        pad = 640-int(640/imgshape[0]*imgshape[1])
        ret = cv.copyMakeBorder(frame, 0, 0,pad//2, pad//2+pad % 2,  cv.BORDER_CONSTANT, value=(255,255,255))
        w = 0
        h = pad//2
    elif imgshape[0]<imgshape[1]:
        pframe = cv.resize(frame,(640, int(640/imgshape[1]*imgshape[0])))
        pad = 640-int(640/imgshape[1]*imgshape[0])
        ret = cv.copyMakeBorder(pframe, pad//2, pad//2+pad % 2, 0, 0,  cv.BORDER_CONSTANT, value=(255,255,255))
        w = pad//2
        h = 0

    return h,w,ret


def preprocess(frame,ort_session):
    # 规格化到640x640,tframe可以用来在openCV中显示
    _, _, tframe = padding(frame)
    # 切换颜色通道，浮点格式，切换维数轴，增加维度以输入网络
    pframe = cv.cvtColor(tframe, cv.COLOR_BGR2RGB)
    pframe = cv.resize(pframe, (640, 640)) / 255  # 这句可不用
    pframe = np.swapaxes(pframe, 0, 2)
    pframe = np.expand_dims(pframe, axis=0)
    # 神经网络推理
    results = ort_session.run(None, {"images": pframe.astype(np.float32)}, )
    return tframe , results