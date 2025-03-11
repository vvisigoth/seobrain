import argparse
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from urllib.parse import urlparse

def capture_webpage(url, output_type='screenshot', output_file=None):
    # Set up headless Chrome
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--start-maximized")  # Ensures full-width capture
    driver = webdriver.Chrome(options=chrome_options)

    try:
        # Load the page
        driver.get(url)

        # Wait for page to load (adjust timeout and conditions as needed)
        wait = WebDriverWait(driver, 10)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))

        # Additional wait to allow AJAX content to load
        time.sleep(5)

        # Create 'captures' directory if it doesn't exist
        os.makedirs('captures', exist_ok=True)

        # Generate filename from URL
        if output_file:
            filename = output_file
        else:
            parsed_url = urlparse(url)
            filename = parsed_url.netloc + parsed_url.path.replace('/', '_')
            if not filename.strip():
                filename = 'homepage'

        if output_type == 'screenshot':
            # Get the total height of the page
            total_height = driver.execute_script("return document.body.scrollHeight")
            
            # Set window size to capture full page
            driver.set_window_size(1920, total_height)
            
            # Take a full page screenshot
            screenshot_path = os.path.join('captures', f"{filename}.png")
            driver.save_screenshot(screenshot_path)
            print(f"Screenshot saved as {screenshot_path}")
            return screenshot_path
        elif output_type == 'content':
            # Get full page content
            page_content = driver.page_source
            content_path = os.path.join('captures', f"{filename}.html")
            with open(content_path, "w", encoding="utf-8") as f:
                f.write(page_content)
            print(f"Full page content saved as {content_path}")
            return content_path

    finally:
        driver.quit()

def main():
    parser = argparse.ArgumentParser(description="Capture webpage screenshot or content")
    parser.add_argument("url", help="URL to capture")
    parser.add_argument("--type", choices=['screenshot', 'content'], default='screenshot',
                        help="Type of capture: 'screenshot' or 'content' (default: screenshot)")
    parser.add_argument("-o", "--output", help="Output file name")
    
    args = parser.parse_args()
    
    capture_webpage(args.url, args.type, args.output)

if __name__ == "__main__":
    main()
