import os
import json
import requests
from base64 import b64encode
import markdown

# === LOAD CONFIGURATION FROM config.json ===
with open('config.json', 'r', encoding='utf-8') as config_file:
    config = json.load(config_file)

directory_path = config.get('directory_path')
wp_url = config.get('wp_url')
username = config.get('username')
app_password = config.get('app_password')

# === AUTHORIZATION HEADER ===
credentials = f'{username}:{app_password}'
token = b64encode(credentials.encode()).decode('utf-8')
headers = {
    'Authorization': f'Basic {token}',
    'Content-Type': 'application/json'
}

# === FUNCTION TO UPLOAD FILE ===
def upload_markdown_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        md_content = f.read()

    # Convert markdown to HTML
    html_content = markdown.markdown(md_content)

    title = os.path.splitext(os.path.basename(filepath))[0]

    data = {
        'title': title,
        'content': html_content,
        'status': 'draft'
    }

    try:
        response = requests.post(wp_url, json=data, headers=headers)
        response.raise_for_status()
        print(f'✅ Uploaded: {title}')
    except requests.exceptions.HTTPError as err:
        print(f'❌ Failed to upload {title}: {err} - {response.text}')

# === MAIN LOOP ===
for filename in os.listdir(directory_path):
    if filename.endswith('.md'):
        full_path = os.path.join(directory_path, filename)
        upload_markdown_file(full_path)
