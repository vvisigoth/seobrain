import argparse
import sys
import tiktoken

def estimate_tokens(text, model='gpt-4'):
    # Initialize the tokenizer for the specified model
    encoding = tiktoken.encoding_for_model(model)
    
    # Encode the text to get the token IDs
    token_ids = encoding.encode(text)
    
    # Return the number of tokens
    return len(token_ids)

def main():
    parser = argparse.ArgumentParser(description="Estimate the number of tokens in a given text.")
    parser.add_argument('-f', '--file', nargs='+', help='List of text files to read from')
    parser.add_argument('-m', '--model', default='gpt-4', help='Model to use for token estimation (default: gpt-4)')
    
    args = parser.parse_args()

    input_text = ""
    
    if args.file:
        # Read and concatenate text from the specified files
        for file_path in args.file:
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    input_text += file.read() + "\n"
            except FileNotFoundError:
                print(f"File not found: {file_path}")
                sys.exit(1)
    else:
        # Read text from standard input
        input_text = sys.stdin.read()

    # Estimate the number of tokens
    token_count = estimate_tokens(input_text, model=args.model)
    print(f"Estimated number of tokens: {token_count}")

if __name__ == '__main__':
    main()