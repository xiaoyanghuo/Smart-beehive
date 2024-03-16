from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import cv2 as cv
import numpy as np
import os
from MOTer import MOTer
import pyodbc
import time
import requests
import socket



data = {'result': 'this is a test'}
host = ("192.168.43.192", 8000)
if os.path.exists("ad.jpg"):
    frame = cv.imread("ad.jpg")
else:
    frame = None


moter = MOTer()
tracker = moter.tracker

timer = 0
max_period = 400
max_time = 10
count_time = 5
lasttime = 0

def insert_tuple(this_db, cursor, table, features, values):
    string = "insert into " + table + "("
    flag = 0
    for f in features:
        if flag == 0:
            flag = 1
        else:
            string = string + ","
        string = string + f
    string = string + ") values ("
    flag = 0
    for v in values:
        if flag == 0:
            flag = 1
        else:
            string = string + ","
        string = string + "?"
    string = string + ");"
    try:
        print(string)
        cursor.execute(string, values)
    except pyodbc.Error as err:
        this_db.rollback()
        print(err)
        return False
    else:
        this_db.commit()
    return True


def update_on_beehives(this_db, cursor, values):
    table = "beehives"
    features = ["id", "location"]
    string = "update " + table + " set "
    string = string + "location = "
    string = string + values[1]
    string = string + " where id = "
    string = string + str(values[0])
    string = string + ";"
    try:
        print(string)
        cursor.execute(string)
    except pyodbc.Error as err:
        this_db.rollback()
        print(err)
        return False
    else:
        this_db.commit()
    return True


def insert_on_humidityandtemperaturerecord(this_db, cursor, values):
    table = "humidityandtemperaturerecord"
    features = ["beehiveId", "upTime", "humidity", "temperature"]
    return insert_tuple(this_db, cursor, table, features, values)

def insert_on_weightrecord(this_db, cursor, values):
    table = "weightrecord"
    features = ["beehiveId", "upTime", "weight"]
    return insert_tuple(this_db, cursor, table, features, values)


def insert_on_quantityrecord(this_db, cursor, values):
    table = "quantityrecord"
    features = ["beehiveId", "upTime", "beeIn", "beeOut"]
    return insert_tuple(this_db, cursor, table, features, values)


def InOutjudge(db, cursor, tracker, time):
    global timer
    bugs_in = tracker.bugs_in
    bugs_out = tracker.bugs_out
    # 计时器
    if timer % max_time == 0:
        insert_on_quantityrecord(db, cursor, [1,time,bugs_in[0]+bugs_in[3], bugs_out[0]+bugs_in[3]])
        if timer % max_period == 0:
            tracker.bugs_in[0] = 0
            tracker.bugs_out[0] = 0
            tracker.bugs_in[3] = 0
            tracker.bugs_out[3] = 0
            timer = 0
        # response = requests.get(url='http://192.168.43.206:8004/quantity?id=1')
    # 害虫检测
    # ant
    if tracker.bugs_in[1] + tracker.bugs_out[1] > 3:
        # response = requests.get(url='http://192.168.43.206:8004/exception?id=1&exceptionId=1')
        tracker.bugs_in[1] = 0
        tracker.bugs_out[1] = 0
    # fly
    if tracker.bugs_in[2] + tracker.bugs_out[2] > 3:
        # response = requests.get(url='http://192.168.43.206:8004/exception?id=1&exceptionId=1')
        tracker.bugs_in[2] = 0
        tracker.bugs_out[2] = 0
    # wasp
    if tracker.bugs_in[4] + tracker.bugs_out[4] != 0:
        # response = requests.get(url='http://192.168.43.206:8004/exception?id=1&exceptionId=1')
        tracker.bugs_in[4] = 0
        tracker.bugs_out[4] = 0



def get_cursor():
    db = pyodbc.connect(
        'DRIVER={MySQL ODBC 8.0 ANSI Driver};SERVER=192.168.43.206;DATABASE=beehive;UID=beehive2;PWD=123'
    )
    # db = pyodbc.connect(
    #         'DRIVER={MySQL ODBC 8.0 ANSI Driver};SERVER=localhost;DATABASE=beehive;UID=root;PWD=021025021025'
    # )
    cursor = db.cursor()
    return db, cursor


def close_db(db, cursor):
    if cursor is not None:
        cursor.close()
    if db is not None:
        db.close()


class Resquest(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode())

    def do_POST(self):
        global frame
        global timer
        global lasttime
        # 获取当前时间
        time_stamp = time.time()
        this_time = time.localtime(time_stamp)
        other_way_time = time.strftime("%Y-%m-%d %H:%M:%S", this_time)
        # 计时器加一
        timer += 1
        print("timer", timer)
        if timer % count_time  == 0:
            print(time_stamp-lasttime)
            print("fps:",count_time/((time_stamp-lasttime)) )
            lasttime = time_stamp
        # print(other_way_time)

        # db, cursor = get_cursor()

        datas = self.rfile.read(int(self.headers['content-length']))
        # print('headers', self.headers)
        # print(self.headers['content-Type'])
        # print("do post:", self.path, self.client_address, datas)
        self.send_response(200)
        self.end_headers()


        # 位置信息获取
        if self.headers['content-Type'] == 'GPS':
            location = json.loads(datas)
            print(location)
            # update_on_beehives(db, cursor, [1, "POINT(" + str(location["longitude"]) + "," + str(location["latitude"]) + ")"])
        # 温湿度及重量获取
        elif self.headers['content-Type'] == 'application/json':
            compo = json.loads(datas)
            print(compo)
            # insert_on_humidityandtemperaturerecord(db, cursor, [1, other_way_time, compo['humidity'], compo['temperature']])
            # insert_on_weightrecord(db, cursor, [1, other_way_time, compo['weight']])
            # response = requests.get(url='http://192.168.43.206:8004/tah?id=1')
            # response = requests.get(url='http://192.168.43.206:8004/weight?id=1')

        # 图像处理并存储
        else:
            image = np.asarray(bytearray(datas), dtype="uint8")
            frame = cv.imdecode(image, cv.IMREAD_COLOR)
            tframe = moter.frametrack(frame)
            # print(tframe.shape)
            tframe = cv.resize(tframe, (2*tframe.shape[0]//3, 2*tframe.shape[1]//3))
            # InOutjudge(db, cursor, tracker,  other_way_time)
            cv.imshow("window", tframe)
            cv.waitKey(1)
            # cv.imwrite("D:\\esp\\work\\server\\ad.jpg",frame)


        # close_db(db, cursor)

if __name__ == '__main__':

    server = HTTPServer(host, Resquest)
    print("Starting server, listen at: %s:%s" % host)
    server.serve_forever()


