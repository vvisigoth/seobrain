# SEO Brain

A Python script that takes a text file where each line is an SEO keyword and generates optimized content for each keyword using AI.

![KRANG](https://cdn11.bigcommerce.com/s-b70w3e4554/images/stencil/1280x1280/products/339/6692/911124_press20_copy__86116.1714570677.jpg)

## Features

- Processes a list of keywords from a text file
- Uses AI to generate SEO-optimized content for each keyword
- Creates a separate markdown file for each generated piece of content
- Configurable AI model and provider

## How It Works

1. The script reads keywords from a text file (one per line)
2. For each keyword, it generates:
   - An SEO-optimized H1 title
   - A meta description (150-160 characters)
   - 5-7 H2 subheadings 
   - 300-500 words of content
   - A call-to-action
3. The content is saved as a markdown file for each keyword in the output directory


## Sample Input File

Create a text file (e.g., `keywords.txt`) with keywords, one per line:

```
best yoga mats 2024
how to make sourdough bread
digital marketing for small businesses
```

## Output

For each keyword, a markdown file will be generated in the output directory with SEO-optimized content.

## Requirements

- Python 3.6+
- `requests` library
- Access to an AI backend (local Ollama instance or API keys for other providers)
- The `composer.py` server must be running on the specified URL

## Installation

1. Clone this repository
2. install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `config.json` file in the same directory (optional - only needed if you want to use non-Ollama providers)

## Basic Usage

```bash
python seo_generator.py keywords.txt
```

### Basic Examples

```bash
# Basic usage
python seo_generator.py my_keywords.txt

# Use a specific model and provider
python seo_generator.py my_keywords.txt -m gpt-4o -p openai

# Save output to a custom directory
python seo_generator.py my_keywords.txt -o custom_output/
```

### Command Line Options

- `input_file`: Path to a text file containing keywords (one per line)
- `-o, --output`: Output directory for generated content (default: `seo_content/`)
- `-m, --model`: AI model to use (default: `anthropic/claude-3.7-sonnet`)
- `-p, --provider`: AI provider (choices: ollama, openai, openrouter, anthropic; default: openrouter)
- `-s, --server`: Server URL for the AI backend (default: http://localhost:5555)

## RAG (Retrieval-Augmented Generation) Features

The SEO Content Generator now includes RAG capabilities, allowing it to search through a knowledge base of documents to enhance article quality with relevant research information.

### Knowledge Base

- Create a `knowledge_base` directory (or specify a custom location) to store your reference documents
- Supports `.txt`, `.md`, `.html`, `.json`, and `.csv` files
- For markdown files, you can use YAML front matter with tags for better organization

### RAG-related Command Line Options

- `--knowledge`: Directory containing knowledge base documents (default: `knowledge_base/`)
- `--index`: Name of the vector index to create/use (default: `seo_index/`)
- `--rebuild-index`: Force rebuild of the search index
- `--results`: Number of research results to include per article (default: 3)
- `--tags`: Only include documents with specific tags in the YAML front matter

### Example YAML Front Matter

For markdown files in your knowledge base, you can add tags using YAML front matter:

```
---
tags:
  - seo
  - marketing
  - analytics
---

Your document content here...
```

### Using the Indexer

The `indexer.py` script monitors your knowledge base directory and automatically updates the search index when files are added or modified:

```bash
# Start watching the knowledge base directory
python indexer.py

# Watch a custom knowledge directory and index
python indexer.py --knowledge my_docs --index my_index

# Only index files with specific tags
python indexer.py --tags seo marketing

# Set a custom cooldown period (in seconds)
python indexer.py --cooldown 10
```

### RAG Examples

```bash
# Generate articles using the knowledge base
python articlegenerator.py keywords.txt --knowledge my_knowledge_base

# Only use documents with specific tags
python articlegenerator.py keywords.txt --tags seo marketing

# Include more research results per article
python articlegenerator.py keywords.txt --results 5

# Force rebuild of the search index
python articlegenerator.py keywords.txt --rebuild-index
```

The RAG system enhances article generation by incorporating relevant information from your knowledge base, making the content more authoritative and informative.

## Advanced Usage

```
# Generate a single article with specific title and keywords
python articlegenerator.py --single --title "Best Yoga Mats for Beginners" --keywords "yoga mats" "beginners yoga" "best yoga equipment" 

# Specify custom output directory and model
python articlegenerator.py --single --title "Digital Marketing Strategies" --keywords "digital marketing" "SEO" "content strategy" -o custom_output/ -m gpt-4

# Use RAG with specific knowledge base and tags
python articlegenerator.py --single --title "Healthy Meal Prep Ideas" --keywords "meal prep" "healthy recipes" "nutrition" --knowledge nutrition_docs/ --tags recipes nutrition
```

## Notes

- This script requires the `composer.py` server to be running, which handles the AI model interactions
- Content generation quality depends on the AI model used
- Rate limits may apply depending on your AI provider
