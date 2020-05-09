import sys
import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_PATH + "\\tool")
import DBConnect, phoneClass, Token
import logging, socket, time, json, random, base64, hmac, hashlib, redis, datetime
from flask import Blueprint, request, jsonify

myaddr = socket.gethostbyname(socket.gethostname())
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
    sql = "update user set U_lastLoginTime = '%s' where U_phone = '%s'" % (
        lastLoginTime,
        phone,
    )
    db.exce_data_commitsql(sql)


# @author dong.sun
# 将图片路径拼接成可以获取的图片路径
# @return string
def getLocalImageUrl(imageName):
    f = open("./log/config.json", encoding="utf-8")
    setting = json.load(f)
    port = setting["port"]
    myaddr = socket.gethostbyname(socket.gethostname())
    imageUrl = "http://%s:%s/static/storeImage/%s" % (myaddr, port, imageName)
    return imageUrl


# @author dong.sun
# 将从数据库取出的数据转换成数组并且拼接成可以获取的图片路径
# @return list
def changeImageList(imgStr):
    if imgStr == "":
        return []
    else:
        imageList = imgStr.split(",")
        imagesList = []
        for img in imageList:
            imagesList.append(getLocalImageUrl(img))
        return imagesList


# @author dong.sun
# 根据用户手机号获取用户头像，姓名，注册时间，发布文章
def getUserInfoOfMyVue(userPhone):
    userInfoSql = db.exce_data_one(
        "select U_name,U_portrait,U_registerTime from user where U_phone = '%s'"
        % userPhone
    )
    userInfo = {
        "name": userInfoSql[0],
        "avatar": userInfoSql[1],
        "register_time": userInfoSql[2],
    }
    gameInfoSql = db.exce_data_one(
        "select U_attention_games from userattentions where U_phone = '%s'" % userPhone
    )[0]
    if gameInfoSql == "" or gameInfoSql == None:
        gameList = []
    else:
        gameList = gameInfoSql.split(",")
    dynamicInfoSql = db.exce_data_one(
        "select count(*) from dynamic where U_phone = '%s'" % userPhone
    )[0]
    articleInfoSql = db.exce_data_one(
        "select count(*) from article where U_phone = '%s'" % userPhone
    )[0]
    return {
        "userInfo": userInfo,
        "gameLength": len(gameList),
        "dynamicLength": dynamicInfoSql,
        "articleLength": articleInfoSql,
    }


# @author dong.sun
# 根据游戏id获取游戏属性
# @return string
def getGameList(gid):
    results = db.exce_data_one("select * from game where G_id = '%s'" % gid)
    return {
        "name": results[0],
        "id": results[1],
        "portrait": results[2],
        "type": results[4],
        "describe": results[5],
    }


# @author dong.sun
# base64转换图片存在存储区
# @return string 在修改头像中使用
def base64ToStorePhoto(fileName, fileBase):
    imgdata = base64.b64decode(fileBase)
    file = open("./static/storeImage/" + fileName, "wb")
    file.write(imgdata)
    file.close()
    return fileName


user = Blueprint("user", __name__)
# 登陆接口
@user.route("/login", methods=["POST"])
def login():
    try:
        res = request.get_json()
        print(res)
        if res["type"] == "pass":
            userPhone = res["userPhone"]
            password = res["password"]
            DBpassword = db.exce_data_one(
                "select U_password from user where U_phone = '%s'" % userPhone
            )[0]
            if PWEncryption(password) == DBpassword:
                token = tokens.generateToken(userPhone)
                updateLastLoginTime(userPhone)
                userId = db.exce_data_one(
                    "select U_id from user where U_phone ='%s'" % userPhone
                )[0]
                return jsonify(
                    {
                        "status": 200,
                        "message": "登陆成功",
                        "type": "success",
                        "data": {
                            "token": token,
                            "userPhone": userPhone,
                            "userId": userId,
                        },
                    }
                )
            else:
                return jsonify({"status": 1001, "message": "密码错误", "type": "error"})
        elif res["type"] == "code":
            print('dddd')
            userPhone = res["userPhone"]
            messageCode = res["messageCode"]
            print(userPhone,messageCode)
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
        print(data)
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
            return jsonify(
                {"status": 2001, "message": "该手机号已经被注册，可通过验证码登陆", "type": "success"}
            )
        else:
            # 如果没被注册
            userName = res["userName"]
            password = PWEncryption(res["password"])
            mailbox = res["mailbox"]
            portrait = res["protrait"]
            userPhone = res["userPhone"]
            birthday = res["birthday"]
            time = getNow(1)
            userId = getNow(0) + PWEncryption(userPhone)
            sql = (
                "insert into user (U_id,U_name,U_password,U_mailbox,U_portrait,U_birthday,U_phone,U_registerTime,U_lastLoginTime) values ('%s','%s','%s','%s','%s','%s','%s','%s','%s')"
                % (
                    userId,
                    userName,
                    password,
                    mailbox,
                    portrait,
                    birthday,
                    userPhone,
                    time,
                    time,
                )
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


# 获取用户信息 ，包括头像，姓名 ，注册时间，关注游戏数目，发布动态数目，发布文章数目
@user.route("/getUserInfo", methods=["GET"])
def getUserInfo():
    try:
        # isUser = request.args.get("isUser")
        userPhone = request.args.get("userPhone")
        userId = request.args.get("userId")
        if userId != "":
            userPhone = db.exce_data_one(
                "select U_phone from user where U_id = '%s'" % userId
            )[0]
        result = getUserInfoOfMyVue(userPhone)
        return jsonify(
            {"status": 200, "message": "发送成功", "type": "success", "data": result}
        )
    except Exception as err:
        print(err)
        logging.error(
            "USER----This error from getUserInfo function:%s______%s" % (Exception, err)
        )
        return jsonify({"status": 5001, "message": "发送失败", "type": "error"})



# 查看我发布过的动态
@user.route("/getUserDynamic", methods=["GET"])
def getUserDynamic():
    try:
        userId = request.args.get("userId")
        userPhone = db.exce_data_one(
            "select U_phone from user where U_id = '%s'" % userId
        )[0]
        resultsList = db.exce_data_all(
            "select * from dynamic where U_Phone = '%s'" % userPhone
        )
        dynamicList = []
        for data in resultsList:
            dynamicId = data[1]
            time = data[2]
            content = data[3]
            labelList = data[5]
            address = data[6]
            likeCounts = data[7]
            comments = data[8]
            labelList = labelList.split(",")
            dynamicList.append(
                {
                    "dynamicId": dynamicId,
                    "time": time,
                    "content": content,
                    "imageList": changeImageList(data[4]),
                    "labelList": labelList,
                    "address": address,
                    "likeCounts": likeCounts,
                    "comments": comments,
                    "status":False
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
    except Exception as err:
        print(err)
        logging.error(
            "USER------This is error from getUserDynamic function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})


# 删除我发布过的某个文章
@user.route("/delUserArticle", methods=["DELETE","POST"])
def delUserArticle():
    try:
        # 验证Token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            res = request.get_json()
            articleId = res["articleId"]
            sql = "DELETE FROM article where A_id ='%s' and U_phone ='%s'" % (
                articleId,
                phone,
            )
            result = db.exce_data_commitsql(sql)
            return jsonify(
                {"status": 200, "message": "删除成功", "type": "success", "data": result}
            )
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as err:
        print(err)
        logging.error(
            "USER------This is error from delUserArticle function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})


# 查看用户关注的游戏社区
@user.route("/getUserGames", methods=["GET"])
def getUserGames():
    try:
        # 主要内容
        userId = request.args.get("userId")
        userPhone = db.exce_data_one(
            "select U_phone from user where U_id = '%s'" % userId
        )[0]
        results = db.exce_data_one(
            "select U_attention_games from userattentions where U_phone='%s'"
            % userPhone
        )[0]
        print(results)
        if results == "" or results == None:
            gameList = []
        else:
            gamestr = results.split(",")
            gameList = []
            for i in gamestr:
                gameList.append(getGameList(i))
        return jsonify(
            {
                "status": 200,
                "message": "查询成功",
                "type": "success",
                "data": {"gameList": gameList},
            }
        )
    except Exception as err:
        print(err)
        logging.error(
            "USER------This is error from getUserGames function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})


# 查看用户发布的所有文章
@user.route("/getUserArticles", methods=["GET"])
def getUserArticles():
    try:
        # 主要内容
        userId = request.args.get("userId")
        userPhone = db.exce_data_one(
            "select U_phone from user where U_id = '%s'" % userId
        )[0]
        results = db.exce_data_all(
            "select * from article where U_phone='%s'" % userPhone
        )
        if results == "" or results == None:
            articleList = []
        else:
            articleList = []
            for data in results:
                articleId = data[0]
                title = data[1]
                portrait = changeImageList(data[3])
                type = data[4]
                articleList.append(
                    {
                        "articleId": articleId,
                        "title": title,
                        "portrait": portrait,
                        "type": type,
                    }
                )
        return jsonify(
            {
                "status": 200,
                "message": "查询成功",
                "type": "success",
                "data": {"articleList": articleList},
            }
        )
    except Exception as err:
        print(err)
        logging.error(
            "USER------This is error from getUserGames function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})


# 删除我发布过的某个动态
@user.route("/delUserDynamic", methods=["DELETE","POST"])
def delUserDynamic():
    try:
        # 验证Token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            res = request.get_json()
            dynamicId = res["dynamicId"]
            sql = "DELETE FROM dynamic where D_id ='%s' and U_phone ='%s'" % (
                dynamicId,
                phone,
            )
            result = db.exce_data_commitsql(sql)
            result = []
            return jsonify(
                {"status": 200, "message": "删除成功", "type": "success", "data": result}
            )
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as err:
        print(err)
        logging.error(
            "USER------This is error from delUserArticle function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})


# 修改用户昵称
@user.route("/updateUserName", methods=["PUT"])
def updateUserName():
    try:
        # 验证token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            res = request.get_json()
            nickName = res["nickName"]
            updateSql = "update user set U_name = '%s' where U_phone = '%s'" % (
                nickName,
                phone,
            )
            result = db.exce_data_commitsql(updateSql)
            return jsonify({"status": 200, "message": "修改成功", "type": result})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as err:
        print(err)
        logging.error(
            "USER------This is error from updateUserName function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})


# 修改头像
@user.route("/updateUserAvatar", methods=["PUT"])
def updateUserAvatar():
    try:
        # 验证token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            res = request.get_json()
            fileName = res["fileName"]
            fileBase = res["fileBase"]
            imageName = base64ToStorePhoto(fileName, fileBase)
            f = open("./log/config.json", encoding="utf-8")
            settingg = json.load(f)
            port = settingg["port"]
            imageUrl = "http://%s:%s/static/storeImage/%s" % (myaddr, port, imageName)
            updateSql = "update user set U_portrait = '%s' where U_phone = '%s'" % (
                imageUrl,
                phone,
            )
            result = db.exce_data_commitsql(updateSql)
            return jsonify(
                {
                    "status": 200,
                    "message": "修改成功",
                    "type": "success",
                    "data": {"imageUrl": imageUrl, "result": result},
                }
            )
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as err:
        print(err)
        logging.error(
            "USER------This is error from updateUserName function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})
