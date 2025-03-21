# SEO Content Generator

A Python script that takes a text file where each line is an SEO keyword and generates optimized content for each keyword using AI.

## Features

- Processes a list of keywords from a text file
- Uses AI to generate SEO-optimized content for each keyword
- Creates a separate markdown file for each generated piece of content
- Configurable AI model and provider

## Requirements

- Python 3.6+
- `requests` library

## Installation

1. Clone this repository
2. install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Create a `config.json` file in the same directory (optional - only needed if you want to use non-Ollama providers)

## Usage

```bash
python seo_generator.py keywords.txt
```

### Command Line Options

- `input_file`: Path to a text file containing keywords (one per line)
- `-o, --output`: Output directory for generated content (default: `seo_content/`)
- `-m, --model`: AI model to use (default: `anthropic/claude-3.7-sonnet`)
- `-p, --provider`: AI provider (choices: ollama, openai, openrouter, anthropic; default: openrouter)
- `-s, --server`: Server URL for the AI backend (default: http://localhost:5555)

### Example

```bash
# Basic usage
python seo_generator.py my_keywords.txt

# Use a specific model and provider
python seo_generator.py my_keywords.txt -m gpt-4o -p openai

# Save output to a custom directory
python seo_generator.py my_keywords.txt -o custom_output/
```

## How It Works

1. The script reads keywords from a text file (one per line)
2. For each keyword, it generates:
   - An SEO-optimized H1 title
   - A meta description (150-160 characters)
   - 5-7 H2 subheadings 
   - 300-500 words of content
   - A call-to-action
3. The content is saved as a markdown file for each keyword in the output directory

## Requirements

- Python 3.6 or higher
- Access to an AI backend (local Ollama instance or API keys for other providers)
- The `composer.py` server must be running on the specified URL

## Sample Input File

Create a text file (e.g., `keywords.txt`) with keywords, one per line:

```
best yoga mats 2024
how to make sourdough bread
digital marketing for small businesses
```

## Output

For each keyword, a markdown file will be generated in the output directory with SEO-optimized content.

## Notes

- This script requires the `composer.py` server to be running, which handles the AI model interactions
- Content generation quality depends on the AI model used
- Rate limits may apply depending on your AI provider
