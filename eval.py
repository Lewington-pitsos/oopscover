import json
import requests
import datetime

ENDPOINT = "http://127.0.0.1:8000/invocations"

id = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
results_file = f'cruft/{id}-results.json'
verbose = []
results = []

template = """Context: {join(documents)}
===
{query}
===
Answer the question strictly in 75 words or less using the above context as guidance. Answer in the style of crocodile dundee. Use short, easy to understand language, 75 words or less. Do not quote from the context. Think step by step.
===
A (75 words or less):"""

def send_query(query, retriever_kwargs, generator_kwargs):
    response = requests.post(ENDPOINT, json={
        "query": query,
        "generator_kwargs": generator_kwargs,
        "retriever_kwargs": retriever_kwargs
    })

    print(response.status_code)

    return response.json()


queries = [
    "How does medicare work?",
    "If I break my leg and have to go to hospital how much will I have to pay, roughly?",
    "I am a greek citizen staying in Australia on holiday. If i go to hospital, will my bills be covered?",
    "I have tonsilitis and i have medicare. Will I have to pay any money for treatment?",
    "If I break my leg and go to hospital, how much will it cost me? I am an Australian Citizen. I do not have any private health cover. I am going to a public hospital.",
    "I have a dental appointment coming up soon. Will medicare cover my dental costs?",
    "I am a citizen of New Guinea, living in australia under a working visa. I need to visit the hospital for epilepsy treatment. Will I have to pay for my treatment?",
    "Are citizens of Germany covered by medicare in Australia?",
    "I have lived in Australia all my life, i was born here, but I don't have a medicare card. Will I have to pay for a hospital visit?",
    "If I have private health insurance, will I still be covered by medicare?",
    "Will I be covered by medicare if I visit a private hospital",
]

generator_kwargs = {
    "invocation_context": {
        "prompt_template": template,
        "max_tokens": 110,
    }
}
retriever_kwargs = {
    "top_k": 6
}

for q in queries:
    response = send_query(q, retriever_kwargs=retriever_kwargs, generator_kwargs=generator_kwargs)
    results.append({
        "query": q,
        "response": response['results'][0]
    })
    verbose.append({
        "query": q,
        "response": response
    })

    with open(results_file, 'w') as f:
        json.dump({
            'retriever_kwargs': retriever_kwargs,
            'generator_kwargs': generator_kwargs, 
            'results': results, 
            'verbose': verbose
        }, f, indent=4)

