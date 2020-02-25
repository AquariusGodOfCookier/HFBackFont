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

# @author dong.sun
# 根据前端传来页数，每次发送pageSizes条数据返回前端
# @return sql
def getDBLimit(page, pageSizes):
    pageCounts = 0 + (page - 1) * pageSizes
    return "select * from article limit %d,%d" % (pageCounts, pageSizes)

# @author dong.sun
# 根据用户手机号获取用户,在getRecommend接口使用
# @return String
def getUserName(userPhone):
    userName = db.exce_data_one(
        "select U_name from user where U_phone='%s'" % userPhone
    )
    return userName[0]


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
# 根据文章id获取用户姓名,在getDetails接口使用
# @return String
def articleGetUser(articleId):
    userName = db.exce_data_one(
        "select (select U_name from user where U_phone = article.U_phone  ) U_phone from article where A_id = '%s'"
        % (articleId)
    )
    return userName[0]


# 首页推荐页
# author dong.sun
home = Blueprint("home", __name__)

# 推荐首页展示文章信息接口
# 这里不需要验证是否登陆
@home.route("/getRecommend", methods=["GET"])
def getRecommend():
    try:
        pageIndex = int(request.args.get("pageIndex"))
        requestList = db.exce_data_all(getDBLimit(pageIndex, 10))
        dataList = []
        for data in requestList:
            articleId = data[0]
            title = data[1]
            userPhone = data[2]
            portrait = data[3]
            userName = getUserName(userPhone)
            dataList.append(
                {
                    "articleId": articleId,
                    "title": title,
                    "userPhone": userPhone,
                    "userName": userName,
                    "portrait": portrait,
                }
            )
        return jsonify(
            {
                "status": 200,
                "message": "查询成功",
                "type": "success",
                "data": {"articleList": dataList},
            }
        )
    except Exception as data:
        logging.error(
            "HOME----This error from getRecommend function:%s______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5002, "message": "查询失败", "type": "error"})


# 首页文章详情页,不需要是否验证登陆;如果登陆了则显示点赞状态，没登陆则只显示点赞数量，不显示状态
@home.route("/getDetails", methods=["GET"])
def getDetails():
    try:
        token = ''
        try: 
            # 已经登陆了
            token = request.headers["Token"]
            phone = request.headers["userPhone"]
        except:
            token = ''
            phone = ''
        articleId = request.args.get("articleId")
        # 根据文章id寻找到用户姓名
        userName = articleGetUser(articleId)
        AdbList = db.exce_data_one(
            "select * from articlecontent where A_id = '%s'" % articleId
        )
        content = AdbList[1]
        releaseTime = AdbList[2]
        likeCounts = AdbList[3]
        if token!='' and phone!='':
            # 这里是登录了的,看是否给这个文章点过赞
            statusid = "%s::%s" % (articleId, phone)
            if r.exists(statusid) and str(r.get(statusid), "utf-8") == "1":
                status = True
            else:
                status = False
        else:
            status = False
        return jsonify(
            {
                "status": 200,
                "message": "查询成功",
                "type": "success",
                "data": {
                    "articleId": articleId,
                    "userName": userName,
                    "content": content,
                    "releaseTime": releaseTime,
                    "likeCounts":likeCounts,
                    "status":status
                },
            }
        )
    except Exception as data:
        print(data)
        logging.error(
            "HOME------This is error from getDetails function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5002, "message": "查询失败", "type": "error"})


# 查看该文章的评论内容, 需要验证登陆
@home.route("/getDetailsComments", methods=["GET"])
def getDetailsComments():
    try:
        # 验证Token
        token = request.headers["Token"]
        Phone = request.headers["userPhone"]
        if tokens.verificationToken(Phone, token):
            articleId = request.args.get("articleId")
            pageIndex = int(request.args.get("pageIndex"))
            pageCounts = 0 + (pageIndex - 1) * 10
            resultsList = db.exce_data_all(
                "select * from comment where Commented_id = '%s' limit %d,10"
                % (articleId, pageCounts)
            )
            commentsList = []
            for data in resultsList:
                comment_id = data[0]
                userPhone = data[2]
                userName = getUserName(userPhone)
                commentTime = data[3]
                commentContent = data[5]
                likeCounts = data[4]
                statusid = "%s::%s" % (comment_id, Phone)
                if r.exists(statusid) and str(r.get(statusid), "utf-8") == "1":
                    status = True
                else:
                    status = False
                commentsList.append(
                    {
                        "userPhone": userPhone,
                        "userName": userName,
                        "commentContent": commentContent,
                        "commentTime": commentTime,
                        "likeCounts": likeCounts,
                        "commentsId": comment_id,
                        "status": status,
                    }
                )
            return jsonify(
                {
                    "status": 200,
                    "message": "查询成功",
                    "type": "success",
                    "data": {"commentsList": commentsList},
                }
            )
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as data:
        logging.error(
            "HOME------This is error from getDetailsComments function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5002, "message": "数据库查询失败", "type": "error"})


# 评论点赞接口,需要验证登陆
@home.route("/toLikeComments", methods=["POST"])
def toLikeComments():
    try:
        # 验证Token
        token = request.headers["Token"]
        Phone = request.headers["userPhone"]
        if tokens.verificationToken(Phone, token):
            # 主要内容
            res = request.get_json()
            commentsId = res["commentsId"]
            statusid = "%s::%s" % (commentsId, Phone)
            r.set(name=statusid, value=1)
            db.exce_update_data(
                "update comment set Comment_likeCounts = Comment_likeCounts +1 where Comment_id = '%s'"
                % commentsId
            )
            return jsonify({"status": 200, "message": "点赞成功", "type": "success"})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as data:
        print(data)
        logging.error(
            "HOME------This is error from toLikeComments function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5001, "message": "数据库添加失败", "type": "error"})


# 取消评论点赞接口，需要验证登陆
@home.route("/cancelLikeComments", methods=["post"])
def cancelLikeComments():
    try:
        # 验证Token
        token = request.headers["Token"]
        Phone = request.headers["userPhone"]
        if tokens.verificationToken(Phone, token):
            # 主要内容
            res = request.get_json()
            commentsId = res["commentsId"]
            statusid = "%s::%s" % (commentsId, Phone)
            r.delete(statusid)
            db.exce_update_data(
                "update comment set Comment_likeCounts = Comment_likeCounts -1 where Comment_id = '%s'"
                % commentsId
            )
            return jsonify({"status": 200, "message": "取消点赞成功", "type": "success"})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as data:
        logging.error(
            "HOME------This is error from toLikeComments function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5001, "message": "发生了某些意料以外的错误", "type": "error"})


# 文章评论接口，需要验证登陆
@home.route("/toComments", methods=["POST"])
def toComments():
    try:
        # 验证token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            res = request.get_json()
            articleId = res["articleId"]
            commentTime = getNow(1)
            commentId = "CA" + phone + getNow(0)
            commentContent = res["commentContent"]
            sql = (
                "insert into comment (Comment_id,Commented_id,U_phone,Comment_time,Comment_content) values('%s','%s','%s','%s','%s')"
                % (commentId, articleId, phone, commentTime, commentContent)
            )
            db.exce_data_commitsql(sql)
            return jsonify({"status": 200, "message": "评论成功", "type": "success"})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as data:
        logging.error(
            "HOME------This is error from toComments function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5001, "message": "发生了某些意料之外的错误", "type": "error"})


# 文章点赞接口,需要验证登陆
@home.route("/toLikeArticle",methods=["POST"])
def toLikeArticle():
    try:
        # 验证Token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            # 主要内容
            res = request.get_json()
            articleId = res["articleId"]
            statusid = "%s::%s" % (articleId, phone)
            r.set(name=statusid, value=1)
            db.exce_update_data(
                "update articlecontent set A_likeCounts = A_likeCounts +1 where A_id = '%s'"
                % articleId
            )
            return jsonify({"status": 200, "message": "点赞成功", "type": "success"})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as data:
        logging.error(
            "HOME------This is error from toLikeComments function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5001, "message": "发生了意料以外的错误", "type": "error"})

# 取消文章点赞接口,需要验证登陆
@home.route("/cancelLikeArticle",methods=["POST"])
def cancelLikeArticle():
    try:
        # 验证Token
        token = request.headers["Token"]
        Phone = request.headers["userPhone"]
        if tokens.verificationToken(Phone, token):
            # 主要内容
            res = request.get_json()
            articleId = res["articleId"]
            statusid = "%s::%s" % (articleId, Phone)
            r.delete(statusid)
            db.exce_update_data(
                "update articlecontent set A_likeCounts = A_likeCounts -1 where A_id = '%s'"
                % articleId
            )
            return jsonify({"status": 200, "message": "取消点赞成功", "type": "success"})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as data:
        logging.error(
            "HOME------This is error from toLikeComments function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5001, "message": "发生了某些意料以外的错误", "type": "error"})
