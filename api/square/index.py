import sys
import os
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_PATH + "\\tool")
import DBConnect, Token
import logging, socket, time, json, random, base64, hmac, hashlib, redis,datetime
from flask import Blueprint, request, jsonify
dblogPath = os.path.dirname(DBConnect.__file__)
db = DBConnect.DBConnect("localhost", "root", "", "happy", dblogPath)
r = redis.StrictRedis(host="localhost", port=6379, db=0)
tokens = Token.Token()

# 验证token
def verificationToken(token):
    token_str = base64.urlsafe_b64decode(token).decode('utf-8')
    token_list = token_str.split(':')
    if len(token_list) != 2:
        return False
    ts_str = token_list[0]
    if float(ts_str) < time.time():
        # token expired
        return False
    return True 

# base64转换图片存到缓存区
def base64ToBufferPhoto(fileName,fileBase):
    imgdata = base64.b64decode(fileBase)
    file = open('./static/bufferImage/'+fileName,'wb')
    file.write(imgdata)
    file.close()
    return fileName


# 获取当前时间
def getNow():
    now_time = datetime.datetime.now().strftime('%Y%m%d%H%M%S')
    return now_time

# 根据前端传来页数，每次发送pageSizes条数据返回前端
def getDBLimit(page, pageSizes):
    pageCounts = 0 + (page - 1) * pageSizes
    return "select * from spanmanage limit %d,%d" % (pageCounts, pageSizes)




# 广场页
square = Blueprint("square",__name__)
# 上传图片接口
@square.route("/uploadImage",methods=["POST"])
def uploadImage():
    try:
        res = request.get_json()
        fileName = res["fileName"]
        fileBase = res["fileBase"]
        imageUrl = base64ToBufferPhoto(fileName,fileBase)
        return jsonify({
            "status":200,
            "message":"上传成功",
            "type":"success",
            "data":{
                "imageUrl":imageUrl
            }
        })
    except Exception as data:
        return jsonify({
            "status":20040,
            "message":"上传失败",
            "type":"error"
        })

# 创建标签接口
@square.route("/createLabel",methods=["POST"])
def createLabel():
    try:
        res = request.get_json()
        userId = res["userId"]
        label_name = res["label_name"]
        label_id = 'span'+userId+getNow()
        db.exce_insert_data({
            "Span_id":"'%s'"%label_id,
            "Span_title":"'%s'"%label_name
        },"spanmanage")
        return jsonify({
            "status":200,
            "message":"创建成功",
            "type":"success",
            "data":{}
        })
    except Exception as data:
        logging.error(
            "SQUARE----This error from createLabel function:%s______%s"%(Exception,data)
        )
        return jsonify({
            "status":5001,
            "message":"创建失败",
            "type":"error"
        })

# 查询标签接口
@square.route("/getLabel",methods=["GET"])
def getLabel():
    try:
        pageIndex = int(request.args.get("pageIndex"))
        requestList = db.exce_data_all(getDBLimit(pageIndex,2))
        labelList = []
        for data in requestList:
            label_id = data[0]
            label_name = data[1]
            labelList.append(
                {
                    "label_id":label_id,
                    "label_name":label_name
                }
            )
        return jsonify({
            "status":200,
            "message":"查询成功",
            "type":"success",
            "data":{
                "labelList":labelList
            }
        })
    except Exception as data:
        logging.error(
            'SQUARE----This error from getLabel function:%s______%s'%(Exception,data)
        )
        return jsonify({
            "status":5002,
            "message":"查询失败",
            "type":"error"
        })

# 动态评论接口
@square.route("/toComments",methods=["POST"])
def toComments():
    try:
        res = request.get_json()
        userId = res["userId"]
        commentId = res["commentId"]
        commentTime = res["commentTime"]
        commentContent = res["commentContent"]
        
        return jsonify({
            "status":200,
            "message":"评论成功",
            "type":"success",
            "data":{}
        })
    except Exception as data:
        logging.error(
            'SQUARE----This error from toComments function:%s______%s'%(Exception,data)
        )
        return jsonify({
            "status":5001,
            "message":"评论失败",
            "type":"error"
        })