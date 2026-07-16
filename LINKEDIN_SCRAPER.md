# LinkedIn Job Scraper - Safe Rate-Limiting Approach

## Overview
LinkedIn scraper module yang aman untuk production, dengan built-in rate-limiting untuk menghindari 403 Forbidden / 429 Too Many Requests.

## Safety Features

### 1. **Rate Limiting**
- **Delay**: 2-5 detik antar request (random rotation)
- **Batch size**: 25 jobs per request (LinkedIn recommended)
- **Max jobs**: 300 per run (default) - dapat disesuaikan

### 2. **User-Agent Rotation**
```python
- Chrome on Windows
- Chrome on macOS
- Chrome on Linux
```
Mencegah LinkedIn mendeteksi bot pattern yang sama terus-menerus.

### 3. **Location Filter**
- Search keyword: `"Indonesia"` (explicit location filter)
- Hanya mengambil job listings dari Indonesia

### 4. **Error Handling**
```
- 429 (Too Many Requests) → Wait 30 sec, retry
- 403 (Forbidden) → Stop gracefully (jangan spam)
- 4xx/5xx → Log & skip
```

## Function Signature
```python
def scrape_linkedin_jobs(session, max_jobs=300):
    """
    session: requests.Session() object dengan headers sudah diatur
    max_jobs: Maximum jobs to scrape (default 300)
    
    Returns: List of job dicts dengan struktur standard:
    {
        "id": "linkedin_12345",
        "title": "Data Analyst",
        "organization_name": "PT Tech Indonesia",
        "location": "Jakarta, Indonesia",
        "url": "https://linkedin.com/jobs/view/12345",
        "source": "LinkedIn",
        ...
    }
    """
```

## Implementation in main()
```python
# Step 3h: Call LinkedIn scraper
linkedin_jobs = scrape_linkedin_jobs(session, max_jobs=300)
for job in linkedin_jobs:
    matched_job = evaluate_job_match(job)
    matched_jobs.append(matched_job)
```

## Performance
- ~12 pages × 25 jobs/page = 300 jobs
- ~30 seconds total (dengan 2-5sec delays)
- Safe untuk Kaggle notebook environment

## Rate Limits Reference
| Limit | Threshold | Action |
|-------|-----------|--------|
| Requests/sec | >1 | Wait 1-5 sec |
| Requests/min | >30 | Wait 30 sec |
| Requests/hour | >200 | Exponential backoff |
| Total jobs/run | 300 | Graceful stop |

## Testing
```bash
# Test syntax
python -m py_compile scraper.py

# Run full scraper (including LinkedIn)
python scraper.py
```

## Notes
- LinkedIn API endpoint: `https://www.linkedin.com/jobs-guest/jobs/api/jobs`
- Public endpoint, no authentication required
- Returns HTML (not JSON) - parse dengan BeautifulSoup
- Location-aware searching mengurangi false positives

## Future Improvements
- [ ] Add exponential backoff for 429 errors
- [ ] Cache job listings (deduplicate across runs)
- [ ] Skill matching optimization untuk LinkedIn format
