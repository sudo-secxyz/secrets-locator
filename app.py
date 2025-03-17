import re
import requests
import argparse
import base64
import os

# Set up argument parsing
parser = argparse.ArgumentParser()
parser.add_argument('-u', '--url', help='GitHub repository URL (https://github.com/user/repo)')
parser.add_argument('-t', '--token', help='GitHub Access Token for API authentication')
args = parser.parse_args()

# Extract repo owner and name from URL
def extract_repo_info(url):
    parts = url.strip().split("/")
    return parts[-2], parts[-1]  # returns (owner, repo_name)

# GitHub API URL format
def get_github_api_url(owner, repo):
    return f'https://api.github.com/repos/{owner}/{repo}/contents'

# Function to find secrets in text
def find_secrets(text):
    # Common API key patterns
    api_key_patterns = [
        r"\b(?:API_KEY|API key|apikey|CLIENT_SECRET|CLIENT secret|client_secret|SECRET_KEY|SECRET_key|secret_key)\s*[:-]\s*['\"]?([a-zA-Z0-9\-_]+)['\"]?",
        r"(?:API_KEY|API key|apikey|CLIENT_SECRET|CLIENT secret|client_secret|SECRET_KEY|SECRET_key|secret_key)[\s:-]*['\"]?([a-zA-Z0-9\-_]+)['\"]?",
        r"(?:API_KEY|API key|apikey|CLIENT_SECRET|CLIENT secret|client_secret|SECRET_KEY|SECRET_key|secret_key)",
        r"sk_live_[a-zA-Z0-9]{24}",  # Stripe live key
        r"rk_live_[a-zA-Z0-9]{24}",  # Recurly live key
        r"pk_live_[a-zA-Z0-9]{24}",  # Stripe public key
        r"access_token\$[a-zA-Z0-9\-\_]+",
        r"gh_[a-zA-Z0-9]{40}",  # GitHub key
        r"[\s:-][a-zA-Z0-9]{25}",  # Okta key

    ]
    
    found_keys = []
    for pattern in api_key_patterns:
        matches = re.findall(pattern, text)
        found_keys.extend(matches)
    return found_keys

# Function to get file content from GitHub
def get_file_content_from_github(url, token):
    headers = {'Authorization': f'token {token}'} if token else {}
    response = requests.get(url, headers=headers)
    
    if response.status_code == 200:
        content_data = response.json()
        if content_data:
            return content_data
    else:
        print(f"Error: {response.status_code}")
        return None

# Recursive function to traverse GitHub repo and search for secrets
def search_repo_for_secrets(owner, repo, token, path=""):
    url = get_github_api_url(owner, repo) + path
    content_data = get_file_content_from_github(url, token)
    
    if content_data is None:
        return
    
    for file_info in content_data:
        file_path = file_info['path']
        if file_info['type'] == 'file':  # File found, now fetch the content
            if file_path.endswith(('.py', '.js', '.env')):  # Limit to certain file types (optional)
                file_url = file_info['download_url']
                response = requests.get(file_url)
                
                if response.status_code == 200:
                    file_content = response.text
                    keys = find_secrets(file_content)
                    if keys:
                        print(f"Secrets found in {file_path}:")
                        for key in keys:
                            print(f"\t{key}")
        elif file_info['type'] == 'dir':  # Directory found, recurse into it
            search_repo_for_secrets(owner, repo, token, path=f"/{file_path}")

# Main execution
if args.url and args.token:
    repo_owner, repo_name = extract_repo_info(args.url)
    print(f"Searching for secrets in {repo_owner}/{repo_name}...")
    search_repo_for_secrets(repo_owner, repo_name, args.token)
else:
    print("Please provide both GitHub repository URL and access token using -u and -t flags.")