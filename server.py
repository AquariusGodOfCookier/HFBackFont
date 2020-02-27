from flask import Flask
import webbrowser
import json
import os
import shutil
from datetime import datetime
from api.main import api
from api.user.index import user
from api.home.index import home
from api.square.index import square
from api.push.index import push
from flask_apscheduler import APScheduler


app = Flask(__name__,static_folder='static',static_url_path='/static')
app.config['JSON_AS_ASCII'] =False
app.register_blueprint(api)
app.register_blueprint(api,url_prefix='/api')
app.register_blueprint(user,url_prefix='/api/user')
app.register_blueprint(home,url_prefix='/api/home')
app.register_blueprint(square,url_prefix='/api/square')
app.register_blueprint(push,url_prefix='/api/push')

class Config(object):
    JOBS=[
        {
            'id':'clearBuffer',
            'func':'__main__:clearBuffer',
            'args':(),
            'trigger':'interval',
            'weeks':2
        }
    ]

app.config.from_object(Config())

# 定时清空缓存区文件
def clearBuffer():
    dirpath = './static/bufferImage'
    shutil.rmtree(dirpath)
    os.mkdir(dirpath)



# clearBuffer(5)
if __name__ == '__main__':
    scheduler = APScheduler()
    scheduler.init_app(app)
    scheduler.start()
    f = open("./log/config.json",encoding='utf-8')
    setting = json.load(f)
    port = setting['port']
    app.run(host='0.0.0.0',port=port,debug=True)