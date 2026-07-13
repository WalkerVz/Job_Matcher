"""Re-score existing matched_jobs.json menggunakan PROFILE terbaru di scraper.py."""
import json
from scraper import evaluate_job_match, save_jobs

with open("matched_jobs.json", encoding="utf-8") as f:
    jobs = json.load(f)

rescored = []
for job in jobs:
    raw = {
        "id": job.get("id"),
        "title": job.get("title"),
        "organization_id": job.get("organization_id"),
        "organization_name": job.get("organization_name"),
        "slug": job.get("slug"),
        "type_name": job.get("type_name"),
        "level": job.get("level"),
        "location": job.get("location"),
        "workplace": job.get("workplace"),
        "due_date": job.get("due_date"),
        "group": job.get("group"),
        "url": job.get("url"),
        "description": job.get("raw_description", ""),
        "requirements": job.get("raw_requirements", ""),
        "source": job.get("source"),
        "logo": job.get("logo"),
    }
    rescored.append(evaluate_job_match(raw))

rescored.sort(key=lambda x: (0 if x["is_blocked"] else 1, x["match_score"]), reverse=True)
filtered = [j for j in rescored if j["match_details"]["major"]["status"] in ["High Match", "Match"]]
print(f"Rescored: {len(rescored)} -> filtered: {len(filtered)}")

ts = save_jobs(filtered)
print("Done. Timestamp:", ts)
