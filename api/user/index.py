import sys
import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_PATH + "\\tool")
import DBConnect
import phoneClass
import Token
import logging
import time
import json
import random
import base64
import hmac
import hashlib
import redis
from flask import Blueprint, request, jsonify

dblogPath = os.path.dirname(DBConnect.__file__)
db = DBConnect.DBConnect("localhost", "root", "", "happy", dblogPath)
r = redis.StrictRedis(host="localhost", port=6379, db=0)
tokens = Token.Token()
# @author dong.sun
# 检查该手机号是否注册
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
# 密码加密
# @return String 返回加密后的密码
def PWEncryption(password):
    enStr = hashlib.md5()
    enStr.update(password.encode("utf-8"))
    return enStr.hexdigest()


# @author dong.sun
# 存储短信验证码
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
                return jsonify(
                    {
                        "status": 200,
                        "message": "登陆成功",
                        "type": "success",
                        "data": {"token": token, "userPhone": userPhone},
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
        return jsonify({"status": 5002, "message": "登陆失败", "type": "error"})


@user.route("/register", methods=["POST"])
def register():
    try:
        req = request.get_json(slient=True)
        phone = req["phone"]
        if checkIsRegister(phone):
            return jsonify(
                {"status": 200, "message": "该手机号已经被注册，可通过验证码登陆", "type": "success"}
            )
        else:
            # 如果没被注册
            userName = req["userName"]
            password = req["password"]
            mailbox = req["mailbox"]
            portrait = req["protrait"]
            registerTime = req["registerTime"]
            birthday = req["birthday"]
            userId = "User" + phone
            result = db.exce_insert_data(
                {
                    "G_id": "2",
                    "U_id": "'%s'" % userId,
                    "U_name": "'%s'" % userName,
                    "U_password": "'%s'" % password,
                    "U_mailbox": "'%s'" % mailbox,
                    "U_portrait": "'%s'" % portrait,
                    "U_birthday": "'%s'" % birthday,
                    "U_phone": "'%s'" % phone,
                    "U_registerTime": "'%s'" % registerTime,
                    "U_lastLoginTime": "'%s'" % registerTime,
                },
                "user",
            )
            if result == "success":
                return jsonify({"status": 200, "message": "注册成功", "type": "success",})
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

