import os
import sys
import logging
from pathlib import Path
from json import JSONDecodeError

import pandas as pd
import streamlit as st
from markdown import markdown
import time

from ui.utils import haystack_is_ready, send_feedback, ouchmate_query

DEFAULT_QUESTION_AT_STARTUP = os.getenv("DEFAULT_QUESTION_AT_STARTUP", "If I break my leg and have to go to hospital, how much will I have to pay, roughly?")

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

    # Title
    st.write("# OuchMate Demo")
    st.markdown(
        """Ask a Question about the **Australian** Medicare system. 

OuchMate will search a bunch of relevant resources and try to give you a straight answer.

## This is not medical advice

OuchMate just gives a general gist. For the love of god consult the sources or an actual doctor or something before making any important decisions.""",
        unsafe_allow_html=True,
    )

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

    # Search bar
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

    # Get results for query
    if run_query and question:
        reset_results()
        st.session_state.question = question

        with st.spinner(
            "🔭🧠 &nbsp;&nbsp; Performing a bloody neural search mate..."
        ):
            try:
                st.session_state.results = ouchmate_query(question)
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
        st.write("## Answer:")
        st.write(st.session_state.results['results'][0])

        with st.expander("References"):
            st.write("#### References:")

            for count, result in enumerate(st.session_state.results['invocation_context']['documents'][:3]):
                if result["content"]:
                    st.write(
                        markdown("<sup><sub>" + result["content"] + "</sub></sup>"),
                        unsafe_allow_html=True,
                    )
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
