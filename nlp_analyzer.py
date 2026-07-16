"""
Enhanced NLP Analyzer for Job Requirements & Automatic Cover Letter Generation.
Separate module untuk better requirement understanding dan professional cover letter creation.
"""

import re
from dotenv import load_dotenv
import os

load_dotenv()

# User Profile
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
    "experience": (
        "AI Engineer di PT Pertamina Hulu Rokan (Upstream Oil & Gas, Jul 2025–Feb 2026); "
        "Data Scientist Intern Id/x partners x Rakamin Academy (Apr–Mei 2025, Best Student 86.96); "
        "Freelance Web Dev & Machine Learning (2025–Sekarang)"
    ),
    "exp_years": 1
}


class RequirementAnalyzer:
    """Analyze job requirements dengan semantic understanding"""
    
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
    def classify_sentence(cls, sentence_lower):
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
        return "description"
    
    @classmethod
    def extract_skills(cls, text_lower):
        """Extract skills dari text dengan category"""
        found_skills = {}
        for category, skills in cls.SKILL_TAXONOMY.items():
            category_skills = []
            for sk in skills:
                pattern = r'\b' + re.escape(sk.lower()) + r'\b'
                if re.search(pattern, text_lower):
                    category_skills.append(sk)
            if category_skills:
                found_skills[category] = category_skills
        return found_skills
    
    @classmethod
    def extract_soft_skills(cls, text_lower):
        """Extract soft skills"""
        found = []
        for skill in cls.SOFT_SKILLS:
            if skill in text_lower:
                found.append(skill.title())
        return found
    
    @classmethod
    def analyze(cls, raw_requirements):
        """Analyze requirements dan return structured breakdown"""
        text = raw_requirements.lower()
        sentences = [s.strip() for s in re.split(r'[\n•\-\*.]+', text) if len(s.strip()) > 15]
        
        breakdown = {
            "mandatory_requirements": [],
            "preferred_requirements": [],
            "nice_to_have": [],
            "responsibilities": [],
            "all_skills": cls.extract_skills(text),
            "soft_skills": list(set(cls.extract_soft_skills(text))),
            "skill_count": sum(len(v) for v in cls.extract_skills(text).values())
        }
        
        for sent in sentences:
            sent_lower = sent.lower()
            sent_type = cls.classify_sentence(sent_lower)
            
            if sent_type == "mandatory" and len(breakdown["mandatory_requirements"]) < 6:
                breakdown["mandatory_requirements"].append(sent.strip())
            elif sent_type == "preferred" and len(breakdown["preferred_requirements"]) < 4:
                breakdown["preferred_requirements"].append(sent.strip())
            elif sent_type == "nice_to_have" and len(breakdown["nice_to_have"]) < 3:
                breakdown["nice_to_have"].append(sent.strip())
            elif sent_type == "responsibility" and len(breakdown["responsibilities"]) < 5:
                breakdown["responsibilities"].append(sent.strip())
        
        return breakdown


class CoverLetterGenerator:
    """Generate professional, personalized cover letter"""
    
    @staticmethod
    def get_matched_skills(required_skills_str):
        """Match profile skills dengan required skills"""
        profile_skills_lower = [s.lower() for s in PROFILE["skills"]]
        matched = []
        
        for skill in required_skills_str.split(", ") if isinstance(required_skills_str, str) else required_skills_str:
            skill_lower = skill.lower()
            if any(ps in skill_lower or skill_lower in ps for ps in profile_skills_lower):
                matched.append(skill)
        
        return matched[:5]
    
    @staticmethod
    def generate(job_title, company_name, requirements_breakdown):
        """Generate cover letter based on job requirements"""
        profile_name = PROFILE["name"]
        profile_location = PROFILE["location"]
        profile_exp = PROFILE["experience"]
        
        # Get all skills from breakdown
        all_skills = []
        for category, skills in requirements_breakdown.get("all_skills", {}).items():
            all_skills.extend(skills)
        
        matched_skills = CoverLetterGenerator.get_matched_skills(all_skills)
        soft_skills = requirements_breakdown.get("soft_skills", [])[:2]
        
        # Build cover letter
        skills_str = ", ".join(matched_skills) if matched_skills else ", ".join(all_skills[:3])
        soft_skills_str = " and ".join(soft_skills) if soft_skills else "teamwork and problem-solving"
        
        cover_letter = f"""Dear Hiring Team at {company_name},

I am writing to express my strong interest in the {job_title} position at {company_name}. With my background in {skills_str}, combined with 1 year of professional experience as an AI Engineer at PT Pertamina Hulu Rokan, I am confident that I can contribute significantly to your team.

In my current role, I have developed expertise in {skills_str}, which directly aligns with your requirements. My experience includes data analysis, machine learning implementation, and end-to-end project development. I have successfully applied these techniques to solve complex business problems, resulting in actionable insights for stakeholders.

Beyond technical skills, I bring strong {soft_skills_str} abilities. I am adaptable, detail-oriented, and committed to continuous learning. I thrive in collaborative environments and am eager to contribute to {company_name}'s mission.

I am enthusiastic about the opportunity to bring my expertise and passion to your organization. Thank you for considering my application. I look forward to discussing how I can add value to {company_name}.

Sincerely,
{profile_name}
{profile_location}
"""
        
        return {
            "cover_letter": cover_letter.strip(),
            "matched_skills": matched_skills,
            "soft_skills_highlighted": soft_skills,
            "key_points": {
                "matched_skills_count": len(matched_skills),
                "total_skills": len(all_skills),
                "soft_skills_count": len(soft_skills)
            }
        }


def analyze_and_generate(job_title, company_name, raw_requirements):
    """Convenience function: analyze requirements + generate cover letter"""
    analysis = RequirementAnalyzer.analyze(raw_requirements)
    cover_letter_data = CoverLetterGenerator.generate(job_title, company_name, analysis)
    
    return {
        "analysis": analysis,
        "cover_letter": cover_letter_data
    }


class RequirementFormatter:
    """Format requirements menjadi HTML yang cantik untuk UI display"""
    
    @staticmethod
    def format_requirements_html(analysis):
        """Format requirement analysis menjadi HTML sections"""
        html = '<div class="requirements-container">\n'
        
        # Mandatory requirements section
        if analysis.get("mandatory_requirements"):
            html += '  <div class="requirement-section mandatory">\n'
            html += '    <h4 class="section-title">[WAJIB] Persyaratan Wajib</h4>\n'
            html += '    <ul class="requirement-list">\n'
            for req in analysis["mandatory_requirements"][:5]:
                html += f'      <li>{req}</li>\n'
            html += '    </ul>\n'
            html += '  </div>\n'
        
        # Preferred requirements section
        if analysis.get("preferred_requirements"):
            html += '  <div class="requirement-section preferred">\n'
            html += '    <h4 class="section-title">[DIUTAMAKAN] Persyaratan Diutamakan</h4>\n'
            html += '    <ul class="requirement-list">\n'
            for req in analysis["preferred_requirements"][:4]:
                html += f'      <li>{req}</li>\n'
            html += '    </ul>\n'
            html += '  </div>\n'
        
        # Nice to have section
        if analysis.get("nice_to_have"):
            html += '  <div class="requirement-section nice-to-have">\n'
            html += '    <h4 class="section-title">[PLUS] Nilai Tambah</h4>\n'
            html += '    <ul class="requirement-list">\n'
            for req in analysis["nice_to_have"][:3]:
                html += f'      <li>{req}</li>\n'
            html += '    </ul>\n'
            html += '  </div>\n'
        
        # Skills section (by category)
        if analysis.get("all_skills"):
            html += '  <div class="requirement-section skills">\n'
            html += '    <h4 class="section-title">[SKILLS] Skills yang Diperlukan</h4>\n'
            for category, skills in analysis["all_skills"].items():
                html += f'    <div class="skill-category">\n'
                html += f'      <span class="category-name">{category}:</span>\n'
                html += f'      <div class="skill-tags">\n'
                for skill in skills:
                    html += f'        <span class="skill-tag">{skill}</span>\n'
                html += f'      </div>\n'
                html += f'    </div>\n'
            html += '  </div>\n'
        
        # Soft skills section
        if analysis.get("soft_skills"):
            html += '  <div class="requirement-section soft-skills">\n'
            html += '    <h4 class="section-title">[SOFT] Soft Skills</h4>\n'
            html += '    <div class="skill-tags">\n'
            for skill in analysis["soft_skills"]:
                html += f'      <span class="skill-tag soft">{skill}</span>\n'
            html += '    </div>\n'
            html += '  </div>\n'
        
        # Responsibilities section
        if analysis.get("responsibilities"):
            html += '  <div class="requirement-section responsibilities">\n'
            html += '    <h4 class="section-title">[TANGGUNG JAWAB] Tanggung Jawab</h4>\n'
            html += '    <ul class="requirement-list">\n'
            for resp in analysis["responsibilities"][:4]:
                html += f'      <li>{resp}</li>\n'
            html += '    </ul>\n'
            html += '  </div>\n'
        
        html += '</div>\n'
        return html
    
    @staticmethod
    def format_cover_letter_html(cover_letter_data):
        """Format cover letter menjadi HTML yang dapat di-copy"""
        cover_letter = cover_letter_data.get("cover_letter", "")
        matched_skills = cover_letter_data.get("matched_skills", [])
        
        html = '<div class="cover-letter-container">\n'
        
        # Matched skills highlight
        if matched_skills:
            html += '  <div class="matched-skills-summary">\n'
            html += '    <h5>Keahlian yang Sesuai:</h5>\n'
            html += '    <div class="skill-tags">\n'
            for skill in matched_skills:
                html += f'      <span class="skill-tag matched">{skill}</span>\n'
            html += '    </div>\n'
            html += '  </div>\n'
        
        # Cover letter text (formatted with line breaks)
        html += '  <div class="cover-letter-text">\n'
        paragraphs = cover_letter.split('\n\n')
        for para in paragraphs:
            if para.strip():
                html += f'    <p>{para.strip()}</p>\n'
        html += '  </div>\n'
        
        # Copy button
        html += '  <div class="copy-button-container">\n'
        html += '    <button class="copy-cover-letter-btn" onclick="copyCoverLetter()">[COPY] Cover Letter</button>\n'
        html += '  </div>\n'
        
        html += '</div>\n'
        return html
    
    @staticmethod
    def format_summary_card(analysis, cover_letter_data):
        """Format summary card untuk quick view"""
        all_skills = analysis.get("all_skills", {})
        total_skills = sum(len(v) for v in all_skills.values())
        mandatory_count = len(analysis.get("mandatory_requirements", []))
        preferred_count = len(analysis.get("preferred_requirements", []))
        soft_skills_count = len(analysis.get("soft_skills", []))
        matched_skills = len(cover_letter_data.get("matched_skills", []))
        
        html = f'''<div class="requirement-summary-card">
  <div class="summary-stat">
    <span class="stat-label">Total Skills:</span>
    <span class="stat-value">{total_skills}</span>
  </div>
  <div class="summary-stat">
    <span class="stat-label">Your Match:</span>
    <span class="stat-value matched">{matched_skills}/{total_skills}</span>
  </div>
  <div class="summary-stat">
    <span class="stat-label">Requirements:</span>
    <span class="stat-value">{mandatory_count} Wajib, {preferred_count} Diutamakan</span>
  </div>
  <div class="summary-stat">
    <span class="stat-label">Soft Skills:</span>
    <span class="stat-value">{soft_skills_count}</span>
  </div>
</div>
'''
        return html


if __name__ == "__main__":
    # Test
    sample_requirements = """
    Memiliki pengalaman 1+ tahun di bidang Data Science atau Machine Learning
    Menguasai Python dan SQL untuk manipulasi data
    Familiar dengan Dataiku, Power BI, atau tools BI lainnya
    Soft skills: komunikasi yang baik, teamwork, problem solving
    Diutamakan memiliki background di bidang oil and gas
    Nice to have: experience dengan Apache Spark, Docker
    """
    
    result = analyze_and_generate("Data Analyst", "PT Tech Indonesia", sample_requirements)
    
    print("=== REQUIREMENT ANALYSIS ===")
    print(f"Skills Found: {result['analysis']['all_skills']}")
    print(f"Soft Skills: {result['analysis']['soft_skills']}")
    print(f"Mandatory: {len(result['analysis']['mandatory_requirements'])} items")
    print(f"Preferred: {len(result['analysis']['preferred_requirements'])} items")
    
    print("\n=== COVER LETTER ===")
    print(result['cover_letter']['cover_letter'])
    print("\n=== MATCHED SKILLS ===")
    print(result['cover_letter']['matched_skills'])
    
    print("\n=== HTML FORMATTED ===")
    print("Requirements HTML:")
    print(RequirementFormatter.format_requirements_html(result['analysis']))
    
    print("\nCover Letter HTML:")
    print(RequirementFormatter.format_cover_letter_html(result['cover_letter']))
    
    print("\nSummary Card:")
    print(RequirementFormatter.format_summary_card(result['analysis'], result['cover_letter']))
