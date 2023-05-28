import json
import logging
import os
from haystack.document_stores import InMemoryDocumentStore
from haystack.nodes import TextConverter, PreProcessor, EmbeddingRetriever, PromptTemplate, PromptNode
from haystack.pipelines import Pipeline
from haystack.schema import Document, Answer

class HaystackEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Answer):
            return obj.to_dict()
        elif isinstance(obj, Document):
            return obj.to_dict()
        return json.JSONEncoder.default(self, obj)

def load_pipeline(doc_dir):
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

    def get_url(doc_dir, filename, mapping):
        if filename[-7:] == "act.txt":
            return "http://classic.austlii.edu.au/au/legis/cth/consol_act/hia1973164/"

        return mapping[filename]

    with open(doc_dir + 'url_mapping.txt') as f:
        mapping_lines = f.readlines()

    mapping = dict()
    for l in mapping_lines:
        mapping[l.split()[1]] = l.split()[0]

    files_to_index = [doc_dir + filename for filename in os.listdir(doc_dir) if filename != 'url_mapping.txt']
    metadata = [{'url': get_url(doc_dir, filenme, mapping)} for filenme in files_to_index]

    indexing_pipeline = Pipeline()
    indexing_pipeline.add_node(component=text_converter, name="TextConverter", inputs=["File"])
    indexing_pipeline.add_node(component=pp, name="PreProcessor", inputs=["TextConverter"])
    indexing_pipeline.add_node(component=document_store, name="DocumentStore", inputs=["PreProcessor"])

    indexing_pipeline.run_batch(file_paths=files_to_index, meta=metadata)



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
        top_k=1,
        model_kwargs={"max_tokens":100},
    )

    pipe = Pipeline()
    pipe.add_node(name="Retriever", component=retriever, inputs=["Query"])
    pipe.add_node(name="Generator", component=generator, inputs=["Retriever"])

    return pipe

def ask_question(pipe, question):
    return pipe.run(
        query=question,
        params={
            "Retriever": {"top_k": 8},
        }
    )