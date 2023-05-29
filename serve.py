import json
from flask import Flask, request

application = Flask(__name__)

@application.route('/', methods=['GET'])
@application.route('/index', methods=['GET'])
@application.route('/ping', methods=['GET'])
def ping():
    return 'serving berving', 200

if __name__ == '__main__':
    # DO NOT SET DEBUG MODE TO "True" OR ELSE WE GET INFINITE RECURSION
    application.run()