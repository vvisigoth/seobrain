import os
import time
import argparse
from PIL import Image
import io
import requests
import json
import sys
import base64
from pathlib import Path
from mimetypes import guess_type
import re
import glob
import subprocess

# Import the diarize module from the current project
import diarize
# import utility to
from url_fetch import capture_webpage

# Constants
DIALOGUE_DIR = "dialogue/"
PREAMBLE_FILE = "preamble.txt"
EXCLUDE_FILE = "exclude.txt"
INCLUDE_FILE = "include.txt"  # Changed from EXCLUDE_FILE to INCLUDE_FILE
GENERATED_DIR = "generated/"
SERVER_URL = "http://localhost:5555/api"  # Default server URL

def set_root_directory(root_dir):
    """Set the root directory and update all path constants"""
    global ROOT_DIR, DIALOGUE_DIR, PREAMBLE_FILE, EXCLUDE_FILE, INCLUDE_FILE, GENERATED_DIR

    ROOT_DIR = os.path.abspath(root_dir)
    DIALOGUE_DIR = os.path.join(ROOT_DIR, "dialogue/")
    PREAMBLE_FILE = os.path.join(ROOT_DIR, "preamble.txt")
    EXCLUDE_FILE = os.path.join(ROOT_DIR, "exclude.txt")
    INCLUDE_FILE = os.path.join(ROOT_DIR, "include.txt")
    GENERATED_DIR = os.path.join(ROOT_DIR, "generated/")

def get_epoch_time():
    return str(int(time.time()))

def encode_image(image_path):
    mime_type, _ = guess_type(image_path)
    if mime_type is None:
        mime_type = 'application/octet-stream'

    with open(image_path, "rb") as image_file:
        base64_encoded_data = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:{mime_type};base64,{base64_encoded_data}"

def process_image(image_path, max_height=7999):
    with Image.open(image_path) as img:
        width, height = img.size

        # Check if image needs to be split
        if height > width * 4/3 and height > max_height:
            pieces = []
            for i in range(0, height, max_height):
                box = (0, i, width, min(i+max_height, height))
                piece = img.crop(box)

                # Convert piece to base64
                buffer = io.BytesIO()
                piece.save(buffer, format="PNG")
                encoded_piece = base64.b64encode(buffer.getvalue()).decode('utf-8')
                pieces.append(f"data:image/png;base64,{encoded_piece}")

            return pieces
        else:
            # If image doesn't need splitting, return it as is
            return [encode_image(image_path)]

def save_prompt(prompt_text, final_context):
    epoch_time = get_epoch_time()
    prompt_file = os.path.join(DIALOGUE_DIR, f"{epoch_time}-prompt.txt")
    # UNCOMMENT TO DEBUG
    #context_file = os.path.join(DIALOGUE_DIR, f"{epoch_time}-context.txt")

    try:
        with open(prompt_file, 'w') as f:
            f.write(prompt_text)

        #with open(context_file, 'w') as f:
        #    f.write(final_context)

    except Exception as e:
        print(f"Error saving files: {e}")

    return epoch_time, prompt_file

def load_preamble():
    if os.path.exists(PREAMBLE_FILE):
        with open(PREAMBLE_FILE, 'r') as f:
            return f.read().strip()
    return ""

def load_inclusions():
    """Load list of files/directories to include in context"""
    if os.path.exists(INCLUDE_FILE):
        with open(INCLUDE_FILE, 'r') as f:
            return [line.strip() for line in f if line.strip()]
    return []

def generate_directory_structure(root_dir, inclusions):
    """Generate directory structure filtered to only show included files/directories"""
    if not inclusions:
        return ""

    # First, get all matching files based on inclusions
    matching_files = []
    for pattern in inclusions:
        matching_files.extend(glob.glob(pattern, recursive=True))

    # If no matching files, return empty string
    if not matching_files:
        return ""

    # Get unique directories containing matching files
    matching_dirs = set()
    for file_path in matching_files:
        # Add all parent directories
        path_parts = Path(file_path).parts
        for i in range(1, len(path_parts)):
            matching_dirs.add(os.path.join(*path_parts[:i]))

    # Create a filtered tree output
    result = f"Project Directory Structure (Filtered):\n"
    result += "./\n"

    # Sort directories for consistent output
    sorted_dirs = sorted(matching_dirs)

    # Add directories with proper indentation
    for directory in sorted_dirs:
        depth = directory.count(os.sep) + 1
        result += f"{' ' * (depth * 2)}├── {os.path.basename(directory)}/\n"

    # Add files with proper indentation
    for file_path in sorted(matching_files):
        if os.path.isfile(file_path):
            depth = file_path.count(os.sep) + 1
            result += f"{' ' * (depth * 2)}├── {os.path.basename(file_path)}\n"

    return result

def gather_context(inclusions):
    """Gather context based on inclusion patterns and format using XML"""
    # Start with an XML root element
    context = "<context>\n"

    # Add directory structure as an XML element
    dir_structure = generate_directory_structure('.', inclusions)
    if dir_structure.strip():
        context += "  <directory_structure>\n"
        context += "    <![CDATA[\n"
        context += dir_structure
        context += "    ]]>\n"
        context += "  </directory_structure>\n"

    # If no inclusions specified, return just the directory structure
    if not inclusions:
        context += "</context>"
        return context

    # Process inclusions
    context += "  <included_files>\n"
    for pattern in inclusions:
        matching_files = glob.glob(pattern, recursive=True)
        for file in matching_files:
            if os.path.isfile(file):
                try:
                    with open(file, 'r', errors="ignore") as f:
                        file_content = f.read()
                        context += f"    <file path=\"{file}\">\n"
                        context += "      <![CDATA[\n"
                        context += file_content
                        context += "\n      ]]>\n"
                        context += "    </file>\n"
                except Exception as e:
                    context += f"    <error file=\"{file}\">{str(e)}</error>\n"

    context += "  </included_files>\n"
    context += "</context>"

    return context

def manage_message_history():
    """
    Maintains only the 5 most recent prompt/response pairs in the dialogue directory.
    Moves older messages to the history directory.
    """
    # Create history directory if it doesn't exist
    history_dir = "history/"
    Path(history_dir).mkdir(exist_ok=True)

    # Get all files in dialogue directory
    all_files = glob.glob(os.path.join(DIALOGUE_DIR, "*.txt"))

    # Group files by their timestamp prefix
    file_groups = {}
    for file_path in all_files:
        filename = os.path.basename(file_path)
        # Extract the timestamp from the filename (format: timestamp-type.txt)
        parts = filename.split('-', 1)
        if len(parts) == 2:
            timestamp = parts[0]
            if timestamp not in file_groups:
                file_groups[timestamp] = []
            file_groups[timestamp].append(file_path)

    # Sort timestamps in ascending order (oldest first)
    sorted_timestamps = sorted(file_groups.keys())

    # If we have more than 5 exchanges, move the oldest ones to history
    if len(sorted_timestamps) > 5:
        # Calculate how many timestamps to move
        timestamps_to_move = sorted_timestamps[:-5]  # All but the 5 most recent

        for timestamp in timestamps_to_move:
            for file_path in file_groups[timestamp]:
                # Get the destination path in the history directory
                dest_path = os.path.join(history_dir, os.path.basename(file_path))

                # Move the file
                try:
                    os.rename(file_path, dest_path)
                    print(f"Moved {file_path} to {dest_path}")
                except Exception as e:
                    print(f"Error moving file {file_path}: {e}")

def gather_message_history():
    files = sorted(glob.glob(os.path.join(DIALOGUE_DIR, "*.txt")), key=os.path.getmtime)
    summaries = [f for f in files if "summary" in f]
    prompts = [f for f in files if "prompt" in f]
    responses = [f for f in files if "response" in f]

    message_history = []

    if summaries:
        with open(summaries[-1], 'r') as f:
            message_history.append({"role": "assistant", "content": f.read().strip()})

    for p, r in zip(prompts, responses):
        with open(p, 'r') as f:
            message_history.append({"role": "user", "content": f.read().strip()})
        with open(r, 'r') as f:
            message_history.append({"role": "assistant", "content": f.read().strip()})

    return message_history

def send_request_to_server(prompt, image_paths=None, include_history=True, server_url=SERVER_URL, provider="openrouter", model="claude-3-7-sonnet-20250219"):
    message_history = gather_message_history() if include_history else []

    if image_paths:
        for image_path in image_paths:
            image_pieces = process_image(image_path)
            for piece in image_pieces:
                if provider == "anthropic":
                    message_history.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": piece.split(",", 1)[1]
                                }
                            }
                        ]
                    })
                else:
                    message_history.append({
                        "role": "user",
                        "content": [
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": piece
                                }
                            }
                        ]
                    })

    # Add the text prompt last
    message_history.append({"role": "user", "content": prompt})

    # Prepare request data
    request_data = {
        "messages": message_history,
        "max_tokens": 1500,
        "temperature": 0.7,
        "provider": provider,
        "model": model
    }

    # Send request to server
    try:
        response = requests.post(
            f"{server_url}/generate",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )

        # Handle response
        if response.status_code == 200:
            result = response.json()
            if result.get("success", False):
                return result.get("content", "")
            else:
                error_msg = result.get("error", "Unknown error")
                raise Exception(f"Server error: {error_msg}")
        else:
            raise Exception(f"HTTP error: {response.status_code} - {response.text}")

    except requests.exceptions.RequestException as e:
        raise Exception(f"Connection error: {str(e)}")

def guess_image_mime_type(encoded_image):
    """Guess the MIME type of the image from the data URL"""
    if encoded_image.startswith("data:image/jpeg"):
        return "image/jpeg"
    elif encoded_image.startswith("data:image/png"):
        return "image/png"
    elif encoded_image.startswith("data:image/gif"):
        return "image/gif"
    elif encoded_image.startswith("data:image/webp"):
        return "image/webp"
    else:
        return "application/octet-stream"  # Default to binary data if unknown

def main():
    """Main function to run the Reich client."""
    Path(DIALOGUE_DIR).mkdir(exist_ok=True)

    # Parse command line arguments
    parser = argparse.ArgumentParser(description="Reich client for AI text generation")
    parser.add_argument('-f', '--file', default='prompt', help='File path to read prompt from')
    parser.add_argument("--history", type=lambda x: (str(x).lower() == 'true'), default=True,
                      help="Include dialogue history in the context (default: True)")
    parser.add_argument("-i", "--images", nargs='+', required=False, help="Image files to send along with the prompt")
    parser.add_argument("-u", "--urls", nargs='+', required=False, help="URLs to capture screenshots from")
    parser.add_argument("-s", "--server", default=SERVER_URL, help=f"Server URL (default: {SERVER_URL})")
    parser.add_argument("-p", "--provider", default="openrouter", choices=["ollama", "openai", "openrouter", "anthropic"])
    parser.add_argument("-m", "--model", default="anthropic/claude-3.7-sonnet", help="Model to use")
    parser.add_argument("-r", "--root", default=".", help="Root directory of the project (default: current directory)")

    args = parser.parse_args()

    # Set the root directory
    set_root_directory(args.root)

    # Process user input
    if args.file:
        with open(os.path.expanduser(args.file), 'r') as file:
            user_prompt = file.read()
    else:
        user_prompt = input("\nEnter your prompt: ")

    # Capture screenshots if URLs are provided
    captured_images = []
    if args.urls:
        for url in args.urls:
            screenshot_path = capture_webpage(url)
            captured_images.append(screenshot_path)

    # Combine captured screenshots with provided images
    image_paths = (args.images or []) + captured_images

    # Load context
    preamble = load_preamble() if os.path.exists(PREAMBLE_FILE) else ""
    inclusions = load_inclusions()
    print(f'inclusions {inclusions}')
    context = gather_context(inclusions)

    # Prepare final prompt with context
    final_prompt = f"{preamble}\n\n{user_prompt}\n\n{context}"
    epoch_time, prompt_file = save_prompt(user_prompt, final_context=final_prompt)

    try:
        # Send request to AI server
        response_text = send_request_to_server(
            prompt=final_prompt,
            image_paths=image_paths,
            include_history=args.history,  # Pass the history flag
            server_url=args.server,
            provider=args.provider,
            model=args.model
        )

        # Save the response
        response_file = os.path.join(DIALOGUE_DIR, f"{epoch_time}-response.txt")
        with open(response_file, 'w') as f:
            f.write(response_text)

        # Manage message history - keep only the 5 most recent exchanges
        manage_message_history()

        # Extract and save code blocks if present
        code_blocks = re.findall(r'```(.*?)```', response_text, re.DOTALL)
        if code_blocks:
            Path(GENERATED_DIR).mkdir(exist_ok=True)
            for i, code_block in enumerate(code_blocks):
                code_block = code_block.strip()
                if code_block.startswith('python'):
                    extension = '.py'
                    content = code_block.split('\n', 1)[1] if '\n' in code_block else code_block
                elif code_block.startswith('javascript'):
                    extension = '.js'
                    content = code_block.split('\n', 1)[1] if '\n' in code_block else code_block
                else:
                    extension = '.txt'
                    content = code_block

                filename = os.path.join(GENERATED_DIR, f"{epoch_time}_{i}{extension}")
                with open(filename, 'w') as file:
                    file.write(content)

        # Print the response
        print("\n" + "="*50)
        print("RESPONSE:")
        print("="*50)
        print(response_text)

    except Exception as e:
        print(f"Error in processing: {e}")
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())
