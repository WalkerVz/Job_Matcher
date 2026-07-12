import json
from datetime import datetime

# New job entry for Klinik Bunda Thamrin
new_job = {
    "id": 99999,
    "title": "IT Support",
    "organization_id": 999,
    "organization_name": "Klinik Bunda Thamrin",
    "slug": "klinik-bunda-thamrin-99999",
    "type_name": "Karyawan Tetap",
    "level": "Entry",
    "location": "Jakarta",
    "workplace": "Work From Office (WFO)",
    "due_date": "2026-07-20 23:59:59",
    "group": "Information Technology",
    "url": "mailto:thamrin_ilamudigitalyahoo.co.id",
    "raw_description": """
    <ul>
    <li>Pro</li>
    <li>Pendidikan minimal D3/S1 Teknik Informatika, Sistem Informasi, Ilmu Komputer, atau jurusan terkait</li>
    <li>Berpengalaman sebagai IT Support menjadi nilai tambah (fresh graduate diperbolehkan jika memiliki kompetensi yang sesuai)</li>
    <li>Mampu melakukan remote computer, server, dan support pengguna serta troubleshooting</li>
    <li>Mampu melakukan instalasi dan konfigurasi antivirus dan backup data</li>
    <li>Memahami dasar keamanan data (data security) dan menjaga kerahasiaan data</li>
    <li>Mampu bekerja secara mandiri maupun dalam tim</li>
    <li>Teliti, disiplin, komunikatif, jujur, dan bertanggung jawab</li>
    <li>Bersedia bekerja di luar jam operasional apabila dibutuhkan untuk penanganan gangguan sistem</li>
    <li>Memiliki pengetahuan CCTV dan fingerprint menjadi nilai tambah</li>
    <li>Penempatan Dusun</li>
    </ul>
    """,
    "raw_requirements": """
    Kualifikasi:
    - Pro
    - Pendidikan minimal D3/S1 Teknik Informatika, Sistem Informasi, Ilmu Komputer, atau jurusan terkait
    - Berpengalaman sebagai IT Support menjadi nilai tambah (fresh graduate diperbolehkan jika memiliki kompetensi yang sesuai)
    - Mampu melakukan remote computer, server, dan support pengguna serta troubleshooting
    - Mampu melakukan instalasi dan konfigurasi antivirus dan backup data
    - Memahami dasar keamanan data (data security) dan menjaga kerahasiaan data
    - Mampu bekerja secara mandiri maupun dalam tim
    - Teliti, disiplin, komunikatif, jujur, dan bertanggung jawab
    - Bersedia bekerja di luar jam operasional apabila dibutuhkan untuk penanganan gangguan sistem
    - Memiliki pengetahuan CCTV dan fingerprint menjadi nilai tambah
    - Penempatan Dusun
    """,
    "source": "Email",
    "match_score": 75,
    "is_blocked": False,
    "match_details": {
        "major": {
            "score": 35,
            "status": "High Match",
            "reason": "Sangat Cocok! Pekerjaan ini mencari lulusan Teknik Informatika atau Sistem Informasi."
        },
        "skills": {
            "score": 25,
            "status": "High Match",
            "reason": "Membutuhkan keahlian IT Support yang sejalan dengan background teknis."
        },
        "gpa": {
            "score": 5,
            "status": "High Match",
            "reason": "IPK 3.39 memenuhi ekspektasi entry-level."
        },
        "age": {
            "score": 5,
            "status": "High Match",
            "reason": "Usia 23 tahun sesuai untuk posisi entry-level."
        },
        "toefl": {
            "score": 5,
            "status": "High Match",
            "reason": "TOEFL 537 cukup untuk entry-level support position."
        },
        "gender": {
            "score": 0,
            "status": "Match",
            "reason": "Posisi terbuka untuk semua gender."
        }
    },
    "parsed_requirements": {
        "gpa": None,
        "age": None,
        "toefl": None,
        "experience": "Fresh graduate diperbolehkan"
    },
    "nlp_breakdown": {
        "education_summary": "S1/D3 Teknik Informatika, Sistem Informasi, atau Ilmu Komputer",
        "mandatory_skills": ["IT Support", "Troubleshooting", "Network Administration", "Windows Support"],
        "plus_skills": ["CCTV Knowledge", "Fingerprint System", "Remote Support", "System Security"],
        "key_sentences": [
            "Fresh graduate diperbolehkan jika memiliki kompetensi yang sesuai",
            "Mampu melakukan instalasi dan konfigurasi antivirus",
            "Memahami dasar keamanan data (data security)"
        ]
    }
}

# Load existing matched_jobs.json
try:
    with open('matched_jobs.json', 'r', encoding='utf-8') as f:
        matched_jobs = json.load(f)
    print(f"Loaded {len(matched_jobs)} existing jobs")
except Exception as e:
    print(f"Error loading matched_jobs.json: {e}")
    matched_jobs = []

# Add new job at the beginning (highest priority)
matched_jobs.insert(0, new_job)

# Save back to file
try:
    with open('matched_jobs.json', 'w', encoding='utf-8') as f:
        json.dump(matched_jobs, f, indent=2, ensure_ascii=False)
    print(f"Success! Added IT Support job. Total jobs now: {len(matched_jobs)}")
except Exception as e:
    print(f"Error saving matched_jobs.json: {e}")

# Also update matched_jobs.js for fallback
try:
    with open('matched_jobs.js', 'w', encoding='utf-8') as f:
        f.write(f"window.lastUpdated = '{datetime.now().strftime('%d %B %Y - %H:%M WIB')}';\n")
        f.write("window.matchedJobs = " + json.dumps(matched_jobs, ensure_ascii=False) + ";")
    print("Updated matched_jobs.js with fallback data")
except Exception as e:
    print(f"Error updating matched_jobs.js: {e}")
