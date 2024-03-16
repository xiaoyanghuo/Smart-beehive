# vim: expandtab:ts=4:sw=4
from __future__ import absolute_import
import numpy as np
from . import kalman_filter
from . import linear_assignment
from . import iou_matching
from .track import Track


class Tracker:#Tracker类，调用卡尔曼滤波的实现。
    """
    This is the multi-target tracker.

    Parameters
    ----------
    metric : nn_matching.NearestNeighborDistanceMetric
        A distance metric for measurement-to-track association.
    max_age : int
        Maximum number of missed misses before a track is deleted.
    n_init : int
        Number of consecutive detections before the track is confirmed. The
        track state is set to `Deleted` if a miss occurs within the first
        `n_init` frames.

    Attributes
    ----------
    metric : nn_matching.NearestNeighborDistanceMetric
        The distance metric used for measurement to track association.
    max_age : int
        Maximum number of missed misses before a track is deleted.
    n_init : int
        Number of frames that a track remains in initialization phase.
    kf : kalman_filter.KalmanFilter
        A Kalman filter to filter target trajectories in image space.
    tracks : List[Track]
        The list of active tracks at the current time step.

    """


    #方法种类有
    #predict
    #update 依照match的结果进行更新
    #_match 在此处应用匈牙利算法，需要代价矩阵，在deep_sort_app.py中用的是余弦距离

    def __init__(self, metric, shape =(640,640),max_iou_distance=1.6, max_age=15, n_init=6):
        self.metric = metric
        self.max_iou_distance = max_iou_distance
        self.max_age = max_age
        self.n_init = n_init
        self.shape = shape
        ##上为参数
        ##
        ##下为类实例的属性
        self.kf = kalman_filter.KalmanFilter()#一个卡尔曼滤波器
        self.tracks = []#所有轨迹所在的list
        self._next_id = 1 #暂时不知道是啥

        self._next_confirmed_id = 1 #虫子id

        self.bugs_in = [0, 0, 0, 0, 0]
        self.bugs_out = [0, 0, 0, 0, 0]

    def predict(self):
        """Propagate track state distributions one time step forward.

        This function should be called once every time step, before `update`.
        """
        for track in self.tracks:#单次预测：对每一个track使用现有kf预测
            track.predict(self.kf)

    def update(self, detections):
        """Perform measurement update and track management.

        Parameters
        ----------
        detections : List[deep_sort.detection.Detection]
            A list of detections at the current time step.

        """
        # Run matching cascade.
        # 匹配上的，未匹配的跟踪框，未匹配的检测框
        matches, unmatched_tracks, unmatched_detections = \
            self._match(detections)

        # Update track set.
        # 匹配上的 更新
        for track_idx, detection_idx in matches:
            if self.tracks[track_idx].update(self.kf, detections[detection_idx],self._next_confirmed_id):
                self._next_confirmed_id += 1
        # 跟踪框未匹配上的，标记为失踪
        for track_idx in unmatched_tracks:
            ret = self.tracks[track_idx].mark_missed()
            if ret != 0:
                bug_class = self.tracks[track_idx].bug_class
                if ret == 1:
                    self.bugs_in[bug_class] += 1
                elif ret == -1:
                    self.bugs_out[bug_class] += 1

        # 检测框未匹配上的，就新建
        for detection_idx in unmatched_detections:
            self._initiate_track(detections[detection_idx])
        self.tracks = [t for t in self.tracks if not t.is_deleted()]

        # Update distance metric.
        active_targets = [t.track_id for t in self.tracks if t.is_confirmed()]
        features, targets = [], []
        for track in self.tracks:
            if not track.is_confirmed():
                continue
            features += track.features
            targets += [track.track_id for _ in track.features]
            track.features = []
        self.metric.partial_fit(
            np.asarray(features), np.asarray(targets), active_targets)

    def _match(self, detections):  # detections为当前检测到的所有目标
        # 匹配的过程就是计算当前检测到的目标和已保存的特征集之间的余弦距离矩阵
        def gated_metric(tracks, dets, track_indices, detection_indices):
            features = np.array([dets[i].feature for i in detection_indices])
            targets = np.array([tracks[i].track_id for i in track_indices])
            cost_matrix = self.metric.distance(features, targets)  # 这里计算的是外观相似度，基于两者之间的128维特征，用余弦距离计算
            cost_matrix = linear_assignment.gate_cost_matrix(
                self.kf, cost_matrix, tracks, dets, track_indices,
                detection_indices)

            return cost_matrix

        # Split track set into confirmed and unconfirmed tracks.
        confirmed_tracks = [
            i for i, t in enumerate(self.tracks) if t.is_confirmed()]
        unconfirmed_tracks = [
            i for i, t in enumerate(self.tracks) if not t.is_confirmed()]

        # Associate confirmed tracks using appearance features.
        matches_a, unmatched_tracks_a, unmatched_detections = \
            linear_assignment.matching_cascade(
                gated_metric, self.metric.matching_threshold, self.max_age,
                self.tracks, detections, confirmed_tracks)

        # Associate remaining tracks together with unconfirmed tracks using IOU.
        iou_track_candidates = unconfirmed_tracks + [
            k for k in unmatched_tracks_a if
            self.tracks[k].time_since_update == 1]
        unmatched_tracks_a = [
            k for k in unmatched_tracks_a if
            self.tracks[k].time_since_update != 1]
        matches_b, unmatched_tracks_b, unmatched_detections = \
            linear_assignment.min_cost_matching(
                iou_matching.iou_cost, self.max_iou_distance, self.tracks,
                detections, iou_track_candidates, unmatched_detections)

        matches = matches_a + matches_b
        unmatched_tracks = list(set(unmatched_tracks_a + unmatched_tracks_b))
        return matches, unmatched_tracks, unmatched_detections

    def _initiate_track(self, detection):
        mean, covariance = self.kf.initiate(detection.to_xyah())
        self.tracks.append(Track(
            mean, covariance, self._next_id, self.n_init, self.max_age,
            detection.feature,detection.bug_class))
        self._next_id += 1
