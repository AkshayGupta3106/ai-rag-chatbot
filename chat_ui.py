# chat_ui.py
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
# CSS (🔥 sexy UI)
# -------------------------
st.markdown("""
<style>
.main {
    background: linear-gradient(180deg, #0f172a, #020617);
    color: #e2e8f0;
}

.chat-bubble-user {
    background: linear-gradient(135deg, #0ea5a4, #0891b2);
    padding: 10px 14px;
    border-radius: 14px;
    color: white;
    display: inline-block;
    margin: 6px 0;
}

.chat-bubble-bot {
    background: #1e293b;
    padding: 10px 14px;
    border-radius: 14px;
    color: #e2e8f0;
    display: inline-block;
    margin: 6px 0;
}

.small-text {
    font-size: 12px;
    color: gray;
}
</style>
""", unsafe_allow_html=True)

# -------------------------
# Helpers
# -------------------------
def safe_json(resp):
    try:
        return resp.json()
    except:
        return resp.text


def make_file_tuple(uploaded_file):
    content = uploaded_file.getvalue()
    return (uploaded_file.name, io.BytesIO(content), "application/pdf")


def render_message(role, content):
    if role == "user":
        st.markdown(f"""
        <div style="text-align:right;">
            <div class="chat-bubble-user">{content}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div style="text-align:left;">
            <div class="chat-bubble-bot">{content}</div>
        </div>
        """, unsafe_allow_html=True)

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
# LEFT COLUMN
# =========================================================
with left_col:

    st.header("📂 Upload PDF")

    uploaded_file = st.file_uploader("Choose a PDF", type=["pdf"])

    if uploaded_file:
        st.success(f"Selected: {uploaded_file.name}")

    if st.button("🚀 Upload & Index", disabled=uploaded_file is None):

        try:
            files = {"file": make_file_tuple(uploaded_file)}

            with st.spinner("⚡ Processing document..."):

                resp = requests.post(
                    f"{API_URL}/upload-pdf",
                    files=files,
                    timeout=UPLOAD_TIMEOUT
                )

            if resp.ok:
                st.success("✅ PDF processed successfully!")
                st.session_state.uploaded_file_name = uploaded_file.name
            else:
                st.error(f"Upload failed: {resp.status_code}")
                st.write(resp.text)

        except Exception as e:
            st.error("Backend connection failed")
            st.exception(e)

# =========================================================
# RIGHT COLUMN
# =========================================================
with right_col:

    st.header("💬 Chat with your document")

    if st.session_state.uploaded_file_name:
        st.info(f"📄 Loaded: {st.session_state.uploaded_file_name}")

    # -------------------------
    # Chat history
    # -------------------------
    for msg in st.session_state.messages:

        if msg["role"] == "user":
            render_message("user", msg["content"])

        else:
            if isinstance(msg["content"], dict):

                answer = msg["content"].get("answer", "")
                file_url = msg["content"].get("file_url")
                sources = msg["content"].get("sources", [])
                audio_bytes = msg["content"].get("audio_bytes")

                render_message("assistant", answer)
                
                if audio_bytes:
                    st.audio(audio_bytes, format="audio/mpeg")

                if file_url:
                    st.markdown(f"[📂 Open document]({file_url})")

                if sources:
                    with st.expander("📚 Sources"):
                        for s in sources:
                            st.write("•", s)

            else:
                render_message("assistant", msg["content"])

    # -------------------------
    # Chat input
    # -------------------------
    from streamlit_mic_recorder import mic_recorder
    
    # Track latest audio to prevent infinite loops on st.rerun()
    if "last_audio_id" not in st.session_state:
        st.session_state.last_audio_id = None

    # We use columns to put the mic button next to the chat input prompt area
    st.write("Voice Input:")
    audio = mic_recorder(
        start_prompt="🎤 Click to Speak",
        stop_prompt="🛑 Stop Recording",
        key="recorder"
    )

    question = st.chat_input("...or type something about the document")

    # If voice was recorded and it's NEW audio
    if audio and audio.get("id") != st.session_state.last_audio_id:
        st.session_state.last_audio_id = audio.get("id")
        with st.spinner("🎧 Transcribing voice..."):
            try:
                files = {"audio": ("audio.wav", audio["bytes"], "audio/wav")}
                transcribe_resp = requests.post(f"{API_URL}/transcribe", files=files, timeout=30)
                if transcribe_resp.ok:
                    question = transcribe_resp.json().get("text", "").strip()
                    if not question:
                        st.warning("Could not hear any speech. Please try again.")
                        question = None # Clear question so it doesn't trigger chat
                else:
                    st.error("Failed to transcribe audio.")
            except Exception as e:
                st.error("Microphone backend error")

    if question:

        st.session_state.messages.append(
            {"role": "user", "content": question}
        )

        with st.spinner("🤖 Thinking..."):

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

            except Exception:
                st.session_state.messages.append(
                    {
                        "role": "assistant",
                        "content": "❌ Backend connection error"
                    }
                )

        st.rerun()

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.caption("⚡ Hybrid RAG Chatbot | Groq + Ollama | Built by Akshay 😤")