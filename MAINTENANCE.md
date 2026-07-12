# MAINTENANCE.md - Automated Job Matcher & Scraper

## Project Overview
**Ravil's Career Radar & Job Matcher** - Static web app that scrapes 6 Indonesian career portals, scores jobs against a fixed profile (Python Developer/Data Analyst, 1yr exp), and displays results in a modern PWA.

## Tech Stack
- **Frontend**: Vanilla HTML/CSS/JS (ES6 modules), PWA with Service Worker
- **Scraper**: Python 3.10+ (requests, beautifulsoup4, ThreadPoolExecutor)
- **Data**: JSON (matched_jobs.json) + JS module (matched_jobs.js) for browser
- **Deploy**: Vercel (static hosting)
- **No package.json** - pure static files + Python script

## Folder Structure
```
job_matcher/
├── index.html          # Main HTML (10KB)
├── style.css           # Styles (40KB) - Dark mode, glassmorphism
├── app.js              # Frontend logic (980 lines) - filtering, pagination, modal
├── sw.js               # Service Worker (PWA offline support)
├── manifest.json       # PWA manifest
├── scraper.py          # Main scraper (1134 lines) - 6 portals, scoring, threading
├── matched_jobs.json   # Raw scraped data (1.5MB)
├── matched_jobs.js     # JS module export (1.3MB) - window.jobsData
├── update_jobs.bat     # Windows batch to run scraper + git commit
├── update_jobs.ipynb   # Jupyter notebook alternative
├── vercel.json         # Vercel config (SPA fallback)
├── .gitignore
└── README.md
```

## Key Files Deep Dive

### scraper.py (Core Logic)
**Profile** (hardcoded lines 10-20):
```python
PROFILE = {
    "name": "Muhammad Ravil",
    "gender": "Laki-laki",
    "age": 23,
    "gpa": 3.39,
    "toefl": 537,
    "major": "Teknik Informatika",
    "skills": ["python", "data science", "data analyst", ...],
    "experience": "Pertamina Hulu Rokan (Python Developer Intern...)",
    "exp_years": 1
}
```

**6 Portal Scrapers** (each has `scrape_<portal>()` function):
1. **Grab** (`grab.careers`) - GraphQL API
2. **IOH** (`careers.ioh.co.id`) - HTML parse
3. **Talentics** (`jobs.talentics.id`) - HTML parse (SKK Migas/KKKS)
4. **Astra** (`career.astra.co.id`) - HTML parse
5. **PTC** (`recruitment.pertamina-ptc.com`) - HTML parse
6. **SawitPRO** (`sawitpro.id/jobs`) - HTML parse

**Scoring Algorithm** (`calculate_match_score()` ~line 400):
- Major match (IT/CS/IS): +30
- Skill keyword match: +10 each (max 40)
- Experience match (1yr): +20
- Blocker detection (GPA min, age max, gender): -100 (hard reject)
- Returns score 0-100 + `is_match` boolean

**Output**: Writes both `matched_jobs.json` and `matched_jobs.js`

### app.js (Frontend)
**State**: `allJobs`, `filteredJobs`, `currentPage`, `itemsPerPage`, `wishlistOnly`

**Key Functions**:
- `loadJobsData()` - fetches from `matched_jobs.js` (window.jobsData)
- `applyFilters()` - search, source, match%, experience, wishlist
- `renderJobCards()` - creates DOM elements
- `renderPagination()` - handles 10/25/50/100/All per page
- `showJobDetail()` - modal with full job info
- `toggleWishlist()` - localStorage persistence

**PWA**: Service worker caches all static assets + data for offline use

## Maintenance Tasks

### Update Job Data (Weekly/Manual)
```bash
# Option 1: Windows batch
update_jobs.bat

# Option 2: Direct Python
python scraper.py

# Option 3: Jupyter
jupyter notebook update_jobs.ipynb
```
Then commit & push - Vercel auto-deploys.

### Modify User Profile
Edit `scraper.py` lines 10-20 (PROFILE dict). Re-run scraper.

### Add/Remove Job Portal
1. Add new `scrape_<portal>()` function in scraper.py
2. Add to `SCRAPERS` dict (line ~1050)
3. Add portal name to `sourceFilter` options in index.html (line ~200)
4. Update `SCRAPER_CONFIG` if needs auth/headers

### Adjust Scoring Weights
Modify `calculate_match_score()` in scraper.py:
- `MAJOR_BONUS = 30`
- `SKILL_BONUS = 10`
- `EXP_BONUS = 20`
- `BLOCKER_PENALTY = -100`

### Update UI/Styling
- `style.css`: Colors (CSS vars at top), glassmorphism, responsive breakpoints
- `index.html`: Filter options, modal structure, meta tags
- `app.js`: Filter logic, rendering, pagination

### Deploy Changes
```bash
git add .
git commit -m "feat: description"
git push origin main
# Vercel auto-deploys in ~30s
```

## Common Issues & Fixes

| Issue | Fix |
|-------|-----|
| Portal HTML changed | Update that portal's `scrape_<portal>()` function |
| Jobs not loading | Check `matched_jobs.js` syntax, browser console for CORS |
| Scoring wrong | Adjust weights in `calculate_match_score()` |
| PWA not updating | Bump version in `sw.js` cache name, or clear site data |
| Vercel 404 on refresh | `vercel.json` has SPA fallback - check routes |

## Data Schema (matched_jobs.json)
```json
{
  "title": "string",
  "company": "string",
  "location": "string",
  "experience": "string",
  "description": "string",
  "requirements": "string",
  "url": "string",
  "source": "Grab|IOH|Talentics|Astra|PTC|SawitPRO",
  "posted_date": "ISO string or 'Unknown'",
  "match_score": 0-100,
  "is_match": true|false,
  "match_reasons": ["string"],
  "blockers": ["string"],
  "scraped_at": "ISO timestamp"
}
```

## Performance Notes
- `matched_jobs.js` is 1.3MB - consider pagination lazy-load if grows >5MB
- Scraper uses ThreadPoolExecutor (max_workers=6) - completes in ~30-60s
- Frontend filters in-memory - O(n) per render, fine for <5000 jobs

## Security
- No secrets in repo (scraper uses public endpoints only)
- No backend - all client-side
- `vercel.json` blocks access to `.py`, `.json` raw files

## Useful Commands
```bash
# Validate JSON syntax
python -m json.tool matched_jobs.json > nul && echo OK

# Count jobs per source
python -c "import json; d=json.load(open('matched_jobs.json')); from collections import Counter; print(Counter(j['source'] for j in d))"

# Check for duplicates
python -c "import json; d=json.load(open('matched_jobs.json')); urls=[j['url'] for j in d]; print(len(urls), len(set(urls)))"
```