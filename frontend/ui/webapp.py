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
        "query": "According to the Australian Medicare system, " + query,
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
    st.set_page_config(page_title="Haystack Demo", page_icon="https://haystack.deepset.ai/img/HaystackIcon.png", initial_sidebar_state="collapsed")


    # Persistent state
    set_state_if_absent("question", DEFAULT_QUESTION_AT_STARTUP)
    set_state_if_absent("answer", None)
    set_state_if_absent("results", None)

    # Small callback to reset the interface in case the text of the question changes
    def reset_results(*args):
        st.session_state.answer = None
        st.session_state.results = None

    image = Image.open('bushmankim.png')

    left_co, cent_co,last_co = st.columns(3)
    with cent_co:
        st.image(image, caption="G'day cobba")

    # Title
    st.write("# Bushman Kim Demo")
    st.markdown(
        """Ask BK a Question about the **Australian** Medicare system, he'll search some relevant resources and try to give you a straight answer in less than 100 words.""",
        unsafe_allow_html=True,)

    # Sidebar
    st.sidebar.header("Options")
    eval_mode = st.sidebar.checkbox("Evaluation mode")
    debug = st.sidebar.checkbox("Show debug info")

    st.sidebar.markdown(
        f"""
    <style>
        a {{
            text-decoration: none;
        }}
        .haystack-footer {{
            text-align: center;
        }}
        .haystack-footer h4 {{
            margin: 0.1rem;
            padding:0;
        }}
        footer {{
            opacity: 0;
        }}
    </style>
    <div class="haystack-footer">
        <hr />
        <h4>Built with <a href="https://haystack.deepset.ai/">Haystack</a> 1.14.0</h4>
        <p>Get it on <a href="https://github.com/deepset-ai/haystack/">GitHub</a> &nbsp;&nbsp; - &nbsp;&nbsp; Read the <a href="https://docs.haystack.deepset.ai/docs">Docs</a></p>
    </div>
    """,
        unsafe_allow_html=True,
    )

    question = st.text_input(
        value=st.session_state.question,
        max_chars=250,
        on_change=reset_results,
        label="question",
        label_visibility="hidden",
    )
    col1 = st.columns(1)[0]
    col1.markdown("<style>.stButton button {width:100%;}</style>", unsafe_allow_html=True)

    # Run button
    run_pressed = col1.button("Ask")

    run_query = (
        run_pressed or question != st.session_state.question
    ) 

    # Check the connection
    with st.spinner("⌛️ &nbsp;&nbsp; Hold up, let me get me glasses on..."):
        if not haystack_is_ready():
            st.error("🚫 &nbsp;&nbsp; Something's up mate. Maybe come back later.")
            run_query = False
            reset_results()

    results_section = st.container()
    
    st.markdown("""## THIS IS NOT MEDICAL ADVICE

OuchMate is just a demo which gives you a general gist. For the love of god consult an actual doctor or the [official sources](https://www.health.gov.au/topics/medicare/about/what-medicare-covers) before making important decisions.""", 
    unsafe_allow_html=True)

    # Get results for query
    if run_query and question:
        st.session_state.question = question
        with results_section:
            with st.spinner(
                "🔭🧠 &nbsp;&nbsp; Performing a bloody neural search mate, should take about 15 seconds..."
            ):
                try:
                    st.session_state.results = bushman_steve(question)
                except JSONDecodeError as je:
                    st.error("👓 &nbsp;&nbsp; An error occurred reading the results. Is the document store working?")
                    return
                except Exception as e:
                    logging.exception(e)
                    if "The server is busy processing requests" in str(e) or "503" in str(e):
                        st.error("🧑‍🌾 &nbsp;&nbsp; All our workers are busy! Try again later.")
                    else:
                        st.error("🐞 &nbsp;&nbsp; An error occurred during the request.")
                    return
            
    if st.session_state.results:
        with results_section:
            st.write("## Answer (NOT ACTUAL MEDICAL ADVICE):")

            st.write(escape_special_characters(st.session_state.results['results'][0]))

            with st.expander("**Sources**"):
                for count, result in enumerate(st.session_state.results['invocation_context']['documents'][:3]):
                    if result["content"]:
                        st.text(result["content"])
                        
                        source = f"[{result['meta']['url']}]({result['meta']['url']})"
                        st.markdown(f"**Relevance:** {result['score']} -  **Source:** {source}")

                    else:
                        st.info(
                            "🤔 &nbsp;&nbsp; Haystack is unsure whether any of the documents contain an answer to your question. Try to reformulate it!"
                        )
                        st.write("**Relevance:** ", result["relevance"])

                    if eval_mode and result["answer"]:
                        # Define columns for buttons
                        is_correct_answer = None
                        is_correct_document = None

                        button_col1, button_col2, button_col3, _ = st.columns([1, 1, 1, 6])
                        if button_col1.button("👍", key=f"{result['context']}{count}1", help="Correct answer"):
                            is_correct_answer = True
                            is_correct_document = True

                        if button_col2.button("👎", key=f"{result['context']}{count}2", help="Wrong answer and wrong passage"):
                            is_correct_answer = False
                            is_correct_document = False

                        if button_col3.button(
                            "👎👍", key=f"{result['context']}{count}3", help="Wrong answer, but correct passage"
                        ):
                            is_correct_answer = False
                            is_correct_document = True

                        if is_correct_answer is not None and is_correct_document is not None:
                            try:
                                send_feedback(
                                    query=question,
                                    answer_obj=result["_raw"],
                                    is_correct_answer=is_correct_answer,
                                    is_correct_document=is_correct_document,
                                    document=result["document"],
                                )
                                st.success("✨ &nbsp;&nbsp; Thanks for your feedback! &nbsp;&nbsp; ✨")
                            except Exception as e:
                                logging.exception(e)
                                st.error("🐞 &nbsp;&nbsp; An error occurred while submitting your feedback!")

                    st.write("___")           

main()
