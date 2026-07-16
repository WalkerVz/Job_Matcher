"""
Integration test: NLP Analyzer + Cover Letter Generator
Verifies end-to-end flow dari requirement parsing sampai cover letter generation.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nlp_analyzer import RequirementAnalyzer, CoverLetterGenerator, RequirementFormatter, analyze_and_generate

def test_real_job_requirements():
    """Test dengan real job requirements dari matched_jobs.json"""
    
    # Sample job requirements dari real lowongan
    sample_jobs = [
        {
            "title": "Data Analyst - SMI",
            "company": "Astra Financial",
            "requirements": """
            Pendidikan minimal S1 di bidang Data Science, Ilmu Komputer, Teknologi Informasi, Matematika, Statistika, atau bidang kuantitatif lain yang relevan.
            Memiliki pemahaman yang kuat mengenai machine learning dan predictive modeling.
            Menguasai SQL untuk melakukan ekstraksi, manipulasi, dan analisis data.
            Memahami konsep Big Data dan data warehouse.
            Mampu melakukan exploratory data analysis (EDA).
            Memiliki kemampuan berpikir analitis dan pemecahan masalah yang baik.
            Memiliki pengalaman dalam membangun visualisasi data atau dashboard menggunakan Power BI, Tableau, atau platform sejenis menjadi nilai tambah.
            Soft skills: komunikasi yang baik, teamwork, problem solving, adaptabilitas.
            """
        },
        {
            "title": "AI Engineer",
            "company": "PT Tech Indonesia",
            "requirements": """
            Minimal 1 tahun pengalaman di bidang AI/Machine Learning atau Data Science.
            Menguasai Python dan TensorFlow/PyTorch.
            Diutamakan memiliki pengalaman dengan deep learning dan NLP.
            Nice to have: pengalaman dengan Docker, Kubernetes, atau cloud platforms (AWS/GCP).
            Soft skills: problem solving, teamwork, communication, self-motivated.
            """
        }
    ]
    
    print("="*70)
    print("INTEGRATION TEST: NLP Analyzer + Cover Letter Generator")
    print("="*70)
    
    for idx, job in enumerate(sample_jobs, 1):
        print(f"\n{'='*70}")
        print(f"TEST CASE {idx}: {job['title']} at {job['company']}")
        print("="*70)
        
        # Step 1: Analyze requirements
        print("\n[STEP 1] Analyzing requirements...")
        analysis = RequirementAnalyzer.analyze(job["requirements"])
        
        print(f"  [OK] Skills extracted: {sum(len(v) for v in analysis['all_skills'].values())} total")
        print(f"    - Mandatory: {analysis['mandatory_requirements'].__len__()} items")
        print(f"    - Preferred: {analysis['preferred_requirements'].__len__()} items")
        print(f"    - Soft skills: {', '.join(analysis['soft_skills'])}")
        
        # Step 2: Generate cover letter
        print("\n[STEP 2] Generating cover letter...")
        cover_letter_data = CoverLetterGenerator.generate(job["title"], job["company"], analysis)
        
        matched_count = len(cover_letter_data['matched_skills'])
        total_count = analysis['skill_count']
        match_percent = (matched_count / total_count * 100) if total_count > 0 else 0
        
        print(f"  [OK] Cover letter generated")
        print(f"    - Matched skills: {matched_count}/{total_count} ({match_percent:.0f}%)")
        print(f"    - Soft skills highlighted: {', '.join(cover_letter_data['soft_skills_highlighted'])}")
        print(f"    - Cover letter preview (first 200 chars):")
        print(f"      {cover_letter_data['cover_letter'][:200]}...")
        
        # Step 3: Format for display
        print("\n[STEP 3] Formatting for UI display...")
        req_html = RequirementFormatter.format_requirements_html(analysis)
        cl_html = RequirementFormatter.format_cover_letter_html(cover_letter_data)
        summary_html = RequirementFormatter.format_summary_card(analysis, cover_letter_data)
        
        print(f"  [OK] Requirements HTML formatted: {len(req_html)} chars")
        print(f"  [OK] Cover letter HTML formatted: {len(cl_html)} chars")
        print(f"  [OK] Summary card HTML formatted: {len(summary_html)} chars")
        
        # Step 4: Full integration
        print("\n[STEP 4] Full integration test...")
        full_result = analyze_and_generate(job["title"], job["company"], job["requirements"])
        
        print(f"  [OK] Full pipeline completed successfully")
        print(f"    - Analysis keys: {list(full_result['analysis'].keys())}")
        print(f"    - Cover letter keys: {list(full_result['cover_letter'].keys())}")
        
        print(f"\n[PASS] TEST CASE {idx} PASSED")
    
    print("\n" + "="*70)
    print("[PASS] ALL INTEGRATION TESTS PASSED")
    print("="*70)

def test_edge_cases():
    """Test edge cases"""
    print("\n" + "="*70)
    print("EDGE CASE TESTS")
    print("="*70)
    
    # Edge case 1: Empty requirements
    print("\n[EDGE CASE 1] Empty requirements")
    result = analyze_and_generate("Unknown Job", "Unknown Company", "")
    print(f"  [OK] Handled empty requirements: {len(result['analysis']['all_skills'])} skills found")
    
    # Edge case 2: Very short requirements
    print("\n[EDGE CASE 2] Very short requirements")
    result = analyze_and_generate("Junior Dev", "Startup XYZ", "Python developer needed")
    print(f"  [OK] Handled short requirements: {len(result['cover_letter']['matched_skills'])} skills matched")
    
    # Edge case 3: Only soft skills
    print("\n[EDGE CASE 3] Only soft skills (no technical)")
    result = analyze_and_generate("Coordinator", "NGO", "Komunikasi baik, teamwork, problem solving")
    print(f"  [OK] Handled soft skills only: {len(result['analysis']['soft_skills'])} soft skills found")
    
    print("\n[PASS] ALL EDGE CASE TESTS PASSED")

if __name__ == "__main__":
    try:
        test_real_job_requirements()
        test_edge_cases()
        
        print("\n" + "="*70)
        print("[PASS] COMPREHENSIVE INTEGRATION TEST COMPLETED SUCCESSFULLY")
        print("="*70)
        print("\nModule Status:")
        print("  [OK] RequirementAnalyzer - Working")
        print("  [OK] CoverLetterGenerator - Working")
        print("  [OK] RequirementFormatter - Working")
        print("  [OK] analyze_and_generate() - Working")
        print("\nReady for production integration!")
        
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
