import json
from flask import Flask, request
from pipeline import load_pipeline, ask_question, HaystackEncoder

application = Flask(__name__)
pipe = load_pipeline("data/mcare/")


@application.route('/', methods=['GET'])
@application.route('/index', methods=['GET'])
@application.route('/ping', methods=['GET'])
def ping():
    return 'all good in the hood', 200

@application.route('/invocations', methods=['POST'])
def invocations():
    payload = request.get_json(force=True)
    query = payload.get('query', None)

    model_kwargs = payload.get('model_kwargs', {})

    if query is None:
        return 'No query provided', 400
    
    response = ask_question(pipe, query, model_kwargs)

    return json.dumps(response, cls=HaystackEncoder)

if __name__ == '__main__':
    # DO NOT SET DEBUG MODE TO "True" OR ELSE WE GET INFINITE RECURSION
    application.run()