#!/usr/bin/env python3
"""
Update README.md with current GitHub statistics.
Fetches real-time data from GitHub API and updates the stats widgets.
"""

import os
import re
from collections import defaultdict
from datetime import datetime
from github import Github
import requests

def get_github_stats(username, token):
    """Fetch GitHub statistics for a user."""
    g = Github(token)
    user = g.get_user(username)
    
    stats = {
        'total_stars': 0,
        'total_commits': 0,
        'total_prs': 0,
        'total_issues': 0,
        'contributed_to': set(),
        'languages': defaultdict(int),
        'total_repos': 0,
        'lines_of_code': 0,
        'published_packages': 0
    }
    
    # Get all repositories
    for repo in user.get_repos():
        stats['total_repos'] += 1
        if not repo.fork:  # Only count non-forked repos
            stats['total_stars'] += repo.stargazers_count
            
            # Get languages for each repo
            languages = repo.get_languages()
            for lang, bytes_count in languages.items():
                stats['languages'][lang] += bytes_count
                # Rough estimate: 25 bytes per line of code
                stats['lines_of_code'] += bytes_count // 25
            
            # Count published packages (repos with releases)
            try:
                if repo.get_releases().totalCount > 0:
                    stats['published_packages'] += 1
            except:
                pass
    
    # Use GitHub GraphQL API for more detailed stats
    # Note: contributionsCollection without date range only shows last year
    # For lifetime stats, we need to aggregate across multiple years
    current_year = datetime.now().year
    lifetime_commits = 0
    lifetime_prs = 0
    lifetime_issues = 0
    contributed_repos = set()
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    # Fetch data for multiple years (GitHub API typically has data from 2008+)
    for year in range(2008, current_year + 1):
        query = """
        query($username: String!, $from: DateTime!, $to: DateTime!) {
          user(login: $username) {
            contributionsCollection(from: $from, to: $to) {
              totalCommitContributions
              totalPullRequestContributions
              totalIssueContributions
              commitContributionsByRepository {
                repository {
                  nameWithOwner
                }
              }
            }
          }
        }
        """
        
        variables = {
            'username': username,
            'from': f'{year}-01-01T00:00:00Z',
            'to': f'{year}-12-31T23:59:59Z'
        }
        
        response = requests.post(
            'https://api.github.com/graphql',
            json={'query': query, 'variables': variables},
            headers=headers
        )
        
        if response.status_code == 200:
            data = response.json().get('data', {}).get('user', {}).get('contributionsCollection', {})
            lifetime_commits += data.get('totalCommitContributions', 0)
            lifetime_prs += data.get('totalPullRequestContributions', 0)
            lifetime_issues += data.get('totalIssueContributions', 0)
            
            # Track contributed repositories
            for contrib in data.get('commitContributionsByRepository', []):
                if contrib.get('repository'):
                    contributed_repos.add(contrib['repository']['nameWithOwner'])
    
    stats['total_commits'] = lifetime_commits
    stats['total_prs'] = lifetime_prs
    stats['total_issues'] = lifetime_issues
    stats['contributed_to'] = len(contributed_repos)
    
    return stats

def calculate_language_percentages(languages):
    """Calculate percentage for each language."""
    total = sum(languages.values())
    if total == 0:
        return {}
    
    percentages = {}
    for lang, bytes_count in languages.items():
        percentage = (bytes_count / total) * 100
        if percentage >= 1.0:  # Only include languages with >= 1%
            percentages[lang] = percentage
    
    # Sort by percentage descending
    sorted_langs = sorted(percentages.items(), key=lambda x: x[1], reverse=True)
    return sorted_langs[:5]  # Top 5 languages

def generate_progress_bar(percentage, width=50):
    """Generate a text-based progress bar."""
    filled = int((percentage / 100) * width)
    bar = '█' * filled + '░' * (width - filled)
    return bar

def format_number(num):
    """Format large numbers with K/M suffixes."""
    if num >= 1_000_000:
        return f"{num/1_000_000:.1f}M"
    elif num >= 1_000:
        return f"{num/1_000:.1f}K"
    else:
        return str(num)

def update_readme(stats, languages):
    """Update README.md with new statistics."""
    with open('README.md', 'r') as f:
        content = f.read()
    
    # Update Language Distribution
    lang_section = "```\n┌──────────────────────────────────────────────────────────────────────────────┐\n"
    lang_section += "│                          Language Distribution                                │\n"
    lang_section += "├──────────────────────────────────────────────────────────────────────────────┤\n"
    
    for lang, percentage in languages:
        bar = generate_progress_bar(percentage, 35)
        lang_section += f"│ {lang:<10} {bar} {percentage:>5.1f}%     │\n"
    
    lang_section += "└──────────────────────────────────────────────────────────────────────────────┘"
    
    # Update Activity stats in Tech Stack section
    # Find and update the Activity section
    activity_pattern = r'(│ Activity\s+│\n)(│\s+\d+\+ Repositories\s+│\n)(│\s+[\d,]+\+ Commits\s+│\n)(│\s+[\dKM]+\+ Lines of Code\s+│\n)(│\s+\d+\+ Published Packages\s+│)'
    
    activity_replacement = (
        r'\1'
        f'│   {stats["total_repos"]}+ Repositories                 │\n'
        f'│   {format_number(stats["total_commits"])}+ Commits                    │\n'
        f'│   {format_number(stats["lines_of_code"])}+ Lines of Code               │\n'
        f'│   {stats["published_packages"]}+ Published Packages            │'
    )
    
    content = re.sub(activity_pattern, activity_replacement, content)
    
    # Update the language distribution section
    lang_pattern = r'```\n┌──────────────────────────────────────────────────────────────────────────────┐\n│\s+Language Distribution\s+│\n├──────────────────────────────────────────────────────────────────────────────┤\n.*?└──────────────────────────────────────────────────────────────────────────────┘'
    content = re.sub(lang_pattern, lang_section, content, flags=re.DOTALL)
    
    # Update Open Source Stats
    stats_section = f"""```
┌─── Open Source Stats (Lifetime) ────────────────────────────────────────────┐
│                                                                              │
│ Total Stars Earned:     {format_number(stats['total_stars']):<10}   Total PRs:         {format_number(stats['total_prs']):<10}      │
│ Total Commits:          {format_number(stats['total_commits']):<10}   Total Issues:      {format_number(stats['total_issues']):<10}      │
│ Contributed to:         {stats['contributed_to']} projects                                       │
│                                                                              │
└──────────────────────────────────────────────────────────────────────────────┘
```"""
    
    # Update the stats section
    stats_pattern = r'```\n┌─── Open Source Stats.*?└──────────────────────────────────────────────────────┘\n```'
    content = re.sub(stats_pattern, stats_section, content, flags=re.DOTALL)
    
    # Check if there are meaningful changes
    with open('README.md', 'r') as f:
        original_content = f.read()
    
    # Extract just the numbers for comparison
    original_numbers = re.findall(r'\d+[KM]?(?:\.\d+)?', original_content)
    new_numbers = re.findall(r'\d+[KM]?(?:\.\d+)?', content)
    
    # Only update if there are meaningful changes
    if original_numbers != new_numbers:
        with open('README.md', 'w') as f:
            f.write(content)
        return True
    
    return False

def main():
    username = 'marcusziade'
    token = os.environ.get('GITHUB_TOKEN')
    
    if not token:
        print("Error: GITHUB_TOKEN environment variable not set")
        exit(1)
    
    print(f"Fetching GitHub stats for {username}...")
    stats = get_github_stats(username, token)
    
    print("Calculating language distribution...")
    languages = calculate_language_percentages(stats['languages'])
    
    print("Updating README.md...")
    if update_readme(stats, languages):
        print("README.md updated with new statistics")
    else:
        print("No meaningful changes detected, skipping update")

if __name__ == '__main__':
    main()