# search.py
import os
import sys
import argparse
from pathlib import Path
import glob
import json
from datetime import datetime
from typing import List, Dict, Any

# RAG components
from langchain_community.embeddings import OpenAIEmbeddings, HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

def load_config():
    """Load API keys from config file"""
    with open('composer/config.json', 'r') as f:
        return json.load(f)

def initialize_embeddings(config):
    """Initialize embeddings model based on available API keys"""
    if config.get("openai_api_key"):
        return OpenAIEmbeddings(api_key=config.get("openai_api_key"))
    else:
        # Fallback to local model that doesn't require API keys
        return HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

def extract_yaml_front_matter(content: str) -> Dict[str, Any]:
    """Extract YAML front matter from markdown content"""
    front_matter = {}
    
    # Check if the content has YAML front matter (starts with ---)
    if content.startswith('---'):
        # Find the closing --- of the front matter
        end_index = content.find('---', 3)
        if end_index != -1:
            # Extract the YAML content
            yaml_content = content[3:end_index].strip()
            
            # Parse the YAML content
            try:
                import yaml
                front_matter = yaml.safe_load(yaml_content)
            except Exception as e:
                print(f"Error parsing YAML front matter: {e}")
    
    return front_matter

def load_documents(directory: str, tags: List[str] = None) -> List[Document]:
    """
    Load all text files from directory
    If tags is provided, only include files with matching tags in YAML front matter
    """
    documents = []
    dir_path = Path(directory)
    
    if not dir_path.exists():
        print(f"Warning: Directory '{directory}' does not exist. Creating it.")
        dir_path.mkdir(exist_ok=True)
        return documents
    
    # Find all text/markdown files recursively
    file_paths = []
    for ext in [".txt", ".md", ".html", ".json", ".csv"]:
        file_paths.extend(glob.glob(os.path.join(directory, f"**/*{ext}"), recursive=True))
    
    for file_path in file_paths:
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            # If tags are specified, check if the file has matching tags
            if tags:
                # Only check for tags in markdown files
                if file_path.endswith(('.md', '.markdown')):
                    front_matter = extract_yaml_front_matter(content)
                    file_tags = front_matter.get('tags', [])
                    
                    # Skip this file if it doesn't have any of the specified tags
                    if not any(tag in file_tags for tag in tags):
                        continue
            
            doc = Document(
                page_content=content,
                metadata={
                    "source": file_path,
                    "filename": os.path.basename(file_path),
                }
            )
            documents.append(doc)
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    print(f"Loaded {len(documents)} documents from {directory}" + 
          (f" with tags: {', '.join(tags)}" if tags else ""))
    return documents

def create_or_load_index(documents: List[Document], embeddings, index_name: str = "history_index"):
    """Create or load vector index"""
    # Create chunks for better retrieval
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = text_splitter.split_documents(documents)
    
    # Check if index already exists
    if os.path.exists(index_name) and os.path.isdir(index_name):
        print(f"Loading existing index from {index_name}")
        try:
            vector_db = FAISS.load_local(index_name, embeddings)
            return vector_db
        except Exception as e:
            print(f"Error loading index: {e}")
            print("Creating new index...")
    
    # Create new index
    print(f"Creating new index with {len(chunks)} chunks")
    vector_db = FAISS.from_documents(chunks, embeddings)
    
    # Save index
    vector_db.save_local(index_name)
    return vector_db

def search_documents(query: str, vector_db, k: int = 5) -> List[Document]:
    """Search for relevant documents"""
    results = vector_db.similarity_search(query, k=k)
    return results

def format_results(results: List[Document]) -> str:
    """Format search results for display"""
    output = []
    
    for i, doc in enumerate(results):
        metadata = doc.metadata
        source = metadata.get("source", "Unknown source")
        timestamp = metadata.get("timestamp")
        doc_type = metadata.get("type", "unknown")
        
        # Format timestamp if available
        time_str = ""
        if timestamp:
            time_str = f" ({timestamp.strftime('%Y-%m-%d %H:%M:%S')})"
        
        # Prepare header
        header = f"\n[{i+1}] {source}{time_str} - Type: {doc_type}"
        output.append(header)
        output.append("-" * len(header))
        
        # Add content preview (truncated if too long)
        content = doc.page_content
        if len(content) > 500:
            content = content[:500] + "..."
        output.append(content)
    
    return "\n".join(output)

def main():
    parser = argparse.ArgumentParser(description="Search through history documents using RAG")
    parser.add_argument("query", help="Search query")
    parser.add_argument("--dir", default="dialogue", help="Directory containing history documents")
    parser.add_argument("--rebuild", action="store_true", help="Force rebuild of the search index")
    parser.add_argument("--results", type=int, default=5, help="Number of results to return")
    args = parser.parse_args()
    
    # Initialize
    config = load_config()
    embeddings = initialize_embeddings(config)
    
    # Load documents
    documents = load_documents(args.dir)
    
    # Create or load vector index
    index_name = "history_index"
    if args.rebuild and os.path.exists(index_name):
        import shutil
        print(f"Rebuilding index - removing {index_name}")
        shutil.rmtree(index_name)
    
    vector_db = create_or_load_index(documents, embeddings, index_name)
    
    # Search for relevant documents
    results = search_documents(args.query, vector_db, k=args.results)
    
    # Format and print results
    if results:
        print(f"\nFound {len(results)} relevant documents for query: '{args.query}'\n")
        formatted_results = format_results(results)
        print(formatted_results)
    else:
        print(f"No relevant documents found for query: '{args.query}'")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
