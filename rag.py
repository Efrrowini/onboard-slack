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

def chunk_handbook(content):
    """Split handbook into overlapping chunks for better retrieval"""
    chunks = []
    
    # Split by major sections
    lines = content.split("\n")
    current_chunk = []
    current_title = ""
    
    for line in lines:
        # Detect section headers (all caps lines)
        if line.strip() and line.strip() == line.strip().upper() and len(line.strip()) > 3:
            # Save previous chunk
            if current_chunk:
                chunk_text = current_title + "\n" + "\n".join(current_chunk)
                if len(chunk_text.strip()) > 50:
                    chunks.append(chunk_text.strip())
            current_title = line.strip()
            current_chunk = []
        else:
            current_chunk.append(line)
    
    # Add last chunk
    if current_chunk:
        chunk_text = current_title + "\n" + "\n".join(current_chunk)
        if len(chunk_text.strip()) > 50:
            chunks.append(chunk_text.strip())
    
    # Also add the full content as one big chunk for broad questions
    chunks.append(content[:3000])
    
    return chunks

def load_and_index_handbook():
    """Split handbook into chunks and index in ChromaDB"""
    if collection.count() > 0:
        print("Handbook already indexed.")
        return

    with open("docs/volunteer_handbook.txt", "r") as f:
        content = f.read()

    chunks = chunk_handbook(content)
    print(f"Indexing {len(chunks)} chunks...")

    collection.add(
        documents=chunks,
        ids=[f"chunk_{i}" for i in range(len(chunks))]
    )
    print("Handbook indexed successfully.")

def search_handbook(query, n_results=4):
    """Search handbook for relevant chunks"""
    results = collection.query(
        query_texts=[query],
        n_results=min(n_results, collection.count())
    )
    docs = results["documents"][0]
    return "\n\n".join(docs)

if __name__ == "__main__":
    load_and_index_handbook()
    result = search_handbook("what programs can I volunteer for?")
    print("Search result:")
    print(result)