import time
import json
from flask import Flask, request
from pipeline import load_pipeline, HaystackEncoder
from haystack.nodes import PromptTemplate

application = Flask(__name__)
pipe = load_pipeline("data/mcare/")

@application.route('/', methods=['GET'])
@application.route('/index', methods=['GET'])
@application.route('/ping', methods=['GET'])
def ping():
    return 'all good in the hood', 200

@application.route('/invocations', methods=['POST'])
def invocations():
    start = time.time()
    payload = request.get_json(force=True)
    query = payload.get('query', None)

    generator_kwargs = payload.get('generator_kwargs', {})
    retriever_kwargs = payload.get('retriever_kwargs', {})

    if 'invocation_context' in generator_kwargs and 'prompt_template' in generator_kwargs['invocation_context']:
        generator_kwargs['invocation_context']['prompt_template'] = PromptTemplate(
        name="question-answering",
        prompt_text=generator_kwargs['invocation_context']['prompt_template']
    )

    if query is None:
        return 'No query provided', 400
    
    try:
        response = pipe.run(
            query=query,
            params={
                "Retriever": retriever_kwargs,
                "Generator": generator_kwargs
            }
        ) 
    except Exception as e:
        return str(e), 500 

    print(time.time() - start)
    return json.dumps(response, cls=HaystackEncoder)

if __name__ == '__main__':
    application.run()