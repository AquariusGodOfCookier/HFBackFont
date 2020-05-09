import sys
import os
import re
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_PATH + "\\tool")
import DBConnect, Token
import random
import string
import numpy as np
import logging, socket, time, json, random, base64, hmac, hashlib, redis,datetime
from flask import Blueprint, request, jsonify
dblogPath = os.path.dirname(DBConnect.__file__)
db = DBConnect.DBConnect("localhost", "root", "", "happy", dblogPath)
r = redis.StrictRedis(host="localhost", port=6379, db=0)
tokens = Token.Token()
myaddr = socket.gethostbyname(socket.gethostname())
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
    sql = "select U_id,U_name,U_portrait from user where U_phone = %s"%userPhone
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
# 将图片路径拼接成可以获取的图片路径
# @return string
def getLocalImageUrl(imageName):
    f = open("./log/config.json",encoding='utf-8')
    setting = json.load(f)
    port = setting['port']
    myaddr = socket.gethostbyname(socket.gethostname())
    imageUrl = "http://%s:%s/static/storeImage/%s"%(myaddr,port,imageName)
    return imageUrl

# @author dong.sun
# 将从数据库取出的数据转换成数组并且拼接成可以获取的图片路径
# @return list
def changeImageList(imgStr):
    if imgStr == '':
        return []
    else:
        imageList = imgStr.split(',')
        imagesList = []
        for img in imageList:
            imagesList.append(getLocalImageUrl(img))
        return imagesList

# @author dong.sun
# 判断该游戏是否已经被用户关注
# @return Boolean
def judgeIsAttention(lists, ids):
    arr = np.array(lists)
    status = (arr == ids).any()
    return True if status == 1 else False

# @author dong.sun
# 将手机号加密
# @return string
def encryPhone(phone):
    if re.match(r"1[35678]\d{9}$",phone):
        return phone[0:3]+'****'+phone[7:11]
    else:
        return 'error'

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
            pageSize = 4
            userAttentions = db.exce_data_one("select U_attention_dynamics from userattentions where U_phone = '%s'"%phone)[0]
            pageCounts = 0 + (pageIndex - 1) * pageSize
            if userAttentions =='' or userAttentions == None:
                sql = "select * from dynamic as a where 1>(select count(*) from dynamic where U_phone=a.U_phone and D_time>a.D_time) and U_phone <> %s ORDER BY D_time desc limit %d,%d"%(phone,pageCounts,pageSize)                
            else:
                sql = "select * from dynamic as a where 1>(select count(*) from dynamic where U_phone=a.U_phone and D_time>a.D_time) and U_phone <> %s and U_phone not in (%s) ORDER BY D_time desc limit %d,%d"%(userAttentions,phone,pageCounts,pageSize)                
            recommendList = db.exce_data_all(sql)
            resultData = []
            for data in recommendList:
                userPhone = data[0]
                userInfoList = getUserInfoByPhone(userPhone)
                # 发布该动态的用户信息
                userInfo = {
                    "userId":userInfoList[0],
                    "userName":userInfoList[1],
                    "userPortrait":userInfoList[2],
                    "status":judgeIsAttention(userAttentions,userPhone)
                }
                # # 该动态信息
                dynamicList = {
                    "dynamicId":data[1],
                    "pushTime":data[2],
                    "content":data[3],
                    "imageList":changeImageList(data[4]),
                    "labelList":[] if data[5]=='' else data[5].split(','),
                    "address":data[6],
                    "likeCounts":data[7],
                    "comments":data[8],
                    "status":judgeIsLike(data[1],phone)
                }
                resultData.append({
                    "userInfo":userInfo,
                    "dynamicList":dynamicList
                })
            return jsonify({
                "status":200,
                "message":"查询成功",
                "type":"success",
                "resultData": resultData
            })
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as err:
        print(err)
        logging.error(
            "SQUARE------This is error from getRecommend function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5001, "message": "发生了某些意料之外的错误", "type": "error"})


# 广场页查看关注接口
@square.route("/getFollow",methods=["GET"])
def getFollow():
    try:
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone,token):
            pageIndex = int(request.args.get("pageIndex"))
            results = db.exce_data_one("select U_attention_dynamics from userattentions where U_phone = '%s'"%phone)[0]
            if results == '' or results == None:
                return jsonify({"status": 200, "message": "您暂时还没有关注任何人", "type": "success"})
            else:
                followList = getDBLimit("select * from dynamic where U_phone in (%s) order by D_time DESC"%results,pageIndex,4)
                resultData = []
                for data in followList:
                    userPhone = data[0]
                    userInfoList = getUserInfoByPhone(userPhone)
                    # 发布该动态的用户信息
                    userInfo = {
                        "userId":userInfoList[0],
                        "userName":userInfoList[1],
                        "userPortrait":userInfoList[2],
                        "status":True
                    }
                    # 该动态信息
                    dynamicList = {
                        "dynamicId":data[1],
                        "pushTime":data[2],
                        "content":data[3],
                        "imageList":changeImageList(data[4]),
                        "labelList":[] if data[5]=='' else data[5].split(','),
                        "address":data[6],
                        "likeCounts":int(data[7]),
                        "comments":int(data[8]),
                        "status":judgeIsLike(data[1],phone)
                    }
                    resultData.append({
                        "userInfo":userInfo,
                        "dynamicList":dynamicList
                    })
            return jsonify({
                "status":200,
                "message":"查询成功",
                "type":"success",
                "resultData": resultData
            })
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as err:
        print(err)
        logging.error(
            "SQUARE----This error from getLabels function:%s______%s"%(Exception,err)
        )
        return jsonify({
            "status":5001,
            "message":"发生了某些意料以外的错误",
            "type":"error"
        })

# 查看引用该标签的动态接口
@square.route("/getLabelDynamics",methods=["GET"])
def getLabelDynamics():
    try:
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone,token):
            pageIndex = int(request.args.get('pageIndex'))
            labelName = request.args.get('labelName')
            sql = "select * from dynamic where find_in_set('%s',D_span) order by D_time DESC"%labelName
            resultsList = getDBLimit(sql,pageIndex,4)
            userAttentions = db.exce_data_one("select U_attention_dynamics from userattentions where U_phone = '%s'"%phone)[0]
            resultData = []
            for data in resultsList:
                userPhone = data[0]
                userInfoList = getUserInfoByPhone(userPhone)
                # 发布该动态的用户信息
                userInfo = {
                    "userId":userInfoList[0],
                    "userName":userInfoList[1],
                    "userPortrait":userInfoList[2],
                    "status":True if userPhone == phone else judgeIsAttention(userAttentions,userPhone)
                }
                # # 该动态信息
                dynamicList = {
                    "dynamicId":data[1],
                    "pushTime":data[2],
                    "content":data[3],
                    "imageList":changeImageList(data[4]),
                    "labelList":[] if data[5]=='' else data[5].split(','),
                    "address":data[6],
                    "likeCounts":data[7],
                    "comments":data[8],
                    "status":judgeIsLike(data[1],phone)
                }
                resultData.append({
                    "userInfo":userInfo,
                    "dynamicList":dynamicList
                })
            return jsonify({
                "status":200,
                "message":"查询成功",
                "type":"success",
                "resultData": resultData
            })
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as data:
        logging.error(
            "SQUARE----This error from getLabelDynamics function:%s______%s"%(Exception,data)
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
            resultsList = getDBLimit("select Span_title from spanmanage order by DegreeOfHeat DESC",1,10)
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
    except Exception as err:
        print(err)
        logging.error(
            "SQUARE----This error from getHotLabels function:%s______%s"%(Exception,err)
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
    except Exception as err:
        print(err)
        logging.error(
            "SQUARE------This is error from updateLikeDynamic function:%s_______%s"
            % (Exception, err)
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
            commentId = encryPhone(phone)+random.choice(string.ascii_lowercase)+dynamicId
            commentContent = res["commentContent"]
            sqlComment = (
                "insert into comment (Comment_id,Commented_id,U_phone,Comment_time,Comment_content) values('%s','%s','%s','%s','%s')"
                % (commentId, dynamicId, phone, commentTime, commentContent)
            )
            sqlCommentCount = (
                "update dynamic set D_comments = D_comments + 1 where D_id = '%s'"
                %dynamicId
            )
            results = db.exce_data_commitsqls([sqlComment,sqlCommentCount])
            return jsonify({"status": results['status'], "message": results['msg'], "type": results['type']})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as data:
        logging.error(
            "HOME------This is error from addComments function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5001, "message": "发生了某些意料之外的错误", "type": "error"})

# 关注某人接口
@square.route("/saveFollow",methods=["POST"])
def saveFollow():
    try:
        # 验证token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            res = request.get_json()
            userId = res["userId"]
            Ftype = int(res["type"])
            if Ftype == 0:
                get_user_phone = db.exce_data_one("select U_phone from user where U_id = '%s'"%userId)[0]
                get_user_attention_dynamics = db.exce_data_one("select U_attention_dynamics from userattentions where U_phone = '%s'"%phone)[0]
                user_attentions = ''
                if judgeIsAttention(get_user_attention_dynamics.split(','),get_user_phone):
                    return jsonify({"status":200,"message":"该用户已经被关注","type":"info"})
                else:
                    if get_user_attention_dynamics == None or get_user_attention_dynamics == '':
                        user_attentions = get_user_phone
                    else:
                        user_attentions = get_user_attention_dynamics+','+get_user_phone
                    results = db.exce_update_data("update userattentions set U_attention_dynamics = '%s' where U_phone = '%s'"%(user_attentions,phone))
                    return jsonify({"status":200,"message":results['msg'],"type":results['type']})
            elif Ftype == 1:
                get_user_phone = db.exce_data_one("select U_phone from user where U_id = '%s'"%userId)[0]
                get_user_attention_dynamics = db.exce_data_one("select U_attention_dynamics from userattentions where U_phone = '%s'"%phone)[0].split(',')
                get_user_attention_dynamics.remove(get_user_phone)
                if len(get_user_attention_dynamics) == 0:
                    user_attentions = ''
                else:
                    user_attentions = ','.join(get_user_attention_dynamics)
                results = db.exce_update_data("update userattentions set U_attention_dynamics = '%s' where U_phone = '%s'"%(user_attentions,phone))
                return jsonify({"status":200,"message":results['msg'],"type":results['type']})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as err:
        print(err)
        logging.error(
            "HOME------This is error from saveFollow function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5001, "message": "发生了某些意料之外的错误", "type": "error"})

# 查看动态评论接口
@square.route("/getComments",methods=["GET"])
def getComments():
    try:
        # 验证token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            dynamicId = request.args.get('dynamicId')
            sql = "select * from comment where Commented_id = '%s'"%dynamicId
            results = db.exce_data_all(sql)
            try:
                resultsData = []
                for data in results:
                    commentatorInfo = getUserInfoByPhone(data[2])
                    commentator = {
                        "userId":commentatorInfo[0],
                        "userName":commentatorInfo[1],
                        "portrait":commentatorInfo[2]
                    }
                    comment = {
                        "commentId":data[0],
                        "Time":data[3],
                        "LikeCounts":data[4],
                        "Content":data[5]
                    }
                    resultsData.append({
                        "commentator":commentator,
                        "comment":comment
                    })
            except Exception as err:
                resultsData = []
            return jsonify({"status": 200, "message": "查询成功", "type": "success","resultsData":resultsData})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as err:
        print(err)
        logging.error(
            "HOME------This is error from getComments function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5001, "message": "发生了某些意料之外的错误", "type": "error"})

