from jobspy import scrape_jobs
import pandas as pd

print("Testing JobSpy dengan berbagai parameter...\n")
print("="*60)

# Test 1: Minimal parameters
print("\nTest 1: Basic search (Data Analyst, no location)")
try:
    jobs = scrape_jobs(
        site_name=["indeed", "glassdoor"],
        search_term="Data Analyst",
        results_wanted=10
    )
    print(f"✓ Found {len(jobs)} jobs")
    if len(jobs) > 0:
        print(f"  Sample jobs:")
        for i, job in enumerate(jobs.head(3).iterrows()):
            print(f"    {i+1}. {job[1]['title']} at {job[1]['company']}")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}\n")

# Test 2: With location (Indonesia)
print("\nTest 2: Search with location (Indonesia)")
try:
    jobs = scrape_jobs(
        site_name=["indeed"],
        search_term="Data Analyst",
        location="Indonesia",
        results_wanted=10
    )
    print(f"✓ Found {len(jobs)} jobs")
    if len(jobs) > 0:
        print(f"  Sample:")
        print(f"    {jobs.iloc[0]['title']} at {jobs.iloc[0]['company']}")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}\n")

# Test 3: Different search term
print("\nTest 3: Different search term (Software Engineer)")
try:
    jobs = scrape_jobs(
        site_name=["indeed", "linkedin"],
        search_term="Software Engineer",
        results_wanted=10
    )
    print(f"✓ Found {len(jobs)} jobs")
    if len(jobs) > 0:
        print(f"  Sample jobs:")
        for i, job in enumerate(jobs.head(3).iterrows()):
            print(f"    {i+1}. {job[1]['title']} - {job[1]['company']}")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}\n")

# Test 4: LinkedIn only
print("\nTest 4: LinkedIn search only")
try:
    jobs = scrape_jobs(
        site_name=["linkedin"],
        search_term="Data Engineer",
        results_wanted=10
    )
    print(f"✓ Found {len(jobs)} jobs")
    if len(jobs) > 0:
        print(f"  Sample:")
        print(f"    {jobs.iloc[0]['title']} at {jobs.iloc[0]['company']}")
except Exception as e:
    print(f"✗ Error: {type(e).__name__}: {e}\n")

print("\n" + "="*60)
print("Diagnosis complete!")
print("\nNote: If all tests return 0 jobs, possible causes:")
print("  1. API rate limit / blocked by job boards")
print("  2. Network/proxy issues")
print("  3. JobSpy library outdated")
print("  4. Job board API changes")
