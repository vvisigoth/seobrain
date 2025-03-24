#!python3.12
"""
SEO Generation Script

This script takes a text file where each line is an SEO keyword
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

# Default settings
DEFAULT_MODEL = "anthropic/claude-3.7-sonnet"
DEFAULT_PROVIDER = "openrouter"
SERVER_URL = "http://localhost:5555"
OUTPUT_DIR = "seo_content"
DEFAULT_ARTICLE_COUNT = 50

# Add to the constants at the top
DEFAULT_PREPROMPT_FILE = "preprompt.txt"

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

def generate_seo_content(keywords: List[str], preprompt: str, model: str, provider: str, server_url: str) -> str:
    """Generate SEO content for a given set of keywords using the AI API."""
    
    # Format the keywords for the prompt
    keywords_str = ", ".join([f'"{kw}"' for kw in keywords])
    primary_keyword = keywords[0]  # Use the first keyword as primary
    
    # Craft the prompt for SEO content generation
    base_prompt = f"""
Generate high-quality SEO content that incorporates ALL of the following keywords: {keywords_str}

Use "{primary_keyword}" as the primary focus, but naturally integrate all the other keywords throughout the article.

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
    """Main function to run the SEO generation script."""
    parser = argparse.ArgumentParser(description="Generate SEO content from keywords")
    parser.add_argument("input_file", help="Text file containing keywords, one per line")
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
    
    args = parser.parse_args()
    
    try:
        # Load keywords
        keywords = load_keywords(args.input_file)
        print(f"Loaded {len(keywords)} keywords from {args.input_file}")
        # Load preprompt if file exists
        preprompt = load_preprompt(args.preprompt)
        if preprompt:
            print(f"Loaded custom preprompt from {args.preprompt}")
        
        # Distribute keywords across articles
        article_keyword_sets = distribute_keywords(keywords, args.num_articles)
        print(f"Distributing keywords across {len(article_keyword_sets)} articles")
        
        # Process each article
        for i, article_keywords in enumerate(article_keyword_sets, 1):
            print(f"\n[{i}/{len(article_keyword_sets)}] Generating article with {len(article_keywords)} keywords")
            print(f"Keywords: {', '.join(article_keywords)}")
            
            # Generate content
            content = generate_seo_content(
                keywords=article_keywords,
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
    
    print(f"\nSEO content generation complete. {len(article_keyword_sets)} articles saved to {args.output} directory.")
    return 0

if __name__ == "__main__":
    sys.exit(main())

