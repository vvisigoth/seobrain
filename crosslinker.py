#!python3.12
"""
crosslinker.py - Automatically creates intelligent crosslinks between published markdown articles

This script scans a directory of markdown files, identifies articles marked as published
in their YAML front matter, and adds relevant crosslinks between related articles.
"""

import os
import sys
import argparse
import re
import yaml
import glob
from pathlib import Path
from typing import List, Dict, Tuple, Set, Optional
from collections import defaultdict

# Import RAG components for semantic search
from search import (
    load_config,
    initialize_embeddings,
    extract_yaml_front_matter,
    create_or_load_index
)
from langchain_core.documents import Document

# Default settings
DEFAULT_CONTENT_DIR = "seo_content"
DEFAULT_MAX_LINKS = 3
DEFAULT_INDEX_NAME = "crosslink_index"

class Article:
    """Class representing a markdown article with metadata"""
    
    def __init__(self, file_path: str, content: str, front_matter: Dict):
        self.file_path = file_path
        self.content = content
        self.front_matter = front_matter
        self.title = self._extract_title()
        self.filename = os.path.basename(file_path)
        self.is_published = front_matter.get("Published", False)
        self.keywords = front_matter.get("keywords", [])
        self.tags = front_matter.get("tags", [])
        
        # Extract the main content without front matter for embedding
        self.main_content = self._extract_main_content(content)
        
        # Keep track of outgoing links
        self.outgoing_links = set()
    
    def _extract_title(self) -> str:
        """Extract the title from the content (H1 heading)"""
        # Try to get title from front matter first
        if "title" in self.front_matter:
            return self.front_matter["title"]
        
        # Otherwise extract from H1 heading
        title_match = re.search(r'^# (.+)$', self.content, re.MULTILINE)
        if title_match:
            return title_match.group(1).strip()
        
        # Fallback to filename
        return os.path.splitext(os.path.basename(self.file_path))[0].replace('_', ' ').title()
    
    def _extract_main_content(self, content: str) -> str:
        """Extract the main content without YAML front matter"""
        if content.startswith('---'):
            # Find the closing --- of the front matter
            end_index = content.find('---', 3)
            if end_index != -1:
                # Return content after front matter
                return content[end_index + 3:].strip()
        
        return content
    
    def add_outgoing_link(self, target_filename: str):
        """Add an outgoing link to another article"""
        self.outgoing_links.add(target_filename)
    
    def has_link_to(self, target_filename: str) -> bool:
        """Check if this article already links to the target"""
        return target_filename in self.outgoing_links
    
    def update_content_with_links(self, links: List[Tuple[str, str]]) -> str:
        """
        Update the article content with crosslinks in Obsidian-compatible format
        
        Args:
            links: List of tuples (target_filename, target_title)
            
        Returns:
            Updated content with added links section
        """
        if not links:
            return self.content
        
        # Prepare the related articles section with Obsidian-compatible links
        related_section = "\n\n## Related Articles\n\n"
        for target_filename, target_title in links:
            # Convert to Obsidian format: [[filename]] or [[filename|display text]]
            # Remove the .md extension for Obsidian links
            filename_without_ext = os.path.splitext(target_filename)[0]
            related_section += f"* [[{filename_without_ext}|{target_title}]]\n"
        
        # Check if there's already a "Related Articles" section
        if "## Related Articles" in self.content:
            # Replace existing section
            pattern = r"## Related Articles\s*\n([\s\S]*?)(?=\n##|\Z)"
            updated_content = re.sub(pattern, related_section, self.content)
        else:
            # Add new section at the end
            updated_content = self.content + related_section
        
        return updated_content

def load_articles(directory: str) -> List[Article]:
    """Load all markdown articles from the directory"""
    articles = []
    
    # Find all markdown files
    markdown_files = glob.glob(os.path.join(directory, "**/*.md"), recursive=True)
    
    for file_path in markdown_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Extract YAML front matter
            front_matter = extract_yaml_front_matter(content)
            
            # Create Article object
            article = Article(file_path, content, front_matter)
            articles.append(article)
            
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
    
    return articles

def prepare_documents_for_embedding(articles: List[Article]) -> List[Document]:
    """Prepare documents for embedding from published articles"""
    documents = []
    
    for article in articles:
        if article.is_published:
            doc = Document(
                page_content=article.main_content,
                metadata={
                    "source": article.file_path,
                    "filename": article.filename,
                    "title": article.title,
                    "keywords": article.keywords,
                    "tags": article.tags
                }
            )
            documents.append(doc)
    
    return documents

def find_related_articles(articles: List[Article], vector_db, max_links_per_article: int) -> Dict[str, List[Tuple[str, str]]]:
    """
    Find related articles using vector similarity search
    
    Returns:
        Dictionary mapping article filenames to lists of (target_filename, target_title) tuples
    """
    related_links = {}
    
    # Get only published articles
    published_articles = [a for a in articles if a.is_published]
    
    # Create a lookup by filename
    article_by_filename = {a.filename: a for a in published_articles}
    
    # For each published article, find related articles
    for article in published_articles:
        # Skip if the article already has outgoing links (detected in content)
        if article.outgoing_links:
            continue
            
        # Search for related articles
        results = vector_db.similarity_search(
            article.main_content,
            k=max_links_per_article + 1  # +1 because the article itself might be in results
        )
        
        # Filter out the current article and get top N
        related = []
        for doc in results:
            target_filename = doc.metadata["filename"]
            if target_filename != article.filename:
                target_title = doc.metadata["title"]
                related.append((target_filename, target_title))
                
                # Add to outgoing links tracking
                article.add_outgoing_link(target_filename)
            
            # Stop once we have enough links
            if len(related) >= max_links_per_article:
                break
        
        related_links[article.filename] = related
    
    return related_links

def update_articles_with_links(articles: List[Article], related_links: Dict[str, List[Tuple[str, str]]]) -> int:
    """
    Update articles with crosslinks
    
    Returns:
        Number of articles updated
    """
    updated_count = 0
    
    for article in articles:
        if not article.is_published:
            continue
            
        # Get related links for this article
        links = related_links.get(article.filename, [])
        
        if links:
            # Update content with links
            updated_content = article.update_content_with_links(links)
            
            # Write updated content back to file
            with open(article.file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)
            
            updated_count += 1
            print(f"Added {len(links)} links to {article.filename}")
    
    return updated_count

def detect_existing_links(articles: List[Article]):
    """Detect existing links in articles to avoid duplicates"""
    # Regular expression to find markdown links
    link_pattern = r'\[.+?\]\(\.?/?(.*?)\)'
    
    for article in articles:
        # Find all links in the content
        matches = re.findall(link_pattern, article.content)
        
        for target in matches:
            # Clean up the target (remove anchor links, etc.)
            clean_target = target.split('#')[0].strip()
            
            # If it's a markdown file, add it to outgoing links
            if clean_target.endswith('.md'):
                article.add_outgoing_link(os.path.basename(clean_target))

def main():
    """Main function to run the crosslinker."""
    parser = argparse.ArgumentParser(description="Generate crosslinks between published markdown articles")
    parser.add_argument("-d", "--directory", default=DEFAULT_CONTENT_DIR,
                        help=f"Directory containing markdown articles (default: {DEFAULT_CONTENT_DIR})")
    parser.add_argument("-m", "--max-links", type=int, default=DEFAULT_MAX_LINKS,
                        help=f"Maximum number of links per article (default: {DEFAULT_MAX_LINKS})")
    parser.add_argument("-i", "--index", default=DEFAULT_INDEX_NAME,
                        help=f"Name of the vector index to create/use (default: {DEFAULT_INDEX_NAME})")
    parser.add_argument("--rebuild-index", action="store_true",
                        help="Force rebuild of the search index")
    
    args = parser.parse_args()
    
    try:
        # Initialize embeddings
        print("Initializing embeddings model...")
        config = load_config()
        embeddings = initialize_embeddings(config)
        
        # Load all articles
        print(f"Loading articles from {args.directory}...")
        articles = load_articles(args.directory)
        print(f"Found {len(articles)} total articles")
        
        # Filter published articles
        published_articles = [a for a in articles if a.is_published]
        print(f"Found {len(published_articles)} published articles")
        
        if not published_articles:
            print("No published articles found. Articles must have 'Published: True' in their YAML front matter.")
            return 1
        
        # Detect existing links to avoid duplicates
        detect_existing_links(articles)
        
        # Prepare documents for embedding
        documents = prepare_documents_for_embedding(published_articles)
        
        # Create or load vector index
        vector_db = create_or_load_index(documents, embeddings, args.index, args.rebuild_index)
        
        # Find related articles
        print(f"Finding related articles (max {args.max_links} links per article)...")
        related_links = find_related_articles(articles, vector_db, args.max_links)
        
        # Update articles with links
        updated_count = update_articles_with_links(articles, related_links)
        print(f"Updated {updated_count} articles with crosslinks")
        
    except Exception as e:
        print(f"Error: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
