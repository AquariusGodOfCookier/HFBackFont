from flask import Flask
import webbrowser
from api.main import api
from api.user.index import user
from api.home.index import home
from api.square.index import square
import time

app = Flask(__name__,static_folder='static',static_url_path='/static')
app.config['JSON_AS_ASCII'] =False
app.register_blueprint(api)
app.register_blueprint(api,url_prefix='/api')
app.register_blueprint(user,url_prefix='/api/user')
app.register_blueprint(home,url_prefix='/api/home')
app.register_blueprint(square,url_prefix='/api/square')


if __name__ == '__main__':
    app.run(host='0.0.0.0',port=8050,debug=True)