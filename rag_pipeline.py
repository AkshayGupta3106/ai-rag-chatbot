from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Load embeddings ONCE (important for speed)
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


def process_pdf(file_path):

    loader = PyPDFLoader(file_path)
    documents = loader.load()

    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1500,
        chunk_overlap=500
    )

    docs = text_splitter.split_documents(documents)

    db = Chroma.from_documents(
        docs,
        embeddings,
        persist_directory="./db"
    )

    return "PDF processed successfully"


def ask_pdf(question):

    db = Chroma(
        persist_directory="./db",
        embedding_function=embeddings
    )

    docs = db.similarity_search(question, k=3)

    if not docs:
        return "", []

    context = ""
    sources = []

    for doc in docs:

        context += doc.page_content + "\n"

        page = doc.metadata.get("page", "unknown")
        source = doc.metadata.get("source", "document")

        sources.append(f"Page {page} — {source}")

    return context, sources