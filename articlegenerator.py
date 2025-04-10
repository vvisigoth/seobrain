#!python3.12
"""
SEO Generation Script with RAG (Retrieval-Augmented Generation)

This script takes a text file where each line is an SEO keyword,
searches a knowledge base for relevant information using RAG,
and generates optimized content that covers multiple keywords in each article.
"""

import os
import sys
import argparse
import json
import requests
import random
from pathlib import Path
from typing import List, Dict, Any, Optional

# Import RAG components from search.py
from search import (
    load_config,
    initialize_embeddings,
    load_documents,
    create_or_load_index,
    search_documents
)

# Default settings
DEFAULT_MODEL = "anthropic/claude-3.7-sonnet"
DEFAULT_PROVIDER = "openrouter"
SERVER_URL = "http://localhost:5555"
OUTPUT_DIR = "seo_content"
DEFAULT_ARTICLE_COUNT = 50
DEFAULT_PREPROMPT_FILE = "preprompt.txt"
DEFAULT_KNOWLEDGE_DIR = "knowledge_base"
DEFAULT_INDEX_NAME = "seo_index"

def load_keywords(file_path: str) -> List[str]:
    """Load keywords from a text file, one per line."""
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def load_preprompt(file_path: str) -> str:
    """Load custom preprompt from a text file."""
    if not os.path.exists(file_path):
        return ""
    
    with open(file_path, 'r') as f:
        return f.read().strip()

def distribute_keywords(keywords: List[str], article_count: int) -> List[List[str]]:
    """
    Distribute all keywords across the specified number of articles.
    Each article will include multiple keywords.
    """
    # Ensure we don't create more articles than keywords
    article_count = min(article_count, len(keywords))
    
    # Shuffle keywords to randomize distribution
    shuffled_keywords = keywords.copy()
    random.shuffle(shuffled_keywords)
    
    # Calculate minimum keywords per article
    min_keywords_per_article = len(shuffled_keywords) // article_count
    remaining = len(shuffled_keywords) % article_count
    
    # Distribute keywords to articles
    articles = []
    index = 0
    for i in range(article_count):
        # Add one extra keyword to some articles if there are remainders
        count = min_keywords_per_article + (1 if i < remaining else 0)
        article_keywords = shuffled_keywords[index:index + count]
        articles.append(article_keywords)
        index += count
    
    return articles

def format_research_results(results: List[Any]) -> str:
    """Format search results for inclusion in the prompt"""
    if not results:
        return "No relevant research found."
    
    output = ["### Relevant Research Information:"]
    
    for i, doc in enumerate(results):
        metadata = doc.metadata
        source = metadata.get("source", "Unknown source")
        
        # Add source information
        output.append(f"\n#### Source {i+1}: {os.path.basename(source)}")
        
        # Add content
        content = doc.page_content
        output.append(content)
    
    return "\n".join(output)

def generate_seo_content(keywords: List[str], research: str, preprompt: str, model: str, provider: str, server_url: str) -> str:
    """Generate SEO content for a given set of keywords using the AI API with research data."""
    
    # Format the keywords for the prompt
    keywords_str = ", ".join([f'"{kw}"' for kw in keywords])
    primary_keyword = keywords[0]  # Use the first keyword as primary
    
    # Craft the prompt for SEO content generation
    base_prompt = f"""
Generate high-quality SEO content that incorporates ALL of the following keywords: {keywords_str}

Use "{primary_keyword}" as the primary focus, but naturally integrate all the other keywords throughout the article.

I've provided some research information below that may be relevant to these keywords. Use this information to make the 
article more authoritative, accurate, and valuable to readers. Incorporate relevant facts, statistics, and insights 
from the research where appropriate.

{research}

Please include:
1. A compelling H1 title (using markdown # syntax) that includes the primary keyword
2. A meta description (150-160 characters) that mentions 2-3 of the keywords
3. 5-7 relevant H2 subheadings (using markdown ## syntax) that incorporate different keywords
4. 800-1200 words of well-structured, informative content that naturally includes all keywords
5. A natural keyword density without keyword stuffing
6. A clear call-to-action at the end

The content should be engaging, informative, and optimized for search engines while providing genuine value to readers.
Ensure the article flows naturally and doesn't feel like it's artificially cramming in keywords.
"""

    # Combine preprompt with base prompt if preprompt exists
    prompt = f"{preprompt}\n\n{base_prompt}" if preprompt else base_prompt

    # Prepare request data
    request_data = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 4000,
        "temperature": 0.7,
        "provider": provider,
        "model": model
    }

    # Send request to server
    try:
        response = requests.post(
            f"{server_url}/api/generate",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )

        if response.status_code != 200:
            raise Exception(f"HTTP error: {response.status_code} - {response.text}")

        return response.json()["content"]
    
    except requests.exceptions.RequestException as e:
        raise Exception(f"Connection error: {str(e)}")

def save_content(primary_keyword: str, all_keywords: List[str], content: str, output_dir: str) -> str:
    """Save the generated content to a file and return the file path."""
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)
    
    # Create a filename from the primary keyword
    filename = primary_keyword.lower().replace(' ', '_').replace("'", "").replace('"', '')
    # Remove any special characters that might cause issues with filenames
    filename = ''.join(c for c in filename if c.isalnum() or c == '_' or c == '-')
    filepath = os.path.join(output_dir, f"{filename}.md")
    
    # Add a header comment with all keywords used
    keywords_comment = "<!--\nKeywords covered in this article:\n"
    for kw in all_keywords:
        keywords_comment += f"- {kw}\n"
    keywords_comment += "-->\n\n"
    
    # Save the content with the keywords comment
    with open(filepath, 'w') as f:
        f.write(keywords_comment + content)
    
    return filepath

def main():
    """Main function to run the SEO generation script with RAG."""
    parser = argparse.ArgumentParser(description="Generate SEO content from keywords with RAG")
    parser.add_argument("input_file", nargs='?', help="Text file containing keywords, one per line")
    parser.add_argument("-o", "--output", default=OUTPUT_DIR, help=f"Output directory (default: {OUTPUT_DIR})")
    parser.add_argument("-m", "--model", default=DEFAULT_MODEL, help=f"AI model to use (default: {DEFAULT_MODEL})")
    parser.add_argument("-p", "--provider", default=DEFAULT_PROVIDER, 
                        choices=["ollama", "openai", "openrouter", "anthropic"],
                        help=f"AI provider (default: {DEFAULT_PROVIDER})")
    parser.add_argument("-s", "--server", default=SERVER_URL, help=f"Server URL (default: {SERVER_URL})")
    parser.add_argument("-n", "--num-articles", type=int, default=DEFAULT_ARTICLE_COUNT,
                        help=f"Number of articles to generate (default: {DEFAULT_ARTICLE_COUNT})")
    parser.add_argument("--preprompt", default=DEFAULT_PREPROMPT_FILE, 
                        help=f"File containing custom instructions to prepend to the prompt (default: {DEFAULT_PREPROMPT_FILE})")
    parser.add_argument("--knowledge", default=DEFAULT_KNOWLEDGE_DIR,
                        help=f"Directory containing knowledge base documents (default: {DEFAULT_KNOWLEDGE_DIR})")
    parser.add_argument("--index", default=DEFAULT_INDEX_NAME,
                        help=f"Name of the vector index to create/use (default: {DEFAULT_INDEX_NAME})")
    parser.add_argument("--rebuild-index", action="store_true",
                        help="Force rebuild of the search index")
    parser.add_argument("--results", type=int, default=3,
                        help="Number of research results to include per article (default: 3)")
    parser.add_argument("--tags", nargs='+', 
                        help="Only include documents with these tags in the YAML front matter")
    
    # New arguments for single article generation
    parser.add_argument("--single", action="store_true",
                        help="Generate a single article with specified title and keywords")
    parser.add_argument("--title", 
                        help="Title for the single article (required with --single)")
    parser.add_argument("--keywords", nargs='+',
                        help="Keywords for the single article (required with --single)")
    
    args = parser.parse_args()
    
    # Validate arguments for single article mode
    if args.single:
        if not args.title:
            print("Error: --title is required when using --single")
            return 1
        if not args.keywords:
            print("Error: --keywords is required when using --single")
            return 1
    elif not args.input_file:
        print("Error: input_file is required when not using --single")
        return 1
    
    try:
        # Initialize RAG components
        print("Initializing RAG components...")
        config = load_config()
        embeddings = initialize_embeddings(config)
        
        # Create knowledge directory if it doesn't exist
        Path(args.knowledge).mkdir(exist_ok=True)
        
        # Load documents from knowledge base, filtering by tags if specified
        documents = load_documents(args.knowledge, args.tags)
        
        # Create or load vector index
        vector_db = create_or_load_index(documents, embeddings, args.index)
        
        # Load preprompt if file exists
        preprompt = load_preprompt(args.preprompt)
        if preprompt:
            print(f"Loaded custom preprompt from {args.preprompt}")
        
        if args.single:
            # Single article mode
            print(f"\nGenerating a single article with title: {args.title}")
            print(f"Keywords: {', '.join(args.keywords)}")
            
            # Search for relevant research for these keywords
            print("Searching for relevant research...")
            search_query = args.title + " " + " ".join(args.keywords)
            research_results = search_documents(search_query, vector_db, k=args.results)
            research_text = format_research_results(research_results)
            
            # Generate content with research data
            content = generate_seo_content(
                keywords=args.keywords,
                research=research_text,
                preprompt=preprompt,
                model=args.model,
                provider=args.provider,
                server_url=args.server
            )
            
            # Create a sanitized filename from the title
            sanitized_title = args.title.lower().replace(' ', '_').replace("'", "").replace('"', '')
            sanitized_title = ''.join(c for c in sanitized_title if c.isalnum() or c == '_' or c == '-')
            
            # Add YAML front matter with title and keywords
            yaml_front_matter = "---\n"
            yaml_front_matter += f"title: \"{args.title}\"\n"
            yaml_front_matter += "keywords:\n"
            for kw in args.keywords:
                yaml_front_matter += f"  - {kw}\n"
            yaml_front_matter += "Published: True\n"
            yaml_front_matter += "---\n\n"
            
            # Save content with YAML front matter
            filepath = os.path.join(args.output, f"{sanitized_title}.md")
            Path(args.output).mkdir(exist_ok=True)
            
            with open(filepath, 'w') as f:
                f.write(yaml_front_matter + content)
            
            print(f"Article saved to: {filepath}")
            
        else:
            # Original multi-article mode
            keywords = load_keywords(args.input_file)
            print(f"Loaded {len(keywords)} keywords from {args.input_file}")
            
            # Distribute keywords across articles
            article_keyword_sets = distribute_keywords(keywords, args.num_articles)
            print(f"Distributing keywords across {len(article_keyword_sets)} articles")
            
            # Process each article
            for i, article_keywords in enumerate(article_keyword_sets, 1):
                print(f"\n[{i}/{len(article_keyword_sets)}] Generating article with {len(article_keywords)} keywords")
                print(f"Keywords: {', '.join(article_keywords)}")
                
                # Search for relevant research for these keywords
                print("Searching for relevant research...")
                search_query = " ".join(article_keywords)
                research_results = search_documents(search_query, vector_db, k=args.results)
                research_text = format_research_results(research_results)
                
                # Generate content with research data
                content = generate_seo_content(
                    keywords=article_keywords,
                    research=research_text,
                    preprompt=preprompt,
                    model=args.model,
                    provider=args.provider,
                    server_url=args.server
                )
                
                # Save content using the first keyword as primary
                primary_keyword = article_keywords[0]
                filepath = save_content(primary_keyword, article_keywords, content, args.output)
                print(f"Article saved to: {filepath}")
    
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    if args.single:
        print(f"\nSingle article generation complete. Article saved to {args.output} directory.")
    else:
        print(f"\nSEO content generation complete. {len(article_keyword_sets)} articles saved to {args.output} directory.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
