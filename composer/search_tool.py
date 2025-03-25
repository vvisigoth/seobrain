#! python3.12

import os
import sys
import argparse
import json
import base64
import requests
from pathlib import Path
import time

# Import from existing modules
from url_fetch import capture_webpage
from search_utils import (
    process_keywords,
    search_google_api,
    load_config,
    create_temp_directory
)

# Constants
SERVER_URL = "http://localhost:5555/api"  # Composer.py server URL
RESULTS_DIR = "search_results"  # Directory to store search results

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Search tool with screenshot capture and LLM summarization")
    parser.add_argument("keywords", nargs="+", help="Keywords to search for")
    parser.add_argument("-n", "--num-results", type=int, default=5, 
                        help="Number of search results to process (default: 5)")
    parser.add_argument("-m", "--model", default="x-ai/grok-2-vision-1212", 
                        help="LLM model to use for summarization")
    parser.add_argument("-p", "--provider", default="openrouter", 
                        choices=["openai", "anthropic", "openrouter", "ollama"],
                        help="AI provider to use")
    parser.add_argument("-s", "--save", action="store_true", 
                        help="Save search results and summaries")
    parser.add_argument("-o", "--output-dir", 
                        help="Directory to save results (default: search_results)")
    return parser.parse_args()

def encode_image(image_path):
    """Encode image to base64 for sending to LLM."""
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode("utf-8")

def prepare_prompt_for_screenshot(url, title, snippet):
    """Prepare a prompt for the LLM to analyze a screenshot."""
    return f"""Please analyze this screenshot of search result: {title}

URL: {url}

Context from search snippet: {snippet}

Provide your response in two parts:
1. TEXT EXTRACTION: Extract the main textual content visible in the screenshot, preserving the structure as much as possible.
2. SUMMARY: Provide a concise summary of what you see in the screenshot. Focus on the main content, key information, and how it relates to the search query. Ignore ads, navigation elements, and other UI components unless they're relevant to understanding the content.

Use the headers "TEXT EXTRACTION:" and "SUMMARY:" to clearly separate these sections."""

def prepare_summary_prompt(search_query, individual_summaries):
    """Prepare a prompt for the LLM to create a final summary of all results."""
    summaries_text = "\n\n".join([f"Result {i+1}: {summary}" for i, summary in enumerate(individual_summaries)])
    
    return f"""You searched for: {search_query}

Here are summaries of the top search results:

{summaries_text}

Please provide a comprehensive yet concise summary of these search results. Identify common themes, contradictions, and unique insights. Focus on answering the original search query based on the information available in these results."""

def send_to_llm(prompt, image_path=None, server_url=SERVER_URL, provider="openai", model="gpt-4o"):
    """Send a prompt and optional image to the LLM via composer.py server."""
    messages = []
    
    # Add image if provided
    if image_path:
        image_base64 = encode_image(image_path)
        
        if provider == "anthropic":
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/png",
                            "data": image_base64
                        }
                    }
                ]
            })
        else:  # OpenAI or OpenRouter format
            messages.append({
                "role": "user",
                "content": [
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/png;base64,{image_base64}"
                        }
                    }
                ]
            })
    
    # Add text prompt
    messages.append({"role": "user", "content": prompt})
    
    # Prepare request data
    request_data = {
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.7,
        "provider": provider,
        "model": model
    }
    
    # Send request to composer.py server
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

def extract_text_and_summary(analysis):
    """Extract the text extraction and summary sections from the LLM analysis."""
    text_extraction = ""
    summary = ""
    
    # Split by headers
    if "TEXT EXTRACTION:" in analysis and "SUMMARY:" in analysis:
        parts = analysis.split("SUMMARY:")
        text_part = parts[0]
        summary = parts[1].strip()
        
        # Extract text content
        if "TEXT EXTRACTION:" in text_part:
            text_extraction = text_part.split("TEXT EXTRACTION:")[1].strip()
    else:
        # Fallback if the LLM didn't follow the format
        summary = analysis
    
    return text_extraction, summary

def save_results(query, search_results, screenshots, analyses, final_summary, output_dir):
    """Save search results, screenshots, and summaries to files."""
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Generate timestamp for filenames
    timestamp = int(time.time())
    
    # Save search results as JSON
    search_results_file = os.path.join(output_dir, f"search_results_{timestamp}.json")
    with open(search_results_file, "w") as f:
        json.dump(search_results, f, indent=2)
    
    # Save individual text extractions and summaries
    extracted_texts = []
    summaries = []
    
    for i, analysis in enumerate(analyses):
        # Extract text and summary from the analysis
        extracted_text, summary = extract_text_and_summary(analysis)
        extracted_texts.append(extracted_text)
        summaries.append(summary)
        
        # Save individual text extraction
        text_file = os.path.join(output_dir, f"text_extraction_{timestamp}_{i+1}.txt")
        with open(text_file, "w") as f:
            f.write(f"Result {i+1}: {search_results[i]['title']}\n")
            f.write(f"URL: {search_results[i]['link']}\n\n")
            f.write(extracted_text)
        
    # Save all summaries in one file
    summaries_file = os.path.join(output_dir, f"summaries_{timestamp}.txt")
    with open(summaries_file, "w") as f:
        for i, summary in enumerate(summaries):
            f.write(f"Result {i+1}: {search_results[i]['title']}\n")
            f.write(f"URL: {search_results[i]['link']}\n")
            f.write(f"{summary}\n\n")
    
    # Save final summary
    final_summary_file = os.path.join(output_dir, f"final_summary_{timestamp}.txt")
    with open(final_summary_file, "w") as f:
        f.write(f"Search Query: {query}\n\n")
        f.write(final_summary)
    
    print(f"Results saved to {output_dir}/")
    return {
        "search_results": search_results_file,
        "summaries": summaries_file,
        "final_summary": final_summary_file,
        "screenshots": screenshots,
        "text_extractions": extracted_texts
    }

def main():
    """Main function to run the search tool."""
    # Parse arguments
    args = parse_arguments()
    
    # Process keywords into a search query
    search_query = " ".join(args.keywords)
    print(f"Searching for: {search_query}")
    
    # Set output directory
    output_dir = args.output_dir if args.output_dir else RESULTS_DIR
    
    # Create temp directory for screenshots
    temp_dir = create_temp_directory()
    
    try:
        # Search Google API
        search_results = search_google_api(search_query, num_results=args.num_results)
        print(f"Found {len(search_results)} results")
        
        # Take screenshots of each result
        screenshots = []
        for i, result in enumerate(search_results):
            print(f"Capturing screenshot for result {i+1}: {result['title']}")
            try:
                # Generate filename based on search result
                filename = f"result_{i+1}_{int(time.time())}.png"
                output_path = os.path.join(temp_dir, filename)
                
                # Capture screenshot
                screenshot_path = capture_webpage(result['link'], output_file=output_path)
                screenshots.append(screenshot_path)
                print(f"Screenshot saved: {screenshot_path}")
                
            except Exception as e:
                print(f"Error capturing screenshot for {result['link']}: {str(e)}")
                screenshots.append(None)
        
        # Analyze screenshots with LLM
        analyses = []
        summaries = []
        for i, (result, screenshot) in enumerate(zip(search_results, screenshots)):
            if screenshot:
                print(f"Analyzing screenshot for result {i+1}")
                prompt = prepare_prompt_for_screenshot(
                    result['link'], 
                    result['title'], 
                    result.get('snippet', 'No snippet available')
                )
                
                # Send to LLM
                analysis = send_to_llm(
                    prompt=prompt,
                    image_path=screenshot,
                    provider=args.provider,
                    model=args.model
                )
                
                analyses.append(analysis)
                
                # Extract just the summary part for the final summary
                _, summary = extract_text_and_summary(analysis)
                summaries.append(summary if summary else analysis)
                
                print(f"Analysis complete for result {i+1}")
            else:
                analyses.append("Screenshot capture failed for this result.")
                summaries.append("Screenshot capture failed for this result.")
        
        # Create final summary
        print("Creating final summary...")
        final_prompt = prepare_summary_prompt(search_query, summaries)
        final_summary = send_to_llm(
            prompt=final_prompt,
            provider=args.provider,
            model=args.model
        )
        
        print("\n" + "="*50)
        print("FINAL SUMMARY")
        print("="*50)
        print(final_summary)
        print("="*50)
        
        # Save results if requested
        if args.save:
            saved_files = save_results(
                search_query,
                search_results,
                screenshots,
                analyses,
                final_summary,
                output_dir
            )
            print(f"Results saved to {saved_files['final_summary']}")
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
