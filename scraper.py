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

# ─── Konstanta bersama (dipakai scraper, rescore, add_job_entry) ───────────────
MONTHS_ID = {
    1: "Januari", 2: "Februari", 3: "Maret", 4: "April", 5: "Mei", 6: "Juni",
    7: "Juli", 8: "Agustus", 9: "September", 10: "Oktober", 11: "November", 12: "Desember"
}

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

# ⚠️ SECURITY: Load sensitive profile data from .env file, NOT hardcoded
import os
from dotenv import load_dotenv
load_dotenv()

# User Profile definition (load dari .env untuk security)
PROFILE = {
    "name": os.getenv("USER_NAME", "Muhammad Ravil"),
    "email": os.getenv("USER_EMAIL", ""),  # Load dari .env, jangan hardcode
    "phone": os.getenv("USER_PHONE", ""),  # Load dari .env
    "location": os.getenv("USER_LOCATION", "Pekanbaru, Riau"),
    "linkedin": os.getenv("USER_LINKEDIN", "linkedin.com/in/Muhammad-ravil"),
    "gender": "Laki-laki",
    "age": 23,  # born 10 August 2002 (current year 2026)
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
        "AI Engineer di PT Pertamina Hulu Rokan (Upstream Oil & Gas, Jul 2025–Feb 2026); "
        "Data Scientist Intern Id/x partners x Rakamin Academy (Apr–Mei 2025, Best Student 86.96); "
        "Freelance Web Dev & Machine Learning (2025–Sekarang)"
    ),
    "exp_years": 1
}

def clean_html(raw_html):
    if not raw_html:
        return ""
    # Remove HTML tags
    cleanr = re.compile('<.*?>')
    cleantext = re.sub(cleanr, ' ', raw_html)
    # Replace multiple spaces/newlines
    cleantext = re.sub(r'\s+', ' ', cleantext)
    return cleantext.strip()

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
    req_html = job.get("requirements", "")
    desc_html = job.get("description", "")
    title = job.get("title", "").lower()
    org_name = job.get("organization_name", "").lower()
    
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
        
    if exp_req <= PROFILE["exp_years"]:
        match_details["exp_years"] = {
            "status": "Match",
            "reason": f"Sesuai. Lowongan meminta minimal {exp_req} tahun pengalaman, sedangkan pengalaman kamu adalah {PROFILE['exp_years']} tahun." if exp_req > 0 else "Sesuai. Terbuka untuk Fresh Graduate / pengalaman ≤ 1 tahun."
        }
    else:
        match_details["exp_years"] = {
            "status": "Low Match",
            "reason": f"Perlu Perhatian: Lowongan meminta pengalaman minimal {exp_req} tahun, sedangkan pengalaman kamu saat ini {PROFILE['exp_years']} tahun."
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
            "experience": f"Minimal {exp_req} tahun" if exp_req > 0 else "Terbuka untuk Fresh Graduate",
            "exp_years": exp_req
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
        "Referer": "https://career.astra.co.id/lowongan"
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
            "CategoryType": 0,
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


def scrape_linkedin_jobs(session, max_jobs=300):
    """
    Scrape LinkedIn jobs dengan safe rate-limiting.
    Safety features:
    - 2-5 detik delay antar request
    - Max 300 jobs per run (avoid rate limit 403)
    - Filter location: Indonesia only
    - User-Agent rotation
    - Graceful error handling
    
    NOTE: LinkedIn actively blocks scrapers. This function gracefully handles:
    - 403 Forbidden → Stop without ban
    - 429 Too Many Requests → Backoff 30 sec
    - 404 Not Found → Skip (endpoint unavailable)
    
    ALTERNATIVE: If LinkedIn scraping fails consistently, manual search + export CSV
    from LinkedIn Jobs is recommended (legal, authorized by LinkedIn).
    """
    print("Scraping LinkedIn Jobs vacancies (Indonesia) dengan safe rate-limiting...")
    linkedin_jobs = []
    
    # Safe User-Agent rotation
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    ]
    
    try:
        # Try multiple LinkedIn public endpoints (if one fails, try next)
        endpoints = [
            {
                "url": "https://www.linkedin.com/jobs-guest/jobs/api/jobs",
                "params_template": {"keywords": "data analyst", "location": "Indonesia", "start": 0, "count": 25}
            },
            {
                "url": "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting",
                "params_template": {"keywords": "data analyst", "location": "Indonesia", "start": 0, "count": 25}
            }
        ]
        
        seen_job_ids = set()
        page_count = 0
        max_pages = (max_jobs // 25) + 1
        
        print(f"Fetching LinkedIn jobs dengan location filter: Indonesia, max pages: {max_pages}")
        
        endpoint_idx = 0
        current_endpoint = endpoints[endpoint_idx]
        
        while page_count < max_pages and len(linkedin_jobs) < max_jobs and endpoint_idx < len(endpoints):
            try:
                # Rate limiting: 2-5 detik delay
                delay = 2 + (page_count % 3) * 1
                time.sleep(delay)
                
                # User-Agent rotation
                ua = user_agents[page_count % len(user_agents)]
                session.headers.update({"User-Agent": ua})
                
                params = current_endpoint["params_template"].copy()
                params["start"] = page_count * 25
                
                print(f"  LinkedIn page {page_count + 1}: fetching with 2-5sec delay...")
                r = session.get(current_endpoint["url"], params=params, timeout=15)
                
                if r.status_code == 200:
                    # Parse response (dapat HTML atau JSON tergantung endpoint)
                    try:
                        soup = BeautifulSoup(r.text, "html.parser")
                        job_cards = soup.find_all("div", class_="base-card")
                        
                        if not job_cards:
                            # Try alternate selectors
                            job_cards = soup.find_all("li", class_="base-list-item")
                        
                        if not job_cards:
                            print(f"  No more LinkedIn jobs found. Stopping.")
                            break
                        
                        new_found = 0
                        for card in job_cards:
                            try:
                                # Extract job info
                                title_el = card.find("h3", class_="base-search-card__title") or card.find("span", class_="job-card-title")
                                title = title_el.get_text(strip=True) if title_el else "LinkedIn Position"
                                
                                company_el = card.find("h4", class_="base-search-card__subtitle") or card.find("span", class_="job-card-company-name")
                                company = company_el.get_text(strip=True) if company_el else "Unknown Company"
                                
                                link_el = card.find("a", class_="base-card__full-link") or card.find("a", class_="base-card__permalink")
                                job_url = link_el["href"] if link_el and "href" in link_el.attrs else ""
                                
                                loc_el = card.find("span", class_="job-search-card__location")
                                location = loc_el.get_text(strip=True) if loc_el else "Indonesia"
                                
                                # Extract job ID
                                job_id = f"linkedin_{len(linkedin_jobs)}"
                                if job_url:
                                    url_match = re.search(r"/(\d{10,})", job_url)
                                    if url_match:
                                        job_id = f"linkedin_{url_match.group(1)}"
                                
                                if job_id in seen_job_ids:
                                    continue
                                
                                seen_job_ids.add(job_id)
                                
                                linkedin_jobs.append({
                                    "id": job_id,
                                    "title": title,
                                    "organization_id": "LinkedIn",
                                    "organization_name": company,
                                    "slug": f"linkedin-{len(linkedin_jobs)}",
                                    "type_name": "Full Time / Contract",
                                    "level": "Profesional",
                                    "location": location,
                                    "workplace": "Hybrid / WFO",
                                    "due_date": "Aktif",
                                    "group": "Tech & Data",
                                    "url": job_url,
                                    "description": f"<p><strong>{title}</strong></p><p>Perusahaan: {company}</p><p>Lokasi: {location}</p>",
                                    "requirements": f"<p><strong>{title}</strong></p><p>Perusahaan: {company}</p><p>Lokasi: {location}</p>",
                                    "source": "LinkedIn",
                                    "logo": None
                                })
                                new_found += 1
                                
                            except Exception as e:
                                print(f"    Exception parsing LinkedIn job card: {e}")
                                continue
                        
                        if new_found == 0:
                            print(f"  No new jobs found on LinkedIn page {page_count + 1}. Stopping.")
                            break
                        
                        print(f"  LinkedIn page {page_count + 1}: found {new_found} new jobs (total: {len(linkedin_jobs)})")
                        page_count += 1
                        
                    except Exception as parse_err:
                        print(f"  Error parsing LinkedIn response: {parse_err}. Trying next endpoint...")
                        endpoint_idx += 1
                        if endpoint_idx < len(endpoints):
                            current_endpoint = endpoints[endpoint_idx]
                        break
                        
                elif r.status_code == 429:
                    print(f"  LinkedIn rate limit (429). Waiting 30 seconds...")
                    time.sleep(30)
                    continue
                    
                elif r.status_code == 403:
                    print(f"  LinkedIn forbidden (403). Skipping LinkedIn scraping to avoid ban.")
                    break
                    
                elif r.status_code == 404:
                    print(f"  LinkedIn endpoint not found (404). Trying alternate endpoint...")
                    endpoint_idx += 1
                    if endpoint_idx < len(endpoints):
                        current_endpoint = endpoints[endpoint_idx]
                        page_count = 0  # Reset page for new endpoint
                    break
                    
                else:
                    print(f"  LinkedIn request failed: {r.status_code}. Stopping.")
                    break
                    
            except Exception as e:
                print(f"  Exception fetching LinkedIn page {page_count}: {e}")
                break
        
        print(f"Total LinkedIn jobs scraped: {len(linkedin_jobs)} (max: {max_jobs})")
        
    except Exception as e:
        print(f"Error during LinkedIn scraping: {e}")
    
    return linkedin_jobs


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
    
    print("\nStep 3: Fetching detailed information for each Hulu Migas job and matching...")
    matched_jobs = []
    for idx, raw_job in enumerate(all_jobs_raw):
        job_title = raw_job.get("title")
        org_slug = raw_job.get("organization", {}).get("slug", "skk-migas")
        job_slug = raw_job.get("slug")
        
        detail_url = f"https://jobs.talentics.id/{org_slug}/{job_slug}"
        print(f"[{idx+1}/{len(all_jobs_raw)}] Fetching details for: {job_title}")
        
        try:
            r_detail = session.get(detail_url)
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
                        job_detail = json.loads(json_str)
                        matched_job = evaluate_job_match(job_detail)
                        matched_jobs.append(matched_job)
                    except Exception as je:
                        print(f"  Error parsing detail JSON: {je}")
                        matched_job = evaluate_job_match(raw_job)
                        matched_jobs.append(matched_job)
                else:
                    print("  Warning: Inline JSON job data not found.")
                    matched_job = evaluate_job_match(raw_job)
                    matched_jobs.append(matched_job)
            else:
                print(f"  Failed to load detail page. Status code: {r_detail.status_code}")
                matched_job = evaluate_job_match(raw_job)
                matched_jobs.append(matched_job)
        except Exception as de:
            print(f"  Exception fetching details: {de}")
            matched_job = evaluate_job_match(raw_job)
            matched_jobs.append(matched_job)
            
        time.sleep(0.5)

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

    print("\nStep 3h: Scraping LinkedIn Jobs vacancies (safe rate-limiting)...")
    # Note: LinkedIn actively blocks scrapers. For production:
    # Option 1: Manual search on LinkedIn Jobs + Export CSV → import ke system
    # Option 2: Use LinkedIn Recruiter API (requires authorization)
    # Option 3: Skip LinkedIn, focus on 7 stable portals (current approach)
    # linkedin_jobs = scrape_linkedin_jobs(session, max_jobs=300)
    # for job in linkedin_jobs:
    #     matched_job = evaluate_job_match(job)
    #     matched_jobs.append(matched_job)
    print("  LinkedIn scraping skipped (anti-bot protection active). Use manual export instead.")

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
