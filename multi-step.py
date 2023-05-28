import logging
import time
import json
import openai

with open('creds.json') as f:
    openai.api_key = json.load(f)['api_key']

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')


with open('cruft/answers2.json') as f:
    answers = json.load(f)

first = answers[0]
prompt = first['answers'][0]['meta']['prompt']
answer = first['answers'][0]['answer']


messages = [
    {'role': 'user', 'content': prompt},
    {'role': 'assistant', 'content': answer}
]


print(messages)




# current_messages = [
#     {'role': 'user', 'content': context}
# ]

# response = openai.ChatCompletion.create(
#     model="gpt-3.5-turbo",
#     messages=current_messages,
#     temperature=0.05
# )
# first_pass = response['choices'][0]['message']['content']

# logging.info(f"actions generated")

# current_messages.append({'role': 'assistant', 'content': first_pass})

# with open(filename, 'w') as f:
#     f.write('---------- VALUES ----------\n\n' + value)
#     f.write('\n\n---------- DILEMMA ----------\n\n' + situation)
#     f.write('\n\n---------- FIRST_PASS ----------\n\n' + first_pass)
