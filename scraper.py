import sys
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

import requests
from bs4 import BeautifulSoup
import json
import re
import time
import os
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
import pytz  # Import di top, jangan dalam function (efficiency + error handling jelas)
from dotenv import load_dotenv
load_dotenv()

try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.chrome.options import Options
    from webdriver_manager.chrome import ChromeDriverManager
    from selenium.webdriver.chrome.service import Service
except ImportError:
    webdriver = None

# Enhanced Scrapers (Firecrawl & JobSpy)
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

def get_timestamp_wib():
    """Kembalikan string timestamp format '12 Juli 2026 - 17:23 WIB'."""
    # Konversi UTC ke WIB (UTC+7) — pytz sudah di-import di top
    utc_now = datetime.datetime.now(datetime.timezone.utc)
    wib_tz = pytz.timezone('Asia/Jakarta')
    wib_now = utc_now.astimezone(wib_tz)
    return f"{wib_now.day} {MONTHS_ID[wib_now.month]} {wib_now.year} - {wib_now.strftime('%H:%M')} WIB"

def detect_new_jobs(matched_jobs, base_dir):
    """
    Bandingkan ID job saat ini dengan run sebelumnya.
    Kembalikan list ID job yang benar-benar baru (belum pernah ada sebelumnya).
    """
    prev_path = os.path.join(base_dir, "matched_jobs.json")
    prev_ids = set()
    if os.path.exists(prev_path):
        try:
            with open(prev_path, encoding="utf-8") as f:
                prev_jobs = json.load(f)
            prev_ids = {str(j.get("id")) for j in prev_jobs}
        except Exception:
            pass

    current_ids = {str(j.get("id")) for j in matched_jobs}
    new_ids = current_ids - prev_ids
    print(f"Job baru terdeteksi: {len(new_ids)} dari {len(current_ids)} total")
    return list(new_ids)


def save_jobs(matched_jobs, base_dir=None):
    """
    Simpan hasil matched_jobs ke empat file output:
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
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(matched_jobs, f, indent=2, ensure_ascii=False)

    output_js = os.path.join(base_dir, "matched_jobs.js")
    with open(output_js, "w", encoding="utf-8") as f:
        f.write(f"window.lastUpdated = '{timestamp_str}';\n")
        f.write("window.matchedJobs = " + json.dumps(matched_jobs, ensure_ascii=False) + ";")

    output_lu = os.path.join(base_dir, "last_updated.json")
    with open(output_lu, "w", encoding="utf-8") as f:
        json.dump({"last_updated": timestamp_str}, f, indent=2, ensure_ascii=False)

    # Simpan ID job baru — dibaca frontend untuk tampilkan notifikasi
    output_new = os.path.join(base_dir, "new_jobs.json")
    with open(output_new, "w", encoding="utf-8") as f:
        json.dump({
            "scraped_at": timestamp_str,
            "new_ids": new_job_ids,
            "count": len(new_job_ids)
        }, f, indent=2, ensure_ascii=False)

    print(f"Output disimpan ke: {output_json}, {output_js}, {output_lu}, {output_new}")
    return timestamp_str
# ──────────────────────────────────────────────────────────────────────────────

# User Profile definition di-import dari config.py di atas (terpusat, DRY)
# clean_html di-import dari config.py di atas

def parse_gpa_req(req_text):
    # Search for GPA / IPK requirement
    # E.g. "IPK minimal 3.00", "GPA min. 3.25", etc.
    text_lower = req_text.lower()
    gpa_pattern = re.findall(r'(?:ipk|gpa)[^\d]*(\d[.,]\d{2})', text_lower)
    if gpa_pattern:
        try:
            return float(gpa_pattern[0].replace(',', '.'))
        except ValueError:
            pass
    return None

def parse_age_req(req_text):
    # Search for Max Age requirement
    # E.g. "Usia maksimal 25 tahun", "maximum age of 27", "maks. 27 tahun"
    text_lower = req_text.lower()
    # Match patterns like: usia/umur/age maksimal/max/maks/maksimal 25
    age_pattern1 = re.findall(r'(?:usia|umur|age)\s*(?:maksimal|maks|maks\.|max|maximum)?[^\d]*(\d{2})', text_lower)
    # Match patterns like: maksimal/maks/max 25 tahun
    age_pattern2 = re.findall(r'(?:maksimal|maks|maks\.|max|maximum)\s*(?:usia|umur|age)?[^\d]*(\d{2})\s*(?:tahun|years)', text_lower)
    
    ages = []
    for match in age_pattern1 + age_pattern2:
        try:
            ages.append(int(match))
        except ValueError:
            pass
    
    if ages:
        return max(ages) # Assume the maximum age restriction found
    return None

def parse_toefl_req(req_text):
    # Search for TOEFL score requirements
    text_lower = req_text.lower()
    toefl_pattern = re.findall(r'toefl[^\d]*(\d{3})', text_lower)
    if toefl_pattern:
        try:
            return int(toefl_pattern[0])
        except ValueError:
            pass
    return None

def check_gender_req(req_text):
    # Check if a specific gender is required
    text_lower = req_text.lower()
    # If the text mentions "laki-laki" or "pria" and NOT "wanita" or "perempuan" (or vice versa)
    has_male = "pria" in text_lower or "laki-laki" in text_lower or "male" in text_lower
    has_female = "wanita" in text_lower or "perempuan" in text_lower or "female" in text_lower
    
    # E.g. "khusus pria", "pria/laki-laki", "diutamakan laki-laki"
    # If both are mentioned (e.g. "Pria/Wanita"), then it's open.
    if has_male and not has_female:
        return "Male Only"
    elif has_female and not has_male:
        return "Female Only"
    return "Open"

def parse_exp_req(req_text):
    """
    Parse experience requirement dengan better accuracy.
    Return dict dengan level + detail, bukan hanya angka.
    """
    text_lower = req_text.lower()
    
    # Patterns untuk extract angka pengalaman
    pattern1 = re.findall(r'(?:pengalaman|experience)\s*(?:kerja)?\s*(?:minimal|min|min\.|diutamakan|at least)?\s*(\d+)\s*(?:\+)?\s*(?:tahun|year)', text_lower)
    pattern2 = re.findall(r'(?:minimal|min|min\.|at least)\s*(\d+)\s*(?:\+)?\s*(?:tahun|year)\s*(?:pengalaman|experience)', text_lower)
    pattern3 = re.findall(r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:relevant\s*)?experience', text_lower)
    pattern4 = re.findall(r'(\d+)\s*(?:tahun)\s*(?:pengalaman)', text_lower)
    
    exps = []
    for match in pattern1 + pattern2 + pattern3 + pattern4:
        try:
            exps.append(int(match))
        except ValueError:
            pass
    
    years_req = max(exps) if exps else 0
    
    # Determine level based on years
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
        "raw_text": text_lower[:200]  # Keep snippet untuk debugging
    }


class RequirementNLPParser:
    """
    Enhanced Natural Language Processing (NLP) Parser for Job Requirements.
    Features:
    - Semantic sentence classification (Mandatory, Preferred, Nice-to-have, Responsibility)
    - Skill taxonomy NER extraction dengan category mapping
    - Education & experience requirements parsing
    - Soft skills & competency detection
    - Context-aware requirement understanding
    """
    SKILL_TAXONOMY = {
        "Languages & Core": ["Python", "SQL", "PHP", "R", "Java", "C++", "JavaScript", "TypeScript", "Go", "Bash", "Shell"],
        "Data Science & Analytics": ["Machine Learning", "Deep Learning", "NLP", "Pandas", "NumPy", "Scikit-Learn", "PyTorch", "TensorFlow", "Data Analysis", "Statistical Modeling", "Analytics", "Dataiku"],
        "BI & Visualization": ["Power BI", "PowerBI", "Tableau", "Looker", "Metabase", "Excel", "Data Studio"],
        "Engineering & Tools": ["React", "React.js", "Laravel", "Airflow", "Spark", "Hadoop", "Docker", "Kubernetes", "AWS", "GCP", "Azure", "Git", "REST API", "CI/CD", "PostgreSQL", "MySQL", "ArcGIS"],
        "Domain & Methodology": ["Hulu Migas", "Oil and Gas", "Oil & Gas", "Upstream", "Agile", "Scrum", "Project Management", "AI Engineer"]
    }
    
    SOFT_SKILLS = [
        "komunikasi", "communication", "teamwork", "tim kerja", "leadership", "kepemimpinan",
        "problem solving", "pemecahan masalah", "critical thinking", "berpikir kritis",
        "analytical", "analitis", "attention to detail", "perhatian detail",
        "adaptability", "adaptif", "flexibility", "fleksibel", "self-motivated", "termotivasi",
        "time management", "manajemen waktu", "presentation", "presentasi"
    ]

    @classmethod
    def classify_sentence(cls, sentence, sentence_lower):
        """Classify sentence type: mandatory, preferred, responsibility, or description"""
        mandatory_triggers = ["wajib", "harus", "minimal", "required", "must", "essential", "syarat", "qualification", "persyaratan"]
        preferred_triggers = ["diutamakan", "preferred", "advantage", "keuntungan", "lebih baik"]
        nice_triggers = ["nice to have", "bonus", "nilai tambah", "nilai plus", "plus point"]
        resp_triggers = ["melakukan", "mengembangkan", "mengelola", "memastikan", "bertanggung jawab", "responsible", "manage", "handle", "develop", "create"]
        
        if any(t in sentence_lower for t in mandatory_triggers):
            return "mandatory"
        elif any(t in sentence_lower for t in preferred_triggers):
            return "preferred"
        elif any(t in sentence_lower for t in nice_triggers):
            return "nice_to_have"
        elif any(t in sentence_lower for t in resp_triggers):
            return "responsibility"
        else:
            return "description"

    @classmethod
    def extract_skills_from_sentence(cls, sentence, sentence_lower):
        """Extract all skills mentioned in sentence dengan category"""
        found_skills = {}
        for category, skills in cls.SKILL_TAXONOMY.items():
            for sk in skills:
                pattern = r'\b' + re.escape(sk.lower()) + r'\b'
                if re.search(pattern, sentence_lower):
                    if category not in found_skills:
                        found_skills[category] = []
                    found_skills[category].append(sk)
        return found_skills

    @classmethod
    def extract_soft_skills(cls, sentence_lower):
        """Extract soft skills mentioned"""
        found_soft_skills = []
        for skill in cls.SOFT_SKILLS:
            if skill in sentence_lower:
                found_soft_skills.append(skill.title())
        return found_soft_skills

    @classmethod
    def parse(cls, job):
        """Parse job requirements dengan semantic understanding"""
        raw = (job.get("requirements", "") + " " + job.get("description", ""))
        text = clean_html(raw)
        
        # Segment into logical sentences or bullet items
        sentences = [s.strip() for s in re.split(r'[\n•\-\*.]+', text) if len(s.strip()) > 15]
        
        mandatory_requirements = []
        preferred_requirements = []
        nice_to_have_requirements = []
        responsibilities = []
        
        mandatory_skills_dict = {}  # {category: [skills]}
        preferred_skills_dict = {}
        soft_skills_found = set()
        
        edu_summary = "S1 / D3 jurusan relevan atau setara"
        exp_summary = "1 Tahun Pengalaman / Fresh Graduate"
        accepts_fresh = False
        job_responsibilities = []
        
        # Parse each sentence
        for sent in sentences:
            sent_lower = sent.lower()
            
            # Classify sentence type
            sent_type = cls.classify_sentence(sent, sent_lower)
            
            # Extract education context
            if any(k in sent_lower for k in ["s1", "d3", "sarjana", "bachelor", "pendidikan"]):
                if len(sent) < 130 and "pendidikan" in sent_lower:
                    edu_summary = sent
            
            # Extract experience context
            if any(k in sent_lower for k in ["fresh graduate", "lulusan baru", "0 tahun", "magang", "internship"]):
                accepts_fresh = True
                if len(sent) < 140:
                    exp_summary = sent
            elif any(k in sent_lower for k in ["pengalaman", "experience", "tahun"]):
                if len(sent) < 140 and exp_summary == "1 Tahun Pengalaman / Fresh Graduate":
                    exp_summary = sent
            
            # Extract skills
            skills_found = cls.extract_skills_from_sentence(sent, sent_lower)
            soft_skills = cls.extract_soft_skills(sent_lower)
            soft_skills_found.update(soft_skills)
            
            # Categorize requirement based on type
            if sent_type == "mandatory":
                mandatory_requirements.append(sent)
                for category, skills in skills_found.items():
                    if category not in mandatory_skills_dict:
                        mandatory_skills_dict[category] = []
                    mandatory_skills_dict[category].extend(skills)
                    
            elif sent_type == "preferred":
                preferred_requirements.append(sent)
                for category, skills in skills_found.items():
                    if category not in preferred_skills_dict:
                        preferred_skills_dict[category] = []
                    preferred_skills_dict[category].extend(skills)
                    
            elif sent_type == "nice_to_have":
                nice_to_have_requirements.append(sent)
                
            elif sent_type == "responsibility":
                responsibilities.append(sent)
                job_responsibilities.append(sent)
        
        # Flatten and deduplicate skills
        mandatory_skills = sorted(list(set([s for skills in mandatory_skills_dict.values() for s in skills])))
        preferred_skills = sorted(list(set([s for skills in preferred_skills_dict.values() for s in skills])))
        
        if accepts_fresh:
            exp_summary = "Terbuka untuk Fresh Graduate / 1 Tahun Pengalaman (" + exp_summary[:90] + "...)"
            
        return {
            # Basic summaries
            "education_summary": edu_summary[:130],
            "experience_summary": exp_summary[:150],
            
            # Skills breakdown
            "mandatory_skills": mandatory_skills,
            "preferred_skills": preferred_skills,
            "soft_skills": sorted(list(soft_skills_found))[:5],
            
            # Detailed requirements
            "mandatory_requirements": mandatory_requirements[:5],  # Top 5
            "preferred_requirements": preferred_requirements[:3],   # Top 3
            "nice_to_have": nice_to_have_requirements[:2],          # Top 2
            
            # Job responsibilities
            "key_responsibilities": job_responsibilities[:4],  # Top 4
            
            # Skill categories
            "skill_categories": list(mandatory_skills_dict.keys()),
            
            # Full requirement breakdown for display
            "full_breakdown": {
                "mandatory": mandatory_requirements[:6],
                "preferred": preferred_requirements[:4],
                "nice_to_have": nice_to_have_requirements[:3],
                "responsibilities": job_responsibilities[:5]
            }
        }


def evaluate_job_match(job):
    # Requirements and Description
    req_html = job.get("requirements") or ""
    desc_html = job.get("description") or ""
    title = str(job.get("title") or "").lower()
    org_name = str(job.get("organization_name") or "").lower()
    
    req_text = clean_html(req_html)
    desc_text = clean_html(desc_html)
    full_text = (title + " " + org_name + " " + req_text + " " + desc_text).lower()
    
    # Scoring factors
    score = 0
    max_score = 100
    
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
    # Check if they request IT majors
    it_keywords = ["informatika", "ilmu komputer", "sistem informasi", "teknik komputer", "computer science", "software", "information technology", "telekomunikasi", "sistem & teknologi informasi", "backend", "fullstack", "full stack", "data analyst", "data scientist", "ai engineer", "machine learning", "engineer", "developer", "odoo", "web"]
    general_keywords = ["semua jurusan", "all major", "semua program studi", "diploma", "sarjana"]
    engineering_keywords = ["teknik", "engineering", "mipa", "sains", "matematika", "statistika"]
    
    major_score = 0
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
        # Check if the title is very specific to other fields (e.g. Geologist, Petroleum, Chemist, Akuntansi)
        non_it_specific = ["geologi", "geofisika", "perminyakan", "pertambangan", "akuntansi", "hukum", "keuangan", "petroleum", "geology", "geophysic", "accounting", "law"]
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
            # GPA doesn't match
            match_details["gpa"] = {
                "score": 0,
                "status": "No Match",
                "reason": f"Tidak Sesuai. IPK minimal yang diminta adalah {gpa_req:.2f}, sedangkan IPK Anda adalah {PROFILE['gpa']:.2f}."
            }
    else:
        # No GPA requirement found
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
        # Ravil is Male, so No Match
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
    # Check for direct Python/Data/IT development terms
    skills_found = [s for s in PROFILE["skills"] if s in full_text]
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
    # Check if the title or company matches "data", "analyst", "analis", "programmer", "developer", "it", "systems", "digital"
    # Also check if it matches Ravil's background at Pertamina Hulu Rokan (Upstream Oil & Gas)
    exp_req = parse_exp_req(req_text)
    
    exp_score = 0
    relevance_reasons = []
    
    role_keywords = ["data", "analyst", "analis", "scientist", "ai engineer", "machine learning", "programmer", "developer", "it", "systems", "digital", "informasi", "komputer", "teknologi", "fullstack", "web"]
    if any(kw in job.get("title", "").lower() for kw in role_keywords):
        exp_score += 5
        relevance_reasons.append("Peran ini di bidang Data / IT / Analis yang sesuai dengan spesialisasi pekerjaan Anda.")
        
    # Hulu Migas / Oil & Gas domain relevance
    hulu_migas_keywords = ["operasi", "operations", "production", "produksi", "reservoir", "lifting", "eksplorasi", "exploration", "drilling", "well", "log", "petrotechnical"]
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
            
    # Check if any hard blocker was failed (e.g. GPA, Age, Gender mismatch)
    is_blocked = (match_details["gpa"]["status"] == "No Match" or 
                  match_details["age"]["status"] == "No Match" or 
                  match_details["gender"]["status"] == "No Match")
    
    # If blocked, reduce match score to maximum of 40% (as warning) or penalize heavily
    final_score = score
    if is_blocked:
        # Cap match score at 40
        final_score = min(score, 40)
        
    nlp_breakdown = RequirementNLPParser.parse(job)
        
    job_details = {
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
            "experience": exp_req["level"],  # Use level string instead of years
            "exp_years": exp_req["years"]    # Extract years from dict
        },
        "source": job.get("source", "Talentics"),
        "logo": job.get("logo", None)
    }
    
    return job_details

def parse_location_from_text(text):
    if not text:
        return "Indonesia"
    text_clean = clean_html(text)
    cities = ["Jakarta", "Bandung", "Semarang", "Surabaya", "Denpasar", "Palembang", "Balikpapan", "Medan", "Makassar", "Yogyakarta", "Solo", "Malang"]
    found_cities = [city for city in cities if city.lower() in text_clean.lower()]
    if found_cities:
        return ", ".join(found_cities)
    return "Indonesia"

def format_astra_date(date_str):
    if not date_str:
        return None
    return date_str.replace("T", " ")

def get_astra_token():
    url = "https://careerservice.astra.co.id/api/v1/auth/login"
    payload = {
        "siteType": "FrontEnd",
        "lang": "ID"
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Referer": "https://career.astra.co.id/lowongan"
    }
    try:
        r = requests.post(url, data=payload, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get("token")
    except Exception as e:
        print(f"Error logging in to Astra: {e}")
    return None

def scrape_astra_listings(token):
    url = "https://careerservice.astra.co.id/api/v1/front-end/lowongan-page/ID"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Content-Type": "application/json",
        "Authorization": token,
        "Referer": "https://career.astra.co.id/lowongan",
        "Origin": "https://career.astra.co.id"
    }
    
    all_astra_raw = []
    page = 1
    total_pages = 1
    page_size = 12
    
    print("Fetching Astra jobs list...")
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
            r = requests.post(url, json=payload, headers=headers, timeout=10)
            if r.status_code == 200:
                data = r.json()
                if "vacancies" in data:
                    v_data = data["vacancies"]
                    total_rows = v_data.get("totalRows", 0)
                    total_pages = (total_rows + page_size - 1) // page_size
                    
                    jobs = v_data.get("data", [])
                    print(f"  Astra page {page}/{total_pages}: found {len(jobs)} jobs.")
                    all_astra_raw.extend(jobs)
                    
                    page += 1
                else:
                    break
            else:
                print(f"  Astra listing page {page} failed: {r.status_code}")
                break
        except Exception as e:
            print(f"  Exception fetching Astra listing page {page}: {e}")
            break
            
    return all_astra_raw

def fetch_astra_job_detail(vacancy_id, token):
    url = f"https://careerservice.astra.co.id/api/v1/front-end/lowongan-detail/{vacancy_id}/ID"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Authorization": token,
        "Referer": "https://career.astra.co.id/lowongan"
    }
    try:
        r = requests.get(url, headers=headers, timeout=10)
        if r.status_code == 200:
            return r.json().get("data")
    except Exception as e:
        print(f"Error fetching Astra vacancy detail {vacancy_id}: {e}")
    return None

def scrape_all_astra_details(raw_jobs, token):
    print(f"Fetching details for {len(raw_jobs)} Astra vacancies concurrently...")
    detailed_jobs = []
    
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_id = {executor.submit(fetch_astra_job_detail, job["vacancyId"], token): job for job in raw_jobs}
        
        for future in as_completed(future_to_id):
            raw_job = future_to_id[future]
            try:
                detail = future.result()
                if detail:
                    detailed_jobs.append(detail)
                else:
                    detailed_jobs.append(raw_job)
            except Exception as e:
                print(f"Exception fetching details for vacancy {raw_job.get('vacancyId')}: {e}")
                detailed_jobs.append(raw_job)
                
    return detailed_jobs

def scrape_pertamina_ptc(session):
    print("Fetching Pertamina Training & Consulting (PTC) vacancies...")
    url = "https://recruitment.pertamina-ptc.com/guest/joblist"
    ptc_jobs = []
    page = 1
    while page <= 10:
        try:
            params = {"page": page} if page > 1 else {}
            r = session.get(url, params=params, timeout=15)
            if r.status_code != 200:
                break
            soup = BeautifulSoup(r.text, 'html.parser')
            cards = soup.find_all("div", class_="card-view")
            if not cards:
                break
                
            new_found = 0
            for card in cards:
                heading_el = card.find("span", class_="text-primary")
                title = heading_el.get_text(strip=True) if heading_el else "Posisi PTC"
                
                code_match = re.search(r'\[([A-Z0-9]+)\]', title)
                job_id = code_match.group(1) if code_match else f"PTC-{len(ptc_jobs)+1}"
                
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
                            
                ptc_job = {
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
                }
                ptc_jobs.append(ptc_job)
                new_found += 1
                
            print(f"  PTC page {page}: found {new_found} jobs.")
            page += 1
            time.sleep(0.5)
        except Exception as e:
            print(f"  Exception fetching PTC page {page}: {e}")
            break
            
    seen_ids = set()
    unique_ptc_jobs = []
    for job in ptc_jobs:
        if job["id"] not in seen_ids:
            seen_ids.add(job["id"])
            unique_ptc_jobs.append(job)
    return unique_ptc_jobs

def fetch_sawitpro_job_detail(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        main = soup.find("main") or soup.body
        text_lines = [l.strip() for l in main.get_text("\n", strip=True).split("\n") if l.strip()]
        desc_lines = []
        for l in text_lines[:50]:
            desc_lines.append(f"<p>{l}</p>")
        return "".join(desc_lines)
    except Exception:
        return ""

def scrape_sawitpro(session):
    print("Fetching SawitPRO vacancies...")
    url = "https://www.sawitpro.id/jobs"
    try:
        r = session.get(url, timeout=15)
    except Exception as e:
        print(f"Error fetching SawitPRO jobs: {e}")
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
            elif any(w in title_l for w in ["lead", "manager", "head", "vp"]):
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
            
    print(f"Found {len(sawitpro_jobs)} SawitPRO jobs.")
    
    print(f"Fetching details for {len(sawitpro_jobs)} SawitPRO vacancies concurrently...")
    with ThreadPoolExecutor(max_workers=12) as executor:
        future_to_job = {executor.submit(fetch_sawitpro_job_detail, job["url"]): job for job in sawitpro_jobs}
        for future in as_completed(future_to_job):
            job = future_to_job[future]
            try:
                detail_html = future.result()
                if detail_html:
                    job["description"] = detail_html
                    job["requirements"] = detail_html
            except Exception:
                pass
                
    return sawitpro_jobs

def fetch_grab_job_detail(url):
    try:
        r = requests.get(url, timeout=10)
        soup = BeautifulSoup(r.text, "html.parser")
        main = soup.find("main") or soup.body
        text_lines = [l.strip() for l in main.get_text("\n", strip=True).split("\n") if l.strip()]
        desc_lines = []
        for line in text_lines:
            if any(k in line for k in ["Equal opportunity", "Featured Links", "Recruitment agencies"]):
                break
            desc_lines.append(line)
        return "<p>" + "</p><p>".join(desc_lines[:30]) + "</p>"
    except Exception:
        return ""

def scrape_grab_careers(session):
    print("Scraping Grab Careers Indonesia jobs...")
    grab_jobs = []
    url = "https://www.grab.careers/en/jobs/?search=&country=Indonesia&pagesize=50"
    try:
        r = session.get(url, timeout=15)
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
        print(f"Error scraping Grab Careers: {e}")
        
    print(f"Found {len(grab_jobs)} Grab Indonesia jobs.")
    print(f"Fetching details for {min(len(grab_jobs), 20)} Grab vacancies concurrently...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_job = {executor.submit(fetch_grab_job_detail, job["url"]): job for job in grab_jobs[:20]}
        for future in as_completed(future_to_job):
            job = future_to_job[future]
            try:
                detail_html = future.result()
                if detail_html:
                    job["description"] = detail_html
                    job["requirements"] = detail_html
            except Exception:
                pass
    return grab_jobs

def fetch_ioh_job_detail(url):
    try:
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        soup = BeautifulSoup(r.text, "html.parser")
        desc_el = soup.find(class_="jobdescription") or soup.find(class_="jobDisplay")
        if desc_el:
            return str(desc_el)
    except Exception:
        pass
    return ""

def scrape_ioh_careers(session):
    print("Scraping Indosat Ooredoo Hutchison (IOH) Careers...")
    ioh_jobs = []
    seen = set()
    try:
        for start in range(0, 150, 10):
            r = session.get(f"https://careers.ioh.co.id/search/?q=&startrow={start}", timeout=15)
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
        print(f"Error scraping IOH Careers: {e}")
        
    print(f"Found {len(ioh_jobs)} Indosat Ooredoo Hutchison jobs.")
    print(f"Fetching details for {len(ioh_jobs)} IOH vacancies concurrently...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        future_to_job = {executor.submit(fetch_ioh_job_detail, job["url"]): job for job in ioh_jobs}
        for future in as_completed(future_to_job):
            job = future_to_job[future]
            try:
                detail_html = future.result()
                if detail_html:
                    job["description"] = detail_html
                    job["requirements"] = detail_html
            except Exception:
                pass
    return ioh_jobs

def scrape_indofood_careers(session):
    print("Scraping Indofood Careers vacancies...")
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
            }
        )
        if r.status_code == 200:
            d_val = r.json().get("d", "")
            if "[space2]" in d_val:
                _, data_part = d_val.split("[space2]")
                data_json = json.loads(data_part)
                vacancies = data_json.get("ListAdvFilterJob", [])
                print(f"Retrieved {len(vacancies)} jobs from Indofood Careers.")
                
                for v in vacancies:
                    # Clean desc & requirements
                    desc_html = v.get("JobDesc", "") or ""
                    req_html = v.get("JobReq", "") or ""
                    
                    job_entry = {
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
                    }
                    indofood_jobs.append(job_entry)
            else:
                print("Failed to find [space2] separator in Indofood response.")
        else:
            print(f"Error calling Indofood API: {r.status_code}")
    except Exception as e:
        print(f"Exception during Indofood scraping: {e}")
        
    return indofood_jobs


def scrape_linkedin_jobs(session, max_per_keyword=10):
    """
    Scrape LinkedIn jobs via LinkedIn guest API.
    Endpoints:
    - Search: https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search
    - Detail: https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{job_id}
    """
    print("\n  Scraping LinkedIn Jobs (Data Science, AI, Python, IT Support in Indonesia)...")
    keywords = ["Data Scientist", "Data Analyst", "Machine Learning", "Python Developer", "IT Support"]
    found_cards = []
    seen_ids = set()

    for kw in keywords:
        url = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
        params = {"keywords": kw, "location": "Indonesia", "start": 0}
        try:
            r = session.get(url, params=params, timeout=12)
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
                print(f"    [+] '{kw}': found {count} listings")
            elif r.status_code == 429:
                print(f"    [!] Rate limited (429) on LinkedIn for '{kw}'. Pausing 10s...")
                time.sleep(10)
            else:
                print(f"    [-] '{kw}': HTTP {r.status_code}")
        except Exception as e:
            print(f"    [!] Error searching LinkedIn for '{kw}': {e}")
        time.sleep(1)

    print(f"    Fetching job descriptions for {len(found_cards)} LinkedIn roles concurrently...")
    
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
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(fetch_linkedin_detail, card) for card in found_cards]
        for f in as_completed(futures):
            detailed_jobs.append(f.result())

    print(f"    ✓ Successfully scraped {len(detailed_jobs)} LinkedIn jobs.")
    return detailed_jobs


def scrape_opentrain_jobs(session):
    """
    Scrape remote AI training & coding jobs dari OpenTrain.ai kategori IT/AI.
    Menggunakan HTTP requests langsung & Schema.org JobPosting extraction (cepat & tanpa Selenium).
    """
    print("\n  Scraping OpenTrain.ai jobs (Coding, Generative AI & Data Annotation)...")
    cat_urls = [
        "https://www.opentrain.ai/jobs/category/coding-software/",
        "https://www.opentrain.ai/jobs/category/generative-ai-rlhf/",
        "https://www.opentrain.ai/jobs/data-annotation/"
    ]
    
    job_links = []
    seen_urls = set()
    for cat_url in cat_urls:
        try:
            r = session.get(cat_url, timeout=12)
            if r.status_code == 200:
                soup = BeautifulSoup(r.text, 'html.parser')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if href.startswith('/jobs/') and not href.startswith('/jobs/category') and not href.startswith('/jobs/location') and href != '/jobs/' and not '?apply=' in href:
                        full_url = 'https://www.opentrain.ai' + href
                        title = a.get_text(' ', strip=True)
                        if full_url not in seen_urls and title and title != 'View job':
                            seen_urls.add(full_url)
                            job_links.append({'title': title, 'url': full_url})
        except Exception as e:
            print(f"    Error fetching OpenTrain category {cat_url}: {e}")
            
    print(f"    Found {len(job_links)} OpenTrain roles. Fetching details concurrently...")
    
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
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(fetch_opentrain_detail, job) for job in job_links]
        for f in as_completed(futures):
            res = f.result()
            if res:
                detailed_jobs.append(res)
                
    print(f"    ✓ Successfully scraped {len(detailed_jobs)} OpenTrain jobs.")
    return detailed_jobs


def scrape_micro1_jobs(session):
    """
    Scrape remote software & AI jobs dari micro1 (microonejobs.com).
    """
    print("\n  Scraping micro1 remote jobs...")
    url = "https://microonejobs.com/jobs"
    jobs = []
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
                    if any(role in p for role in ['Engineer', 'Developer', 'Designer', 'Marketer', 'Analyst']):
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
                
                # Fetch job detail
                desc = ''
                try:
                    r_det = session.get(full_url, timeout=8)
                    if r_det.status_code == 200:
                        soup_det = BeautifulSoup(r_det.text, 'html.parser')
                        main_content = soup_det.find('main') or soup_det.find('article') or soup_det.body
                        if main_content:
                            desc = main_content.get_text('\n', strip=True)
                except Exception:
                    pass
                
                desc_text = (desc or title) + (f"\nSalary: {salary}" if salary else "")
                jobs.append({
                    'id': f"micro1_{slug}",
                    'title': title,
                    'organization_name': company,
                    'location': location,
                    'workplace': 'Work From Home (Remote)',
                    'due_date': 'Active',
                    'group': 'Engineering & Tech',
                    'url': full_url,
                    'description': desc_text,
                    'requirements': 'Software Engineering, Remote, Problem Solving, Fullstack/Backend/Frontend/AI',
                    'type_name': 'Full Time / Remote',
                    'source': 'micro1'
                })
    except Exception as e:
        print(f"    Warning: micro1 scrape error: {e}")
        
    print(f"    ✓ Successfully scraped {len(jobs)} micro1 jobs.")
    return jobs


def scrape_with_firecrawl(url, format_output="markdown"):
    """
    Gunakan Firecrawl untuk extract clean data dari URL.
    Lebih powerful untuk handle dynamic content dan complex HTML.
    """
    if FirecrawlApp is None:
        return None
        
    try:
        api_key = os.getenv("FIRECRAWL_API_KEY")
        if not api_key:
            return None
            
        app = FirecrawlApp(api_key=api_key)
        # Mendukung Firecrawl v4+ (keyword args) dan versi lawas (dictionary options)
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


def scrape_with_jobspy(job_title, location="", max_results=50):
    """
    Gunakan JobSpy untuk aggregate jobs dari LinkedIn.
    
    Note: Indeed & Glassdoor have anti-bot protection (403/KeyError).
    LinkedIn adalah sumber paling stabil dan reliable.
    """
    if scrape_jobs is None:
        return []
        
    try:
        # Try LinkedIn first (most reliable)
        print(f"  Scraping LinkedIn via JobSpy for '{job_title}'...")
        
        # Specify encoding to avoid charmap errors
        import sys
        original_encoding = sys.stdout.encoding
        
        jobs = scrape_jobs(
            site_name=["linkedin"],  # LinkedIn only - most stable
            search_term=job_title,
            location=location,
            results_wanted=max_results,
        )
        
        if len(jobs) > 0:
            print(f"    ✓ Found {len(jobs)} jobs from LinkedIn")
        else:
            print(f"    No jobs found on LinkedIn")
        
        # Convert to our format (handle encoding properly)
        normalized_jobs = []
        for idx, job in jobs.iterrows():
            try:
                normalized_job = {
                    "id": hash(str(job.get("job_url", "")) + str(job.get("title", ""))),
                    "title": str(job.get("title", "")).encode('utf-8', errors='ignore').decode('utf-8'),
                    "organization_name": str(job.get("company", "")).encode('utf-8', errors='ignore').decode('utf-8'),
                    "location": str(job.get("location", "")).encode('utf-8', errors='ignore').decode('utf-8'),
                    "workplace": "Unknown",
                    "due_date": str(job.get("date_posted", "")),
                    "group": str(job.get("job_type", "")),
                    "url": str(job.get("job_url", "")),
                    "description": str(job.get("description", "") or job.get("job_description", "")).encode('utf-8', errors='ignore').decode('utf-8')[:500],
                    "requirements": str(job.get("description", "") or job.get("job_description", "")).encode('utf-8', errors='ignore').decode('utf-8')[:500],
                    "salary_min": job.get("min_amount"),
                    "salary_max": job.get("max_amount"),
                    "source": "JobSpy (LinkedIn)",
                }
                normalized_jobs.append(normalized_job)
            except Exception as inner_e:
                print(f"    Warning: Skipped 1 job due to encoding: {inner_e}")
                continue
            
        return normalized_jobs
    except Exception as e:
        import traceback
        error_msg = str(e)[:80]
        print(f"  ⚠️  JobSpy error: {type(e).__name__}: {error_msg}")
        # print(traceback.format_exc())
        return []


def main():
    session = requests.Session()
    session.headers.update({
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    })

    print("Step 1: Establishing session and fetching CSRF token...")
    url_main = "https://jobs.talentics.id/jobs?search=rekrutmen%20hulu%20migas"
    try:
        r_main = session.get(url_main)
        if r_main.status_code != 200:
            print(f"Failed to fetch main page: {r_main.status_code}")
            return
    except Exception as e:
        print(f"Error fetching main page: {e}")
        return

    soup = BeautifulSoup(r_main.text, 'html.parser')
    meta_csrf = soup.find('meta', attrs={'name': 'csrf-token'})
    csrf_token = meta_csrf.get('content') if meta_csrf else None
    
    if not csrf_token:
        print("Warning: CSRF token not found. Requests might fail.")
    else:
        print(f"CSRF Token obtained: {csrf_token}")

    ajax_url = "https://jobs.talentics.id/ajaxs/jobs"
    ajax_headers = {
        "Accept": "application/json, text/plain, */*",
        "Referer": url_main,
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRF-TOKEN": csrf_token
    }

    all_jobs_raw = []
    page = 1
    last_page = 1

    print("\nStep 2: Scraping Hulu Migas (Talentics) job search pages...")
    while page <= last_page:
        print(f"Fetching page {page} of {last_page}...")
        params = {
            "search": "rekrutmen hulu migas",
            "page": page
        }
        try:
            r_ajax = session.get(ajax_url, params=params, headers=ajax_headers)
            if r_ajax.status_code == 200:
                res_data = r_ajax.json()
                last_page = res_data.get("last_page", last_page)
                jobs_data = res_data.get("data", [])
                print(f"  Retrieved {len(jobs_data)} jobs.")
                all_jobs_raw.extend(jobs_data)
                page += 1
                time.sleep(0.5)
            else:
                print(f"  Error fetching page {page}: {r_ajax.status_code}")
                break
        except Exception as e:
            print(f"  Exception fetching page {page}: {e}")
            break

    print(f"\nTotal raw Hulu Migas jobs fetched: {len(all_jobs_raw)}")

    def fetch_talentics_detail(raw_job):
        """Fetch & parse detail satu job Talentics. Dipakai secara concurrent."""
        org_slug = raw_job.get("organization", {}).get("slug", "skk-migas")
        job_slug = raw_job.get("slug")
        detail_url = f"https://jobs.talentics.id/{org_slug}/{job_slug}"
        try:
            r_detail = session.get(detail_url, timeout=15)
            if r_detail.status_code == 200:
                text = r_detail.text
                match = re.search(r'job:\s*(\{.*)', text, re.DOTALL)
                if match:
                    content = match.group(1)
                    brace_count = 0
                    json_str = ""
                    for char in content:
                        if char == '{':
                            brace_count += 1
                        elif char == '}':
                            brace_count -= 1
                        json_str += char
                        if brace_count == 0:
                            break
                    try:
                        return json.loads(json_str)
                    except Exception:
                        pass
        except Exception as de:
            print(f"  Exception fetching Talentics detail for '{raw_job.get('title')}': {de}")
        return raw_job  # fallback: gunakan data raw tanpa detail

    print("\nStep 3: Fetching detailed information for Hulu Migas jobs concurrently...")
    matched_jobs = []
    with ThreadPoolExecutor(max_workers=8) as executor:
        future_to_raw = {executor.submit(fetch_talentics_detail, raw_job): raw_job for raw_job in all_jobs_raw}
        done_count = 0
        for future in as_completed(future_to_raw):
            raw_job = future_to_raw[future]
            done_count += 1
            try:
                job_detail = future.result()
                matched_job = evaluate_job_match(job_detail)
            except Exception as ex:
                print(f"  Error evaluating job '{raw_job.get('title')}': {ex}")
                matched_job = evaluate_job_match(raw_job)
            matched_jobs.append(matched_job)
            if done_count % 10 == 0 or done_count == len(all_jobs_raw):
                print(f"  [{done_count}/{len(all_jobs_raw)}] Talentics jobs processed...")

    print("\nStep 3a: Logging in to Astra Careers and scraping vacancies...")
    astra_token = get_astra_token()
    if astra_token:
        raw_astra_jobs = scrape_astra_listings(astra_token)
        print(f"Found {len(raw_astra_jobs)} Astra jobs.")
        
        # Concurrently fetch detailed requirement & descriptions
        detailed_astra_jobs = scrape_all_astra_details(raw_astra_jobs, astra_token)
        
        print("\nStep 3b: Normalizing and evaluating Astra jobs...")
        for job in detailed_astra_jobs:
            req_text = job.get("requirement", "") or ""
            desc_text = job.get("description", "") or ""
            
            normalized_job = {
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
            }
            
            matched_job = evaluate_job_match(normalized_job)
            matched_jobs.append(matched_job)
    else:
        print("Warning: Skipping Astra Careers scraping because guest login failed.")

    print("\nStep 3c: Scraping Pertamina Training & Consulting (PTC) vacancies...")
    ptc_jobs = scrape_pertamina_ptc(session)
    print(f"Found {len(ptc_jobs)} Pertamina PTC jobs.")
    for job in ptc_jobs:
        matched_job = evaluate_job_match(job)
        matched_jobs.append(matched_job)

    print("\nStep 3d: Scraping SawitPRO vacancies...")
    sawitpro_jobs = scrape_sawitpro(session)
    for job in sawitpro_jobs:
        matched_job = evaluate_job_match(job)
        matched_jobs.append(matched_job)

    print("\nStep 3e: Scraping Grab Careers Indonesia vacancies...")
    grab_jobs = scrape_grab_careers(session)
    for job in grab_jobs:
        matched_job = evaluate_job_match(job)
        matched_jobs.append(matched_job)

    print("\nStep 3f: Scraping Indosat Ooredoo Hutchison (IOH) vacancies...")
    ioh_jobs = scrape_ioh_careers(session)
    for job in ioh_jobs:
        matched_job = evaluate_job_match(job)
        matched_jobs.append(matched_job)

    print("\nStep 3g: Scraping Indofood Careers vacancies...")
    indofood_jobs = scrape_indofood_careers(session)
    for job in indofood_jobs:
        matched_job = evaluate_job_match(job)
        matched_jobs.append(matched_job)

    print("\nStep 3h: Scraping OpenTrain.ai AI Training Jobs...")
    opentrain_jobs = scrape_opentrain_jobs(session)
    for job in opentrain_jobs:
        matched_job = evaluate_job_match(job)
        matched_jobs.append(matched_job)

    print("\nStep 3i: Scraping micro1 Remote Jobs...")
    micro1_jobs = scrape_micro1_jobs(session)
    for job in micro1_jobs:
        matched_job = evaluate_job_match(job)
        matched_jobs.append(matched_job)

    print("\nStep 3j: Scraping LinkedIn Jobs...")
    linkedin_jobs = scrape_linkedin_jobs(session, max_per_keyword=10)
    for job in linkedin_jobs:
        matched_job = evaluate_job_match(job)
        matched_jobs.append(matched_job)

    # Sort matched jobs by match score (highest first), placing blocked jobs at the end
    matched_jobs.sort(key=lambda x: (0 if x["is_blocked"] else 1, x["match_score"]), reverse=True)

    # Filter to only keep jobs with IT major (High Match) or All Majors (Match)
    filtered_jobs = [job for job in matched_jobs if job["match_details"]["major"]["status"] in ["High Match", "Match"]]
    print(f"Filtered out {len(matched_jobs) - len(filtered_jobs)} jobs that do not match major requirements (IT or All Majors).")
    matched_jobs = filtered_jobs

    print("\nStep 4: Writing output files...")
    save_jobs(matched_jobs)
    print(f"Berhasil memproses {len(matched_jobs)} lowongan!")

if __name__ == "__main__":
    main()
