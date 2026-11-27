"""Re-score existing matched_jobs.json menggunakan PROFILE & scoring engine terbaru di scraper.py."""
import json
from scraper import deduplicate_jobs, evaluate_job_match, save_jobs

with open("matched_jobs.json", encoding="utf-8") as f:
    jobs = json.load(f)

rescored = []
for job in jobs:
    location = job.get("location")
    if isinstance(location, str) and location.startswith("-R-e-m-o-t-e-"):
        # Pulihkan lokasi micro1 yang sempat rusak oleh .replace('', '-')
        location = "".join(
            ch for idx, ch in enumerate(location) if not (ch == "-" and idx % 2 == 0)
        ).strip()

    raw_desc = job.get("raw_description", "") or ""
    raw_reqs = job.get("raw_requirements", "") or raw_desc

    raw = {
        "id": job.get("id"),
        "title": job.get("title"),
        "organization_id": job.get("organization_id"),
        "organization_name": job.get("organization_name"),
        "slug": job.get("slug"),
        "type_name": job.get("type_name"),
        "employment_type": job.get("employment_type"),
        "level": job.get("level"),
        "location": location,
        "workplace": job.get("workplace"),
        "due_date": job.get("due_date"),
        "group": job.get("group"),
        "url": job.get("url"),
        "description": raw_desc,
        "requirements": raw_reqs,
        "source": job.get("source"),
        "logo": job.get("logo"),
    }
    rescored.append(evaluate_job_match(raw))

deduped = deduplicate_jobs(rescored)
deduped.sort(key=lambda x: (0 if x["is_blocked"] else 1, x["match_score"]), reverse=True)
filtered = [j for j in deduped if j["match_details"]["major"]["status"] in ["High Match", "Match"]]
print(f"Rescored: {len(jobs)} -> deduped: {len(deduped)} -> filtered: {len(filtered)}")

ts = save_jobs(filtered, update_metadata=False)
print("Done. Preserved new_jobs.json & last_updated.json (rescore timestamp:", ts, ")")
