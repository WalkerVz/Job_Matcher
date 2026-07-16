# LinkedIn Jobs - Manual Export Approach

## Problem
LinkedIn actively blocks automated scrapers with:
- 404 Not Found (endpoint blocked)
- 403 Forbidden (IP/User-Agent banned)
- 429 Too Many Requests (rate limit)

**Recommendation**: Use manual LinkedIn search + CSV export instead.

## Solution: Manual Search + Export (5 minutes)

### Step 1: Search LinkedIn Jobs
1. Go to: https://www.linkedin.com/jobs/search/?keywords=data%20analyst&location=Indonesia
2. Filter:
   - Keywords: "data analyst", "python", "machine learning", "data scientist"
   - Location: Indonesia
   - Experience level: Entry, Mid-level

### Step 2: Export to CSV
LinkedIn allows up to 500 job results per search. Export process:
1. Click **"Save"** or bookmark the search
2. Use browser **Developer Tools** (F12) → Console → Run this script:

```javascript
// Extract visible jobs on page
const jobs = [];
document.querySelectorAll('.jobs-search-results [data-job-id]').forEach(el => {
  const title = el.querySelector('.base-search-card__title')?.innerText || '';
  const company = el.querySelector('.base-search-card__subtitle')?.innerText || '';
  const location = el.querySelector('.job-search-card__location')?.innerText || '';
  const url = el.querySelector('a.base-card__full-link')?.href || '';
  
  jobs.push({
    title: title.trim(),
    company: company.trim(),
    location: location.trim(),
    url: url.trim()
  });
});

// Copy to clipboard as JSON
copy(JSON.stringify(jobs, null, 2));
console.log(`✅ Copied ${jobs.length} jobs to clipboard. Paste into new_jobs_linkedin.json`);
```

3. Paste output into: `new_jobs_linkedin.json`

### Step 3: Import into Scraper
Create `import_linkedin_csv.py`:

```python
import json
import csv

def import_linkedin_jobs(json_file="new_jobs_linkedin.json"):
    """Load manually exported LinkedIn jobs from JSON."""
    with open(json_file, encoding='utf-8') as f:
        jobs_data = json.load(f)
    
    linkedin_jobs = []
    for idx, job in enumerate(jobs_data):
        linkedin_jobs.append({
            "id": f"linkedin_{idx}",
            "title": job.get("title", ""),
            "organization_id": "LinkedIn",
            "organization_name": job.get("company", ""),
            "slug": f"linkedin-{idx}",
            "type_name": "Full Time / Contract",
            "level": "Profesional",
            "location": job.get("location", "Indonesia"),
            "workplace": "Hybrid / WFO",
            "due_date": "Aktif",
            "group": "Tech & Data",
            "url": job.get("url", ""),
            "description": f"<p>{job.get('title')}</p><p>{job.get('company')}</p>",
            "requirements": f"<p>{job.get('title')}</p><p>{job.get('company')}</p>",
            "source": "LinkedIn",
            "logo": None
        })
    
    return linkedin_jobs

if __name__ == "__main__":
    linkedin_jobs = import_linkedin_jobs()
    print(f"Imported {len(linkedin_jobs)} LinkedIn jobs from JSON")
    with open("linkedin_jobs_imported.json", "w", encoding='utf-8') as f:
        json.dump(linkedin_jobs, f, indent=2, ensure_ascii=False)
```

### Alternative: Use LinkedIn Recruiter API
If integrating with production system:
1. Apply for [LinkedIn Recruiter API](https://business.linkedin.com/talent-solutions/recruiter)
2. Requires LinkedIn Enterprise subscription
3. Official, authorized, no rate-limiting issues

## Current Approach
**Scraper skips LinkedIn (Step 3h commented out)** and focuses on 7 stable portals:
- ✅ Talentics (SKK Migas search)
- ✅ Astra Careers
- ✅ Pertamina Training & Consulting (PTC)
- ✅ SawitPRO
- ✅ Grab Careers Indonesia
- ✅ Indosat Ooredoo Hutchison (IOH)
- ✅ Indofood Careers

**Total**: ~270+ jobs per scrape run (verified stable)

## Why Not Selenium?
Selenium approach rejected because:
1. **Slow**: 2-5 min for 300 jobs (vs 3-5 sec for static portals)
2. **Resource-intensive**: Kaggle notebook has limited resources
3. **Unreliable**: LinkedIn detects and blocks Selenium user-agents
4. **Maintenance**: Breakage on UI changes

## Recommendation for Production
1. **Short term**: Use 7 stable portals (current)
2. **Medium term**: Add manual LinkedIn CSV export workflow
3. **Long term**: Integrate LinkedIn Recruiter API (if budget allows)

This balanced approach maintains reliability while keeping job listings fresh.
