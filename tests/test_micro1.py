import requests
from bs4 import BeautifulSoup
import json

print("Testing Micro1 Jobs Scraper...\n")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

# Try different endpoints
urls = [
    "https://microonejobs.com/jobs",
    "https://microonejobs.com/api/jobs",
    "https://microonejobs.com/api/vacancies",
]

for url in urls:
    print(f"Testing: {url}")
    try:
        r = session.get(url, timeout=5)
        print(f"  Status: {r.status_code}")
        
        if r.status_code == 200:
            # Try parse as JSON first
            try:
                data = r.json()
                print(f"  JSON Response: {type(data)}")
                print(f"  Keys: {list(data.keys())[:5] if isinstance(data, dict) else 'N/A'}")
                if isinstance(data, list):
                    print(f"  Items count: {len(data)}")
                    if len(data) > 0:
                        print(f"  First item: {data[0]}")
            except:
                # Try HTML parsing
                soup = BeautifulSoup(r.text, 'html.parser')
                job_elements = soup.find_all(['div', 'article'], class_=['job', 'vacancy', 'listing', 'card'])
                print(f"  HTML Elements found: {len(job_elements)}")
                
                # Check for script data
                scripts = soup.find_all('script', type='application/json')
                print(f"  JSON scripts found: {len(scripts)}")
                if len(scripts) > 0:
                    try:
                        data = json.loads(scripts[0].string)
                        print(f"  Embedded JSON: {type(data)}, {list(data.keys())[:3] if isinstance(data, dict) else len(data)}")
                    except:
                        pass
    except Exception as e:
        print(f"  Error: {type(e).__name__}: {str(e)[:50]}")
    
    print()

print("\nConclusion: Check which endpoint returns data")
print("If no luck, might need Selenium for JavaScript rendering")
