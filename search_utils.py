#! python3.12

import os
import json
import time
import tempfile
from pathlib import Path
import requests

def load_config():
    """Load configuration from config.json file."""
    config_path = Path("config.json")
    if not config_path.exists():
        raise FileNotFoundError("config.json not found. Please create a config file with Google API keys.")
    
    with open(config_path, "r") as f:
        config = json.load(f)
    
    # Check if required keys exist
    if "google_api_key" not in config or "google_cx" not in config:
        raise KeyError("Missing required Google API keys in config.json. Please add 'google_api_key' and 'google_cx'.")
    
    return config


def process_keywords(keywords):
    """Process a list of keywords into a search query string."""
    if isinstance(keywords, list):
        return " ".join(keywords)
    return str(keywords)

def create_temp_directory():
    """Create a temporary directory for storing screenshots."""
    temp_dir = os.path.join(tempfile.gettempdir(), f"search_screenshots_{int(time.time())}")
    os.makedirs(temp_dir, exist_ok=True)
    return temp_dir

def search_google_api(query, num_results=5):
    """
    Search Google using the Google Custom Search JSON API.
    
    Args:
        query (str): The search query
        num_results (int): Number of results to return (max 10)
        
    Returns:
        list: List of search result dictionaries with title, link, and snippet
    """
    # Load API keys from config
    config = load_config()
    api_key = config["google_api_key"]
    cx = config["google_cx"]
    
    # Build the API URL
    base_url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "key": api_key,
        "cx": cx,
        "q": query,
        "num": min(num_results, 10),  # Google API limits to 10 results per request
    }
    
    try:
        # Make the API request
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors
        
        # Parse the response
        search_data = response.json()
        
        # Extract the search results
        if "items" not in search_data:
            print("No search results found.")
            return []
        
        results = []
        for item in search_data["items"]:
            result = {
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
                "displayLink": item.get("displayLink", "")
            }
            results.append(result)
        
        return results[:num_results]
        
    except requests.exceptions.RequestException as e:
        print(f"Error making Google Search API request: {str(e)}")
        raise
    except (KeyError, ValueError) as e:
        print(f"Error parsing Google Search API response: {str(e)}")
        raise

def filter_search_results(results, exclude_domains=None):
    """
    Filter search results to exclude specific domains.
    
    Args:
        results (list): List of search result dictionaries
        exclude_domains (list): List of domains to exclude
        
    Returns:
        list: Filtered list of search results
    """
    if not exclude_domains:
        return results
    
    filtered_results = []
    for result in results:
        domain = result.get("displayLink", "")
        if not any(excluded in domain for excluded in exclude_domains):
            filtered_results.append(result)
    
    return filtered_results

def format_search_results(results):
    """
    Format search results for display.
    
    Args:
        results (list): List of search result dictionaries
        
    Returns:
        str: Formatted string of search results
    """
    if not results:
        return "No results found."
    
    formatted = []
    for i, result in enumerate(results, 1):
        formatted.append(f"{i}. {result['title']}")
        formatted.append(f"   URL: {result['link']}")
        formatted.append(f"   {result['snippet']}")
        formatted.append("")
    
    return "\n".join(formatted)

def save_search_results(results, output_file):
    """
    Save search results to a JSON file.
    
    Args:
        results (list): List of search result dictionaries
        output_file (str): Path to the output file
        
    Returns:
        str: Path to the saved file
    """
    with open(output_file, "w") as f:
        json.dump(results, f, indent=2)
    
    return output_file

if __name__ == "__main__":
    # Example usage
    query = "python web scraping tutorial"
    results = search_google_api(query, num_results=5)
    print(format_search_results(results))
