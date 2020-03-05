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
def base64ToBufferPhoto(fileName,fileBase):
    imgdata = base64.b64decode(fileBase)
    file = open('./static/bufferImage/'+fileName,'wb')
    file.write(imgdata)
    file.close()
    return fileName



# @author dong.sun
# 遍历缓存区，如果有相同的图片，说明提交的就是该图片
# @reuturn string 在发布动态接口中引用
def isBuffer(imgName):
    bufferPath = os.getcwd()+"\\static\\bufferImage"
    for files in os.listdir(bufferPath):
        if(files==imgName):
            return True
        else:
            return False

# @author dong.sun
# 将缓存区的图片存储到存储区
# @reuturn string 在发布动态接口中引用
def bufferTostore(imgList):
    storeList = []
    for i in imgList:
        if isBuffer(i):
            BIpath = os.getcwd()+"\\static\\bufferImage\\"+i
            with open(BIpath,"rb") as f:
                base64_data = base64.b64decode(base64.b64encode(f.read()))
                file = open('./static/storeImage/'+i,'wb')
                file.write(base64_data)
                file.close()
    
            storeList.append("/static/storeImage/"+i)
    return storeList


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
            articleId = "Article" + phone + getNow(0)
            db.exce_insert_data({
                "A_id":"'%s'"%articleId,
                "A_title":"'%s'"%title,
                "U_Phone":"'%s'"%phone,
                "A_image":"'%s'"%portraitUrl,
                "A_type":"'%s'"%A_type,
                "A_releaseTime":"'%s'"%releaseTime
            },'article')
            sql = (
                "insert into articlecontent (A_id,A_content,A_releaseTime) values('%s','%s','%s')"
                % (articleId, content, releaseTime)
            )
            db.exce_data_commitsql(sql)
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
@push.route("/addDynamic",methods=["POST"])
def addDynamic():
    try:
        # 验证token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            res = request.get_json()
            content = res['content']
            imageList = res['imageList']
            address = res['address']
            labelList = res['labelIdList']
            pushTime = getNow(1)
            storeList = bufferTostore(imageList)
            D_id = 'Dynamic'+phone+getNow(0)
            for span_title in labelList:
                db.exce_update_data(
                    "update spanmanage set DegreeOfHeat = DegreeOfHeat +1 where Span_title = '%s'"
                    % span_title
                )
            strLabelList = ','.join(labelList)
            strStoreList = ','.join(storeList)
            sql = (
                "insert into dynamic(U_Phone,D_id,D_time,D_content,D_image,D_span,D_address) values('%s','%s','%s','%s','%s','%s','%s')"
                %(phone,D_id,pushTime,content,strStoreList,strLabelList,address)
            )
            results = db.exce_data_commitsql(sql)
            print(results)
            return jsonify({
                "status":200,
                "message":"发布成功",
                "type":results,
            })
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as data:
        print(data)
        logging.error(
            "PUSH----This error from toDynamic function:%s______%s" % (Exception, data)
        )
        return jsonify({
            "status":5001,
            "message":"发生了某些意料以外的错误",
            "type":"error"
        })

# 上传图片接口.不需要验证登陆，只是一个功能性接口
@push.route("/uploadImage",methods=["POST"])
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