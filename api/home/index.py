import sys
import os

BASE_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_PATH + "\\tool")
import DBConnect, Token
import logging, socket, time, json, random, base64, hmac, hashlib, redis, datetime
from flask import Blueprint, request, jsonify
import numpy as np

dblogPath = os.path.dirname(DBConnect.__file__)
db = DBConnect.DBConnect("localhost", "root", "", "happy", dblogPath)
r = redis.StrictRedis(host="localhost", port=6379, db=0)
tokens = Token.Token()

# @author dong.sun
# 根据前端传来页数，每次发送pageSizes条数据返回前端
# @param sql 拼接的mysql语句，pageIndex页数,pageSizes 每页的查询个数
# @return Array
def getDBLimit(sqls, pageIndex, pageSize):
    pageCounts = 0 + (pageIndex - 1) * pageSize
    sql = sqls + " limit %d,%d" % (pageCounts, pageSize)
    results = db.exce_data_all(sql)
    return results


# @author dong.sun
# 根据用户手机号获取用户信息,在getRecommend接口使用
# @return String
def getUserInfo(userPhone):
    userInfo = db.exce_data_one(
        "select U_name,U_id,U_portrait from user where U_phone='%s'" % userPhone
    )
    return userInfo


# @author dong.sun
# 根据用户id获取用户信息
# @return String
def getIdUserInfo(uid):
    userInfo = db.exce_data_one(
        "select U_name,U_portrait from user where U_id='%s'" % uid
    )
    return userInfo


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
# 根据文章id获取用户姓名,在getDetails等接口使用
# @return String
def articleGetUser(articleId):
    user = db.exce_data_one(
        "select U_name,U_portrait,U_id from user where U_phone in (select U_phone from article where A_id ='%s')"
        % (articleId)
    )
    return user


# @author dong.sun
# 遍历获取文章或者动态的时候，判断该文章/动态是否点过赞
# @return object
def judgeIsLike(ids, phone):
    statusid = "%s::%s" % (ids, phone)
    if r.exists(statusid) and str(r.get(statusid), "utf-8") == "1":
        status = True
    else:
        status = False
    return status


# @author dong.sun
# 添加点赞功能,在各个点赞接口使用
# @return string
def toLike(ids, phone):
    if judgeIsLike(ids, phone):
        # 如果点过赞了
        return "error"
    else:
        statusid = "%s::%s" % (ids, phone)
        r.set(name=statusid, value=1)
        return "success"


# @author dong.sun
# 根据用户id获取该用户最近发表的文章,获取最近发表的文章
# @return string
def uidGetHotArticle(uid):
    userInfo = getIdUserInfo(uid)
    articleInfo = db.exce_data_one(
        "select A_id,A_title,A_image,A_type,A_releaseTime from article where U_phone in (select U_phone from user where U_id = '%s') order by A_releaseTime desc"
        % uid
    )
    return {
        "userInfo": {"userName": userInfo[0], "userId": uid, "portrait": userInfo[1]},
        "articleInfo": {
            "id": articleInfo[0],
            "title": articleInfo[1],
            "preview": articleInfo[2],
            "type": articleInfo[3],
            "time": articleInfo[4],
        },
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
    }


# @author dong.sun
# 判断该游戏是否已经被用户关注
# @return Boolean
def judgeIsAttention(lists, ids):
    arr = np.array(lists)
    status = (arr == ids).any()
    if status:
        status = 1
    else:
        status = 2
    return status

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

# 首页推荐页
# author dong.sun
home = Blueprint("home", __name__)

# 随机获取文章列表
# 这里不需要验证是否登陆
@home.route("/getRecommend", methods=["GET"])
def getRecommend():
    try:
        # 验证Token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            # 主要内容
            pageIndex = int(request.args.get("pageIndex"))
            results = getDBLimit("select * from article where U_phone<>%s order by rand()"%phone,pageIndex,4)
            articleList = []
            articleInfo = {}
            userInfo= {}
            for data in results:
                articleInfo={
                    "id":data[0],
                    "preview":getLocalImageUrl(data[3]),
                    "title":data[1],
                    "type":data[4]
                }
                userInfo = {
                    "portrait":getUserInfo(data[2])[2],
                    "userId":getUserInfo(data[2])[1],
                    "userName":getUserInfo(data[2])[0]
                }
                articleList.append({
                    "articleInfo":articleInfo,
                    "userInfo":userInfo
                })
            
            return jsonify({
                "status":200,
                "message":"请求成功",
                "type":"success",
                "data":{
                    "articleList":articleList
                }
            })
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as err:
        print(err)
        logging.error(
            "HOME------This is error from getRecommend function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})


# 首页文章详情页,不需要是否验证登陆;如果登陆了则显示点赞状态，没登陆则只显示点赞数量，不显示状态
@home.route("/getDetail", methods=["GET"])
def getDetail():
    try:
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            articleId = request.args.get("articleId")
            # 根据文章id寻找到用户信息
            user = articleGetUser(articleId)
            statusid = "%s::%s" % (articleId, phone)
            if r.exists(statusid) and str(r.get(statusid), "utf-8") == "1":
                status = True
            else:
                status = False
            articleContentList = db.exce_data_one(
                "select * from articlecontent where A_id = '%s'" % articleId
            )
            articleInfo = db.exce_data_one(
                "select * from article where A_id = '%s'"%articleId
            )
            userList = {
                "userName":user[0],
                "portrait":user[1],
                "userId":user[2]
            }
            articleContent = {
                "content":articleContentList[1],
                "releaseTime":articleContentList[2],
                "likeCounts":articleContentList[3],
                "comments":articleContentList[4],
                "status":status
            }
            articleInfo = {
                "title":articleInfo[1],
                "portrait":getLocalImageUrl(articleInfo[3]),
                "type":articleInfo[4]
            }
            # 这里是登录了的,看是否给这个文章点过赞
            return jsonify(
                {
                    "status": 200,
                    "message": "查询成功",
                    "type": "success",
                    "data": {
                        "articleContent":articleContent,
                        "user": userList,
                        'articleInfo':articleInfo,
                    },
                }
            )
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as err:
        print(err)
        logging.error(
            "HOME------This is error from getDetails function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5002, "message": "查询失败", "type": "error"})

# 获取游戏详情页
@home.route("/getGameDetail",methods=["POST"])
def getGameDetail():
    try:
        res = request.get_json()
        gameId = res["gameId"]
        pageIndex = int(res["pageIndex"])
        gameInfoSql = db.exce_data_one(
            "select * from game where G_id = '%s'"%gameId
        )
        gameInfo = {
            "name":gameInfoSql[0],
            "id":gameInfoSql[1],
            "avator":gameInfoSql[2],
            "hot":gameInfoSql[3],
            "platform":gameInfoSql[4],
            "describe":gameInfoSql[5]
        }
        gameArticleSql  = getDBLimit("select * from article where A_type = '%s'"%gameId,pageIndex,10)
        try:
            gameArticleList = []
            for data in gameArticleSql:
                articleInfo={
                    "id":data[0],
                    "preview":getLocalImageUrl(data[3]),
                    "title":data[1],
                    "type":data[4]
                }
                userInfo = {
                    "portrait":getUserInfo(data[2])[2],
                    "userId":getUserInfo(data[2])[1],
                    "userName":getUserInfo(data[2])[0]
                }
                gameArticleList.append({
                    "articleInfo":articleInfo,
                    "userInfo":userInfo
                })
        except:
            gameArticleList = []
        result = {
            "gameInfo":gameInfo,
            "article":gameArticleList,
            "pageIndex":pageIndex
        }
        return jsonify({"status": 200, "message": "请求成功", "type": "success","data":result})
    except Exception as err:
        print(err)
        logging.error(
            "HOME------This is error from getGameDetail function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5001, "message": "发生了某些意料之外的错误", "type": "error"})


# 查看该文章的评论内容, 需要验证登陆
@home.route("/getDetailsComments", methods=["GET","POST"])
def getDetailsComments():
    try:
        # 验证Token
        token = request.headers["Token"]
        Phone = request.headers["userPhone"]
        if tokens.verificationToken(Phone, token):
            # articleId = request.args.get("articleId")
            # pageIndex = int(request.args.get("pageIndex"))
            res = request.get_json()
            articleId = res["articleId"]
            pageIndex = int(res["pageIndex"])
            pageCounts = 0 + (pageIndex - 1) * 10
            resultsList = db.exce_data_all(
                "select * from comment where Commented_id = '%s' limit %d,10"
                % (articleId, pageCounts)
            )
            commentsList = []
            for data in resultsList:
                comment_id = data[0]
                userPhone = data[2]
                userName = getUserInfo(userPhone)[0]
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


# 文章评论接口，需要验证登陆
@home.route("/addComments", methods=["POST"])
def addComments():
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
            sqlComment = (
                "insert into comment (Comment_id,Commented_id,U_phone,Comment_time,Comment_content) values('%s','%s','%s','%s','%s')"
                % (commentId, articleId, phone, commentTime, commentContent)
            )
            sqlCommentCount = (
                "update articlecontent set A_comments = A_comments + 1 where A_id = '%s'"
                % articleId
            )
            db.exce_data_commitsqls([sqlComment, sqlCommentCount])
            return jsonify({"status": 200, "message": "评论成功", "type": "success"})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "info"})
    except Exception as data:
        logging.error(
            "HOME------This is error from addComments function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5001, "message": "发生了某些意料之外的错误", "type": "error"})


# 文章点赞接口,需要验证登陆
@home.route("/updateLikeArticle", methods=["PUT"])
def updateLikeArticle():
    try:
        # 验证Token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            # 主要内容
            res = request.get_json()
            articleId = res["articleId"]
            likeType = int(res["type"])
            if likeType == 0:
                # 点赞
                result = toLike(articleId, phone)
                if result == "error":
                    return jsonify({"status": 200, "message": "已经点过赞了", "type": "info"})
                elif result == "success":
                    db.exce_update_data(
                        "update articlecontent set A_likeCounts = A_likeCounts +1 where A_id = '%s'"
                        % articleId
                    )
                    return jsonify(
                        {"status": 200, "message": "点赞成功", "type": "success"}
                    )
            else:
                statusid = "%s::%s" % (articleId, phone)
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
            "HOME------This is error from toLikeArticle function:%s_______%s"
            % (Exception, data)
        )
        return jsonify({"status": 5001, "message": "发生了意料以外的错误", "type": "error"})


# 评论点赞接口,需要验证登陆
@home.route("/updateLikeComments", methods=["PUT"])
def updateLikeComments():
    try:
        # 验证Token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            # 主要内容
            res = request.get_json()
            commentsId = res["commentsId"]
            likeType = int(res["type"])
            if likeType == 0:
                # 点赞
                result = toLike(commentsId, phone)
                if result == "error":
                    return jsonify({"status": 200, "message": "已经点过赞了", "type": "info"})
                elif result == "success":
                    db.exce_update_data(
                        "update comment set Comment_likeCounts = Comment_likeCounts +1 where Comment_id = '%s'"
                        % commentsId
                    )
                    return jsonify(
                        {"status": 200, "message": "点赞成功", "type": "success"}
                    )
            else:
                statusid = "%s::%s" % (commentsId, phone)
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
        return jsonify({"status": 5001, "message": "数据库添加失败", "type": "error"})


# 搜索文章接口,不需要验证登陆
@home.route("/searchArticle", methods=["POST"])
def searchArticle():
    try:
        res = request.get_json()
        content = res["content"]
        args = "%" + content + "%"
        results = db.exce_data_all(
            "select * from article where A_title like'%s'" % args
        )
        articleList = []
        for data in results:
            articleId = data[0]
            title = data[1]
            userPhone = data[2]
            portrait = data[3]
            userName = getUserInfo(userPhone)[0]
            userId = getUserInfo(userPhone)[1]
            articleList.append(
                {
                    "articleId": articleId,
                    "title": title,
                    "userName": userName,
                    "userId": userId,
                    "portrait": portrait,
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
        logging.error(
            "HOME------This is error from searchArticle function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以为的错误", "type": "error"})


# 查看我关注的人,需要验证登陆
@home.route("/getFollowUser", methods=["GET"])
def getFollowUser():
    try:
        # 验证Token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            # 主要内容
            results = db.exce_data_one(
                "select U_attention_articles from userattentions where U_phone='%s'"
                % phone
            )[0]
            if results == None or results == '':
                userList = []
            else:
                userList = []
                userStr = results.split(",")
                for data in userStr:
                    user = getUserInfo(data)
                    userName = user[0]
                    portrait = user[2]
                    userId = user[1]
                    userList.append(
                        {"userName": userName, "portrait": portrait, "userId": userId}
                    )
            return jsonify(
                {
                    "status": 200,
                    "message": "查询成功",
                    "type": "success",
                    "data": {"userList": userList},
                }
            )
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as err:
        print(err)
        logging.error(
            "HOME------This is error from followUser function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})


# 查看我关注人的最新文章,需要验证登陆
@home.route("/getFollowHotArticle", methods=["POST"])
def getFollowHotArticle():
    try:
        # 验证Token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            # 主要内容
            res = request.get_json()
            attentionList = res["attentionList"]
            hotArticleList = []
            for uid in attentionList:
                article = uidGetHotArticle(uid)
                hotArticleList.append(article)
            return jsonify(
                {
                    "status": 200,
                    "message": "查询成功",
                    "type": "success",
                    "data": {"articleList": hotArticleList},
                }
            )
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as err:
        print(err)
        logging.error(
            "HOME------This is error from followUser function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})


# 查看我加入的游戏社区
@home.route("/getFollowGames", methods=["GET"])
def getFollowGames():
    try:
        # 验证Token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            # 主要内容
            results = db.exce_data_one(
                "select U_attention_games from userattentions where U_phone='%s'"
                % phone
            )[0]
            if results=='' or results == None:
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
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as err:
        print(err)
        logging.error(
            "HOME------This is error from followUser function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})


# 查看排名前十的游戏社区
@home.route("/getAllGames", methods=["GET"])
def getAllGames():
    try:
        # 验证Token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            # 主要内容
            CGSQL = db.exce_data_all(
                "select * from game where G_type = 'CG' order by G_hot limit 0,10"
            )
            MGSQL = db.exce_data_all(
                "select * from game where G_type = 'MG' order by G_hot limit 0,10"
            )
            Myresults = db.exce_data_one(
                "select U_attention_games from userattentions where U_phone='%s'"
                % phone
            )[0]
            if Myresults == None:
                MyGame = ''
            else:
                MyGame = Myresults.split(",")
            CGList = []
            MGList = []
            for i in CGSQL:
                status = judgeIsAttention(MyGame, i[1])
                CGList.append(
                    {
                        "name": i[0],
                        "id": i[1],
                        "portrait": i[2],
                        "hot": i[3],
                        "describe": i[5],
                        "status": status,
                    }
                )
            for i in MGSQL:
                status = judgeIsAttention(MyGame, i[1])
                MGList.append(
                    {
                        "name": i[0],
                        "id": i[1],
                        "portrait": i[2],
                        "hot": i[3],
                        "describe": i[5],
                        "status": status,
                    }
                )
            return jsonify(
                {
                    "status": 200,
                    "message": "请求成功",
                    "type": "success",
                    "data": {"CGList": CGList, "MGList": MGList},
                }
            )
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as err:
        print(err)
        logging.error(
            "HOME------This is error from followUser function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})


# 搜索游戏接口
@home.route("/searchGame", methods=["POST"])
def searchGame():
    try:
        res = request.get_json()
        content = res["content"]
        args = "%" + content + "%"
        results = db.exce_data_all("select * from game where G_name like '%s'" % args)
        game = []
        for item in results:
            game.append(
                {
                    "name": item[0],
                    "id": item[1],
                    "portrait": item[2],
                    "hot": item[3],
                    "type": item[4],
                }
            )
        return jsonify(
            {"status": 200, "message": "查询成功", "type": "success", "data": game}
        )
    except Exception as err:
        print(err)
        logging.error(
            "HOME------This is error from searchGame function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5002, "message": "发生了某些意料以外的错误", "type": "error"})

# 加入/退出游戏社区 type:1:退出 2:加入
@home.route("/updateGameAttention",methods=["PUT"])
def updateGameAttention():
    try:
        # 验证Token
        token = request.headers["Token"]
        phone = request.headers["userPhone"]
        if tokens.verificationToken(phone, token):
            # 主要内容
            res = request.get_json()
            gameId = res["gameId"]
            attentionType = int(res["type"])
            if attentionType == 1:
                # 退出
                MyGame = db.exce_data_one("select U_attention_games from userattentions where U_phone='%s' for update"% phone)[0]
                MyGameList = MyGame.split(',')
                MyGameList.remove(gameId)
                MyGameStr = ','.join(MyGameList)
                db.exce_update_data(
                    "update userattentions set U_attention_games = '%s' where U_phone ='%s'"
                    %(MyGameStr,phone)
                )
                db.exce_update_data(
                    "update game set G_hot = G_hot-1 where G_id = '%s'"
                    %gameId
                )
                return jsonify({"status": 200, "message": "退出成功", "type": "success"})
            else:
                # 加入
                MyGame = db.exce_data_one("select U_attention_games from userattentions where U_phone='%s' for update"% phone)[0]
                if MyGame == '' or MyGame == None:
                    MyGame = gameId
                else:
                    MyGame = MyGame+','+gameId
                db.exce_update_data(
                    "update userattentions set U_attention_games = '%s' where U_phone ='%s'"
                    %(MyGame,phone)
                )
                db.exce_update_data(
                    "update game set G_hot = G_hot+1 where G_id = '%s'"
                    %gameId
                )
                return jsonify({"status": 200, "message": "加入成功", "type": "success"})
        else:
            return jsonify({"status": 1004, "message": "token过期", "type": "error"})
    except Exception as err:
        print(err)
        logging.error(
            "SQUARE------This is error from updateGameAttention function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5001, "message": "发生了意料以外的错误", "type": "error"})

# 查看用户搜索缓存
@home.route("/getHistorySearch",methods=["GET"])
def getHistorySearch():
    try:
        phone = request.headers["userPhone"]
        # 获取该用户的查询缓存
        resultSql = db.exce_data_one(
            "select U_search from user where U_phone = '%s'"
            %phone
        )[0]
        if resultSql == '' or resultSql == None:
            result = []
        else:
            result = resultSql.split(',')
        return jsonify({"status": 200, "message": "查询成功", "type": "success","data":result})
    except Exception as err:
        print(err)
        logging.error(
            "SQUARE------This is error from getHistorySearch function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5001, "message": "发生了意料以外的错误", "type": "error"})

# 搜索接口
@home.route("/getSearchContent",methods=["GET"])
def getSearchContent():
    phone = request.headers["userPhone"]
    try:
        inputValue = request.args.get("inputValue")
        message = "查询成功"
        types = "success"
        # 先把搜索内容插入到数据库中
        try:
            userSearchSql = db.exce_data_one("select U_search from user where U_phone = '%s'"%phone)[0]
            if userSearchSql == None or userSearchSql == '':
                userSearchSql = inputValue
            else:
                userList = userSearchSql.split(',')
                if inputValue in userList:
                    userSearchSql = userSearchSql
                else:
                    userSearchSql += ','+inputValue
            db.exce_update_data("update user set U_search = '%s' where U_phone='%s'"%(
                userSearchSql,phone
            ))
        except Exception as err:
            print(err)
            message = "插入失败"
            types = "error"
        # 再返回用户搜索的内容
        try:
            args = "%" + inputValue + "%"
            gameSql = db.exce_data_all("select * from game where G_name like '%s'" % args)
            userSql = db.exce_data_all("select * from user where U_name like '%s'" % args)
            articlSql = db.exce_data_all("select * from articlecontent where A_content like '%s'" %args)
            if len(list(gameSql)) == 0:
                gameInfo = []
            else:
                gameInfo = []
                for item in gameSql:
                    gameInfo.append(
                        {
                            "name":item[0],
                            "id":item[1],
                            "portrait":item[2],
                            "hot":item[3],
                            "type":item[4]
                        }
                    )
            if len(list(userSql)) == 0:
                userInfo = []
            else:
                userInfo = []
                for item in userSql:
                    userInfo.append(
                        {
                            "id":item[0],
                            "name":item[1],
                            "avator":item[4]
                        }
                    )
            if len(list(articlSql)) == 0:
                articleInfo = []
            else:
                articleInfo = []
                for item in articlSql:
                    articleInfo.append(
                        {
                            'id':item[0],
                            'content':item[1]
                        }
                    )
        except:
            userInfo = []
            gameInfo = []
            articleInfo = []
        return jsonify({
            "status":200,
            "message":message,
            "type":types,
            "data":{
                "userInfo":userInfo,
                "gameInfo":gameInfo,
                "articleInfo":articleInfo
            }
        })
    except Exception as err:
        print(err)
        logging.error(
            "SQUARE------This is error from getSearchContent function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5001, "message": "发生了意料以外的错误", "type": "error"})

# 清空搜索历史
@home.route("/clearSearch",methods=["PUT"])
def clearSearch():
    phone = request.headers["userPhone"]
    try:
        db.exce_update_data("update user set U_search = '' where U_phone = '%s'"%phone)
        return jsonify({
            "status":200,
            "message":"清空成功",
            "type":"success",
            "data":{}
        })
    except Exception as err:
        print(err)
        logging.error(
            "SQUARE------This is error from clearSearch function:%s_______%s"
            % (Exception, err)
        )
        return jsonify({"status": 5001, "message": "发生了意料以外的错误", "type": "error"})