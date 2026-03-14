from fastapi import FastAPI
import subprocess

app = FastAPI()

@app.get("/")
def home():
    return {"message": "AI Chatbot Running"}

@app.get("/chat")
def chat(question: str):

    response = subprocess.run(
        ["ollama", "run", "llama3", question],
        capture_output=True,
        text=True
    )

    return {"question": question, "answer": response.stdout}
