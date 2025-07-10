#!/usr/bin/env python3
import xml.etree.ElementTree as ET
import urllib.request
import re
from datetime import datetime

def fetch_blog_posts():
    rss_url = 'https://compiledthoughts.pages.dev/rss.xml'
    
    try:
        req = urllib.request.Request(rss_url)
        req.add_header('User-Agent', 'Mozilla/5.0 (compatible; GitHub Actions)')
        with urllib.request.urlopen(req) as response:
            rss_content = response.read()
        
        root = ET.fromstring(rss_content)
        
        posts = []
        for item in root.findall('.//item')[:10]:  # Get last 10 posts
            title = item.find('title').text if item.find('title') is not None else ''
            link = item.find('link').text if item.find('link') is not None else ''
            pub_date = item.find('pubDate').text if item.find('pubDate') is not None else ''
            
            # Parse and format date
            if pub_date:
                try:
                    # Try multiple date formats
                    date_formats = [
                        '%a, %d %b %Y %H:%M:%S %Z',
                        '%a, %d %b %Y %H:%M:%S %z',
                        '%d %b %Y %H:%M:%S %Z'
                    ]
                    date_obj = None
                    for fmt in date_formats:
                        try:
                            date_obj = datetime.strptime(pub_date, fmt)
                            break
                        except:
                            continue
                    
                    if date_obj:
                        formatted_date = date_obj.strftime('%b %-d, %Y')
                    else:
                        formatted_date = pub_date
                except:
                    formatted_date = pub_date
            else:
                formatted_date = ''
            
            posts.append({
                'title': title,
                'link': link,
                'date': formatted_date
            })
        
        return posts
    except Exception as e:
        print(f"Error fetching blog posts: {e}")
        return []

def update_readme():
    posts = fetch_blog_posts()
    if not posts:
        print("No blog posts found")
        return False
    
    # Read current README
    with open('README.md', 'r') as f:
        content = f.read()
    
    # Extract current blog posts section if it exists
    blog_start = content.find('<!-- Recent Blog Posts -->')
    blog_end = content.find('<!-- End Recent Blog Posts -->')
    
    if blog_start == -1 or blog_end == -1:
        print("Blog posts section not found in README")
        return False
    
    # Extract current blog section
    blog_end += len('<!-- End Recent Blog Posts -->')
    current_section = content[blog_start:blog_end]
    
    # Build new blog posts section
    new_lines = []
    for post in posts:
        line = f'<a href="{post["link"]}">{post["title"]}</a> • {post["date"]}'
        new_lines.append(line)
    
    new_section = f'''<!-- Recent Blog Posts -->
<div style="width: 80%; text-align: right;">
<pre style="text-align: left; margin-left: auto; font-size: 0.7em; line-height: 1.4;">
{chr(10).join(new_lines)}
</pre>
</div>
<!-- End Recent Blog Posts -->'''
    
    # Check if content changed
    if current_section.strip() == new_section.strip():
        print("No changes in blog posts")
        return False
    
    # Update README
    new_content = content[:blog_start] + new_section + content[blog_end:]
    
    with open('README.md', 'w') as f:
        f.write(new_content)
    
    print("README updated with new blog posts")
    return True

if __name__ == '__main__':
    changed = update_readme()
    # Create a flag file if changes were made
    if changed:
        with open('blog_changes_detected', 'w') as f:
            f.write('true')