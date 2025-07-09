#!/usr/bin/env python3
"""
Update README.md with current language distribution from GitHub.
Only updates the language statistics, no other stats.
"""

import os
import re
import json
from collections import defaultdict
from urllib.request import urlopen, Request

def fetch_github_api(url, token):
    """Fetch data from GitHub API with authentication."""
    req = Request(url)
    req.add_header('Authorization', f'token {token}')
    req.add_header('Accept', 'application/vnd.github.v3+json')
    
    with urlopen(req) as response:
        return json.loads(response.read().decode())

def get_language_distribution(username, token):
    """Fetch language statistics across all public repositories."""
    languages = defaultdict(int)
    page = 1
    
    while True:
        # Get repos with pagination
        url = f'https://api.github.com/users/{username}/repos?type=all&per_page=100&page={page}'
        repos = fetch_github_api(url, token)
        
        if not repos:
            break
            
        for repo in repos:
            # Skip private repos, forks, and repos not owned by the user
            if (not repo.get('private', True) and 
                not repo.get('fork', False) and 
                repo.get('owner', {}).get('login', '').lower() == username.lower()):
                
                print(f"  Processing {repo.get('name')} (original repo)...")
                try:
                    # Get languages for each repo
                    languages_url = repo['languages_url']
                    repo_languages = fetch_github_api(languages_url, token)
                    
                    # Filter out certain languages that are typically not "written" by the user
                    excluded_languages = {'Jupyter Notebook', 'HTML', 'CSS', 'Shell', 'Dockerfile', 
                                        'Makefile', 'CMake', 'M4', 'Roff', 'Yacc', 'Lex', 'Vim script',
                                        'Emacs Lisp', 'XSLT', 'Rich Text Format', 'DIGITAL Command Language',
                                        'Module Management System', 'SRecode Template', 'RPC', 'XS',
                                        'Logos', 'LLVM', 'Objective-C++'}
                    
                    for lang, bytes_count in repo_languages.items():
                        if lang not in excluded_languages:
                            languages[lang] += bytes_count
                except Exception as e:
                    print(f"Skipping repo {repo.get('name', 'unknown')}: {e}")
                    pass
        
        page += 1
    
    return languages

def calculate_language_percentages(languages):
    """Calculate percentage for each language."""
    total = sum(languages.values())
    if total == 0:
        return []
    
    percentages = {}
    for lang, bytes_count in languages.items():
        percentage = (bytes_count / total) * 100
        if percentage >= 0.5:  # Include languages with >= 0.5%
            percentages[lang] = percentage
    
    # Sort by percentage descending
    sorted_langs = sorted(percentages.items(), key=lambda x: x[1], reverse=True)
    return sorted_langs[:5]  # Top 5 languages

def generate_progress_bar(percentage, width=50):
    """Generate a text-based progress bar."""
    filled = int((percentage / 100) * width)
    bar = '█' * filled + '░' * (width - filled)
    return bar

def parse_existing_languages(content):
    """Parse the existing language distribution from README content."""
    pattern = r'│\s+(\w+)\s+[█░]+\s+([\d.]+)%\s+│'
    matches = re.findall(pattern, content)
    return [(lang, float(pct)) for lang, pct in matches]

def is_meaningful_change(old_languages, new_languages):
    """Determine if the change in language distribution is meaningful."""
    # Convert to dictionaries for easier comparison
    old_dict = {lang: pct for lang, pct in old_languages}
    new_dict = {lang: pct for lang, pct in new_languages}
    
    # Check 1: New language in top 5 or language dropped from top 5
    old_langs = set(lang for lang, _ in old_languages)
    new_langs = set(lang for lang, _ in new_languages)
    if old_langs != new_langs:
        print(f"Meaningful change: Language set changed from {old_langs} to {new_langs}")
        return True
    
    # Check 2: Any language changed by 1% or more
    for lang, new_pct in new_dict.items():
        old_pct = old_dict.get(lang, 0)
        if abs(new_pct - old_pct) >= 1.0:
            print(f"Meaningful change: {lang} changed from {old_pct:.1f}% to {new_pct:.1f}%")
            return True
    
    # Check 3: Order of languages changed
    old_order = [lang for lang, _ in old_languages]
    new_order = [lang for lang, _ in new_languages]
    if old_order != new_order:
        print(f"Meaningful change: Language order changed from {old_order} to {new_order}")
        return True
    
    print("No meaningful changes detected")
    return False

def update_readme(languages):
    """Update README.md with new language distribution."""
    with open('README.md', 'r') as f:
        content = f.read()
    
    # Parse existing languages
    existing_languages = parse_existing_languages(content)
    
    # Check if this is a meaningful change
    if existing_languages and not is_meaningful_change(existing_languages, languages):
        return False
    
    # Build the new language distribution section
    lang_section = "```\n┌──────────────────────────────────────────────────────────────────────────────┐\n"
    lang_section += "│                          Language Distribution                               │\n"
    lang_section += "├──────────────────────────────────────────────────────────────────────────────┤\n"
    
    for lang, percentage in languages:
        bar = generate_progress_bar(percentage, 50)
        # Ensure proper spacing and alignment
        lang_padded = f"{lang:<10}"
        percentage_str = f"{percentage:>5.1f}%"
        # Adjust spacing: removed extra spaces to accommodate wider bar
        lang_section += f"│ {lang_padded} {bar} {percentage_str} │\n"
    
    lang_section += "└──────────────────────────────────────────────────────────────────────────────┘\n```"
    
    # Find and replace the language distribution section
    # Look for the pattern that starts with ```\n┌─── and contains "Language Distribution"
    # Allow for optional newlines
    pattern = r'```\n┌──────────────────────────────────────────────────────────────────────────────┐\n│\s+Language Distribution\s+│\n├──────────────────────────────────────────────────────────────────────────────┤\n.*?└──────────────────────────────────────────────────────────────────────────────┘\n+```'
    
    # Check if pattern exists
    if re.search(pattern, content, flags=re.DOTALL):
        new_content = re.sub(pattern, lang_section, content, flags=re.DOTALL)
    else:
        print("Warning: Could not find language distribution section in README")
        return False
    
    # Write the changes
    with open('README.md', 'w') as f:
        f.write(new_content)
    return True

def main():
    username = 'marcusziade'
    token = os.environ.get('GITHUB_TOKEN')
    
    if not token:
        # Try GH_TOKEN as alternative
        token = os.environ.get('GH_TOKEN')
        if not token:
            print("Error: GITHUB_TOKEN or GH_TOKEN environment variable not set")
            exit(1)
    
    print(f"Fetching language distribution for {username}...")
    languages = get_language_distribution(username, token)
    
    print("Calculating language percentages...")
    language_percentages = calculate_language_percentages(languages)
    
    if not language_percentages:
        print("No language data found")
        exit(1)
    
    print("\nLanguage distribution:")
    for lang, pct in language_percentages:
        print(f"  {lang}: {pct:.1f}%")
    
    print("\nUpdating README.md...")
    if update_readme(language_percentages):
        print("README.md updated with new language distribution")
    else:
        print("No changes detected, skipping update")

if __name__ == '__main__':
    main()