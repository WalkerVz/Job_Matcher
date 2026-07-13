"""
Tambah entri lowongan manual ke matched_jobs.json.
Scoring dihitung otomatis oleh evaluate_job_match() dari scraper.py.
"""
import json
from scraper import evaluate_job_match, save_jobs

# ─── Data mentah lowongan yang ingin ditambahkan ──────────────────────────────
new_job_raw = {
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
    "source": "Email",
    "logo": None,
    "description": """
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
    "requirements": """
    Kualifikasi:
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
}

# Hitung score otomatis (tidak perlu hardcode manual)
new_job = evaluate_job_match(new_job_raw)

# ─── Load, insert di posisi pertama, simpan ───────────────────────────────────
try:
    with open("matched_jobs.json", "r", encoding="utf-8") as f:
        matched_jobs = json.load(f)
    print(f"Loaded {len(matched_jobs)} lowongan yang sudah ada")
except Exception as e:
    print(f"Error loading matched_jobs.json: {e}")
    matched_jobs = []

matched_jobs.insert(0, new_job)
print(f"Match score otomatis: {new_job['match_score']}%  |  Blocked: {new_job['is_blocked']}")

ts = save_jobs(matched_jobs)
print(f"Selesai! Total lowongan sekarang: {len(matched_jobs)}  |  Timestamp: {ts}")
