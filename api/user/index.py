import sys
import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_PATH + "\\tool")
import DBConnect, phoneClass, Token
import logging, socket, time, json, random, base64, hmac, hashlib, redis,datetime
from flask import Blueprint, request, jsonify

dblogPath = os.path.dirname(DBConnect.__file__)
db = DBConnect.DBConnect("localhost", "root", "", "happy", dblogPath)
r = redis.StrictRedis(host="localhost", port=6379, db=0)
tokens = Token.Token()


# @author dong.sun
# 检查该手机号是否注册 在注册接口使用
# @return Boolean
def checkIsRegister(phone):
    try:
        isRegister = db.exce_data_one("select * from user where U_phone = '%s'" % phone)
        if isRegister != None:
            return True
        else:
            return False
    except Exception as data:
        logging.error("This is checkIsRegister function:%s____%s" % (Exception, data))


# @author dong.sun
# 密码加密 在注册接口使用
# @return String 返回加密后的密码 
def PWEncryption(password):
    enStr = hashlib.md5()
    enStr.update(password.encode("utf-8"))
    return enStr.hexdigest()

# @author dong.sun
# 获取当前时间 在注册接口使用
# @param type = 0 拼接id格式  type = 1 插入数据库格式
# @return string
def getNow(type):
    if type == 0:
        now_time = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
        return now_time
    elif type == 1:
        return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# @author dong.sun
# 登陆之后，修改用户最后登陆时间
# @param phone 用户手机号
# @return
def updateLastLoginTime(phone):
    lastLoginTime = getNow(1)
    sql = "update user set U_lastLoginTime = '%s' where U_phone = '%s'"%(lastLoginTime,phone)
    db.exce_data_commitsql(sql)

user = Blueprint("user", __name__)
# 登陆接口
@user.route("/login", methods=["POST"])
def login():
    try:
        res = request.get_json()
        if res["type"] == "pass":
            userPhone = res["userPhone"]
            password = res["password"]
            DBpassword = db.exce_data_one(
                "select U_password from user where U_phone = '%s'" % userPhone
            )[0]
            if PWEncryption(password) == DBpassword:
                token = tokens.generateToken(userPhone)
                updateLastLoginTime(userPhone)
                userId = db.exce_data_one("select U_id from user where U_phone ='%s'"%userPhone)[0]
                return jsonify(
                    {
                        "status": 200,
                        "message": "登陆成功",
                        "type": "success",
                        "data": {"token": token, "userPhone": userPhone,"userId":userId},
                    }
                )
            else:
                return jsonify({"status": 1001, "message": "密码错误", "type": "error"})
        elif res["type"] == "code":
            userPhone = res["userPhone"]
            messageCode = res["messageCode"]
            if r.exists(userPhone) == 1:
                MessageCode = r.get(userPhone)
                if str(MessageCode, "utf-8") == messageCode:
                    token = tokens.generateToken(userPhone)
                    updateLastLoginTime(userPhone)
                    return jsonify(
                        {
                            "status": 200,
                            "message": "登陆成功",
                            "type": "success",
                            "data": {"token": token, "userPhone": userPhone},
                        }
                    )
                else:
                    return jsonify(
                        {"status": 1002, "message": "验证码错误", "type": "error"}
                    )
            else:
                return jsonify({"status": 1003, "message": "验证码已过期", "type": "error"})
    except Exception as data:
        logging.error(
            "USER----This error from Login function:%s______%s" % (Exception, data)
        )
        return jsonify({"status": 5002, "message": "登陆失败", "type": "error"})


# 注册接口
@user.route("/register", methods=["POST"])
def register():
    try:
        res = request.get_json()
        userPhone = res["userPhone"]
        if checkIsRegister(userPhone):
            return jsonify({"status": 2001, "message": "该手机号已经被注册，可通过验证码登陆", "type": "success"})
        else:
            # 如果没被注册
            userName = res["userName"]
            password = PWEncryption(res["password"])
            mailbox = res["mailbox"]
            portrait = res["protrait"]
            userPhone = res["userPhone"]
            birthday = res["birthday"]
            time = getNow(1)
            userId = getNow(0)+PWEncryption(userPhone)
            sql = (
                "insert into user (U_id,U_name,U_password,U_mailbox,U_portrait,U_birthday,U_phone,U_registerTime,U_lastLoginTime) values ('%s','%s','%s','%s','%s','%s','%s','%s','%s')"
                %(userId,userName,password,mailbox,portrait,birthday,userPhone,time,time)
            )
            result = db.exce_data_commitsql(sql)
            return jsonify({"status": 200, "message": "注册成功", "type": result})
    except Exception as data:
        logging.error(
            "USER----This error from register function:%s______%s" % (Exception, data)
        )
        return jsonify({"status": 5001, "message": "注册失败", "type": "error"})


# 获取短信验证码
@user.route("/sendMessage", methods=["POST"])
def getMessage():
    try:
        res = request.get_json()
        phone = res["phone"]
        sendUser = phoneClass.SendPhone(phone)
        Mcode = sendUser.sendLogin()["messageCode"]
        r.set(name=phone, value=Mcode)
        r.expire(phone, 120)  # 该验证码120秒后过期
        return jsonify({"status": 200, "message": "发送成功", "type": "success"})
    except Exception as data:
        logging.error(
            "USER----This error from sendMessage function:%s______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5001, "message": "发送失败", "type": "error"})


# 查看我发布过的文章
@user.route("/getMyArticle", methods=["GET"])
def getMyArticle():
    try:
        # 验证Token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            resultsList = db.exce_data_all(
                "select * from article where U_Phone = '%s'" % phone
            )
            articleList = []
            for data in resultsList:
                articleId = data[0]
                title = data[1]
                portrait = data[3]
                articleList.append(
                    {"articleId": articleId, "title": title, "portrait": portrait}
                )
            return jsonify(
                {
                    "status": 200,
                    "message": "查询成功",
                    "type": "success",
                    "data": {"articleList": articleList},
                }
            )
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as data:
        logging.error(
            "USER------This is error from getMyArticle function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})


# 删除我发布过的某个文章
@user.route("/delMyArticle", methods=["DELETE"])
def delMyArticle():
    try:
        # 验证Token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            res = request.get_json()
            articleIdList = res["articleIdList"]
            for articleId in articleIdList:
                sql = "DELETE FROM article where A_id ='%s' and U_phone ='%s'" % (articleId,phone)
                result = db.exce_data_commitsql(sql)
            return jsonify(
                {"status": 200, "message": "删除成功", "type": "success", "data": result}
            )
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as data:
        logging.error(
            "USER------This is error from delMyArticle function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})



# 查看我发布过的动态
@user.route("/getMyDynamic", methods=["GET"])
def getMyDynamic():
    try:
        # 验证token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            resultsList = db.exce_data_all(
                "select * from dynamic where U_Phone = '%s'" % phone
            )
            dynamicList = []
            myaddr = socket.gethostbyname(socket.gethostname())
            f = open("./log/config.json", encoding="utf-8")
            setting = json.load(f)
            port = setting["port"]
            for data in resultsList:
                dynamicId = data[1]
                time = data[2]
                content = data[3]
                imags = data[4]
                labelList = data[5]
                address = data[6]
                likeCounts = data[7]
                comments = data[8]
                images = imags.split(",")
                imageList = []
                for image in images:
                    imageList.append(myaddr + ":" + str(port) + image)
                labelList = labelList.split(",")
                dynamicList.append(
                    {
                        "dynamicId": dynamicId,
                        "time": time,
                        "content": content,
                        "imageList": imageList,
                        "labelList": labelList,
                        "address": address,
                        "likeCounts": likeCounts,
                        "comments": comments,
                    }
                )
            return jsonify(
                {
                    "status": 200,
                    "message": "请求成功",
                    "type": "success",
                    "data": {"dynamicList": dynamicList},
                }
            )
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as data:
        logging.error(
            "USER------This is error from getMyDynamic function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})


# 删除我发布过的动态
@user.route("/delMyDynamic", methods=["DELETE"])
def delMyDynamic():
    try:
        # 验证token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            res = request.get_json()
            dynamicId = res["dynamicId"]
            sql = "delete from dynamic where D_id = '%s' and U_phone ='%s'" % (dynamicId,phone)
            result = db.exce_data_commitsql(sql)
            return jsonify({"status": 200, "message": "删除成功", "type": result})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as data:
        logging.error(
            "USER------This is error from delMyDynamic function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})
