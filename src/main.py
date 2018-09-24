import os

from flask import Flask
app = Flask(__name__)

__location__ = os.path.realpath(
    os.path.join(os.getcwd(), os.path.dirname(__file__)))

@app.route('/')
def hello_world():
    return 'Hello World! ' + __location__

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
