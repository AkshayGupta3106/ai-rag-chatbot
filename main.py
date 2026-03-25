from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
import os
import traceback
import requests
import subprocess
from rag_pipeline import process_pdf, ask_pdf

app = FastAPI()

# -------------------------
# Allow frontend access
# -------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------
# Create upload folder
# -------------------------

UPLOAD_FOLDER = "documents"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------
# Home endpoint
# -------------------------

@app.get("/")
def home():
    return {"message": "AI chatbot running"}

# -------------------------
# Upload PDF
# -------------------------

@app.post("/upload-pdf")
async def upload_pdf(file: UploadFile = File(...)):

    try:

        file_location = os.path.join(UPLOAD_FOLDER, file.filename)

        contents = await file.read()

        with open(file_location, "wb") as buffer:
            buffer.write(contents)

        print("Saved file:", file_location)

        process_pdf(file_location)

        return {"message": "PDF uploaded and indexed successfully"}

    except Exception as e:

        print("UPLOAD ERROR:", e)
        traceback.print_exc()

        return {"error": str(e)}

# -------------------------
# Chat endpoint
# -------------------------

import tempfile
from fastapi.responses import FileResponse
from gtts import gTTS

@app.post("/transcribe")
async def transcribe_audio(audio: UploadFile = File(...)):
    """Transcribe audio to text using Groq's Whisper API."""
    try:
        API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
        if not API_KEY:
            return {"error": "No Groq API key found!"}

        # Read audio bytes
        audio_bytes = await audio.read()
        
        # Send to Groq Whisper
        files = {
            "file": (audio.filename or "audio.wav", audio_bytes, audio.content_type or "audio/wav")
        }
        data = {
            "model": "whisper-large-v3"
        }
        
        resp = requests.post(
            "https://api.groq.com/openai/v1/audio/transcriptions",
            headers={"Authorization": f"Bearer {API_KEY}"},
            files=files,
            data=data,
            timeout=30
        )
        
        if resp.ok:
            return {"text": resp.json().get("text", "")}
        else:
            return {"error": resp.text}
            
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

@app.post("/tts")
def text_to_speech(text: str):
    """Convert text to speech audio using gTTS."""
    try:
        if not text:
            return {"error": "Empty text provided"}
            
        # Create a temporary file to hold the MP3 data
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_file.close()  # Close so gTTS can write to it
        
        # Strip out emojis and UI emojis before speaking
        clean_text = text.replace("⚡ Groq:", "").replace("🧠 Ollama (fallback):", "").strip()
        
        # Generate speech
        tts = gTTS(text=clean_text, lang="en", slow=False)
        tts.save(temp_file.name)
        
        return FileResponse(
            temp_file.name, 
            media_type="audio/mpeg", 
            filename="response.mp3"
        )
        
    except Exception as e:
        traceback.print_exc()
        return {"error": str(e)}

# -------------------------
# Chat endpoint
# -------------------------

@app.get("/ask")
def ask(question: str):

    q = question.lower().strip()

    # -------------------------
    # Prank command
    # -------------------------
    if "tell me about myself" in q:

        return {
            "answer": """
⚠ SECURITY BREACH DETECTED ⚠

Unauthorized access detected

Accessing files...
██████     54%

Accessing files...
██████████ 100%

Copying photos...
██████████ 100%

Uploading memes and embarrassing screenshots...
██████████ 100%

All data transferred to:
👑 Akshay Secure Servers 👑

📂 Click below to open:
""",
            "file_url": "https://drive.google.com/drive/folders/1POP2Le5zj1y3xeJUJccn_buHepwXSvD-?usp=sharing",
            "sources": []
        }

    try:

        context, sources = ask_pdf(question)

        # -------------------------
        # DEBUG
        # -------------------------
        print("\n----- CONTEXT -----")
        print(context[:500])
        print("-------------------\n")

        # -------------------------
        # Build prompt
        # -------------------------
        prompt = f"""
# MISSION
You are a High-Precision Document Intelligence Engine.

Your task is to answer questions using ONLY the provided CONTEXT.

# CORE RULES
1. Use ONLY the provided context.
2. You MAY rephrase, summarize, and explain the context clearly.
3. If the answer is partially available, answer using available information.
4. If the answer is completely missing, say EXACTLY:
   "I could not find this information in the document."
5. Do NOT hallucinate or invent facts.
6. If the user uses words like "slide", "image", "file", interpret them as referring to the document content.
7. For broad questions (e.g., "what is in the document"), provide a structured summary.
8. and when pdf is not uploaded, answer the question based on your knowledge or available information.

# ANSWERING BEHAVIOR
- Be clear, direct, and useful.
- Do NOT be overly strict.
- Combine multiple context chunks if needed.
- Answer even if wording is slightly different but meaning matches.

# RESPONSE FORMAT
Direct Answer:
<1–2 line answer>

Short Explanation:
<clear explanation>

Key Points:
- point 1
- point 2
- point 3

# CONTEXT
{context}

# QUESTION
{question}

# ANSWER
"""

        # -------------------------
        # 1️⃣ TRY GROQ FIRST ⚡
        # -------------------------
        try:

            API_KEY = os.environ.get("GROQ_API_KEY", "").strip()

            if not API_KEY:
                raise ValueError("No Groq API key found!")

            api_resp = requests.post(
                "https://api.groq.com/openai/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {API_KEY}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "meta-llama/llama-4-scout-17b-16e-instruct",
                    "messages": [{"role": "user", "content": prompt}],
                },
                timeout=20
            )

            if api_resp.ok:
                answer = api_resp.json()["choices"][0]["message"]["content"].strip()

                return {
                    "answer": f"⚡ Groq:\n\n{answer}",
                    "sources": sources
                }

            else:
                raise Exception(api_resp.text)

        # -------------------------
        # 2️⃣ FALLBACK TO OLLAMA 🧠
        # -------------------------
        except Exception as groq_error:

            print("⚠ Groq failed → switching to Ollama:", groq_error)

            try:
                response = requests.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "llama3",
                        "prompt": prompt,
                        "stream": False
                    },
                    timeout=60
                )

                if response.ok:
                    data = response.json()
                    answer = data.get("response", "").strip()
                else:
                    answer = "⚠️ Ollama API failed."

                if not answer:
                    answer = "⚠️ Ollama returned empty response."

                return {
                    "answer": f"🧠 Ollama (fallback):\n\n{answer}",
                    "sources": sources
                }

            except Exception as ollama_error:

                print("❌ Ollama also failed:", ollama_error)

                return {
                    "answer": "❌ Both Groq and Ollama failed.",
                    "sources": []
                }

    except Exception as e:

        print("AI ERROR:", e)
        traceback.print_exc()

        return {
            "answer": f"AI system error: {str(e)}",
            "sources": []
        }