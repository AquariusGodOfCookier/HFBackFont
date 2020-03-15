import sys
import os
import re

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_PATH + "\\tool")
import Token, DBConnect
import random
import string
import numpy as np
import logging, socket, time, json, random, base64, hmac, hashlib, redis, datetime
from flask import Blueprint, request, jsonify

dblogPath = os.path.dirname(DBConnect.__file__)
db = DBConnect.DBConnect("localhost", "root", "", "happy", dblogPath)
r = redis.StrictRedis(host="localhost", port=6379, db=0)
tokens = Token.Token()
myaddr = socket.gethostbyname(socket.gethostname())
# 验证token
def verificationToken(token):
    token_str = base64.urlsafe_b64decode(token).decode("utf-8")
    token_list = token_str.split(":")
    if len(token_list) != 2:
        return False
    ts_str = token_list[0]
    if float(ts_str) < time.time():
        # token expired
        return False
    return True


# 消息页面
chat = Blueprint("chat", __name__)

# 查看动态评论接口
@chat.route("/getUserInfo", methods=["GET"])
def getUserInfo():
    try:
        # 验证token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            my_userId = request.args.get("my_userId")
            to_userId = request.args.get("to_userId")
            sqlMyUser = db.exce_data_one(
                "select U_name,U_portrait from user where U_id = '%s'" % my_userId
            )
            sqlToUser = db.exce_data_one(
                "select U_name,U_portrait from user where U_id = '%s'" % to_userId
            )
            resultsData = {
                "myName": sqlMyUser[0],
                "myPortrait": sqlMyUser[1],
                "toName": sqlToUser[0],
                "toPortrait": sqlToUser[1],
            }
            return jsonify(
                {
                    "status": 200,
                    "message": "查询成功",
                    "type": "success",
                    "resultsData": resultsData,
                }
            )
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as err:
        print(err)
        logging.error(
            "CHAT------This is error from getUserInfo function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5001, "message": "发生了某些意料之外的错误", "type": "error"})

# 待优化
#获取该用户的聊天记录里的用户信息 这里暂时不用token验证
@chat.route('/getUserChatListInfo',methods=["POST"])
def getUserChatListInfo():
    try:
        res = request.get_json()
        chatList = json.loads(res['chatList'])
        print(chatList)
        for info in chatList:
            to_userId = info['to_userId']
            toUserInfo = db.exce_data_one("select U_portrait,U_name from user where U_id = '%s'"%to_userId)
            info['to_user_portrait'] = toUserInfo[0]
            info['to_user_name'] = toUserInfo[1]
        return jsonify({
            "status":200,
            "type":"success",
            "message":"查询成功",
            "resultData":chatList
        })
    except Exception as err:
        print(err)
        logging.error(
            "CHAT------This is error from getUserChatListInfo function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5001, "message": "发生了某些意料之外的错误", "type": "error"})
