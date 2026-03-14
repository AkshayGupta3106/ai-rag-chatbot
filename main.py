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

        # If PDF context exists → use RAG
        if context.strip():

            prompt = f"""
Answer the question using the context below.

Context:
{context}

Question:
{question}
"""

        else:
            # Normal LLM chat
            prompt = question

        OLLAMA_PATH = r"C:\Users\aksha\AppData\Local\Programs\Ollama\ollama.exe"

        result = subprocess.run(
            [OLLAMA_PATH, "run", "llama3", prompt],
            capture_output=True,
            text=True,
            encoding="utf-8"
        )

        answer = result.stdout.strip()

        if not answer:
            answer = "⚠️ Ollama returned empty response."

        return {
            "answer": answer,
            "sources": sources
        }

    except Exception as e:

        print("AI ERROR:", e)
        traceback.print_exc()

        return {
            "answer": f"AI system error: {str(e)}",
            "sources": []
        }