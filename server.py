import numpy as np
import cv2
from flask import Flask,render_template,Response
from flask_caching import Cache
from ctypes import *
import math
import random
import os
import darknet
import postgresql
import time
import threading

config = {
    "DEBUG": True,          # some Flask specific configs
    "CACHE_TYPE": "simple", # Flask-Caching related configs
    "CACHE_DEFAULT_TIMEOUT": 300
}
app = Flask(__name__)
# tell Flask to use the above defined config
app.config.from_mapping(config)
cache = Cache(app)

netMain = None
metaMain = None
altNames = None

configPath = "./cfg/yolov4.cfg"
weightPath = "./yolov4.weights"
metaPath = "./cfg/coco.data"

netMain = darknet.load_net_custom(configPath.encode(
            "ascii"), weightPath.encode("ascii"), 0, 1)
metaMain = darknet.load_meta(metaPath.encode("ascii"))

darknet_image = darknet.make_image(darknet.network_width(netMain),
    darknet.network_height(netMain),3)


#从数据库获取需要关注的对象
lists= postgresql.operate_postgre_tbl_product("select object_name from follow_list")
print (lists)
print('=====================================================================================')

class MyThread(threading.Thread):
    def __init__(self, func, args, name=''):
        threading.Thread.__init__(self)
        self.name = name
        self.func = func
        self.args = args
        self.result = self.func(*self.args)
 
    def get_result(self):
        try:
            return self.result
        except Exception:
            return None

def is_follow_target(find_object):
    for ob in lists:
        if(ob['object_name']==find_object):
            return True
    return False

def need_save(find_object):
    if(not is_follow_target(find_object)): 
        return False
    data=time.strftime('%Y-%m-%d %H',time.localtime(time.time()))
    list_real_time=postgresql.operate_postgre_tbl_product("select target_name from target_information where time like %s and target_name=%s"%("'"+data+"%'","'"+find_object+"'"))
    if(list_real_time==None or len(list_real_time)==0):
        return True
    return False
def get_id():
    max_id=postgresql.operate_postgre_tbl_product("select max(tid) from target_information")
    if(max_id[0]['max']==None):
        return 1
    return max_id[0]['max']+1

def deal_object(find_object):
    if(need_save(find_object)):
        tid="'"+str(get_id())+"'"
        targetName="'"+find_object+"'"
        data="'"+time.strftime('%Y-%m-%d %H-%M-%S',time.localtime(time.time()))+"'"
        print(data)
        postgresql.operate_set("insert into target_information (tid,target_name,time) values (%s,%s,%s)"%(tid,targetName,data))

def convertBack(x, y, w, h):
    xmin = int(round(x - (w / 2)))
    xmax = int(round(x + (w / 2)))
    ymin = int(round(y - (h / 2)))
    ymax = int(round(y + (h / 2)))
    return xmin, ymin, xmax, ymax


def cvDrawBoxes(detections, img):
    for detection in detections:
        print('======================1======================')
        x, y, w, h = detection[2][0],\
            detection[2][1],\
            detection[2][2],\
            detection[2][3]
        xmin, ymin, xmax, ymax = convertBack(
            float(x), float(y), float(w), float(h))
        pt1 = (xmin, ymin)
        pt2 = (xmax, ymax)
        cv2.rectangle(img, pt1, pt2, (0, 255, 0), 1)
        cv2.putText(img,
                    detection[0].decode() +
                    " [" + str(round(detection[1] * 100, 2)) + "]",
                    (pt1[0], pt1[1] - 5), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                    [0, 255, 0], 2)
    
        find_object=detection[0].decode()
        deal_object(find_object)
        print('=======================%s====================='%(find_object))
    return img

def get_img(frame_read):
    frame_rgb = cv2.cvtColor(frame_read, cv2.COLOR_BGR2RGB)
    frame_resized = cv2.resize(frame_rgb,
                                (darknet.network_width(netMain),
                                darknet.network_height(netMain)),
                                interpolation=cv2.INTER_LINEAR)

    darknet.copy_image_from_bytes(darknet_image,frame_resized.tobytes())

    detections = darknet.detect_image(netMain, metaMain, darknet_image, thresh=0.25)
    image = cvDrawBoxes(detections, frame_resized)
    print("get_iamging")
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    return image


def get_img_thread(frame_read):
    get=False
    while not get:
        frame_rgb = cv2.cvtColor(frame_read, cv2.COLOR_BGR2RGB)
        frame_resized = cv2.resize(frame_rgb,
                                    (darknet.network_width(netMain),
                                    darknet.network_height(netMain)),
                                    interpolation=cv2.INTER_LINEAR)

        darknet.copy_image_from_bytes(darknet_image,frame_resized.tobytes())

        detections = darknet.detect_image(netMain, metaMain, darknet_image, thresh=0.25)
        image = cvDrawBoxes(detections, frame_resized)
        image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        print("get_iamging")
        get=True
    return image



with open(metaPath) as metaFH:
    metaContents = metaFH.read()
    import re
    match = re.search("names *= *(.*)$", metaContents,
                        re.IGNORECASE | re.MULTILINE)
    if match:
        result = match.group(1)
    else:
        result = None

    if os.path.exists(result):
        with open(result) as namesFH:
            namesList = namesFH.read().strip().split("\n")
            altNames = [x.strip() for x in namesList]

class VideoCamera(object):
   
    def __init__(self,enable_detect,way,index):
        # 通过opencv获取实时视频流
        path='rtsp://admin:abc12345@192.168.0.5:554/Streaming/Channels/'+index
        if(way=='main'):
            path+='01'
        else:
            path+='02'
        
        self.video = cv2.VideoCapture(path) 
        self.enable_detect=enable_detect
        #self.out=cv2.VideoWriter('./static/out.avi', cv2.VideoWriter_fourcc(*'XVID'), 5, (608, 608))
        #self.video = cv2.VideoCapture(0)
    def __del__(self):
        self.video.release()
    
    
    def get_frame(self):
        #global image
        success, image = self.video.read()
        success, image = self.video.read()
        success, image = self.video.read()
        success, image = self.video.read()
        
        # image = get_img(detection_model, image)
        # 因为opencv读取的图片并非jpeg格式，因此要用motion JPEG模式需要先将图片转码成jpg格式图片
        if(self.enable_detect=='true'):
            image = MyThread(get_img_thread, (image,), get_img_thread.__name__).get_result()
            #image=get_img(image)
        #image = cv2.resize(image, (640, 480))
        #self.out.write(image)
        ret, jpeg = cv2.imencode('.jpg', image)
        
        return jpeg.tobytes()

def gen(camera):
    while True:
        frame = camera.get_frame()
        # 使用generator函数输出视频流， 每次请求输出的content类型是image/jpeg
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

@app.route('/video_feed/<enable_detect>/<way>/<index>')  # 这个地址返回视频流响应
def video_feed(enable_detect,way,index):
    #return "为啥啊，干"
    return Response(gen(VideoCamera(enable_detect,way,index)),
                    mimetype='multipart/x-mixed-replace; boundary=frame')   

@app.route('/1/<test1>/<test2>/<test3>')
def test(test1,test2,test3):
    return test1+test2+test3
if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000, debug=True)