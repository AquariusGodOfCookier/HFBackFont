from flask import Flask
import webbrowser
import json
from api.main import api
from api.user.index import user
from api.home.index import home
from api.square.index import square
from api.push.index import push

import time

app = Flask(__name__,static_folder='static',static_url_path='/static')
app.config['JSON_AS_ASCII'] =False
app.register_blueprint(api)
app.register_blueprint(api,url_prefix='/api')
app.register_blueprint(user,url_prefix='/api/user')
app.register_blueprint(home,url_prefix='/api/home')
app.register_blueprint(square,url_prefix='/api/square')
app.register_blueprint(push,url_prefix='/api/push')

if __name__ == '__main__':
    f = open("./log/config.json",encoding='utf-8')
    setting = json.load(f)
    port = setting['port']
    app.run(host='0.0.0.0',port=8050,debug=True)