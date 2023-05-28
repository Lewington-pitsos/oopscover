import os
import json
from flask import Flask, request
from pipeline import load_pipeline, ask_question, HaystackEncoder

app = Flask(__name__)

pipe = load_pipeline("data/combo/")

@app.route('/ping', methods=['GET'])
def ping():
    return '', 200

@app.route('/invocations', methods=['POST'])
def invocations():
    payload = request.get_json(force=True)
    query = payload.get('query', None)

    if query is None:
        return 'No query provided', 400
    
    response = ask_question(pipe, query)

    return json.dumps(response, cls=HaystackEncoder)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))