import json
import logging
import os
from haystack.document_stores import InMemoryDocumentStore
from haystack.nodes import TextConverter, PreProcessor, PromptTemplate, EmbeddingRetriever, PromptNode
from haystack.pipelines import Pipeline
from haystack.utils import print_answers
from haystack.schema import Document, Answer
from uuid import uuid4

class HaystackEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Answer):
            return obj.to_dict()
        elif isinstance(obj, Document):
            return obj.to_dict()
        return json.JSONEncoder.default(self, obj)


with open('creds.json') as f:
    api_key = json.load(f)['api_key']

logging.basicConfig(format="%(levelname)s - %(name)s -  %(message)s", level=logging.WARNING)
logging.getLogger("haystack").setLevel(logging.INFO)
document_store = InMemoryDocumentStore(embedding_dim=384)
text_converter = TextConverter()
pp = PreProcessor(
    clean_header_footer=True,
    split_length=150,
    split_overlap=15,
    max_chars_check=10_000
)

doc_dir = "data/combo/"

def get_url(doc_dir, filename):
    if filename == "act.txt":
        return "https://www5.austlii.edu.au/au/legis/cth/consol_act/hia1973164/"

    filename = filename.replace(".txt", "").replace("_", "/")

    return "https://" + filename.replace(doc_dir, "")

files_to_index = [doc_dir + f for f in os.listdir(doc_dir)]
metadata = [{'url': get_url(doc_dir, f)} for f in files_to_index]

indexing_pipeline = Pipeline()
indexing_pipeline.add_node(component=text_converter, name="TextConverter", inputs=["File"])
indexing_pipeline.add_node(component=pp, name="PreProcessor", inputs=["TextConverter"])
indexing_pipeline.add_node(component=document_store, name="DocumentStore", inputs=["PreProcessor"])

indexing_pipeline.run_batch(file_paths=files_to_index, meta=metadata)

d = document_store.get_all_documents_generator()

retriever = EmbeddingRetriever(
    document_store=document_store,
   embedding_model="sentence-transformers/all-MiniLM-L6-v2",
   model_format="sentence_transformers"
)
document_store.update_embeddings(retriever)

generator_template = PromptTemplate(
    name="question-answering",
    prompt_text="===\nContext: {join(documents)}"
     "\n===\n {query}\n"
    "\n===\n Answer the question using the above context as guidance. Be as helpful as possible. Answer in the style of crocodile dundee, use lots of aussie slang and short words. Think step by step.\nA:"
)
generator = PromptNode(
    api_key=api_key,
    model_name_or_path="gpt-3.5-turbo", 
    default_prompt_template=generator_template,
    max_length=200,
    top_k=1
)


pipe = Pipeline()
pipe.add_node(name="Retriever", component=retriever, inputs=["Query"])
pipe.add_node(name="Generator", component=generator, inputs=["Retriever"])

questions = [
    "If I break my leg and go to hospital, how much will it cost me? I am an Australian Citizen. I do not have any private health cover. I am going to a public hospital.",
    "I have tonsilitis and i have medicare. Will I have to pay any money for treatment?",
    "I have a dental appointment coming up soon. Will medicare cover my dental costs?",
    "I am a citizen of New Guinea, living in australia under a working visa. I need to visit the hospital for epilepsy treatment. Will I have to pay for my treatment?",
    "Are citizens of Germany covered by medicare in Australia?",
    "I have lived in Australia all my life, i was born here, but I don't have a medicare card. Will I have to pay for a hospital visit?"
]

answers = []


def ask_question(pipe, question):
    return pipe.run(
        query=question,
        params={
            "Retriever": {"top_k": 10},
        }
    )

for q in questions:
    prediction = ask_question(pipe, q)
    print(prediction['results'])
    answers.append(prediction)

with open(f'cruft/answers-{uuid4()}.json', 'w') as f:
    json.dump(answers, f, indent=4, cls=HaystackEncoder)