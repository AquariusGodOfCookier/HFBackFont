import sys
import os
import re
import random
import string
BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_PATH + "\\tool")
import DBConnect, Token
import logging, socket, time, json, random, base64, hmac, hashlib, redis, datetime
from flask import Blueprint, request, jsonify
myaddr = socket.gethostbyname(socket.gethostname())
dblogPath = os.path.dirname(DBConnect.__file__)
db = DBConnect.DBConnect("localhost", "root", "", "happy", dblogPath)
r = redis.StrictRedis(host="localhost", port=6379, db=0)
tokens = Token.Token()

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
# base64转换图片存到缓存区
# @reuturn string 在上传图片接口使用
def base64ToBufferPhoto(fileName, fileBase):
    imgdata = base64.b64decode(fileBase)
    file = open("./static/bufferImage/" + fileName, "wb")
    file.write(imgdata)
    file.close()
    return fileName


# @author dong.sun
# 遍历缓存区，如果有相同的图片，说明提交的就是该图片
# @return string 在发布动态接口中引用
def isBuffer(imgName):
    print(imgName,'isBuffer')
    bufferPath = os.getcwd() + "\\static\\bufferImage"
    if imgName in os.listdir(bufferPath):
        return True
    else:
        return False


# @author dong.sun
# 将缓存区的图片名称存储到存储区
# @return string 在发布动态接口中引用
def bufferImageToStore(imgName):
    try:
        print(imgName,'ookk')
        if isBuffer(imgName):
            print(imgName,'yes')
            BIpath = os.getcwd() + "\\static\\bufferImage\\" + imgName
            with open(BIpath, "rb") as f:
                base64_data = base64.b64decode(base64.b64encode(f.read()))
                file = open("./static/storeImage/" + imgName, "wb")
                file.write(base64_data)
                file.close()
    except Exception as err:
        print(err)
        return err

# @author dong.sun
# 将缓存区的图片数组存储到存储区
# @return string
def bufferTostore(imgList):
    storeList = []
    for i in imgList:
        bufferImageToStore(i)
        storeList.append("/static/storeImage/" + i)
    return storeList


# @author dong.sun
# 解析文章中的图片路径，获取图片名称，并且把该图片存到存储区
# @return 
def analyArticle(content):
    pattern =r"bufferImage/(.*?g|.*?G)"
    reg = re.compile(pattern)
    m1 = re.findall(reg,content)
    if len(m1)>0:
        bufferImageToStore(m1)
    return m1

# @author dong.sun
# 通过标签name判断该标签是否被创建过,在创建标签接口中使用
# @return Boolean
def isHaveThisLabel(labelName):
    result = db.exce_data_one("select isnull((select Span_title from spanmanage where Span_title = '%s' limit 1))"%labelName)[0]
    return True if result==0 else False

# @author dong.sun
# 将手机号加密
# @return string
def encryPhone(phone):
    if re.match(r"1[35678]\d{9}$",phone):
        return phone[0:3]+'****'+phone[7:11]
    else:
        return 'error'


push = Blueprint("push", __name__)

# 发布文章接口,需要验证登陆
@push.route("/addArticle", methods=["POST"])
def addArticle():
    try:
        # 验证token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            res = request.get_json()
            title = res["title"]
            content = res["content"]
            portraitUrl = res["portrait"]
            A_type = res["type"]
            releaseTime = getNow(1)
            articleId = "Article"+encryPhone(phone)+random.choice(string.ascii_lowercase)+getNow(0)
            articleImages = analyArticle(content)
            portraiImage = analyArticle(portraitUrl)
            imgList = articleImages+portraiImage
            bufferTostore(imgList)
            articleContent = content.replace('bufferImage','storeImage')
            sqlarticle = (
                "insert into article (A_id,A_title,U_phone,A_image,A_type) values('%s','%s','%s','%s','%s')"
                %(articleId,title,phone,portraiImage[0],A_type)
            )
            sqlContent = (
                "insert into articlecontent(A_id,A_content,A_releaseTime) values('%s','%s','%s')"
                %(articleId,articleContent,releaseTime)
            )
            db.exce_data_commitsql(sqlarticle)
            db.exce_data_commitsql(sqlContent)
            return jsonify({"status": 200, "message": "发布成功", "type": "success"})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as err:
        print(err)
        logging.error(
            "HOME------This is error from toPushArticle function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5001, "message": "发生了某些意料之外的错误", "type": "error"})


# 发布动态接口,需要验证登陆
@push.route("/addDynamic", methods=["POST"])
def addDynamic():
    try:
        # 验证token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            res = request.get_json()
            content = res["content"]
            imageList = json.loads(res["imageList"])
            address = res["address"]
            labelList = json.loads(res["labelList"])
            if len(labelList) == 0:
                strLabelList = ''
            else:
                for span_title in labelList:
                    if isHaveThisLabel(span_title):
                        # 已经创建过该值了
                        result = db.exce_update_data(
                            "update spanmanage set DegreeOfHeat = DegreeOfHeat +1 where Span_title = '%s'"
                            %span_title
                        )
                        if result == 'error':
                            return jsonify({"status": 5001, "message": "插入标签失败", "type": "error"})
                    else:
                        # 创建标签
                        sqlContent = (
                            "insert into spanmanage(Span_title,DegreeOfHeat) values('%s',1)"
                            %(span_title)
                        )
                        result = db.exce_data_commitsql(sqlContent)
                        if result == 'error':
                            return jsonify({"status": 5001, "message": "创建标签失败", "type": "error"})
                strLabelList = ",".join(labelList)
            if len(imageList) == 0:
                strimageList = ''
            else:
                strimage = []
                for imglist in imageList:
                    bufferImageToStore(analyArticle(imglist)[0])
                    strimage.append(analyArticle(imglist)[0])
                strimageList = ','.join(strimage)
           
            dynamicId = encryPhone(phone)+random.choice(string.ascii_lowercase)+getNow(0)
            pushTime = getNow(1)
            
            sql = (
                "insert into dynamic(U_Phone,D_id,D_time,D_content,D_image,D_span,D_address) values('%s','%s','%s','%s','%s','%s','%s')"
                % (phone, dynamicId, pushTime, content, strimageList, strLabelList, address)
            )
            results = db.exce_data_commitsql(sql)
            return jsonify({"type":results["type"],"message":results["msg"]})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as err:
        print(err)
        logging.error(
            "PUSH----This error from addDynamic function:%s______%s" % (Exception, err)
        )
        return jsonify({"status": 5001, "message": "发生了某些意料以外的错误", "type": "error"})


# 上传图片接口.不需要验证登陆，只是一个功能性接口
@push.route("/uploadImage", methods=["POST"])
def uploadImage():
    try:
        res = request.get_json()
        fileName = res["fileName"]
        fileBase = res["fileBase"]
        imageName = base64ToBufferPhoto(fileName, fileBase)
        f = open("./log/config.json",encoding='utf-8')
        setting = json.load(f)
        port = setting['port']
        imageUrl = "http://%s:%s/static/bufferImage/%s"%(myaddr,port,imageName)
        return jsonify(
            {
                "status": 200,
                "message": "上传成功",
                "type": "success",
                "data": {"imageUrl": imageUrl},
            }
        )
    except Exception as err:
        print(err)
        logging.error(
            "PUSH----This error from uploadImage function:%s______%s" % (Exception, err)
        )
        return jsonify({"status": 20040, "message": "上传失败", "type": "error"})

