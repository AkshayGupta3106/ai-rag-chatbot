from langchain_community.document_loaders import PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings

# Load embeddings ONCE (important for speed)
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2"
)


def process_pdf(file_path):
    import shutil

    # 🔥 CLEAR OLD DB
    if os.path.exists("./db"):
        shutil.rmtree("./db")

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