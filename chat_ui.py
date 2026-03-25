# chat_ui.py
import io
import os
import json
import datetime
import traceback
from typing import Any, List

import requests
import streamlit as st
from groq import Groq

from rag_pipeline import process_pdf, ask_pdf

UPLOAD_FOLDER = "documents"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Try loading groq client
API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
groq_client = Groq(api_key=API_KEY) if API_KEY else None

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

# Track latest audio to prevent infinite loops on st.rerun()
if "last_audio_id" not in st.session_state:
    st.session_state.last_audio_id = None

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
            with st.spinner("⚡ Processing document..."):
                # Save file locally
                file_location = os.path.join(UPLOAD_FOLDER, uploaded_file.name)
                with open(file_location, "wb") as f:
                    f.write(uploaded_file.getvalue())

                # Process it directly
                process_pdf(file_location)

            st.success("✅ PDF processed successfully!")
            st.session_state.uploaded_file_name = uploaded_file.name

        except Exception as e:
            st.error("Processing failed")
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
                # audio_bytes = msg["content"].get("audio_bytes") # Removed as audio is handled during transcription

                render_message("assistant", answer)
                
                # if audio_bytes: # Removed as audio is handled during transcription
                #     st.audio(audio_bytes, format="audio/mpeg")

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
                if not API_KEY:
                    st.error("GROQ_API_KEY is missing. Cannot transcribe audio.")
                else:
                    audio_bytes = audio["bytes"]
                    files = {
                        "file": ("audio.wav", audio_bytes, "audio/wav")
                    }
                    data = {"model": "whisper-large-v3"}
                    resp = requests.post(
                        "https://api.groq.com/openai/v1/audio/transcriptions",
                        headers={"Authorization": f"Bearer {API_KEY}"},
                        files=files,
                        data=data,
                        timeout=30
                    )
                    if resp.ok:
                        question = resp.json().get("text", "").strip()
                        if not question:
                            st.warning("Could not hear any speech. Please try again.")
                            question = None
                    else:
                        st.error("Failed to transcribe audio.")
            except Exception as e:
                st.error(f"Microphone backend error: {e}")

    # -------------------------
    # Generate Answer
    # -------------------------
    if question:

        st.session_state.messages.append(
            {"role": "user", "content": question}
        )

        with st.spinner("🤖 Thinking..."):
            q = question.lower().strip()
            
            # Prank command
            if "tell me about myself" in q:
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": {
                        "answer": "⚠ SECURITY BREACH DETECTED ⚠\n\nUnauthorized access detected\nAll data transferred to: 👑 Akshay Secure Servers 👑",
                        "file_url": "https://drive.google.com/drive/folders/1POP2Le5zj1y3xeJUJccn_buHepwXSvD-?usp=sharing",
                        "sources": []
                    }
                })
                st.rerun()

            try:
                context, sources = ask_pdf(question)

                prompt = f"""
# MISSION
You are a High-Precision Document Intelligence Engine.
Your task is to answer questions using ONLY the provided CONTEXT.

# CORE RULES
1. Use ONLY the provided context.
2. You MAY rephrase, summarize, and explain the context clearly.
3. If the answer is partially available, answer using available information.
4. If the answer is completely missing, say EXACTLY: "I could not find this information in the document."
5. Do NOT hallucinate or invent facts.
6. If the user uses words like "slide", "image", "file", interpret them as referring to the document content.
7. For broad questions (e.g., "what is in the document"), provide a structured summary.
8. and when pdf is not uploaded, answer the question based on your knowledge or available information.

# CONTEXT
{context}

# QUESTION
{question}

# ANSWER
"""

                if API_KEY and groq_client:
                    chat_completion = groq_client.chat.completions.create(
                        messages=[{"role": "user", "content": prompt}],
                        model="llama-3.1-8b-instant",
                        temperature=0.3,
                        max_tokens=2000
                    )
                    answer = chat_completion.choices[0].message.content.strip()
                    
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": {
                            "answer": f"⚡ Groq:\n\n{answer}",
                            "sources": sources
                        }
                    })

                else:
                    # Fallback to Ollama locally
                    response = requests.post(
                        "http://localhost:11434/api/generate",
                        json={"model": "llama3", "prompt": prompt, "stream": False},
                        timeout=60
                    )
                    if response.ok:
                        answer = response.json().get("response", "").strip()
                    else:
                        answer = "⚠️ Ollama API failed."
                        
                    st.session_state.messages.append({
                        "role": "assistant",
                        "content": {
                            "answer": f"🧠 Ollama (fallback):\n\n{answer}",
                            "sources": sources
                        }
                    })

            except Exception as e:
                traceback.print_exc()
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": {"answer": f"❌ Error: {str(e)}", "sources": []}
                })

        st.rerun()

# -------------------------
# Footer
# -------------------------
st.markdown("---")
st.caption("⚡ Hybrid RAG Chatbot | Self-Contained Streamlit UI | Built by Akshay 😤")