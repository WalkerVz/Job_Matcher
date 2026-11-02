"""
scraper.py - Multi-Portal Job Scraper & Intelligent Matching Engine
Dioptimasi untuk performa tinggi, concurrency, HTTP Connection Pooling,
resilience terhadap network errors, dan parsing regex yang sangat cepat.
"""

import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import warnings
warnings.filterwarnings("ignore", message=".*urllib3.*or chardet.*")
warnings.filterwarnings("ignore", message=".*RequestsDependencyWarning.*")

import os
import re
import time
import json
import datetime
import hashlib
import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any, Dict, List, Optional, Tuple, Set

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from bs4 import BeautifulSoup
import pytz
from dotenv import load_dotenv

load_dotenv()

# Enhanced Scrapers (Firecrawl & JobSpy) - Optional
try:
    from firecrawl import FirecrawlApp
except ImportError:
    FirecrawlApp = None

try:
    from jobspy import scrape_jobs
except ImportError:
    scrape_jobs = None

# ─── Shared Config & Constants (terpusat di config.py) ─────────────────────────
from config import PROFILE, MONTHS_ID, clean_html


# ─── Pre-compiled Regex Patterns (Optimasi Kecepatan NLP & Parsing) ─────────────
RE_GPA = re.compile(r'(?:ipk|gpa)[^\d]*(\d[.,]\d{2})', re.IGNORECASE)
RE_AGE_1 = re.compile(r'(?:usia|umur|age)\s*(?:maksimal|maks|maks\.|max|maximum)?[^\d]*(\d{2})', re.IGNORECASE)
RE_AGE_2 = re.compile(r'(?:maksimal|maks|maks\.|max|maximum)\s*(?:usia|umur|age)?[^\d]*(\d{2})\s*(?:tahun|years)', re.IGNORECASE)
RE_TOEFL = re.compile(r'toefl[^\d]*(\d{3})', re.IGNORECASE)

RE_EXP_1 = re.compile(r'(?:pengalaman|experience)\s*(?:kerja)?\s*(?:minimal|min|min\.|diutamakan|at least)?\s*(\d+)\s*(?:\+)?\s*(?:tahun|year)', re.IGNORECASE)
RE_EXP_2 = re.compile(r'(?:minimal|min|min\.|at least)\s*(\d+)\s*(?:\+)?\s*(?:tahun|year)\s*(?:pengalaman|experience)', re.IGNORECASE)
RE_EXP_3 = re.compile(r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:relevant\s*)?experience', re.IGNORECASE)
RE_EXP_4 = re.compile(r'(\d+)\s*(?:tahun)\s*(?:pengalaman)', re.IGNORECASE)

RE_SENTENCE_SPLIT = re.compile(r'[\n•\-\*.]+')
RE_HTML_CLEAN = re.compile(r'<.*?>')
RE_WHITESPACE = re.compile(r'\s+')

# Pre-compiled word-boundary regexes untuk skill profile user
def _build_skill_pattern(skill: str) -> re.Pattern:
    s = skill.strip().lower()
    if len(s) <= 3:
        return re.compile(r'\b' + re.escape(s) + r'\b', re.IGNORECASE)
    return re.compile(r'(?:\b|_)' + re.escape(s) + r'(?:\b|_)', re.IGNORECASE)

COMPILED_PROFILE_SKILLS: List[Tuple[str, re.Pattern]] = [
    (sk, _build_skill_pattern(sk)) for sk in PROFILE.get("skills", [])
]


# ─── HTTP Session Factory dengan Connection Pooling ───────────────────────────
_GLOBAL_SESSION: Optional[requests.Session] = None

def get_default_session(pool_size: int = 50, retries: int = 3) -> requests.Session:
    """
    Mengembalikan session singleton dengan connection pooling & automatic retry.
    Menghindari overhead TLS handshake berulang-ulang pada ribuan request concurrent.
    """
    global _GLOBAL_SESSION
    if _GLOBAL_SESSION is None:
        session = requests.Session()
        retry_strategy = Retry(
            total=retries,
            backoff_factor=0.3,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST", "OPTIONS"]
        )
        adapter = HTTPAdapter(
            pool_connections=pool_size,
            pool_maxsize=pool_size,
            max_retries=retry_strategy
        )
        session.mount("https://", adapter)
        session.mount("http://", adapter)
        session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "id-ID,id;q=0.9,en-US;q=0.8,en;q=0.7",
        })
        _GLOBAL_SESSION = session
    return _GLOBAL_SESSION


# ─── Helper Functions ──────────────────────────────────────────────────────────
def get_timestamp_wib() -> str:
    """Kembalikan string timestamp format '12 Juli 2026 - 17:23 WIB'."""
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    wib_tz = pytz.timezone('Asia/Jakarta')
    wib_now = utc_now.astimezone(wib_tz)
    return f"{wib_now.day} {MONTHS_ID[wib_now.month]} {wib_now.year} - {wib_now.strftime('%H:%M')} WIB"


def detect_new_jobs(matched_jobs: List[Dict[str, Any]], base_dir: str) -> List[str]:
    """
    Bandingkan ID job saat ini dengan run sebelumnya.
    Kembalikan list ID job yang baru sejak run terakhir.
    """
    prev_path = os.path.join(base_dir, "matched_jobs.json")
    prev_ids = set()
    if os.path.exists(prev_path):
        try:
            with open(prev_path, encoding="utf-8") as f:
                prev_jobs = json.load(f)
            prev_ids = {str(j.get("id")) for j in prev_jobs if j.get("id") is not None}
        except Exception:
            pass

    current_ids = {str(j.get("id")) for j in matched_jobs if j.get("id") is not None}
    new_ids = current_ids - prev_ids
    print(f"Job baru terdeteksi: {len(new_ids)} dari {len(current_ids)} total")
    return list(new_ids)


def _atomic_write_json(filepath: str, data: Any, indent: Optional[int] = 2) -> None:
    """Tulis file JSON secara atomik menggunakan replace untuk mencegah korupsi file."""
    tmp_path = filepath + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
    os.replace(tmp_path, filepath)


def save_jobs(matched_jobs: List[Dict[str, Any]], base_dir: Optional[str] = None) -> str:
    """
    Simpan hasil matched_jobs ke empat file output secara atomik:
      - matched_jobs.json
      - matched_jobs.js  (window global fallback untuk browser)
      - last_updated.json
      - new_jobs.json    (ID job baru sejak scrape terakhir, dibaca app.js)
    """
    if base_dir is None:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    # Deteksi job baru SEBELUM overwrite matched_jobs.json
    new_job_ids = detect_new_jobs(matched_jobs, base_dir)
    timestamp_str = get_timestamp_wib()

    output_json = os.path.join(base_dir, "matched_jobs.json")
    _atomic_write_json(output_json, matched_jobs, indent=2)

    output_js = os.path.join(base_dir, "matched_jobs.js")
    tmp_js = output_js + ".tmp"
    with open(tmp_js, "w", encoding="utf-8") as f:
        f.write(f"window.lastUpdated = '{timestamp_str}';\n")
        f.write("window.matchedJobs = " + json.dumps(matched_jobs, ensure_ascii=False) + ";")
    os.replace(tmp_js, output_js)

    output_lu = os.path.join(base_dir, "last_updated.json")
    _atomic_write_json(output_lu, {"last_updated": timestamp_str}, indent=2)

    output_new = os.path.join(base_dir, "new_jobs.json")
    _atomic_write_json(output_new, {
        "scraped_at": timestamp_str,
        "new_ids": new_job_ids,
        "count": len(new_job_ids)
    }, indent=2)

    print(f"Output disimpan ke: {output_json}, {output_js}, {output_lu}, {output_new}")
    return timestamp_str


# ─── Requirement Parsing Helpers ───────────────────────────────────────────────
def parse_gpa_req(req_text: str) -> Optional[float]:
    """Parse syarat minimal IPK/GPA."""
    if not req_text:
        return None
    match = RE_GPA.search(req_text)
    if match:
        try:
            return float(match.group(1).replace(',', '.'))
        except ValueError:
            pass
    return None


def parse_age_req(req_text: str) -> Optional[int]:
    """Parse batas umur maksimal."""
    if not req_text:
        return None
    ages = []
    for match in RE_AGE_1.findall(req_text) + RE_AGE_2.findall(req_text):
        try:
            ages.append(int(match))
        except ValueError:
            pass
    return max(ages) if ages else None


def parse_toefl_req(req_text: str) -> Optional[int]:
    """Parse syarat skor TOEFL minimal."""
    if not req_text:
        return None
    match = RE_TOEFL.search(req_text)
    if match:
        try:
            return int(match.group(1))
        except ValueError:
            pass
    return None


def check_gender_req(req_text: str) -> str:
    """Cek apakah ada syarat jenis kelamin spesifik."""
    if not req_text:
        return "Open"
    text_lower = req_text.lower()
    has_male = "pria" in text_lower or "laki-laki" in text_lower or "male" in text_lower
    has_female = "wanita" in text_lower or "perempuan" in text_lower or "female" in text_lower
    if has_male and not has_female:
        return "Male Only"
    elif has_female and not has_male:
        return "Female Only"
    return "Open"


def parse_exp_req(req_text: str) -> Dict[str, Any]:
    """
    Parse syarat pengalaman kerja dengan regex yang telah di-precompile.
    Return dict berisi level dan tahun pengalaman yang diminta.
    """
    if not req_text:
        return {"years": 0, "level": "Open / Not Specified", "raw_text": ""}
    
    text_lower = req_text.lower()
    exps = []
    for pattern in (RE_EXP_1, RE_EXP_2, RE_EXP_3, RE_EXP_4):
        for match in pattern.findall(text_lower):
            try:
                exps.append(int(match))
            except ValueError:
                pass

    years_req = max(exps) if exps else 0

    if "fresh graduate" in text_lower or "lulusan baru" in text_lower or "0 tahun" in text_lower:
        level = "Fresh Graduate / Entry Level"
        years_req = 0
    elif years_req == 0:
        level = "Open / Not Specified"
    elif years_req <= 1:
        level = "Fresh / Junior (0-1 tahun)"
    elif years_req <= 3:
        level = "Mid Level (1-3 tahun)"
    elif years_req <= 5:
        level = "Senior (3-5 tahun)"
    else:
        level = f"Expert / Lead ({years_req}+ tahun)"

    return {
        "years": years_req,
        "level": level,
        "raw_text": text_lower[:200]
    }


# ─── Requirement NLP Parser ────────────────────────────────────────────────────
class RequirementNLPParser:
    """
    High-Performance Natural Language Processing (NLP) Parser for Job Requirements.
    Menggunakan regex pre-compiled dan classification berbasis set untuk kecepatan maksimal.
    """
    SKILL_TAXONOMY = {
        "Languages & Core": ["Python", "SQL", "PHP", "R", "Java", "C++", "JavaScript", "TypeScript", "Go", "Bash", "Shell"],
        "Data Science & Analytics": ["Machine Learning", "Deep Learning", "NLP", "Pandas", "NumPy", "Scikit-Learn", "PyTorch", "TensorFlow", "Data Analysis", "Statistical Modeling", "Analytics", "Dataiku"],
        "BI & Visualization": ["Power BI", "PowerBI", "Tableau", "Looker", "Metabase", "Excel", "Data Studio"],
        "Engineering & Tools": ["React", "React.js", "Laravel", "Airflow", "Spark", "Hadoop", "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Git", "REST API", "CI/CD", "PostgreSQL", "MySQL", "ArcGIS"],
        "Domain & Methodology": ["Hulu Migas", "Oil and Gas", "Oil & Gas", "Upstream", "Agile", "Scrum", "Project Management", "AI Engineer"]
    }

    _COMPILED_TAXONOMY = {
        category: [
            (sk, re.compile(r'\b' + re.escape(sk.lower()) + r'\b', re.IGNORECASE))
            for sk in skills
        ]
        for category, skills in SKILL_TAXONOMY.items()
    }

    SOFT_SKILLS = [
        "komunikasi", "communication", "teamwork", "tim kerja", "leadership", "kepemimpinan",
        "problem solving", "pemecahan masalah", "critical thinking", "berpikir kritis",
        "analytical", "analitis", "attention to detail", "perhatian detail",
        "adaptability", "adaptif", "flexibility", "fleksibel", "self-motivated", "termotivasi",
        "time management", "manajemen waktu", "presentation", "presentasi"
    ]

    _MANDATORY_TRIGGERS = ("wajib", "harus", "minimal", "required", "must", "essential", "syarat", "qualification", "persyaratan")
    _PREFERRED_TRIGGERS = ("diutamakan", "preferred", "advantage", "keuntungan", "lebih baik")
    _NICE_TRIGGERS = ("nice to have", "bonus", "nilai tambah", "nilai plus", "plus point")
    _RESP_TRIGGERS = ("melakukan", "mengembangkan", "mengelola", "memastikan", "bertanggung jawab", "responsible", "manage", "handle", "develop", "create")

    @classmethod
    def classify_sentence(cls, sentence_lower: str) -> str:
        """Klasifikasi tipe kalimat persyaratan."""
        if any(t in sentence_lower for t in cls._MANDATORY_TRIGGERS):
            return "mandatory"
        elif any(t in sentence_lower for t in cls._PREFERRED_TRIGGERS):
            return "preferred"
        elif any(t in sentence_lower for t in cls._NICE_TRIGGERS):
            return "nice_to_have"
        elif any(t in sentence_lower for t in cls._RESP_TRIGGERS):
            return "responsibility"
        return "description"

    @classmethod
    def extract_skills_from_sentence(cls, sentence_lower: str) -> Dict[str, List[str]]:
        """Ekstraksi skill menggunakan regex yang sudah di-precompile."""
        found_skills: Dict[str, List[str]] = {}
        for category, skill_pairs in cls._COMPILED_TAXONOMY.items():
            for sk, pattern in skill_pairs:
                if pattern.search(sentence_lower):
                    if category not in found_skills:
                        found_skills[category] = []
                    found_skills[category].append(sk)
        return found_skills

    @classmethod
    def extract_soft_skills(cls, sentence_lower: str) -> List[str]:
        """Ekstraksi soft skills."""
        return [skill.title() for skill in cls.SOFT_SKILLS if skill in sentence_lower]

    @classmethod
    def parse(cls, job: Dict[str, Any]) -> Dict[str, Any]:
        """Parse job requirements secara semantik."""
        raw = (job.get("requirements") or "") + " " + (job.get("description") or "")
        text = clean_html(raw)
        
        sentences = [s.strip() for s in RE_SENTENCE_SPLIT.split(text) if len(s.strip()) > 15]

        mandatory_requirements = []
        preferred_requirements = []
        nice_to_have_requirements = []
        responsibilities = []

        mandatory_skills_dict: Dict[str, List[str]] = {}
        preferred_skills_dict: Dict[str, List[str]] = {}
        soft_skills_found: Set[str] = set()

        edu_summary = "S1 / D3 jurusan relevan atau setara"
        exp_summary = "1 Tahun Pengalaman / Fresh Graduate"
        accepts_fresh = False
        job_responsibilities = []

        for sent in sentences:
            sent_lower = sent.lower()
            sent_type = cls.classify_sentence(sent_lower)

            if any(k in sent_lower for k in ("s1", "d3", "sarjana", "bachelor", "pendidikan")):
                if len(sent) < 130 and "pendidikan" in sent_lower:
                    edu_summary = sent

            if any(k in sent_lower for k in ("fresh graduate", "lulusan baru", "0 tahun", "magang", "internship")):
                accepts_fresh = True
                if len(sent) < 140:
                    exp_summary = sent
            elif any(k in sent_lower for k in ("pengalaman", "experience", "tahun")):
                if len(sent) < 140 and exp_summary == "1 Tahun Pengalaman / Fresh Graduate":
                    exp_summary = sent

            skills_found = cls.extract_skills_from_sentence(sent_lower)
            soft_skills = cls.extract_soft_skills(sent_lower)
            soft_skills_found.update(soft_skills)

            if sent_type == "mandatory":
                mandatory_requirements.append(sent)
                for category, sks in skills_found.items():
                    if category not in mandatory_skills_dict:
                        mandatory_skills_dict[category] = []
                    mandatory_skills_dict[category].extend(sks)
            elif sent_type == "preferred":
                preferred_requirements.append(sent)
                for category, sks in skills_found.items():
                    if category not in preferred_skills_dict:
                        preferred_skills_dict[category] = []
                    preferred_skills_dict[category].extend(sks)
            elif sent_type == "nice_to_have":
                nice_to_have_requirements.append(sent)
            elif sent_type == "responsibility":
                responsibilities.append(sent)
                job_responsibilities.append(sent)

        mandatory_skills = sorted(list(set([s for skills in mandatory_skills_dict.values() for s in skills])))
        preferred_skills = sorted(list(set([s for skills in preferred_skills_dict.values() for s in skills])))

        if accepts_fresh:
            exp_summary = "Terbuka untuk Fresh Graduate / 1 Tahun Pengalaman (" + exp_summary[:90] + "...)"

        return {
            "education_summary": edu_summary[:130],
            "experience_summary": exp_summary[:150],
            "mandatory_skills": mandatory_skills,
            "preferred_skills": preferred_skills,
            "soft_skills": sorted(list(soft_skills_found))[:5],
            "mandatory_requirements": mandatory_requirements[:5],
            "preferred_requirements": preferred_requirements[:3],
            "nice_to_have": nice_to_have_requirements[:2],
            "key_responsibilities": job_responsibilities[:4],
            "skill_categories": list(mandatory_skills_dict.keys()),
            "full_breakdown": {
                "mandatory": mandatory_requirements[:6],
                "preferred": preferred_requirements[:4],
                "nice_to_have": nice_to_have_requirements[:3],
                "responsibilities": job_responsibilities[:5]
            }
        }


# ─── Job Match Evaluation Engine ───────────────────────────────────────────────
def evaluate_job_match(job: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluasi tingkat kecocokan profil kandidat terhadap kualifikasi lowongan.
    Dioptimasi dengan fast substring checks dan pre-compiled regex.
    """
    req_html = job.get("requirements") or ""
    desc_html = job.get("description") or ""
    title = str(job.get("title") or "").lower()
    org_name = str(job.get("organization_name") or "").lower()

    req_text = clean_html(req_html)
    desc_text = clean_html(desc_html)
    full_text = f"{title} {org_name} {req_text} {desc_text}".lower()

    score = 0
    match_details = {
        "major": {"score": 0, "status": "Neutral", "reason": "Jurusan tidak dispesifikasikan secara ketat atau bersifat umum."},
        "gpa": {"score": 15, "status": "Match", "reason": f"IPK Anda ({PROFILE['gpa']}) memenuhi syarat."},
        "age": {"score": 10, "status": "Match", "reason": f"Usia Anda ({PROFILE['age']} tahun) memenuhi syarat."},
        "toefl": {"score": 10, "status": "Match", "reason": f"TOEFL Anda ({PROFILE['toefl']}) memenuhi syarat."},
        "gender": {"score": 5, "status": "Match", "reason": "Pekerjaan terbuka untuk pria/wanita."},
        "skills": {"score": 0, "status": "Low Match", "reason": "Tidak mendeteksi kecocokan skill Python/Data yang signifikan."},
        "experience": {"score": 0, "status": "Neutral", "reason": "Bukan peran langsung di bidang IT/Data."},
        "exp_years": {"status": "Match", "reason": "Sesuai dengan pengalaman kerja 1 tahun Anda."}
    }

    # 1. MAJOR MATCHING (Max 35 points)
    it_keywords = ("informatika", "ilmu komputer", "sistem informasi", "teknik komputer", "computer science", "software", "information technology", "telekomunikasi", "sistem & teknologi informasi", "backend", "fullstack", "full stack", "data analyst", "data scientist", "ai engineer", "machine learning", "engineer", "developer", "odoo", "web")
    general_keywords = ("semua jurusan", "all major", "semua program studi", "diploma", "sarjana")
    engineering_keywords = ("teknik", "engineering", "mipa", "sains", "matematika", "statistika")

    if any(kw in full_text for kw in it_keywords):
        major_score = 35
        match_details["major"] = {
            "score": 35,
            "status": "High Match",
            "reason": "Sangat Cocok! Pekerjaan ini secara eksplisit mencari lulusan Teknik Informatika, Sistem Informasi, atau bidang IT/Komputer."
        }
    elif any(kw in full_text for kw in general_keywords):
        major_score = 25
        match_details["major"] = {
            "score": 25,
            "status": "Match",
            "reason": "Cocok. Terbuka untuk semua jurusan (All Majors)."
        }
    elif any(kw in full_text for kw in engineering_keywords):
        major_score = 20
        match_details["major"] = {
            "score": 20,
            "status": "Medium Match",
            "reason": "Cukup Cocok. Mencari rumpun Teknik / Sains secara umum."
        }
    else:
        non_it_specific = ("geologi", "geofisika", "perminyakan", "pertambangan", "akuntansi", "hukum", "keuangan", "petroleum", "geology", "geophysic", "accounting", "law")
        if any(kw in full_text for kw in non_it_specific):
            major_score = 5
            match_details["major"] = {
                "score": 5,
                "status": "Low Match",
                "reason": "Kurang Cocok. Persyaratan menyebutkan jurusan spesifik non-IT (seperti Geologi, Perminyakan, Hukum, atau Keuangan)."
            }
        else:
            major_score = 15
            match_details["major"] = {
                "score": 15,
                "status": "Neutral",
                "reason": "Netral. Jurusan spesifik tidak disebutkan dengan jelas, mungkin membutuhkan verifikasi manual."
            }
    score += major_score

    # 2. GPA MATCHING (15 points)
    gpa_req = parse_gpa_req(req_text)
    if gpa_req:
        if PROFILE["gpa"] >= gpa_req:
            score += 15
            match_details["gpa"] = {
                "score": 15,
                "status": "Match",
                "reason": f"Sesuai. IPK minimal yang diminta adalah {gpa_req:.2f}, sedangkan IPK Anda adalah {PROFILE['gpa']:.2f}."
            }
        else:
            match_details["gpa"] = {
                "score": 0,
                "status": "No Match",
                "reason": f"Tidak Sesuai. IPK minimal yang diminta adalah {gpa_req:.2f}, sedangkan IPK Anda adalah {PROFILE['gpa']:.2f}."
            }
    else:
        score += 15
        match_details["gpa"] = {
            "score": 15,
            "status": "Match",
            "reason": "Sesuai. Tidak ada syarat IPK minimal yang tertulis secara eksplisit."
        }

    # 3. AGE MATCHING (10 points)
    age_req = parse_age_req(req_text)
    if age_req:
        if PROFILE["age"] <= age_req:
            score += 10
            match_details["age"] = {
                "score": 10,
                "status": "Match",
                "reason": f"Sesuai. Batas usia maksimal adalah {age_req} tahun, sedangkan usia Anda saat ini adalah {PROFILE['age']} tahun."
            }
        else:
            match_details["age"] = {
                "score": 0,
                "status": "No Match",
                "reason": f"Tidak Sesuai. Batas usia maksimal adalah {age_req} tahun, sedangkan usia Anda saat ini adalah {PROFILE['age']} tahun."
            }
    else:
        score += 10
        match_details["age"] = {
            "score": 10,
            "status": "Match",
            "reason": "Sesuai. Tidak ada batas usia maksimal yang disebutkan secara spesifik."
        }

    # 4. TOEFL MATCHING (10 points)
    toefl_req = parse_toefl_req(req_text)
    if toefl_req:
        if PROFILE["toefl"] >= toefl_req:
            score += 10
            match_details["toefl"] = {
                "score": 10,
                "status": "Match",
                "reason": f"Sesuai. Skor TOEFL minimal yang diminta adalah {toefl_req}, sedangkan skor TOEFL Anda adalah {PROFILE['toefl']}."
            }
        else:
            match_details["toefl"] = {
                "score": 0,
                "status": "No Match",
                "reason": f"Tidak Sesuai. Skor TOEFL minimal yang diminta adalah {toefl_req}, sedangkan skor TOEFL Anda adalah {PROFILE['toefl']}."
            }
    else:
        score += 10
        match_details["toefl"] = {
            "score": 10,
            "status": "Match",
            "reason": "Sesuai. Tidak ada syarat nilai TOEFL tertulis secara spesifik."
        }

    # 5. GENDER MATCHING (5 points)
    gender_req = check_gender_req(req_text)
    if gender_req == "Female Only":
        match_details["gender"] = {
            "score": 0,
            "status": "No Match",
            "reason": "Tidak Sesuai. Lowongan ini diutamakan atau dikhususkan untuk Wanita."
        }
    else:
        score += 5
        if gender_req == "Male Only":
            match_details["gender"] = {
                "score": 5,
                "status": "Match",
                "reason": "Sesuai. Lowongan ini dikhususkan atau diutamakan untuk Pria."
            }
        else:
            match_details["gender"] = {
                "score": 5,
                "status": "Match",
                "reason": "Sesuai. Lowongan terbuka untuk Pria dan Wanita."
            }

    # 6. SKILLS MATCHING (Max 20 points)
    skills_found = [s for s, pattern in COMPILED_PROFILE_SKILLS if pattern.search(full_text)]
    skills_score = min(len(skills_found) * 5, 20)
    score += skills_score

    if len(skills_found) >= 3:
        match_details["skills"] = {
            "score": skills_score,
            "status": "High Match",
            "reason": f"Sangat Cocok! Menemukan kecocokan keahlian Anda: {', '.join(skills_found)}."
        }
    elif len(skills_found) >= 1:
        match_details["skills"] = {
            "score": skills_score,
            "status": "Match",
            "reason": f"Cocok. Menemukan beberapa kecocokan kata kunci keahlian: {', '.join(skills_found)}."
        }
    else:
        match_details["skills"] = {
            "score": 0,
            "status": "Low Match",
            "reason": "Tidak mendeteksi kecocokan keahlian teknis (Python, Dataiku, AI/ML, Data Analyst) pada deskripsi lowongan ini."
        }

    # 7. EXPERIENCE & UPSTREAM DOMAIN MATCHING (Max 10 points)
    exp_req = parse_exp_req(req_text)
    exp_score = 0
    relevance_reasons = []

    role_keywords = ("data", "analyst", "analis", "scientist", "ai engineer", "machine learning", "programmer", "developer", "it", "systems", "digital", "informasi", "komputer", "teknologi", "fullstack", "web")
    if any(kw in title for kw in role_keywords):
        exp_score += 5
        relevance_reasons.append("Peran ini di bidang Data / IT / Analis yang sesuai dengan spesialisasi pekerjaan Anda.")

    hulu_migas_keywords = ("operasi", "operations", "production", "produksi", "reservoir", "lifting", "eksplorasi", "exploration", "drilling", "well", "log", "petrotechnical")
    if any(kw in full_text for kw in hulu_migas_keywords):
        exp_score += 5
        relevance_reasons.append("Sangat Relevan! Lowongan ini berkaitan dengan sektor operasional hulu migas, di mana Anda memiliki pengalaman magang di Pertamina Hulu Rokan.")

    score += exp_score
    if exp_score >= 8:
        match_details["experience"] = {
            "score": exp_score,
            "status": "High Match",
            "reason": "Sangat Cocok! " + " ".join(relevance_reasons)
        }
    elif exp_score >= 4:
        match_details["experience"] = {
            "score": exp_score,
            "status": "Match",
            "reason": "Cocok. " + " ".join(relevance_reasons)
        }
    else:
        match_details["experience"] = {
            "score": 0,
            "status": "Neutral",
            "reason": "Bukan peran langsung di bidang IT/Data."
        }

    if exp_req["years"] <= PROFILE["exp_years"]:
        match_details["exp_years"] = {
            "status": "Match",
            "reason": f"Sesuai. Lowongan meminta minimal {exp_req['years']} tahun pengalaman, sedangkan pengalaman kamu adalah {PROFILE['exp_years']} tahun." if exp_req['years'] > 0 else "Sesuai. Terbuka untuk Fresh Graduate / pengalaman ≤ 1 tahun."
        }
    else:
        match_details["exp_years"] = {
            "status": "Low Match",
            "reason": f"Perlu Perhatian: Lowongan meminta pengalaman minimal {exp_req['years']} tahun, sedangkan pengalaman kamu saat ini {PROFILE['exp_years']} tahun."
        }

    # Hard blocker check (GPA, Age, Gender)
    is_blocked = (
        match_details["gpa"]["status"] == "No Match" or
        match_details["age"]["status"] == "No Match" or
        match_details["gender"]["status"] == "No Match"
    )

    final_score = min(score, 40) if is_blocked else score
    nlp_breakdown = RequirementNLPParser.parse(job)

    return {
        "id": job.get("id"),
        "title": job.get("title"),
        "organization_id": job.get("organization_id"),
        "organization_name": job.get("organization_name"),
        "slug": job.get("slug"),
        "type_name": job.get("type_name", "Karyawan Tetap"),
        "level": job.get("level", "Staff"),
        "location": job.get("location"),
        "workplace": job.get("workplace", "WFO"),
        "due_date": job.get("due_date"),
        "group": job.get("group"),
        "url": job.get("url") if job.get("url") else f"https://jobs.talentics.id/{job.get('organization', {}).get('slug', 'skk-migas')}/{job.get('slug')}",
        "raw_description": job.get("description"),
        "raw_requirements": job.get("requirements"),
        "match_score": final_score,
        "is_blocked": is_blocked,
        "match_details": match_details,
        "nlp_breakdown": nlp_breakdown,
        "parsed_requirements": {
            "gpa": gpa_req,
            "age": age_req,
            "toefl": toefl_req,
            "gender": gender_req,
            "experience": exp_req["level"],
            "exp_years": exp_req["years"]
        },
        "source": job.get("source", "Talentics"),
        "logo": job.get("logo", None)
    }


# ─── Individual Portal Scrapers ────────────────────────────────────────────────
def parse_location_from_text(text: str) -> str:
    """Ekstraksi nama kota Indonesia dari teks lowongan."""
    if not text:
        return "Indonesia"
    text_clean = clean_html(text).lower()
    cities = ("Jakarta", "Bandung", "Semarang", "Surabaya", "Denpasar", "Palembang", "Balikpapan", "Medan", "Makassar", "Yogyakarta", "Solo", "Malang")
    found_cities = [city for city in cities if city.lower() in text_clean]
    return ", ".join(found_cities) if found_cities else "Indonesia"


def format_astra_date(date_str: Optional[str]) -> Optional[str]:
    return date_str.replace("T", " ") if date_str else None


# 1. Talentics (Hulu Migas)
def scrape_talentics_jobs(session: Optional[requests.Session] = None, max_workers: int = 8) -> List[Dict[str, Any]]:
    """Scrape lowongan Hulu Migas / SKK Migas dari Talentics."""
    if session is None:
        session = get_default_session()

    print("Fetching Hulu Migas (Talentics) listings...")
    url_main = "https://jobs.talentics.id/jobs?search=rekrutmen%20hulu%20migas"
    try:
        r_main = session.get(url_main, timeout=12)
        if r_main.status_code != 200:
            print(f"  Warning: Talentics main page HTTP {r_main.status_code}")
            return []
    except Exception as e:
        print(f"  Warning: Error connecting to Talentics: {e}")
        return []

    soup = BeautifulSoup(r_main.text, 'html.parser')
    meta_csrf = soup.find('meta', attrs={'name': 'csrf-token'})
    csrf_token = meta_csrf.get('content') if meta_csrf else None

    ajax_url = "https://jobs.talentics.id/ajaxs/jobs"
    ajax_headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": url_main,
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRF-TOKEN": csrf_token or ""
    }

    all_jobs_raw = []
    page = 1
    last_page = 1

    while page <= last_page:
        params = {"search": "rekrutmen hulu migas", "page": page}
        try:
            r_ajax = session.get(ajax_url, params=params, headers=ajax_headers, timeout=12)
            if r_ajax.status_code == 200:
                res_data = r_ajax.json()
                last_page = res_data.get("last_page", last_page)
                jobs_data = res_data.get("data", [])
                all_jobs_raw.extend(jobs_data)
                page += 1
            else:
                break
        except Exception as e:
            print(f"  Warning: Exception on Talentics page {page}: {e}")
            break

    print(f"  Found {len(all_jobs_raw)} raw Talentics listings. Fetching details concurrently...")

    def fetch_talentics_detail(raw_job):
        org_slug = raw_job.get("organization", {}).get("slug", "skk-migas")
        job_slug = raw_job.get("slug")
        detail_url = f"https://jobs.talentics.id/{org_slug}/{job_slug}"
        try:
            r_detail = session.get(detail_url, timeout=12)
            if r_detail.status_code == 200:
                text = r_detail.text
                match = re.search(r'job:\s*(\{.*)', text, re.DOTALL)
                if match:
                    content = match.group(1)
                    brace_count = 0
                    end_idx = -1
                    for idx, char in enumerate(content):
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = idx + 1
                                break
                    if end_idx != -1:
                        try:
                            return json.loads(content[:end_idx])
                        except Exception:
                            pass
        except Exception:
            pass
        return raw_job

    detailed_jobs = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_talentics_detail, raw_job) for raw_job in all_jobs_raw]
        for f in as_completed(futures):
            detailed_jobs.append(f.result())

    print(f"  ✓ Talentics: retrieved {len(detailed_jobs)} jobs.")
    return detailed_jobs


# 2. Astra Careers
def get_astra_token(session: Optional[requests.Session] = None) -> Optional[str]:
    if session is None:
        session = get_default_session()
    url = "https://careerservice.astra.co.id/api/v1/auth/login"
    payload = {"siteType": "FrontEnd", "lang": "ID"}
    headers = {
        "Referer": "https://career.astra.co.id/lowongan"
    }
    try:
        r = session.post(url, data=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get("token")
    except Exception as e:
        print(f"Error logging in to Astra: {e}")
    return None


def scrape_astra_listings(token: str, session: Optional[requests.Session] = None) -> List[Dict[str, Any]]:
    if session is None:
        session = get_default_session()
    url = "https://careerservice.astra.co.id/api/v1/front-end/lowongan-page/ID"
    headers = {
        "Content-Type": "application/json",
        "Authorization": token,
        "Referer": "https://career.astra.co.id/lowongan",
        "Origin": "https://career.astra.co.id"
    }
    all_astra_raw = []
    page = 1
    total_pages = 1
    page_size = 12

    while page <= total_pages:
        payload = {
            "SearchString": "",
            "BranchId": [],
            "VacancyDepartmentId": [],
            "CategoryType": [],
            "IsMatch": False,
            "PageSize": page_size,
            "PageNo": page
        }
        try:
            r = session.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if "vacancies" in data:
                    v_data = data["vacancies"]
                    total_rows = v_data.get("totalRows", 0)
                    total_pages = (total_rows + page_size - 1) // page_size
                    jobs = v_data.get("data", [])
                    all_astra_raw.extend(jobs)
                    page += 1
                else:
                    break
            else:
                break
        except Exception:
            break
    return all_astra_raw


def fetch_astra_job_detail(vacancy_id: str, token: str, session: Optional[requests.Session] = None) -> Optional[Dict[str, Any]]:
    if session is None:
        session = get_default_session()
    url = f"https://careerservice.astra.co.id/api/v1/front-end/lowongan-detail/{vacancy_id}/ID"
    headers = {
        "Authorization": token,
        "Referer": "https://career.astra.co.id/lowongan"
    }
    try:
        r = session.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get("data")
    except Exception:
        pass
    return None


def scrape_all_astra_details(raw_jobs: list, token: str, session: Optional[requests.Session] = None, max_workers: int = 10) -> List[Dict[str, Any]]:
    if session is None:
        session = get_default_session()
    detailed_jobs = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_id = {executor.submit(fetch_astra_job_detail, job["vacancyId"], token, session): job for job in raw_jobs}
        for future in as_completed(future_to_id):
            raw_job = future_to_id[future]
            try:
                detail = future.result()
                detailed_jobs.append(detail if detail else raw_job)
            except Exception:
                detailed_jobs.append(raw_job)
    return detailed_jobs


def scrape_astra_jobs(session: Optional[requests.Session] = None, max_workers: int = 10) -> List[Dict[str, Any]]:
    """Scrape dan normalkan seluruh lowongan Astra Careers."""
    if session is None:
        session = get_default_session()

    print("Fetching Astra Careers vacancies...")
    token = get_astra_token(session)
    if not token:
        print("  Warning: Guest login to Astra failed.")
        return []

    raw_jobs = scrape_astra_listings(token, session)
    print(f"  Found {len(raw_jobs)} Astra jobs. Fetching details concurrently...")
    detailed = scrape_all_astra_details(raw_jobs, token, session, max_workers=max_workers)

    normalized_jobs = []
    for job in detailed:
        req_text = job.get("requirement", "") or ""
        desc_text = job.get("description", "") or ""
        normalized_jobs.append({
            "id": job.get("vacancyId"),
            "title": job.get("positionTitleName"),
            "organization_id": job.get("branchId"),
            "organization_name": job.get("branchName"),
            "slug": f"astra-{job.get('vacancyId')}",
            "type_name": "Karyawan Kontrak" if "kontrak" in (req_text + desc_text).lower() else "Karyawan Tetap",
            "level": job.get("categoryName", "Profesional"),
            "location": parse_location_from_text(req_text),
            "workplace": "Work From Office (WFO)",
            "due_date": format_astra_date(job.get("endDate", "")),
            "group": job.get("departmentTitle"),
            "url": f"https://career.astra.co.id/lowongan/lowongan-detail-page/{job.get('vacancyId')}/detail",
            "description": desc_text,
            "requirements": req_text,
            "source": "Astra",
            "logo": job.get("branchImage")
        })

    print(f"  ✓ Astra: retrieved {len(normalized_jobs)} jobs.")
    return normalized_jobs


# 3. Pertamina Training & Consulting (PTC)
def scrape_pertamina_ptc(session: Optional[requests.Session] = None) -> List[Dict[str, Any]]:
    """Scrape lowongan Pertamina Training & Consulting (PTC)."""
    if session is None:
        session = get_default_session()

    print("Fetching Pertamina Training & Consulting (PTC) vacancies...")
    url = "https://recruitment.pertamina-ptc.com/guest/joblist"
    ptc_jobs = []
    seen_ids = set()

    for page in range(1, 11):
        try:
            params = {"page": page} if page > 1 else {}
            r = session.get(url, params=params, timeout=12)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, 'html.parser')
            cards = soup.find_all("div", class_="card-view")
            if not cards:
                break

            for card in cards:
                heading_el = card.find("span", class_="text-primary")
                title = heading_el.get_text(strip=True) if heading_el else "Posisi PTC"

                code_match = re.search(r'\[([A-Z0-9]+)\]', title)
                job_id = code_match.group(1) if code_match else f"PTC-{len(ptc_jobs)+1}"

                if job_id in seen_ids:
                    continue
                seen_ids.add(job_id)

                body = card.find("div", class_="panel-body")
                job_type = "Karyawan Kontrak"
                location = "Indonesia"
                qualifications_html = ""

                if body:
                    for b_tag in body.find_all("b"):
                        label = b_tag.get_text(strip=True).lower()
                        parent_div = b_tag.parent
                        span_val = parent_div.find("span", class_="clabels-text") if parent_div else None
                        if not span_val:
                            continue
                        if "jenis pekerjaan" in label:
                            job_type = span_val.get_text(strip=True)
                        elif "kualifikasi" in label:
                            qualifications_html = str(span_val)
                        elif "lokasi" in label:
                            location = span_val.get_text(strip=True)

                ptc_jobs.append({
                    "id": job_id,
                    "title": title,
                    "organization_id": "PTC",
                    "organization_name": "PT Pertamina Training and Consulting",
                    "slug": f"ptc-{job_id}",
                    "type_name": job_type,
                    "level": "Profesional",
                    "location": location,
                    "workplace": "Work From Office (WFO)",
                    "due_date": "Aktif",
                    "group": "Pertamina Training and Consulting",
                    "url": "https://recruitment.pertamina-ptc.com/guest/joblist",
                    "description": qualifications_html,
                    "requirements": qualifications_html,
                    "source": "Pertamina PTC",
                    "logo": "https://recruitment.pertamina-ptc.com/assets/data/images/logo/ptc.png"
                })
        except Exception:
            break

    print(f"  ✓ PTC: retrieved {len(ptc_jobs)} jobs.")
    return ptc_jobs


# 4. SawitPRO
def fetch_sawitpro_job_detail(url: str, session: Optional[requests.Session] = None) -> str:
    if session is None:
        session = get_default_session()
    try:
        r = session.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        main = soup.find("main") or soup.body
        text_lines = [l.strip() for l in main.get_text("\n", strip=True).split("\n") if l.strip()]
        desc_lines = [f"<p>{l}</p>" for l in text_lines[:50]]
        return "".join(desc_lines)
    except Exception:
        return ""


def scrape_sawitpro(session: Optional[requests.Session] = None, max_workers: int = 12) -> List[Dict[str, Any]]:
    """Scrape lowongan SawitPRO."""
    if session is None:
        session = get_default_session()

    print("Fetching SawitPRO vacancies...")
    url = "https://www.sawitpro.id/jobs"
    try:
        r = session.get(url, timeout=12)
        if r.status_code != 200:
            return []
    except Exception as e:
        print(f"  Warning: Error fetching SawitPRO jobs: {e}")
        return []

    soup = BeautifulSoup(r.text, "html.parser")
    sawitpro_jobs = []
    seen_urls = set()
    idx = 1

    for a in soup.find_all("a", href=True):
        if "/jobsdetails/" in a["href"]:
            href = a["href"]
            if href in seen_urls:
                continue
            seen_urls.add(href)
            full_url = href if href.startswith("http") else "https://www.sawitpro.id" + href
            p2 = a.parent.parent
            children = [c.get_text(strip=True) for c in p2.children if c.name]
            title = children[0] if len(children) > 0 else "SawitPRO Position"
            loc = children[1] if len(children) > 1 else "Indonesia"

            title_l = title.lower()
            level = "Staff / Professional"
            if "intern" in title_l:
                level = "Internship"
            elif any(w in title_l for w in ("lead", "manager", "head", "vp")):
                level = "Manager / Lead"
            elif "senior" in title_l or "sr." in title_l:
                level = "Senior Level"

            sawitpro_jobs.append({
                "id": f"sawitpro_{idx}",
                "title": title,
                "organization_id": "SawitPRO",
                "organization_name": "SawitPRO (PT Digital Sawit Pro)",
                "slug": f"sawitpro-{idx}",
                "type_name": "Full Time",
                "level": level,
                "location": loc,
                "workplace": "WFO / Hybrid",
                "due_date": "Aktif",
                "group": "Engineering & Operations",
                "url": full_url,
                "description": f"<p>Posisi: <strong>{title}</strong></p><p>Perusahaan: PT Digital Sawit Pro (SawitPRO)</p><p>Lokasi: {loc}</p>",
                "requirements": f"<p>Posisi: <strong>{title}</strong></p><p>Perusahaan: PT Digital Sawit Pro (SawitPRO)</p><p>Lokasi: {loc}</p>",
                "source": "SawitPRO",
                "logo": "https://www.sawitpro.id/favicon.ico"
            })
            idx += 1

    print(f"  Found {len(sawitpro_jobs)} SawitPRO jobs. Fetching details concurrently...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_job = {executor.submit(fetch_sawitpro_job_detail, job["url"], session): job for job in sawitpro_jobs}
        for future in as_completed(future_to_job):
            job = future_to_job[future]
            try:
                detail_html = future.result()
                if detail_html:
                    job["description"] = detail_html
                    job["requirements"] = detail_html
            except Exception:
                pass

    print(f"  ✓ SawitPRO: retrieved {len(sawitpro_jobs)} jobs.")
    return sawitpro_jobs


# 5. Grab Careers
def fetch_grab_job_detail(url: str, session: Optional[requests.Session] = None) -> str:
    if session is None:
        session = get_default_session()
    try:
        r = session.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        main = soup.find("main") or soup.body
        text_lines = [l.strip() for l in main.get_text("\n", strip=True).split("\n") if l.strip()]
        desc_lines = []
        for line in text_lines:
            if any(k in line for k in ("Equal opportunity", "Featured Links", "Recruitment agencies")):
                break
            desc_lines.append(line)
        return "<p>" + "</p><p>".join(desc_lines[:30]) + "</p>"
    except Exception:
        return ""


def scrape_grab_careers(session: Optional[requests.Session] = None, max_workers: int = 10) -> List[Dict[str, Any]]:
    """Scrape lowongan Grab Careers Indonesia."""
    if session is None:
        session = get_default_session()

    print("Fetching Grab Careers Indonesia vacancies...")
    grab_jobs = []
    url = "https://www.grab.careers/en/jobs/?search=&country=Indonesia&pagesize=50"
    try:
        r = session.get(url, timeout=12)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, "html.parser")
            job_links = soup.find_all("a", href=re.compile(r"/en/jobs/\d+/"))
            seen_urls = set()
            for a in job_links:
                title = a.get_text(strip=True)
                href = a["href"]
                if not href.startswith("http"):
                    href = "https://www.grab.careers" + href
                if href in seen_urls or not title:
                    continue
                seen_urls.add(href)

                job_id_match = re.search(r"/jobs/(\d+)/", href)
                job_id = job_id_match.group(1) if job_id_match else str(len(grab_jobs))

                parent = a.find_parent("div") or a.find_parent("li")
                location = "Jakarta, Indonesia"
                if parent:
                    loc_el = parent.find(class_=re.compile(r"location|city|country", re.I))
                    if loc_el:
                        location = loc_el.get_text(strip=True)

                grab_jobs.append({
                    "id": f"grab_{job_id}",
                    "title": title,
                    "organization_id": "Grab",
                    "organization_name": "Grab Indonesia",
                    "slug": f"grab-{job_id}",
                    "type_name": "Full Time",
                    "level": "Profesional",
                    "location": location,
                    "workplace": "Hybrid / WFO",
                    "due_date": "Aktif",
                    "group": "Grab Tech & Operations",
                    "url": href,
                    "description": f"<p>Posisi: <strong>{title}</strong></p><p>Perusahaan: Grab Indonesia</p><p>Lokasi: {location}</p>",
                    "requirements": f"<p>Posisi: <strong>{title}</strong></p><p>Perusahaan: Grab Indonesia</p><p>Lokasi: {location}</p>",
                    "source": "Grab",
                    "logo": "https://www.grab.careers/favicon.ico"
                })
    except Exception as e:
        print(f"  Warning: Error scraping Grab: {e}")

    print(f"  Found {len(grab_jobs)} Grab jobs. Fetching details concurrently...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_job = {executor.submit(fetch_grab_job_detail, job["url"], session): job for job in grab_jobs[:20]}
        for future in as_completed(future_to_job):
            job = future_to_job[future]
            try:
                detail_html = future.result()
                if detail_html:
                    job["description"] = detail_html
                    job["requirements"] = detail_html
            except Exception:
                pass

    print(f"  ✓ Grab: retrieved {len(grab_jobs)} jobs.")
    return grab_jobs


# 6. Indosat Ooredoo Hutchison (IOH)
def fetch_ioh_job_detail(url: str, session: Optional[requests.Session] = None) -> str:
    if session is None:
        session = get_default_session()
    try:
        r = session.get(url, timeout=12)
        soup = BeautifulSoup(r.text, "html.parser")
        desc_el = soup.find(class_="jobdescription") or soup.find(class_="jobDisplay")
        if desc_el:
            return str(desc_el)
    except Exception:
        pass
    return ""


def scrape_ioh_careers(session: Optional[requests.Session] = None, max_workers: int = 10) -> List[Dict[str, Any]]:
    """Scrape lowongan Indosat Ooredoo Hutchison (IOH)."""
    if session is None:
        session = get_default_session()

    print("Fetching Indosat Ooredoo Hutchison (IOH) vacancies...")
    ioh_jobs = []
    seen = set()
    try:
        for start in range(0, 150, 10):
            r = session.get(f"https://careers.ioh.co.id/search/?q=&startrow={start}", timeout=12)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, "html.parser")
            tiles = soup.find_all("li", class_="job-tile")
            new_found = 0
            for t in tiles:
                a = t.find("a", class_="jobTitle-link")
                if not a or "href" not in a.attrs:
                    continue
                href = a["href"]
                full_url = "https://careers.ioh.co.id" + href
                if full_url in seen:
                    continue
                seen.add(full_url)
                new_found += 1

                title = a.get_text(strip=True)
                job_id_match = re.search(r"/(\d+)/?$", href)
                job_id = job_id_match.group(1) if job_id_match else str(len(seen))

                loc_el = t.find(class_="location")
                loc = loc_el.get_text(strip=True).replace("Location", "").strip() if loc_el else "Jakarta, Indonesia"
                dept_el = t.find(class_="dept")
                dept = dept_el.get_text(strip=True).replace("Department", "").strip() if dept_el else "Indosat Ooredoo Hutchison"

                ioh_jobs.append({
                    "id": f"ioh_{job_id}",
                    "title": title,
                    "organization_id": "IOH",
                    "organization_name": "Indosat Ooredoo Hutchison",
                    "slug": f"ioh-{job_id}",
                    "type_name": "Full Time",
                    "level": "Profesional",
                    "location": loc or "Jakarta, Indonesia",
                    "workplace": "Hybrid / WFO",
                    "due_date": "Aktif",
                    "group": dept or "Indosat Ooredoo Hutchison",
                    "url": full_url,
                    "description": f"<p>Posisi: <strong>{title}</strong></p><p>Perusahaan: Indosat Ooredoo Hutchison</p><p>Divisi: {dept}</p>",
                    "requirements": f"<p>Posisi: <strong>{title}</strong></p><p>Perusahaan: Indosat Ooredoo Hutchison</p><p>Divisi: {dept}</p>",
                    "source": "Indosat Ooredoo Hutchison",
                    "logo": "https://rmkcdn.successfactors.com/00ae8fcf/5c0af18e-1ebe-4f24-80ab-0.png"
                })
            if new_found == 0:
                break
    except Exception as e:
        print(f"  Warning: Error scraping IOH: {e}")

    print(f"  Found {len(ioh_jobs)} IOH jobs. Fetching details concurrently...")
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_job = {executor.submit(fetch_ioh_job_detail, job["url"], session): job for job in ioh_jobs}
        for future in as_completed(future_to_job):
            job = future_to_job[future]
            try:
                detail_html = future.result()
                if detail_html:
                    job["description"] = detail_html
                    job["requirements"] = detail_html
            except Exception:
                pass

    print(f"  ✓ IOH: retrieved {len(ioh_jobs)} jobs.")
    return ioh_jobs


# 7. Indofood Careers
def scrape_indofood_careers(session: Optional[requests.Session] = None) -> List[Dict[str, Any]]:
    """Scrape lowongan Indofood Careers via AJAX POST."""
    if session is None:
        session = get_default_session()

    print("Fetching Indofood Careers vacancies...")
    indofood_jobs = []
    payload = {
        "advFilter": {
            "NeedJobList": "Y",
            "RefreshCE": "Y",
            "SearchKeyword": "",
            "CheckedAdvFilterEduLevel": [],
            "CheckedAdvFilterFunction": [],
            "CheckedAdvFilterExpLevel": [],
            "CheckedAdvFilterCity": [],
            "pageNumber": 1,
            "PageSize": 100,
            "BindFuncANDJOB": False,
            "SortedBy": "lastposted",
            "Lang": "id"
        }
    }
    try:
        r = session.post(
            "https://career.indofood.com/default.aspx/OnGetAdvFilter",
            json=payload,
            headers={
                "Content-Type": "application/json; charset=utf-8",
                "X-Requested-With": "XMLHttpRequest"
            },
            timeout=12
        )
        if r.status_code == 200:
            d_val = r.json().get("d", "")
            if "[space2]" in d_val:
                _, data_part = d_val.split("[space2]")
                data_json = json.loads(data_part)
                vacancies = data_json.get("ListAdvFilterJob", [])

                for v in vacancies:
                    desc_html = v.get("JobDesc", "") or ""
                    req_html = v.get("JobReq", "") or ""
                    indofood_jobs.append({
                        "id": v.get("JobID"),
                        "title": v.get("JobPositionName"),
                        "organization_id": v.get("JobDivision"),
                        "organization_name": v.get("JobDivisionName") or "PT Indofood Sukses Makmur Tbk",
                        "slug": f"indofood-{v.get('JobID')}",
                        "type_name": "Karyawan Tetap" if v.get("JobStatusName2") == "Tetap" else "Karyawan Kontrak",
                        "level": v.get("ExpLevelName") or "Professional",
                        "location": f"{v.get('JobLocation', '')} - {v.get('CityName', '')}".strip(" -"),
                        "workplace": "Work From Office (WFO)",
                        "due_date": v.get("JobValidUntilStrID"),
                        "group": v.get("JobFunctionName"),
                        "url": f"https://career.indofood.com/vacancy_detail.aspx?id={v.get('JobID')}",
                        "description": desc_html,
                        "requirements": req_html,
                        "source": "Indofood",
                        "logo": None
                    })
    except Exception as e:
        print(f"  Warning: Exception during Indofood scraping: {e}")

    print(f"  ✓ Indofood: retrieved {len(indofood_jobs)} jobs.")
    return indofood_jobs


# 8. OpenTrain.ai
def scrape_opentrain_jobs(session: Optional[requests.Session] = None, max_workers: int = 10) -> List[Dict[str, Any]]:
    """Scrape lowongan remote AI training & coding dari OpenTrain.ai."""
    if session is None:
        session = get_default_session()

    print("Fetching OpenTrain.ai jobs...")
    cat_urls = [
        "https://www.opentrain.ai/jobs/category/coding-software/",
        "https://www.opentrain.ai/jobs/category/generative-ai-rlhf/",
        "https://www.opentrain.ai/jobs/data-annotation/"
    ]

    job_links = []
    seen_urls = set()

    def fetch_category_links(cat_url):
        results = []
        try:
            r = session.get(cat_url, timeout=12)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if href.startswith('/jobs/') and not href.startswith('/jobs/category') and not href.startswith('/jobs/location') and href != '/jobs/' and '?apply=' not in href:
                        full_url = 'https://www.opentrain.ai' + href
                        title = a.get_text(' ', strip=True)
                        if title and title != 'View job':
                            results.append({'title': title, 'url': full_url})
        except Exception:
            pass
        return results

    with ThreadPoolExecutor(max_workers=3) as executor:
        for links in executor.map(fetch_category_links, cat_urls):
            for link in links:
                if link['url'] not in seen_urls:
                    seen_urls.add(link['url'])
                    job_links.append(link)

    print(f"  Found {len(job_links)} OpenTrain roles. Fetching details concurrently...")

    def fetch_opentrain_detail(job_info):
        url = job_info['url']
        try:
            r = session.get(url, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                for s in soup.find_all('script', type='application/ld+json'):
                    try:
                        data = json.loads(s.string)
                        if data.get('@type') == 'JobPosting':
                            desc = data.get('description', '')
                            clean_desc = clean_html(desc)
                            valid_through = str(data.get('validThrough', '')).replace('T', ' ')[:19]
                            return {
                                'id': f"opentrain_{url.rstrip('/').split('--')[-1]}",
                                'title': data.get('title') or job_info['title'],
                                'organization_name': 'OpenTrain.ai',
                                'location': 'Remote (Worldwide)',
                                'workplace': 'Work From Home (Remote)',
                                'due_date': valid_through or 'Active',
                                'group': 'AI Training & RLHF',
                                'url': url,
                                'description': clean_desc,
                                'requirements': 'Remote AI Training, Evaluation, Python, LLM Reasoning, Data Annotation',
                                'type_name': 'Freelance / Contract',
                                'source': 'OpenTrain.ai'
                            }
                    except Exception:
                        pass
        except Exception:
            pass
        slug = url.rstrip('/').split('/')[-1]
        return {
            'id': f"opentrain_{slug}",
            'title': job_info['title'],
            'organization_name': 'OpenTrain.ai',
            'location': 'Remote (Worldwide)',
            'workplace': 'Work From Home (Remote)',
            'due_date': 'Active',
            'group': 'AI Training & RLHF',
            'url': url,
            'description': f"Role for {job_info['title']} at OpenTrain.ai. Remote AI Training & RLHF tasks.",
            'requirements': 'Remote AI Training, Evaluation, Python, LLM Reasoning, Data Annotation',
            'type_name': 'Freelance / Contract',
            'source': 'OpenTrain.ai'
        }

    detailed_jobs = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_opentrain_detail, job) for job in job_links]
        for f in as_completed(futures):
            res = f.result()
            if res:
                detailed_jobs.append(res)

    print(f"  ✓ OpenTrain: retrieved {len(detailed_jobs)} jobs.")
    return detailed_jobs


# 9. micro1 Remote
def scrape_micro1_jobs(session: Optional[requests.Session] = None, max_workers: int = 10) -> List[Dict[str, Any]]:
    """
    Scrape remote software & AI jobs dari micro1.
    Dioptimasi untuk fetch detail secara concurrent (bukan sequential loop).
    """
    if session is None:
        session = get_default_session()

    print("Fetching micro1 remote jobs...")
    url = "https://microonejobs.com/jobs"
    raw_stubs = []
    try:
        r = session.get(url, timeout=12)
        if r.status_code == 200:
            soup = BeautifulSoup(r.text, 'html.parser')
            cards = soup.find_all('a', href=lambda h: h and h.startswith('/jobs/'))
            for c in cards:
                href = c['href']
                full_url = "https://microonejobs.com" + href
                text_parts = [t.strip() for t in c.get_text(';', strip=True).split(';') if t.strip()]

                title = ''
                company = 'micro1'
                salary = ''
                location = 'Remote (Worldwide)'
                for p in text_parts:
                    if any(role in p for role in ('Engineer', 'Developer', 'Designer', 'Marketer', 'Analyst')):
                        title = p
                    elif '$' in p:
                        salary = p
                    elif 'Remote' in p:
                        location = p.replace('\ufffd', '-').replace('', '-')

                if not title and len(text_parts) > 2:
                    title = text_parts[2]
                if len(text_parts) > 1 and not ('Engineer' in text_parts[1] or '$' in text_parts[1]):
                    company = text_parts[1]

                slug = href.replace('/jobs/', '')
                raw_stubs.append({
                    'id': f"micro1_{slug}",
                    'title': title or "Software Engineer",
                    'organization_name': company,
                    'location': location,
                    'workplace': 'Work From Home (Remote)',
                    'due_date': 'Active',
                    'group': 'Engineering & Tech',
                    'url': full_url,
                    'salary': salary,
                    'requirements': 'Software Engineering, Remote, Problem Solving, Fullstack/Backend/Frontend/AI',
                    'type_name': 'Full Time / Remote',
                    'source': 'micro1'
                })
    except Exception as e:
        print(f"  Warning: micro1 listing fetch error: {e}")
        return []

    print(f"  Found {len(raw_stubs)} micro1 listings. Fetching details concurrently...")

    def fetch_micro1_detail(stub):
        desc = ''
        try:
            r_det = session.get(stub['url'], timeout=8)
            if r_det.status_code == 200:
                soup_det = BeautifulSoup(r_det.text, 'html.parser')
                main_content = soup_det.find('main') or soup_det.find('article') or soup_det.body
                if main_content:
                    desc = main_content.get_text('\n', strip=True)
        except Exception:
            pass
        salary_str = f"\nSalary: {stub['salary']}" if stub.get('salary') else ""
        stub['description'] = (desc or stub['title']) + salary_str
        stub.pop('salary', None)
        return stub

    jobs = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_micro1_detail, stub) for stub in raw_stubs]
        for f in as_completed(futures):
            jobs.append(f.result())

    print(f"  ✓ micro1: retrieved {len(jobs)} jobs.")
    return jobs


# 10. LinkedIn Jobs (Guest API)
def scrape_linkedin_jobs(session: Optional[requests.Session] = None, max_per_keyword: int = 10, max_workers: int = 5) -> List[Dict[str, Any]]:
    """Scrape lowongan LinkedIn via Guest API dengan concurrency terkontrol."""
    if session is None:
        session = get_default_session()

    print("Fetching LinkedIn Jobs via Guest API...")
    keywords = ("Data Scientist", "Data Analyst", "Machine Learning", "Python Developer", "IT Support")
    found_cards = []
    seen_ids = set()

    for kw in keywords:
        url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        params = {"keywords": kw, "location": "Indonesia", "start": 0}
        try:
            r = session.get(url, params=params, timeout=10)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                items = soup.find_all("li")
                count = 0
                for item in items:
                    if count >= max_per_keyword:
                        break
                    title_el = item.find("h3", class_="base-search-card__title")
                    comp_el = item.find("h4", class_="base-search-card__subtitle")
                    loc_el = item.find("span", class_="job-search-card__location")
                    link_el = item.find("a", class_="base-card__full-link")
                    date_el = item.find("time")

                    title = title_el.get_text(strip=True) if title_el else ""
                    comp = comp_el.get_text(strip=True) if comp_el else "Unknown Company"
                    loc = loc_el.get_text(strip=True) if loc_el else "Indonesia"
                    link = link_el.get("href", "") if link_el else ""
                    clean_url = link.split("?")[0] if link else ""
                    date = date_el.get_text(strip=True) if date_el else "Aktif"

                    if not title or not clean_url:
                        continue

                    job_id_match = re.search(r"(\d{8,})", clean_url)
                    job_id = job_id_match.group(1) if job_id_match else clean_url.rstrip("/").split("-")[-1]

                    if job_id in seen_ids:
                        continue
                    seen_ids.add(job_id)

                    found_cards.append({
                        "job_id": job_id,
                        "title": title,
                        "company": comp,
                        "location": loc,
                        "url": clean_url,
                        "date": date,
                        "kw": kw
                    })
                    count += 1
            elif r.status_code == 429:
                print(f"    [!] LinkedIn rate limit for '{kw}'. Skipping keyword.")
                break
        except Exception as e:
            print(f"    [!] LinkedIn search exception for '{kw}': {e}")

    print(f"  Found {len(found_cards)} LinkedIn roles. Fetching descriptions concurrently...")

    def fetch_linkedin_detail(card):
        jid = card["job_id"]
        detail_url = f"https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{jid}"
        desc_html = ""
        raw_desc = f"{card['title']} di {card['company']}, Lokasi: {card['location']}."
        try:
            r = session.get(detail_url, timeout=8)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, "html.parser")
                desc_el = soup.find("div", class_="show-more-less-html__markup")
                if desc_el:
                    desc_html = str(desc_el)
                    raw_desc = clean_html(desc_html)
        except Exception:
            pass

        if not desc_html:
            desc_html = f"<p><strong>{card['title']}</strong></p><p>Perusahaan: {card['company']}</p><p>Lokasi: {card['location']}</p><p>Diposting: {card['date']}</p>"

        return {
            "id": f"linkedin_{jid}",
            "title": card["title"],
            "organization_id": "LinkedIn",
            "organization_name": card["company"],
            "slug": f"linkedin-{jid}",
            "type_name": "Full Time / Contract",
            "level": "Profesional",
            "location": card["location"],
            "workplace": "Hybrid / Onsite",
            "due_date": card["date"],
            "group": "Tech & Data",
            "url": card["url"],
            "raw_description": raw_desc,
            "description": desc_html,
            "requirements": desc_html,
            "source": "LinkedIn",
            "logo": None
        }

    detailed_jobs = []
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(fetch_linkedin_detail, card) for card in found_cards]
        for f in as_completed(futures):
            detailed_jobs.append(f.result())

    print(f"  ✓ LinkedIn: retrieved {len(detailed_jobs)} jobs.")
    return detailed_jobs


# ─── Optional Firecrawl & JobSpy Integrations ─────────────────────────────────
def scrape_with_firecrawl(url: str, format_output: str = "markdown") -> Optional[str]:
    """Gunakan Firecrawl untuk extract data bersih dari URL."""
    if FirecrawlApp is None:
        return None
    try:
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            return None
        app = FirecrawlApp(api_key=api_key)
        try:
            scrape_result = app.scrape_url(url, formats=[format_output], timeout=30000)
        except TypeError:
            scrape_result = app.scrape_url(url, {"formats": [format_output], "timeout": 30000})

        if scrape_result:
            if hasattr(scrape_result, format_output):
                return getattr(scrape_result, format_output)
            elif isinstance(scrape_result, dict):
                return scrape_result.get(format_output) or (scrape_result.get("data", {}).get(format_output) if isinstance(scrape_result.get("data"), dict) else None)
        return None
    except Exception as e:
        print(f"  Firecrawl error on {url}: {e}")
        return None


def scrape_with_jobspy(job_title: str, location: str = "", max_results: int = 50) -> List[Dict[str, Any]]:
    """Gunakan JobSpy untuk aggregate jobs dari LinkedIn dengan hash ID deterministik."""
    if scrape_jobs is None:
        return []
    try:
        print(f"  Scraping LinkedIn via JobSpy for '{job_title}'...")
        jobs = scrape_jobs(
            site_name=["linkedin"],
            search_term=job_title,
            location=location,
            results_wanted=max_results,
        )
        if len(jobs) == 0:
            return []

        normalized_jobs = []
        for _, job in jobs.iterrows():
            url = str(job.get("job_url", ""))
            title = str(job.get("title", ""))
            stable_id = hashlib.sha256(f"{url}_{title}".encode('utf-8')).hexdigest()[:16]
            normalized_jobs.append({
                "id": f"jobspy_{stable_id}",
                "title": title,
                "organization_name": str(job.get("company", "")),
                "location": str(job.get("location", "")),
                "workplace": "Unknown",
                "due_date": str(job.get("date_posted", "")),
                "group": str(job.get("job_type", "")),
                "url": url,
                "description": str(job.get("description", "") or job.get("job_description", ""))[:500],
                "requirements": str(job.get("description", "") or job.get("job_description", ""))[:500],
                "salary_min": job.get("min_amount"),
                "salary_max": job.get("max_amount"),
                "source": "JobSpy (LinkedIn)",
            })
        return normalized_jobs
    except Exception as e:
        print(f"  ⚠️ JobSpy error: {e}")
        return []


# ─── Scraper Registry & Orchestrator ──────────────────────────────────────────
SCRAPER_REGISTRY = {
    "talentics": ("Talentics (Hulu Migas)", scrape_talentics_jobs),
    "astra": ("Astra Careers", scrape_astra_jobs),
    "ptc": ("Pertamina PTC", scrape_pertamina_ptc),
    "sawitpro": ("SawitPRO", scrape_sawitpro),
    "grab": ("Grab Careers Indonesia", scrape_grab_careers),
    "ioh": ("Indosat Ooredoo Hutchison", scrape_ioh_careers),
    "indofood": ("Indofood Careers", scrape_indofood_careers),
    "opentrain": ("OpenTrain.ai", scrape_opentrain_jobs),
    "micro1": ("micro1 Remote", scrape_micro1_jobs),
    "linkedin": ("LinkedIn Jobs", lambda s: scrape_linkedin_jobs(s, max_per_keyword=10)),
}


def run_pipeline(
    portals: Optional[List[str]] = None,
    parallel: bool = True,
    filter_major: bool = True,
    portal_workers: int = 5
) -> List[Dict[str, Any]]:
    """
    Eksekusi pipeline scraping dengan opsi paralel lintas-portal dan scoring cerdas.
    """
    session = get_default_session()
    start_time = time.time()

    # Pilih scraper yang aktif
    if portals:
        selected_scrapers = {k: v for k, v in SCRAPER_REGISTRY.items() if k.lower() in [p.lower() for p in portals]}
    else:
        selected_scrapers = SCRAPER_REGISTRY

    print("=" * 70)
    print(f"🚀 Memulai Job Matcher Scraper Pipeline ({len(selected_scrapers)} portal)")
    print(f"Mode: {'Paralel (' + str(portal_workers) + ' threads)' if parallel else 'Sekuensial'}")
    print("=" * 70)

    raw_jobs_by_portal: Dict[str, List[Dict[str, Any]]] = {}

    if parallel and len(selected_scrapers) > 1:
        with ThreadPoolExecutor(max_workers=portal_workers) as portal_executor:
            future_to_key = {
                portal_executor.submit(runner, session): (key, label)
                for key, (label, runner) in selected_scrapers.items()
            }
            for future in as_completed(future_to_key):
                key, label = future_to_key[future]
                try:
                    jobs = future.result() or []
                    raw_jobs_by_portal[key] = jobs
                    print(f"  [+] Portal {label} selesai ({len(jobs)} jobs)")
                except Exception as ex:
                    print(f"  [!] Error pada portal {label}: {ex}")
                    raw_jobs_by_portal[key] = []
    else:
        for key, (label, runner) in selected_scrapers.items():
            try:
                jobs = runner(session) or []
                raw_jobs_by_portal[key] = jobs
                print(f"  [+] Portal {label} selesai ({len(jobs)} jobs)")
            except Exception as ex:
                print(f"  [!] Error pada portal {label}: {ex}")
                raw_jobs_by_portal[key] = []

    # Flatten dan Global Deduplication
    all_raw_jobs = [job for jobs in raw_jobs_by_portal.values() for job in jobs]
    print(f"\nTotal lowongan mentah terkumpul: {len(all_raw_jobs)}")

    # Deduplikasi cerdas berdasarkan (source, id)
    seen_keys: Set[str] = set()
    deduped_raw: List[Dict[str, Any]] = []

    for job in all_raw_jobs:
        src = str(job.get("source") or "").strip().lower()
        jid = str(job.get("id") or "").strip().lower()
        raw_url = str(job.get("url") or "").strip().lower()

        if jid:
            key = f"{src}:{jid}"
        elif raw_url:
            key = f"{src}:{raw_url}"
        else:
            key = f"{src}:{hash(str(job))}"

        if key in seen_keys:
            continue
        seen_keys.add(key)
        deduped_raw.append(job)

    print(f"Deduplikasi selesai: {len(deduped_raw)} lowongan unik tersisa.")

    # Scoring & NLP Match Evaluation
    print("Mengevaluasi match score dan NLP breakdown...")
    matched_jobs: List[Dict[str, Any]] = []
    for job in deduped_raw:
        try:
            matched_jobs.append(evaluate_job_match(job))
        except Exception as e:
            print(f"  Warning: Error scoring job '{job.get('title')}': {e}")

    # Sorting: skor tertinggi duluan, non-blocked diutamakan
    matched_jobs.sort(key=lambda x: (0 if x["is_blocked"] else 1, x["match_score"]), reverse=True)

    # Filter major (IT / All Majors) jika diminta
    if filter_major:
        filtered = [j for j in matched_jobs if j["match_details"]["major"]["status"] in ("High Match", "Match")]
        print(f"Filter major aktif: menyaring {len(matched_jobs) - len(filtered)} lowongan non-IT/spesifik.")
        matched_jobs = filtered

    # Jika partial run (--portal diberikan), merge dengan job dari portal lain yang sudah ada di matched_jobs.json
    base_dir = os.path.dirname(os.path.abspath(__file__))
    output_json = os.path.join(base_dir, "matched_jobs.json")
    if portals and os.path.exists(output_json):
        try:
            with open(output_json, "r", encoding="utf-8") as f:
                existing_jobs = json.load(f)
            # Ambil nama source portal yang baru saja di-scrape
            scraped_sources = {str(j.get("source") or "").strip().lower() for j in matched_jobs}
            # Simpan job dari portal lain yang tidak di-scrape kali ini
            retained_jobs = [
                j for j in existing_jobs
                if str(j.get("source") or "").strip().lower() not in scraped_sources
            ]
            merged_jobs = matched_jobs + retained_jobs
            merged_jobs.sort(key=lambda x: (0 if x["is_blocked"] else 1, x["match_score"]), reverse=True)
            matched_jobs = merged_jobs
            print(f"Merge partial run: {len(retained_jobs)} lowongan portal lain dipertahankan, total: {len(matched_jobs)}.")
        except Exception as e:
            print(f"  Warning: Gagal merge data existing: {e}")

    # Simpan output
    print("\nMenyimpan file output...")
    save_jobs(matched_jobs, base_dir=base_dir)

    elapsed = time.time() - start_time
    print("=" * 70)
    print(f"✓ Pipeline selesai dalam {elapsed:.2f} detik! Total {len(matched_jobs)} lowongan tersimpan.")
    print("=" * 70)

    return matched_jobs


def main():
    parser = argparse.ArgumentParser(description="Job Matcher Scraper Engine (High Performance)")
    parser.add_argument("--portal", type=str, default="", help="Pilih portal tertentu, dipisahkan koma (contoh: astra,ptc,talentics)")
    parser.add_argument("--sequential", action="store_true", help="Jalankan scraper secara sekuensial (bukan paralel)")
    parser.add_argument("--workers", type=int, default=5, help="Jumlah thread worker untuk scraping paralel lintas portal")
    parser.add_argument("--no-filter", action="store_true", help="Jangan filter jurusan (simpan semua lowongan)")
    args = parser.parse_args()

    portals = [p.strip() for p in args.portal.split(",") if p.strip()] if args.portal else None
    run_pipeline(
        portals=portals,
        parallel=not args.sequential,
        filter_major=not args.no_filter,
        portal_workers=args.workers
    )


if __name__ == "__main__":
    main()
