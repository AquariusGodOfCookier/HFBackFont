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


# @author dong.sun
# 获取当前时间
# @param type = 0 拼接id格式  type = 1 插入数据库格式
# @return string
def getNow(type):
    if type == 0:
        now_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        return now_time
    elif type == 1:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# @author dong.sun
# 根据前端传来页数，每次发送pageSizes条数据返回前端
# @param sql 拼接的mysql语句，pageIndex页数,pageSizes 每页的查询个数
# @return Array
def getDBLimit(sqls,pageIndex, pageSize):
    pageCounts = 0 + (pageIndex - 1) * pageSize
    sql = sqls+' limit %d,%d'%(pageCounts,pageSize)
    results = db.exce_data_all(sql)
    return results

# @author dong.sun
# 根据用户手机号获取该用户的用户名，头像信息,在广场页推荐接口使用
# @return object
def getUserInfoByPhone(userPhone):
    sql = "select U_name,U_portrait from user where U_phone = %s"%userPhone
    results = db.exce_data_one(sql)
    return results

# @author dong.sun
# 遍历获取文章或者动态的时候，判断该文章/动态是否点过赞,在广场页推荐接口使用
# @return object
def judgeIsLike(ids,phone):
    statusid = "%s::%s" % (ids, phone)
    if r.exists(statusid) and str(r.get(statusid), "utf-8") == "1":
        status = True
    else:
        status = False
    return status

# @author dong.sun
# 添加点赞功能,在各个点赞接口使用
# @return string
def toLike(ids,phone):
    if judgeIsLike(ids,phone):
        # 如果点过赞了
        return 'error'
    else:
        statusid = "%s::%s" % (ids, phone)
        r.set(name=statusid, value=1)
        return 'success'

# @author dong.sun
# 通过标签name判断该标签是否被创建过,在创建标签接口中使用
# @return Boolean
def isHaveThisLabel(labelName):
    sql = "select * from spanmanage where Span_title = '%s'"%labelName
    result = db.exce_data_one(sql)
    if result == None:
        # 如果为空，说明没有创建过，返回false
        return False
    else:
        return True

# 广场页
square = Blueprint("square",__name__)

# 广场页推荐接口
@square.route("/getRecommend",methods=["GET"])
def getRecommend():
    try:
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone,token):
            pageIndex = int(request.args.get("pageIndex"))
            resultsList = getDBLimit("select * from dynamic where U_phone<>%s"%phone,pageIndex,10)
            dynamicList = []
            myaddr = socket.gethostbyname(socket.gethostname())
            f = open("./log/config.json", encoding="utf-8")
            setting = json.load(f)
            port = setting["port"]
            for data in resultsList:
                userPhone = data[0]
                dynamicId = data[1]
                time = data[2]
                content = data[3]
                imags = data[4]
                labelList = data[5]
                address = data[6]
                likeCounts = data[7]
                comments = data[8]
                user = getUserInfoByPhone(userPhone)
                userName = user[0]
                portrait = user[1]
                status = judgeIsLike(dynamicId,phone)
                images = imags.split(",")
                imageList = []
                for image in images:
                    imageList.append(myaddr + ":" + str(port) + image)
                labelList = labelList.split(",")
                dynamicList.append(
                    {
                        "userPhone":userPhone,
                        "dynamicId": dynamicId,
                        "time": time,
                        "userName":userName,
                        "portrait":portrait,
                        "content": content,
                        "imageList": imageList,
                        "labelList": labelList,
                        "address": address,
                        "likeCounts": likeCounts,
                        "comments": comments,
                        "status":status
                    }
                )
            return jsonify({
                "status":200,
                "message":"查询成功",
                "type":"success",
                "data": {"dynamicList": dynamicList},
            })
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as data:
        print(data)
        logging.error(
            "SQUARE------This is error from getRecommend function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5001, "message": "发生了某些意料之外的错误", "type": "error"})

# 创建标签接口
@square.route("/addLabel",methods=["POST"])
def addLabel():
    try:
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone,token):
            res = request.get_json()
            labelName = res["label_name"]
            if isHaveThisLabel(labelName):
                #如果存在这个label
                return jsonify({
                    "status":2002,
                    "message":"该标签已经存在，您可以通过搜索该标签添加",
                    "type":"success"
                })
            else:
                results = db.exce_insert_data({
                    "Span_title":"'%s'"%labelName
                },"spanmanage")
                return jsonify({
                    "status":200,
                    "message":"创建成功",
                    "type":results
                })
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
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
@square.route("/getLabels",methods=["GET"])
def getLabels():
    try:
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone,token):
            pageIndex = int(request.args.get('pageIndex'))
            resultsList = getDBLimit('select * from spanmanage',pageIndex,20)
            labelList = []
            for data in resultsList:
                labelList.append(data[0])
            return jsonify({
                "status":200,
                "message":"查询成功",
                "type":"success",
                "data":{
                    "labelList":labelList
                }
            })
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as data:
        logging.error(
            "SQUARE----This error from getLabels function:%s______%s"%(Exception,data)
        )
        return jsonify({
            "status":5001,
            "message":"创建失败",
            "type":"error"
        })

# 查询标签热度榜
@square.route("/getHotLabels",methods=["GET"])
def getHotLabels():
    try:
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone,token):
            resultsList = getDBLimit('select * from spanmanage order by DegreeOfHeat DESC',1,10)
            labelList = []
            for data in resultsList:
                labelList.append(data[0])
            return jsonify({
                "status":200,
                "message":"查询成功",
                "type":"success",
                "data":{
                    "labelList":labelList
                }
            })
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as data:
        print(data)
        logging.error(
            "SQUARE----This error from getHotLabels function:%s______%s"%(Exception,data)
        )
        return jsonify({
            "status":5001,
            "message":"发生了某些意料以为的错误",
            "type":"error"
        })

# 动态点赞/取消点赞接口
@square.route("/updateLikeDynamic",methods=["PUT"])
def updateLikeDynamic():
    try:
        # 验证Token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            # 主要内容
            res = request.get_json()
            dynamicId = res["dynamicId"]
            likeType = int(res["type"])
            if likeType == 0:
                # 点赞
                toLike(dynamicId,phone)
                db.exce_update_data(
                    "update dynamic set D_likeCounts = D_likeCounts +1 where D_id = '%s'"
                    % dynamicId
                )
                return jsonify({"status": 200, "message": "点赞成功", "type": "success"})
            else:
                statusid = "%s::%s" % (dynamicId, phone)
                r.delete(statusid)
                db.exce_update_data(
                "update dynamic set D_likeCounts = D_likeCounts -1 where D_id = '%s'"
                % dynamicId
                )
                return jsonify({"status": 200, "message": "取消点赞成功", "type": "success"})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as data:
        logging.error(
            "SQUARE------This is error from toLikeDynamic function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5001, "message": "发生了意料以外的错误", "type": "error"})

# 广场动态评论接口
@square.route("/addComments",methods=["POST"])
def addComments():
    try:
        # 验证token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            res = request.get_json()
            dynamicId = res["dynamicId"]
            commentTime = getNow(1)
            commentId = "CA" + phone + getNow(0)
            commentContent = res["commentContent"]
            sqlComment = (
                "insert into comment (Comment_id,Commented_id,U_phone,Comment_time,Comment_content) values('%s','%s','%s','%s','%s')"
                % (commentId, dynamicId, phone, commentTime, commentContent)
            )
            sqlCommentCount = (
                "update dynamic set D_comments = D_comments + 1 where D_id = '%s'"
                %dynamicId
            )
            db.exce_data_commitsqls([sqlComment,sqlCommentCount])
            return jsonify({"status": 200, "message": "评论成功", "type": "success"})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as data:
        logging.error(
            "HOME------This is error from addComments function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5001, "message": "发生了某些意料之外的错误", "type": "error"})