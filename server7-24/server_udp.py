import json
import cv2 as cv
import numpy as np
import os
from MOTer import MOTer
import pyodbc
import time
import requests
import socket
import select
import queue

send = False
send = True

data = {'result': 'this is a test'}
host = ("192.168.43.192", 8000)

image_list = queue.Queue()
preimage_list = queue.Queue()

moter = MOTer(modelpath='nju.onnx')
tracker = moter.tracker

timer = 0
max_period = 800
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


def InOutjudge(db, cursor, tracker, time, http_socket):
    global timer
    bugs_in = tracker.bugs_in
    bugs_out = tracker.bugs_out
    # 计时器
    if timer % max_time == 0:
        if send:
            insert_on_quantityrecord(db, cursor, [1,time,bugs_in[0]+bugs_in[3], bugs_out[0]+bugs_in[3]])
        if timer % max_period == 0:
            tracker.bugs_in[0] = 0
            tracker.bugs_out[0] = 0
            tracker.bugs_in[3] = 0
            tracker.bugs_out[3] = 0
            timer = 0
        if send:
            response = requests.get(url='http://60.204.223.197:8004/quantity?id=1')
            # http_socket.sendto("3".encode(), ('127.0.0.1', 8001))
    # 害虫检测
    # ant
    if tracker.bugs_in[1] + tracker.bugs_out[1] > 3:
        if send:
            response = requests.get(url='http://60.204.223.197:8004/exception?id=1&exceptionId=1')
            # http_socket.sendto("4".encode(), ('127.0.0.1', 8001))
        tracker.bugs_in[1] = 0
        tracker.bugs_out[1] = 0
        print("ANT Warning!")
    # fly
    if tracker.bugs_in[2] + tracker.bugs_out[2] > 3:
        if send:
            response = requests.get(url='http://60.204.223.197:8004/exception?id=1&exceptionId=1')
            # http_socket.sendto("5".encode(), ('127.0.0.1', 8001))
        tracker.bugs_in[2] = 0
        tracker.bugs_out[2] = 0
        print("FLY Warning!")
    # wasp
    if tracker.bugs_in[4] + tracker.bugs_out[4] != 0:
        if send:
            response = requests.get(url='http://60.204.223.197:8004/exception?id=1&exceptionId=1')
            # http_socket.sendto("6".encode(), ('127.0.0.1', 8001))
        tracker.bugs_in[4] = 0
        tracker.bugs_out[4] = 0
        print("WASP Warning!")


def get_cursor():
    db = pyodbc.connect(
        'DRIVER={MySQL ODBC 8.0 ANSI Driver};SERVER=60.204.223.197;DATABASE=beehive;UID=root;PWD=12345678.Fgo'
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

if __name__ == '__main__' :
    PORT = 8000
    address = ("0.0.0.0", PORT)
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    server_socket.bind(address)

    PORT1 = 8888
    address1 = ("0.0.0.0", PORT1)
    http_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    http_socket.bind(address1)

    # picture directory
    if not os.path.exists('save'):
        os.makedirs("save")
    this_time = time.localtime(time.time())
    timedir = time.strftime("%Y-%m-%d-%H-%M-%S", this_time)
    timedirimg = 'save/' + timedir + '_img'
    timedirtrack = 'save/' +timedir + '_track'
    os.makedirs(timedirimg)
    os.makedirs(timedirtrack)
    if send:
        db, cursor = get_cursor()
    else:
        db = None
        cursor = None
    while True:
        r_list, w_list, e_list = select.select([server_socket, ], [], [], 1)  # 监听套接字是否发生状态变化(达到无阻塞效果)
        if len(r_list) > 0:  # 套接字可以读取

            # 获取当前时间
            time_stamp = time.time()
            this_time = time.localtime(time_stamp)
            other_way_time = time.strftime("%Y-%m-%d %H:%M:%S", this_time)


            data, addr = server_socket.recvfrom(65536)
            if len(data)<200:
                jsondata = json.loads(data)
                #  GPS位置信息
                if len(jsondata.keys()) == 2:
                    location = jsondata
                    print(location)
                    if send:
                        update_on_beehives(db, cursor, [1, "POINT(" + str(location["longitude"]) + "," + str(location[
                            "latitude"]) + ")"])
                #  温湿度模块
                elif len(jsondata.keys()) == 3:
                    compo = jsondata
                    print(compo)
                    if send:
                        insert_on_humidityandtemperaturerecord(db, cursor, [1, other_way_time, compo['humidity'],
                            compo['temperature']])
                        insert_on_weightrecord(db, cursor, [1, other_way_time, compo['weight']])
                        response = requests.get(url='http://60.204.223.197:8004/tah?id=1')
                        # http_socket.sendto("1".encode(), ('127.0.0.1', 8001))
                        response = requests.get(url='http://60.204.223.197:8004/weight?id=1')
                        # http_socket.sendto("2".encode(), ('127.0.0.1', 8001))

            #图像处理
            else:
                # 计时器加一
                timer += 1

                image = np.asarray(bytearray(data), dtype="uint8")
                frame = cv.imdecode(image, cv.IMREAD_COLOR)
                # print("frame shape:", frame.shape)
                tframe = moter.frametrack(frame)
                # print(tframe.shape)
                result = cv.resize(tframe, (2 * tframe.shape[0] // 3, 2 * tframe.shape[1] // 3))
                InOutjudge(db, cursor, tracker,  other_way_time, http_socket)
                cv.imshow("window", result)
                cv.imwrite(timedirimg + '/frame' + str(timer) +'.jpg', frame)
                cv.imwrite(timedirtrack + '/frame' + str(timer) + '.jpg', tframe)


            # print("timer", timer)
            if timer % count_time == 0:
                # print(time_stamp - lasttime)
                print("fps:", count_time / ((time_stamp - lasttime)))
                lasttime = time_stamp
            # print(other_way_time)
        if timer != 0:
            key = cv.waitKey(1)
            if key == ord('/'):
                break
    if send:
        close_db(db, cursor)
    server_socket.close()
    cv.destroyAllWindows()


