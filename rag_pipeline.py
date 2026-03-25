import os
import shutil

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

from ocr_pipeline import pdf_to_text_via_ocr

# Absolute path to DB — avoids CWD issues on Windows
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "db")

# Load embeddings ONCE (important for speed)
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


def load_pdf(file_path: str) -> list:
    """Use Groq vision OCR to extract text, return LangChain Document objects."""
    raw_pages = pdf_to_text_via_ocr(file_path)
    return [
        Document(
            page_content=p["page_content"],
            metadata=p["metadata"]
        )
        for p in raw_pages
    ]


def process_pdf(file_path):

    # 🔥 CLEAR OLD DB — use delete_collection() to avoid Windows file-lock issues
    if os.path.exists(DB_PATH):
        try:
            old_db = Chroma(persist_directory=DB_PATH, embedding_function=embeddings)
            old_db.delete_collection()
            del old_db
        except Exception:
            pass
        shutil.rmtree(DB_PATH, ignore_errors=True)

    # Load PDF via OCR pipeline
    documents = load_pdf(file_path)

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=500
    )

    docs = text_splitter.split_documents(documents)

    db = Chroma.from_documents(
        docs,
        embeddings,
        persist_directory=DB_PATH
    )

    return "PDF processed successfully"


def ask_pdf(question):

    db = Chroma(
        persist_directory=DB_PATH,
        embedding_function=embeddings
    )

    docs = db.max_marginal_relevance_search(question, k=3, fetch_k=10)

    if not docs:
        return "", []

    context_chunks = []
    sources = []
    seen = set()

    for doc in docs:

        chunk = doc.page_content.strip()

        if chunk not in context_chunks:
            context_chunks.append(chunk)

        page = doc.metadata.get("page", "unknown")
        source = doc.metadata.get("source", "document")

        key = f"{page}-{source}"

        if key not in seen:
            seen.add(key)
            sources.append(f"Page {page} — {source}")

    context = "\n\n".join(context_chunks)
    context = context[:2000]

    return context, sources