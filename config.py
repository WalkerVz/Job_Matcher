"""
config.py - Konfigurasi terpusat untuk Job Matcher
Berisi PROFILE user dan konstanta bersama.
Import dari file ini agar tidak ada duplikasi definisi di setiap modul.
"""

import os
import re
from dotenv import load_dotenv

load_dotenv()

def clean_html(raw_html):
    """Membersihkan tag HTML dan spasi berlebih dari teks."""
    if not raw_html:
        return ""
    cleanr = re.compile(r'<.*?>')
    cleantext = re.sub(cleanr, ' ', raw_html)
    cleantext = re.sub(r'\s+', ' ', cleantext)
    return cleantext.strip()

# Konstanta Bulan Indonesia
MONTHS_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}

# Profil User
# SECURITY: Data sensitif (email, phone, linkedin) di-load dari .env, tidak hardcode.
PROFILE = {
    "name": os.getenv("USER_NAME", "Muhammad Ravil"),
    "email": os.getenv("USER_EMAIL", ""),
    "phone": os.getenv("USER_PHONE", ""),
    "location": os.getenv("USER_LOCATION", "Pekanbaru, Riau"),
    "linkedin": os.getenv("USER_LINKEDIN", "linkedin.com/in/Muhammad-ravil"),
    "gender": "Laki-laki",
    "age": 23,
    "gpa": 3.39,
    "toefl": 537,
    "major": "Teknik Informatika",
    "university": "Universitas Islam Negeri Sultan Syarif Kasim Riau",
    "skills": [
        "python", "data science", "data analyst", "data analysis", "machine learning",
        "sql", "dataiku", "power bi", "excel", "react", "laravel", "php", "javascript",
        "ai engineer", "ai", "programming", "developer", "analytics", "it",
        "web development", "fullstack", "full stack", "git", "arcgis", "it support",
        "sentiment analysis", "naive bayes", "tableau", "mysql"
    ],
    "certifications": [
        "TOEFL 537 (Elskill 2023)",
        "IT Support Fundamentals (Google 2024)",
        "FullStack Web Development (Udemy 2025)",
        "Data Science Mastery (Udemy 2025)",
        "Data Analysis (Myskill 2025)",
    ],
    "experience": (
        "AI Engineer di PT Pertamina Hulu Rokan (Upstream Oil & Gas, Jul 2025-Feb 2026); "
        "Data Scientist Intern Id/x partners x Rakamin Academy (Apr-Mei 2025, Best Student 86.96); "
        "Freelance Web Dev & Machine Learning (2025-Sekarang)"
    ),
    "exp_years": 1
}
