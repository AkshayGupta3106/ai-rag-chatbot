# chat_ui.py
"""
Streamlit chat UI for AI Document Chatbot
"""

import io
import json
import datetime
from typing import Any, List

import requests
import streamlit as st

API_URL = "http://127.0.0.1:8000"
UPLOAD_TIMEOUT = 120

# -------------------------
# Page config
# -------------------------
st.set_page_config(
    page_title="AI Document Chatbot",
    layout="wide"
)

# -------------------------
# Helper functions
# -------------------------
def safe_json(resp: requests.Response):
    try:
        return resp.json()
    except:
        return resp.text


def make_file_tuple(uploaded_file):
    content = uploaded_file.getvalue()
    return (uploaded_file.name, io.BytesIO(content), "application/pdf")


# -------------------------
# Session state
# -------------------------
if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_file_name" not in st.session_state:
    st.session_state.uploaded_file_name = None

# -------------------------
# Layout
# -------------------------
left_col, right_col = st.columns([1, 2])

# =========================================================
# LEFT COLUMN (UPLOAD)
# =========================================================
with left_col:

    st.header("Upload PDF")

    uploaded_file = st.file_uploader("Upload your PDF", type=["pdf"])

    if uploaded_file:
        st.write("Selected:", uploaded_file.name)

    if st.button("Upload & Index", disabled=uploaded_file is None):

        try:
            files = {"file": make_file_tuple(uploaded_file)}

            with st.spinner("Uploading..."):

                resp = requests.post(
                    f"{API_URL}/upload-pdf",
                    files=files,
                    timeout=UPLOAD_TIMEOUT
                )

            if resp.ok:
                st.success("PDF processed successfully!")
                st.session_state.uploaded_file_name = uploaded_file.name
            else:
                st.error(f"Upload failed: {resp.status_code}")
                st.write(resp.text)

        except Exception as e:
            st.error("Backend connection failed")
            st.exception(e)

# =========================================================
# RIGHT COLUMN (CHAT)
# =========================================================
with right_col:

    st.header("Chat with your document")

    if st.session_state.uploaded_file_name:
        st.info(f"Loaded: {st.session_state.uploaded_file_name}")

    # Display chat history
    for msg in st.session_state.messages:

        if msg["role"] == "user":
            st.chat_message("user").write(msg["content"])

        else:
            if isinstance(msg["content"], dict):

                answer = msg["content"].get("answer", "")
                file_url = msg["content"].get("file_url")
                sources = msg["content"].get("sources", [])

                st.chat_message("assistant").write(answer)

                if file_url:
                    st.markdown(f"[Open document]({file_url})")

                if sources:
                    with st.expander("Sources"):
                        for s in sources:
                            st.write("-", s)

            else:
                st.chat_message("assistant").write(msg["content"])

    # -------------------------
    # Chat input
    # -------------------------
    question = st.chat_input("Ask something about the document...")

    if question:

        st.session_state.messages.append(
            {"role": "user", "content": question}
        )

        try:

            resp = requests.get(
                f"{API_URL}/ask",
                params={"question": question},
                timeout=30
            )

            if resp.ok:

                data = safe_json(resp)

                if isinstance(data, dict):
                    assistant_msg = data
                else:
                    assistant_msg = str(data)

                st.session_state.messages.append(
                    {"role": "assistant", "content": assistant_msg}
                )

            else:
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": f"Server error {resp.status_code}"
                    }
                )

        except Exception as e:

            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": "Backend connection error"
                }
            )

        st.rerun()


# =========================================================
# Footer
# =========================================================
st.markdown("---")
st.caption(
    "Tip: Make sure FastAPI backend is running at http://127.0.0.1:8000"
)