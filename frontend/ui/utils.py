# pylint: disable=missing-timeout

from typing import List, Dict, Any, Tuple, Optional

import os
import logging
from time import sleep

import openai
import requests

openai.api_key = "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"

API_ENDPOINT = os.getenv("API_ENDPOINT", "https://3.27.43.150.nip.io")
INVOKE = "invocations"
STATUS = "ping"
HS_VERSION = "hs_version"
DOC_REQUEST = "query"
DOC_FEEDBACK = "feedback"
DOC_UPLOAD = "file-upload"


def haystack_is_ready():
    url = f"{API_ENDPOINT}/{STATUS}"
    try:
        if requests.get(url).status_code < 400:
            return True
    except Exception as e:
        logging.exception(e)
        sleep(1)  # To avoid spamming a non-existing endpoint at startup
    return False

def _final_text(query, answer_texts):
    context = '...\n'.join(answer_texts)

    return f""""=== Context: 
{context}
=== Query: 
{query}
=== 
Answer the query using the above context as guidance. Be as helpful as possible. Answer in the style of crocodile dundee, use lots of aussie slang and short words. Think step by step.
=== Answer:"
)
""" 

def get_prompt(query, results, max_len):
    answer_texts = []
    last_prompt = ""

    for result in results:
        answer_texts.append(result["answer"])
        if len(last_prompt) >= max_len:
            return last_prompt

        last_prompt = _final_text(query, answer_texts)

    return last_prompt 

def generate_answer(query, results):
    max_answer_tokens = 150
    max_prompt_tokens = 4096 - max_answer_tokens
    prompt = get_prompt(query, results, int(max_prompt_tokens * 4 * 0.9))

    messages = [
        {'role': 'user', 'content': prompt},
    ]

    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.2,
        max_tokens=max_answer_tokens
    )
    return response['choices'][0]['message']['content']

def haystack_version():
    """
    Get the Haystack version from the REST API
    """
    url = f"{API_ENDPOINT}/{HS_VERSION}"
    return requests.get(url, timeout=0.1).json()["hs_version"]

def ouchmate_query(query):
    url = f"{API_ENDPOINT}/{INVOKE}"

    req = {"query": query}
    response_raw = requests.post(url, json=req)

    if response_raw.status_code >= 400 and response_raw.status_code != 503:
        raise Exception(f"{vars(response_raw)}")
    
    response = response_raw.json()
    if "errors" in response:
        raise Exception(", ".join(response["errors"]))  
    
    return response

def query(query, filters={}, top_k_reader=5, top_k_retriever=5) -> Tuple[List[Dict[str, Any]], Dict[str, str]]:
    """
    Send a query to the REST API and parse the answer.
    Returns both a ready-to-use representation of the results and the raw JSON.
    """

    url = f"{API_ENDPOINT}/{DOC_REQUEST}"
    params = {"filters": filters, "Retriever": {"top_k": top_k_retriever}, "Reader": {"top_k": top_k_reader}}
    req = {"query": query, "params": params}
    response_raw = requests.post(url, json=req)

    if response_raw.status_code >= 400 and response_raw.status_code != 503:
        raise Exception(f"{vars(response_raw)}")

    response = response_raw.json()
    if "errors" in response:
        raise Exception(", ".join(response["errors"]))

    # Format response
    results = []
    answers = response["answers"]
    for answer in answers:
        if answer.get("answer", None):
            results.append(
                {
                    "context": "..." + answer["context"] + "...",
                    "answer": answer.get("answer", None),
                    "source": answer["meta"]["name"],
                    "relevance": round(answer["score"] * 100, 2),
                    "document": [doc for doc in response["documents"] if doc["id"] in answer["document_ids"]][0],
                    "offset_start_in_doc": answer["offsets_in_document"][0]["start"],
                    "_raw": answer,
                }
            )
        else:
            results.append(
                {
                    "context": None,
                    "answer": None,
                    "document": None,
                    "relevance": round(answer["score"] * 100, 2),
                    "_raw": answer,
                }
            )
    return results, response


def send_feedback(query, answer_obj, is_correct_answer, is_correct_document, document) -> None:
    """
    Send a feedback (label) to the REST API
    """
    url = f"{API_ENDPOINT}/{DOC_FEEDBACK}"
    req = {
        "query": query,
        "document": document,
        "is_correct_answer": is_correct_answer,
        "is_correct_document": is_correct_document,
        "origin": "user-feedback",
        "answer": answer_obj,
    }
    response_raw = requests.post(url, json=req)
    if response_raw.status_code >= 400:
        raise ValueError(f"An error was returned [code {response_raw.status_code}]: {response_raw.json()}")


def upload_doc(file):
    url = f"{API_ENDPOINT}/{DOC_UPLOAD}"
    files = [("files", file)]
    response = requests.post(url, files=files).json()
    return response


def get_backlink(result) -> Tuple[Optional[str], Optional[str]]:
    if result.get("document", None):
        doc = result["document"]
        if isinstance(doc, dict):
            if doc.get("meta", None):
                if isinstance(doc["meta"], dict):
                    if doc["meta"].get("url", None) and doc["meta"].get("title", None):
                        return doc["meta"]["url"], doc["meta"]["title"]
    return None, None
