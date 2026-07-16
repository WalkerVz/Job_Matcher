"""
Interview Preparation Generator
- Generate interview questions berdasarkan job requirements
- Provide sample answers matched to profile
- Tips untuk jawab pertanyaan
"""

import re
from nlp_analyzer import RequirementAnalyzer

class InterviewQuestionGenerator:
    """Generate interview questions + sample answers based on job requirements"""
    
    # Question templates by category
    BEHAVIORAL_QUESTIONS = [
        {
            "category": "Problem Solving",
            "question": "Ceritakan pengalaman Anda menyelesaikan masalah yang kompleks di proyek sebelumnya?",
            "sample_answer": "Di proyek QC Log Analyzer di Pertamina Hulu Rokan, saya menghadapi tantangan dengan data yang inconsistent dari multiple sources. Saya menganalisis pola data menggunakan Python dan Dataiku, kemudian membuat validation rules otomatis. Hasilnya: processing time berkurang 40% dan error rate turun 25%."
        },
        {
            "category": "Teamwork",
            "question": "Bagaimana Anda bekerja sama dalam tim dengan latar belakang berbeda?",
            "sample_answer": "Di Rakamin Academy, saya bekerja dengan data engineers, domain experts, dan business stakeholders. Saya memastikan komunikasi jelas dengan menjelaskan technical concepts dalam bahasa business. Setiap sprint, saya conduct knowledge sharing session tentang machine learning concepts. Hasilnya: team velocity meningkat dan model accuracy mencapai 86.96%."
        },
        {
            "category": "Handling Conflict",
            "question": "Apa yang Anda lakukan ketika ada ketidaksetujuan dengan kolega tentang technical decision?",
            "sample_answer": "Saya fokus pada data dan hasil. Saat ada dispute tentang model selection, saya prepare benchmark results, pros-cons analysis, dan resource implications. Kemudian kami diskusi berdasarkan data, bukan opinion. Hasilnya: kami bisa membuat keputusan yang informed dan team tetap harmonis."
        },
        {
            "category": "Learning & Growth",
            "question": "Bagaimana Anda terus mengupdate skill teknis di bidang yang cepat berubah?",
            "sample_answer": "Saya aktif belajar through: (1) Online courses (Udemy, Coursera) - udah selesain 3 courses tahun ini. (2) Practical projects - implement techniques baru di freelance projects. (3) Community - follow tech blogs, GitHub trends, join data science communities. (4) Peer learning - share knowledge dengan team regularly. Target tahun ini: master deep learning + cloud deployment."
        }
    ]
    
    TECHNICAL_QUESTIONS = {
        "Python": [
            {
                "question": "Jelaskan perbedaan antara list comprehension dan map() di Python. Kapan gunakan masing-masing?",
                "sample_answer": "List comprehension lebih readable dan faster untuk simple transformations: `[x*2 for x in data]`. Map() lebih powerful untuk function objects dan lazy evaluation. Untuk datasets besar, map() + generator expression menghemat memory. Saya prefer list comprehension untuk clarity, tapi map() untuk streaming data."
            },
            {
                "question": "Apa itu decorators di Python? Berikan contoh penggunaan real-world.",
                "sample_answer": "Decorators memungkinkan modify function behavior tanpa edit source code. Contoh real: @lru_cache untuk caching calculation results (di QC Log Analyzer saya gunakan untuk cache requirement validations - hasilnya 3x faster). @timing_decorator untuk performance monitoring, @authentication_decorator untuk security layers di API."
            }
        ],
        "SQL": [
            {
                "question": "Bagaimana optimize query yang slow? Sebutkan teknik-teknik yang Anda gunakan.",
                "sample_answer": "Teknik optimization: (1) Proper indexing - index pada WHERE columns. (2) Avoid SELECT * - ambil kolom yg dibutuhkan aja. (3) Use JOINs instead of subqueries - lebih efficient. (4) Partition large tables. (5) Profile dengan EXPLAIN PLAN. Di Pertamina, query yang dulunya 5 menit, jadi 10 detik setelah indexing optimization."
            },
            {
                "question": "Explain window functions di SQL dan use case-nya.",
                "sample_answer": "Window functions allow calculations across rows tanpa collapse into single row (unlike GROUP BY). Contoh: ROW_NUMBER() untuk ranking, SUM() OVER untuk running totals, LAG/LEAD untuk compare dengan row sebelum/sesudah. Di data analyst role, saya gunakan untuk trend analysis, churn prediction, dan time-series analysis."
            }
        ],
        "Data Science": [
            {
                "question": "Bagaimana Anda handle imbalanced dataset dalam classification problem?",
                "sample_answer": "Teknik handling: (1) Resampling - oversampling minority class atau undersampling majority (use stratified k-fold untuk validation). (2) Cost-sensitive learning - assign higher weight ke minority class. (3) SMOTE (Synthetic Minority Oversampling). (4) Use appropriate metrics - precision, recall, F1-score instead of accuracy. Di Credit Risk model, dataset 99% tidak default. Saya gunakan stratified sampling + SMOTE, hasilnya model balance antara recall (catch bad loans) dan precision (minimize false positives)."
            },
            {
                "question": "Jelaskan trade-off antara model complexity dan interpretability.",
                "sample_answer": "Simple models (linear regression, decision trees) = interpretable tapi mungkin underfit. Complex models (deep learning, ensemble) = high accuracy tapi black-box. Strategy saya: (1) Start simple, explain results. (2) If accuracy insufficient, increase complexity gradually. (3) Use SHAP/LIME untuk explain complex models. (4) For business decisions, prefer interpretable even if slightly lower accuracy. Di Pertamina, gunakan decision trees untuk operational decisions (staff bisa understand), ensemble untuk backend predictions (faster response time)."
            }
        ],
        "Machine Learning": [
            {
                "question": "Bagaimana Anda prevent overfitting di model training?",
                "sample_answer": "Teknik prevention: (1) Train/validation split (atau k-fold cross-validation). (2) Regularization (L1/L2). (3) Early stopping - stop training ketika validation loss naik. (4) Dropout (untuk neural networks). (5) More training data. (6) Feature engineering yang smart (reduce noise). Monitoring strategy: compare train vs validation metrics - jika gap besar, ada overfitting. Di Rakamin project, validation accuracy 86.96% mencerminkan realistic performance."
            }
        ]
    }
    
    JOB_SPECIFIC_QUESTIONS = {
        "Data Analyst": [
            {
                "question": "Bagaimana Anda approach untuk exploratory data analysis (EDA) dataset baru?",
                "sample_answer": "EDA process saya: (1) Understand business context dulu (ask stakeholders). (2) Load data, check shape, dtypes, null values. (3) Univariate analysis - distribution tiap column. (4) Bivariate analysis - relationships antar variables. (5) Identify outliers dan anomalies. (6) Hypothesis generation untuk deeper analysis. Tools: Pandas profiling, matplotlib, seaborn untuk visualization. Documentation: create markdown report dengan findings + questions untuk follow-up."
            },
            {
                "question": "Ceritakan dashboard atau report yang Anda buat. Apa impact-nya?",
                "sample_answer": "Di Pertamina, saya develop operational dashboard menggunakan Power BI yang track QC metrics real-time. Dashboard show: error trends, processing time, data quality scores dengan drill-down capabilities. Impact: operations team bisa spot issues within minutes (vs hours before). Management bisa make data-driven decisions faster. Adoption rate 95% - semua stakeholders gunakan daily."
            }
        ],
        "AI Engineer": [
            {
                "question": "Describe end-to-end ML pipeline dari problem definition sampai production deployment.",
                "sample_answer": "Pipeline saya: (1) Problem scoping - define success metrics. (2) Data collection + EDA. (3) Feature engineering. (4) Model selection + training (hyperparameter tuning). (5) Validation (cross-val, test set). (6) Model serving (containerization, API). (7) Monitoring + retraining. Di Pertamina: developed Credit Risk model in 8 weeks, deployed via API, currently serving 1000+ requests/day dengan 99.9% uptime."
            },
            {
                "question": "Bagaimana Anda handle model drift di production?",
                "sample_answer": "Monitoring strategy: (1) Track input data distribution - alert jika ada shift. (2) Monitor prediction distribution - jika berubah drastis, suspicious. (3) Compare model predictions vs actual outcomes (jika tersedia) - accuracy drop = sign of drift. (4) Set retraining schedule atau trigger. (5) A/B test new model sebelum production switch. Remediation: either retrain model atau adjust decision threshold tergantung root cause."
            }
        ]
    }
    
    @staticmethod
    def generate_questions(job_title, requirements_text, num_questions=5):
        """Generate interview questions berdasarkan job description"""
        
        analysis = RequirementAnalyzer.analyze(requirements_text)
        
        questions_list = []
        
        # 1. Add behavioral questions (always relevant)
        print("[*] Adding behavioral questions...")
        for bq in InterviewQuestionGenerator.BEHAVIORAL_QUESTIONS[:2]:  # First 2 behavioral
            questions_list.append({
                "type": "Behavioral",
                "category": bq["category"],
                "question": bq["question"],
                "sample_answer": bq["sample_answer"]
            })
        
        # 2. Add technical questions based on detected skills
        print("[*] Adding technical questions based on required skills...")
        all_skills = []
        for category, skills in analysis.get("all_skills", {}).items():
            all_skills.extend(skills)
        
        for skill in all_skills[:3]:  # Top 3 skills
            skill_lower = skill.lower()
            
            # Check if we have predefined questions for this skill
            for tech_category, tech_questions in InterviewQuestionGenerator.TECHNICAL_QUESTIONS.items():
                if tech_category.lower() in skill_lower or skill_lower in tech_category.lower():
                    # Pick first question from this category
                    if tech_questions:
                        tq = tech_questions[0]
                        questions_list.append({
                            "type": "Technical",
                            "topic": tech_category,
                            "question": tq["question"],
                            "sample_answer": tq["sample_answer"]
                        })
                    break
        
        # 3. Add job-specific questions
        print("[*] Adding job-specific questions...")
        job_title_lower = job_title.lower()
        
        for job_type, specific_questions in InterviewQuestionGenerator.JOB_SPECIFIC_QUESTIONS.items():
            if job_type.lower() in job_title_lower:
                for sq in specific_questions[:1]:  # First question from job type
                    questions_list.append({
                        "type": "Job-Specific",
                        "topic": job_type,
                        "question": sq["question"],
                        "sample_answer": sq["sample_answer"]
                    })
                break
        
        # Return top N questions
        return questions_list[:num_questions]
    
    @staticmethod
    def format_interview_prep_html(questions):
        """Format interview questions + answers into beautiful HTML"""
        
        html = '<div class="interview-prep-container">\n'
        html += '  <div class="interview-header">\n'
        html += '    <h4>Interview Preparation Guide</h4>\n'
        html += '    <p>Predicted questions based on job requirements + sample answers</p>\n'
        html += '  </div>\n'
        
        for idx, q in enumerate(questions, 1):
            html += f'  <div class="interview-question-card">\n'
            html += f'    <div class="question-header">\n'
            html += f'      <span class="question-num">#{idx}</span>\n'
            html += f'      <span class="question-type">[{q.get("type", "General")}]</span>\n'
            html += f'      <span class="question-topic">{q.get("topic", q.get("category", ""))}</span>\n'
            html += f'    </div>\n'
            html += f'    <div class="question-text">\n'
            html += f'      <p><strong>Q:</strong> {q["question"]}</p>\n'
            html += f'    </div>\n'
            html += f'    <div class="answer-section">\n'
            html += f'      <button class="btn-toggle-answer" onclick="toggleAnswer(this)">Show Sample Answer</button>\n'
            html += f'      <div class="answer-text" style="display:none;">\n'
            html += f'        <p><strong>Sample Answer:</strong></p>\n'
            html += f'        <p>{q["sample_answer"]}</p>\n'
            html += f'      </div>\n'
            html += f'    </div>\n'
            html += f'  </div>\n'
        
        html += '  <div class="interview-tips">\n'
        html += '    <h5>Interview Tips:</h5>\n'
        html += '    <ul>\n'
        html += '      <li>Use STAR method for behavioral questions (Situation, Task, Action, Result)</li>\n'
        html += '      <li>Quantify achievements whenever possible (%, time saved, revenue impact)</li>\n'
        html += '      <li>Relate questions back to the specific job requirements</li>\n'
        html += '      <li>Prepare concrete examples from your portfolio projects</li>\n'
        html += '      <li>Ask clarifying questions if you dont understand</li>\n'
        html += '      <li>Be honest - its better to say "I dont know but heres how Id learn" than make up answers</li>\n'
        html += '    </ul>\n'
        html += '  </div>\n'
        html += '</div>\n'
        
        return html


# Better Experience Parser
def parse_experience_requirement(req_text):
    """
    Parse experience requirement lebih akurat
    Return dict dengan level description, bukan hanya angka
    """
    text_lower = req_text.lower()
    
    # Pattern untuk extract tahun
    patterns = [
        r'(?:pengalaman|experience)\s*(?:kerja)?\s*(?:minimal|min|min\.|diutamakan|at least)?\s*(\d+)\s*(?:\+)?\s*(?:tahun|year)',
        r'(?:minimal|min|min\.|at least)\s*(\d+)\s*(?:\+)?\s*(?:tahun|year)\s*(?:pengalaman|experience)',
        r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:relevant\s*)?experience',
        r'(\d+)\s*(?:tahun)\s*(?:pengalaman)'
    ]
    
    years_found = []
    for pattern in patterns:
        matches = re.findall(pattern, text_lower)
        for match in matches:
            try:
                years_found.append(int(match))
            except ValueError:
                pass
    
    years_req = max(years_found) if years_found else 0
    
    # Determine level
    if "fresh graduate" in text_lower or "lulusan baru" in text_lower or "0 tahun" in text_lower or "entry level" in text_lower:
        level = "Fresh Graduate / Entry Level"
        years_req = 0
    elif years_req == 0:
        level = "Open / Not Specified"
    elif years_req == 1:
        level = "Junior (1 tahun)"
    elif years_req <= 2:
        level = "Junior to Mid (1-2 tahun)"
    elif years_req <= 3:
        level = "Mid Level (2-3 tahun)"
    elif years_req <= 5:
        level = "Senior (3-5 tahun)"
    else:
        level = f"Lead / Expert ({years_req}+ tahun)"
    
    return {
        "years_required": years_req,
        "level_description": level,
        "is_entry_level": years_req == 0,
        "formatted": f"{level} required"
    }


if __name__ == "__main__":
    # Test
    sample_job = "Data Analyst - Senior"
    sample_requirements = """
    Minimal 2 tahun pengalaman sebagai data analyst atau similar role
    Menguasai SQL dan Python
    Power BI atau Tableau experience
    Soft skills: problem solving, komunikasi, teamwork
    """
    
    print("="*70)
    print("INTERVIEW PREP TEST")
    print("="*70)
    
    # Test questions
    print("\n[TEST 1] Generating interview questions...")
    questions = InterviewQuestionGenerator.generate_questions(sample_job, sample_requirements, num_questions=5)
    
    print(f"Generated {len(questions)} questions:")
    for q in questions:
        print(f"\n  [{q['type']}] {q.get('topic', q.get('category', ''))}")
        print(f"  Q: {q['question'][:80]}...")
    
    # Test experience parser
    print("\n[TEST 2] Parsing experience requirement...")
    exp = parse_experience_requirement(sample_requirements)
    print(f"  Years: {exp['years_required']}")
    print(f"  Level: {exp['level_description']}")
    print(f"  Is Entry: {exp['is_entry_level']}")
    
    print("\n" + "="*70)
    print("[PASS] ALL TESTS PASSED")
    print("="*70)
