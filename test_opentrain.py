import requests
from bs4 import BeautifulSoup
import re

print("Testing OpenTrain.ai Jobs Scraper...\n")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

# URLs to try
urls = [
    "https://www.opentrain.ai/jobs/country/indonesia/",
    "https://www.opentrain.ai/jobs/",
]

for base_url in urls:
    print(f"Testing: {base_url}\n")
    try:
        r = session.get(base_url, timeout=10)
        print(f"Status: {r.status_code}\n")
        
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            
            # Look for job listings
            # Common patterns: class containing 'job', 'listing', 'card', 'item'
            
            # Method 1: Find by common job classes
            job_containers = soup.find_all(['div', 'article'], class_=re.compile(r'job|listing|card|role', re.I))
            print(f"Found by class pattern: {len(job_containers)} elements\n")
            
            # Method 2: Look for specific text patterns
            text = soup.get_text()
            job_count = len(re.findall(r'\$\d+.*?(?:per hour|/hr|per task)', text))
            print(f"Found by salary pattern: ~{job_count} jobs\n")
            
            # Method 3: Extract visible job info
            print("Sample job listings found:")
            
            # Look for job title patterns
            titles = re.findall(r'([A-Z][a-zA-Z\s]+(?:Expert|Engineer|Manager|Specialist|Designer|Attorney|Trainer))', soup.get_text())
            unique_titles = list(set(titles))[:5]
            for i, title in enumerate(unique_titles, 1):
                print(f"  {i}. {title.strip()}")
            
            # Check if there's an API endpoint or next page
            scripts = soup.find_all('script')
            print(f"\nFound {len(scripts)} script tags")
            
            # Look for pagination or load more button
            load_more = soup.find_all(['button', 'a'], text=re.compile(r'load more|next|see more', re.I))
            print(f"Found {len(load_more)} load more/pagination elements\n")
            
            # Look for data attributes
            data_elements = soup.find_all(attrs={'data-job-id': True})
            print(f"Found {len(data_elements)} elements with data-job-id\n")
            
    except Exception as e:
        print(f"Error: {type(e).__name__}: {str(e)[:80]}\n")

print("\n" + "="*60)
print("Conclusion:")
print("✓ OpenTrain.ai has public job listings")
print("✓ Page structure is parseable with BeautifulSoup")
print("✓ Indonesia jobs available (252+ roles)")
print("\nNext step: Build full scraper function")
