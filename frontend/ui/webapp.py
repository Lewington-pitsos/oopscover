import os
import logging
from pathlib import Path
from json import JSONDecodeError
import streamlit as st
import os
import logging
from time import sleep
import requests
import re
from PIL import Image
from io import BytesIO


# API_ENDPOINT = os.getenv("API_ENDPOINT", "https://3.27.43.150.nip.io")
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

def haystack_version():
    """
    Get the Haystack version from the REST API
    """
    url = f"{API_ENDPOINT}/{HS_VERSION}"
    return requests.get(url, timeout=0.1).json()["hs_version"]

def bushman_steve(query):
    url = f"{API_ENDPOINT}/{INVOKE}"

    template = """Context: {join(documents)}
===
{query}
===
Answer the question strictly in 75 words or less using the above context as guidance. Answer in the style of crocodile dundee. Use short, easy to understand language, 75 words or less. Do not quote from the context. Think step by step.
===
A (75 words or less):"""

    req = {
        "query": query,
        "retriever_kwargs": {"top_k": 6},
        "generator_kwargs": {
            "invocation_context": {
                "prompt_template": template,
                "max_tokens": 110,
            }
        },

    }
    response_raw = requests.post(url, json=req)

    if response_raw.status_code >= 400 and response_raw.status_code != 503:
        raise Exception(f"{vars(response_raw)}")
    
    response = response_raw.json()
    if "errors" in response:
        raise Exception(", ".join(response["errors"]))  
    
    return response

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

DEFAULT_QUESTION_AT_STARTUP = os.getenv("DEFAULT_QUESTION_AT_STARTUP", "How does medicare work?")

def escape_special_characters(text):
    special_characters = r'[\^$.|?*+(){}'
    escaped_text = re.sub(f'([{re.escape(special_characters)}])', r'\\\1', text)
    return escaped_text

# Labels for the evaluation
EVAL_LABELS = os.getenv("EVAL_FILE", str(Path(__file__).parent / "eval_labels_example.csv"))

# Whether the file upload should be enabled or not
DISABLE_FILE_UPLOAD = bool(os.getenv("DISABLE_FILE_UPLOAD"))

def set_state_if_absent(key, value):
    if key not in st.session_state:
        st.session_state[key] = value

def main():
    st.set_page_config(page_title="Bushman Kim", page_icon="https://haystack.deepset.ai/img/HaystackIcon.png", initial_sidebar_state="collapsed")


    # Persistent state
    set_state_if_absent("question", DEFAULT_QUESTION_AT_STARTUP)
    set_state_if_absent("answer", None)
    set_state_if_absent("results", None)

    # Small callback to reset the interface in case the text of the question changes
    def reset_results(*args):
        st.session_state.answer = None
        st.session_state.results = None

    response = requests.get('https://bushmankims-bucket-hands-off-cobba.s3.ap-southeast-2.amazonaws.com/bushmankim.png')
    image = Image.open(BytesIO(response.content))

    left_co, cent_co,last_co = st.columns(3)
    with cent_co:
        st.image(image, caption="G'day cobba")
    
    # Title
    st.write("# Bushman Kim Demo [out for lunch]")
    st.markdown(
        """Sorry mate, I'm out looking for another good old GPU to live on, not much to see here right the minute cobba.""",
        unsafe_allow_html=True,)

    # Sidebar
main()
