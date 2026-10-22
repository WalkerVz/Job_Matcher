import requests
from bs4 import BeautifulSoup
import json

print("Testing OpenTrain.ai - Direct extraction\n")

session = requests.Session()
session.headers.update({
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
})

url = "https://www.opentrain.ai/jobs/"
print(f"Fetching: {url}\n")

try:
    r = session.get(url, timeout=15)
    print(f"Status: {r.status_code}\n")
    
    if r.status_code == 200:
        soup = BeautifulSoup(r.text, 'html.parser')
        
        # Method 1: Direct text extraction
        text = soup.get_text()
        lines = text.split('\n')
        
        # Find patterns
        print("Raw text sample (first 2000 chars):")
        print(text[:2000])
        print("\n" + "="*60 + "\n")
        
        # Look for job title indicators
        job_titles = []
        for i, line in enumerate(lines):
            line = line.strip()
            if any(kw in line for kw in ['Expert', 'Engineer', 'Manager', 'Specialist', 'Designer', 'Attorney', 'Trainer', 'Creator', 'Evaluator', 'Analyst']):
                if len(line) > 10 and len(line) < 150:
                    job_titles.append(line)
                    print(f"Found: {line[:80]}")
        
        print(f"\n\nTotal patterns found: {len(job_titles)}")
        
        # Method 2: Check for data attributes
        print("\n\nChecking for data elements...")
        data_elems = soup.find_all(attrs={'class': lambda x: x and 'job' in x.lower()})
        print(f"Elements with 'job' class: {len(data_elems)}")
        
        # Method 3: Check scripts for embedded data
        scripts = soup.find_all('script', type='application/json')
        print(f"JSON scripts: {len(scripts)}")
        
        if len(scripts) > 0:
            for i, script in enumerate(scripts[:2]):
                try:
                    data = json.loads(script.string)
                    print(f"Script {i}: {type(data)}")
                    if isinstance(data, dict):
                        print(f"  Keys: {list(data.keys())[:5]}")
                    elif isinstance(data, list):
                        print(f"  Length: {len(data)}")
                        if len(data) > 0:
                            print(f"  First item keys: {list(data[0].keys())[:5] if isinstance(data[0], dict) else 'N/A'}")
                except:
                    pass
        
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")

print("\n\nConclusion: Site uses JavaScript rendering - needs Selenium or Playwright")
