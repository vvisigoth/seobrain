# Reich - AI Assistant CLI Tool

Reich is a command-line interface tool for interacting with large language models (LLMs), currently supporting both OpenAI's GPT models and Anthropic's Claude models. It allows you to send prompts, include context from your current directory, and save the conversation history.

## Features

- Send prompts to OpenAI GPT models or Anthropic Claude models
- Include images with your prompts (OpenAI only)
- Automatically include directory structure and file contents as context
- Save conversation history for future reference
- Extract and save code blocks from responses
- Summarize conversations for better context management

## Installation

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/reich.git
   cd reich
   ```

2. Install the required packages:
   ```
   pip install openai anthropic
   ```

3. Set up your configuration:
   ```
   cp example.config.json config.json
   ```

4. Edit `config.json` to include your API keys:
   ```json
   {
     "openai_api_key": "your-openai-api-key",
     "anthropic_api_key": "your-anthropic-api-key"
   }
   ```

   Note: If both API keys are provided, Reich will default to using OpenAI. If only one API key is provided, it will use the available service.

## Usage

### Basic Usage

To start a basic conversation:

```
python reich.py
```

You'll be prompted to enter your query.

### Reading Prompts from a File

To read a prompt from a file:

```
python reich.py -f path/to/prompt.txt
```

### Including an Image (OpenAI only)

To include an image with your prompt:

```
python reich.py -i path/to/image.jpg
```

Or combined with a file prompt:

```
python reich.py -f path/to/prompt.txt -i path/to/image.jpg
```

## Configuration Files

- `config.json`: Contains your API keys for OpenAI and Anthropic
- `preamble.txt`: Contains system instructions that are sent with each prompt
- `exclude.txt`: List of files or directories to exclude from context

## Directory Structure

```
.
├── backup.py              # Backup script
├── config.example.json    # Example configuration
├── config.json            # Your configuration (with API keys)
├── dialogue/              # Directory where conversation history is stored
├── example.config.json    # Another example configuration format
├── exclude.txt            # Files/directories to exclude from context
├── generated/             # Directory where extracted code is saved
├── preamble.txt           # System instructions for the AI
├── reich.py               # Main script
└── system.txt             # Additional system context
```

## How It Works

1. When you run `reich.py`, it gathers context from your current directory
2. It combines your prompt with a preamble and the gathered context
3. It sends this to either OpenAI's GPT or Anthropic's Claude API depending on your configuration
4. The response is saved to the `dialogue` directory
5. Any code blocks in the response are extracted and saved to the `generated` directory
6. The conversation is summarized for future context

## Search.py - Semantic Search for Your Dialogue History

The `search.py` script provides a powerful way to search through your past conversations with AI models. It uses Retrieval Augmented Generation (RAG) principles with vector embeddings to find semantically relevant content rather than just exact keyword matches.

### Key Features

- **Semantic search**: Find content based on meaning, not just keywords
- **Multiple embedding options**: Uses OpenAI embeddings when available, with fallback to local HuggingFace embeddings
- **Automatic indexing**: Creates and maintains a searchable index of your dialogue history
- **Smart file change detection**: Automatically rebuilds the index when new conversation files are detected

### Usage

```bash
# Basic search
python search.py "your search query"

# Search with more results
python search.py "your search query" --results 10

# Force rebuilding the search index
python search.py "your search query" --rebuild

# Search in a different directory
python search.py "your search query" --dir custom_dialogue_dir
```

### Requirements

The script requires the following Python packages:
- `langchain_community`
- `langchain`
- `faiss-cpu` (for the vector database)

If you have an OpenAI API key in your config.json, it will use OpenAI's embeddings. Otherwise, it falls back to a local HuggingFace model (`all-MiniLM-L6-v2`).

### Index Management

The search index is stored in the `history_index` directory. The script automatically manages this index:

- Creates a new index if none exists
- Uses the existing index for faster searches
- Automatically detects when documents have been added or modified and rebuilds as needed
- Can be forced to rebuild with the `--rebuild` flag

### Examples

Find conversations about Python code:
```bash
python search.py "python function examples"
```

Search for discussions about specific concepts:
```bash
python search.py "API authentication methods"
```

Look up past configuration questions:
```bash
python search.py "how to configure API keys"
```

## TODO
- Return patches instead of code text to avoid
- Programmatically reindex
- Install script to init project `curl sSL https://url.com/script | bash`
- Structured output to avoid code block parsing
    ```
    {
        "explanation": "",
        "patches": [
            "",
            ""
        ]
    }
    ```
- helper scripts/executables

## License

[TBD]
