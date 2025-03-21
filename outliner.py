#!python3.12
"""
SEO Generation Script

This script takes a text file where each line is an SEO keyword
and generates optimized content for each keyword.
"""

import os
import sys
import argparse
import json
import requests
from pathlib import Path
from typing import List, Dict, Any, Optional

# Default settings
DEFAULT_MODEL = "anthropic/claude-3.7-sonnet"
DEFAULT_PROVIDER = "openrouter"
SERVER_URL = "http://localhost:5555"
OUTPUT_DIR = "seo_content"

def load_keywords(file_path: str) -> List[str]:
    """Load keywords from a text file, one per line."""
    with open(file_path, 'r') as f:
        return [line.strip() for line in f if line.strip()]

def generate_seo_content(keyword: str, model: str, provider: str, server_url: str) -> str:
    """Generate SEO content for a given keyword using the AI API."""
    
    # Craft the prompt for SEO content generation
    prompt = f"""
Generate high-quality SEO content for the keyword: "{keyword}"

Please include:
1. A compelling H1 title (using markdown # syntax)
2. A meta description (150-160 characters)
3. 5-7 relevant H2 subheadings (using markdown ## syntax)
4. 300-500 words of well-structured, informative content
5. A natural keyword density of 1-2%
6. A clear call-to-action at the end

The content should be engaging, informative, and optimized for search engines while providing value to readers.
"""

    # Prepare request data
    request_data = {
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 2000,
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

def save_content(keyword: str, content: str, output_dir: str) -> str:
    """Save the generated content to a file and return the file path."""
    # Create output directory if it doesn't exist
    Path(output_dir).mkdir(exist_ok=True)
    
    # Create a filename from the keyword
    filename = keyword.lower().replace(' ', '_').replace("'", "").replace('"', '')
    # Remove any special characters that might cause issues with filenames
    filename = ''.join(c for c in filename if c.isalnum() or c == '_' or c == '-')
    filepath = os.path.join(output_dir, f"{filename}.md")
    
    # Save the content
    with open(filepath, 'w') as f:
        f.write(content)
    
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
    
    args = parser.parse_args()
    
    try:
        # Load keywords
        keywords = load_keywords(args.input_file)
        print(f"Loaded {len(keywords)} keywords from {args.input_file}")
        
        # Process each keyword
        for i, keyword in enumerate(keywords, 1):
            print(f"\n[{i}/{len(keywords)}] Generating content for keyword: '{keyword}'")
            
            # Generate content
            content = generate_seo_content(
                keyword=keyword,
                model=args.model,
                provider=args.provider,
                server_url=args.server
            )
            
            # Save content
            filepath = save_content(keyword, content, args.output)
            print(f"Content saved to: {filepath}")
    
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    print(f"\nSEO content generation complete. Files saved to {args.output} directory.")
    return 0

if __name__ == "__main__":
    sys.exit(main())
