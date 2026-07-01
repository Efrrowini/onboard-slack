import os
import chromadb
from chromadb.utils import embedding_functions

# Setup ChromaDB
chroma_client = chromadb.PersistentClient(path="./data/chroma")

embedding_fn = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="all-MiniLM-L6-v2"
)

collection = chroma_client.get_or_create_collection(
    name="volunteer_handbook",
    embedding_function=embedding_fn
)

def load_and_index_handbook():
    """Split handbook into chunks and index in ChromaDB"""
    if collection.count() > 0:
        print("Handbook already indexed.")
        return

    with open("docs/volunteer_handbook.txt", "r") as f:
        content = f.read()

    # Split into sections by double newline
    chunks = [c.strip() for c in content.split("\n\n") if c.strip()]

    print(f"Indexing {len(chunks)} chunks...")

    collection.add(
        documents=chunks,
        ids=[f"chunk_{i}" for i in range(len(chunks))]
    )
    print("Handbook indexed successfully.")

def search_handbook(query, n_results=3):
    """Search handbook for relevant chunks"""
    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count())
    )
    docs = results["documents"][0]
    return "\n\n".join(docs)

if __name__ == "__main__":
    load_and_index_handbook()
    # Test search
    result = search_handbook("when is orientation?")
    print("Search result:")
    print(result)