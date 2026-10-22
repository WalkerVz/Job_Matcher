from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

print("Testing Selenium with OpenTrain...\n")

try:
    # Setup Selenium
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64)")
    
    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=chrome_options)
    
    print("OK: Chrome driver initialized\n")
    
    url = "https://www.opentrain.ai/jobs/"
    print(f"Loading: {url}")
    driver.get(url)
    
    print("OK: Page loaded")
    print(f"OK: Page title: {driver.title}\n")
    
    # Wait for content
    time.sleep(5)
    
    # Parse page
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    # Get text sample
    text = soup.get_text()
    print(f"Page text length: {len(text)} chars\n")
    print("First 1000 chars:")
    print(text[:1000])
    print("\n" + "="*60 + "\n")
    
    # Look for job elements
    job_cards = soup.find_all(['div', 'article'], class_=lambda x: x and ('job' in str(x).lower() or 'card' in str(x).lower()))
    print(f"Found {len(job_cards)} job card elements\n")
    
    # Search for job titles
    lines = text.split('\n')
    job_titles = []
    for line in lines:
        line = line.strip()
        if any(kw in line for kw in ['Expert', 'Engineer', 'Specialist', 'Manager', 'Trainer', 'Analyst']):
            if len(line) > 10 and len(line) < 150:
                job_titles.append(line)
    
    print(f"Found {len(job_titles)} potential job titles\n")
    if len(job_titles) > 0:
        print("Sample titles:")
        for title in job_titles[:5]:
            print(f"  - {title}")
    
    driver.quit()
    print("\n✓ Browser closed successfully")
    
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
