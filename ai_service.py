"""
AI Service for Job Matcher
Supports multiple AI Providers: Groq API (Free Llama-3.3-70B) & Google Gemini API
Provides intelligent features: job summarization and interview question prediction
"""

from dotenv import load_dotenv
import os
import requests
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
from scraper import clean_html  # reuse, tidak perlu definisi ulang

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration from .env
AI_PROVIDER = os.getenv('AI_PROVIDER', 'groq').lower()

GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_MODEL = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
GEMINI_MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.0-flash')


def generate_ai_content(prompt):
    """Generate content using the active AI Provider (Groq or Gemini)"""
    if AI_PROVIDER == 'groq':
        if not GROQ_API_KEY or GROQ_API_KEY == 'gsk_your_groq_api_key_here':
            raise ValueError("GROQ_API_KEY belum dikonfigurasi di file .env. Dapatkan API Key gratis di https://console.groq.com")
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": GROQ_MODEL,
            "messages": [
                {"role": "system", "content": "Kamu adalah asisten karir profesional dalam Bahasa Indonesia."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.4
        }
        resp = requests.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            try:
                err_info = resp.json().get('error', {}).get('message', resp.text)
            except Exception:
                err_info = resp.text
            raise RuntimeError(f"Groq API Error ({resp.status_code}): {err_info}")
        
        data = resp.json()
        return data['choices'][0]['message']['content'].strip()

    elif AI_PROVIDER == 'gemini':
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY belum dikonfigurasi di file .env")
        model = genai.GenerativeModel(GEMINI_MODEL)
        response = model.generate_content(prompt)
        return response.text.strip()

    else:
        raise ValueError(f"AI_PROVIDER '{AI_PROVIDER}' tidak dikenali. Pilih 'groq' atau 'gemini'")


@app.route('/api/summarize-job', methods=['POST'])
def summarize_job():
    """
    Summarize lengthy job descriptions into concise bullet points
    """
    try:
        data = request.get_json(silent=True) or {}
        job_title = data.get('title', '')
        job_description = clean_html(data.get('description', ''))
        requirements = clean_html(data.get('requirements', ''))
        
        if not job_description and not requirements:
            return jsonify({'success': False, 'error': 'Job description or requirements is required'}), 400
        
        prompt = f"""
Kamu adalah asisten karir profesional. Ringkas deskripsi pekerjaan berikut menjadi 5-7 poin bullet yang mudah dipahami dalam Bahasa Indonesia.

Posisi: {job_title}

Deskripsi:
{job_description}

Persyaratan:
{requirements}

Format output:
- Gunakan bahasa Indonesia yang natural dan mudah dipahami
- Maksimal 7 bullet points
- Setiap poin fokus pada tanggung jawab utama atau benefit menarik
- Hindari jargon teknis yang berlebihan
- Highlight hal-hal yang menarik untuk fresh graduate IT

Output format (hanya bullet points, tanpa penjelasan tambahan):
"""
        
        summary = generate_ai_content(prompt)
        
        return jsonify({
            'success': True,
            'summary': summary,
            'provider': AI_PROVIDER.upper()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/predict-interview', methods=['POST'])
def predict_interview():
    """
    Predict likely interview questions based on job requirements
    """
    try:
        data = request.get_json(silent=True) or {}
        job_title = data.get('title', '')
        job_description = clean_html(data.get('description', ''))
        requirements = clean_html(data.get('requirements', ''))
        company = data.get('company', '')
        
        if not job_title:
            return jsonify({'success': False, 'error': 'Job title is required'}), 400
        
        prompt = f"""
Kamu adalah career coach berpengalaman. Prediksi 8-10 pertanyaan interview yang kemungkinan besar ditanyakan untuk posisi ini.

Perusahaan: {company}
Posisi: {job_title}

Deskripsi Pekerjaan:
{job_description}

Persyaratan:
{requirements}

Buat prediksi pertanyaan interview yang:
1. Relevan dengan posisi dan requirement
2. Campuran antara technical dan behavioral questions
3. Disesuaikan untuk fresh graduate IT
4. Dalam Bahasa Indonesia yang natural
5. Mencakup pertanyaan umum HR, technical skill, dan situational

Format output (hanya list pertanyaan, tanpa penjelasan):
1. [pertanyaan 1]
2. [pertanyaan 2]
...
"""
        
        questions = generate_ai_content(prompt)
        
        return jsonify({
            'success': True,
            'questions': questions,
            'provider': AI_PROVIDER.upper()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/generate-cover-letter', methods=['POST'])
def generate_cover_letter():
    """
    Generate personalized cover letter based on job requirements and user CV
    """
    try:
        data = request.get_json(silent=True) or {}
        job_title = data.get('title', '')
        company = data.get('company', '')
        job_description = clean_html(data.get('description', ''))
        requirements = clean_html(data.get('requirements', ''))
        
        # User CV data
        user_major = data.get('user_major', 'Teknik Informatika')
        user_gpa = data.get('user_gpa', '3.5')
        user_skills = data.get('user_skills', 'Python, Data Science, Machine Learning')
        user_experience = data.get('user_experience', '1 tahun')
        
        if not job_title:
            return jsonify({'success': False, 'error': 'Job title is required'}), 400
        
        prompt = f"""
Kamu adalah career coach profesional yang ahli menulis cover letter. Buatkan cover letter profesional dalam Bahasa Indonesia untuk lamaran ini.

INFORMASI PELAMAR (CV):
- Jurusan: {user_major}
- IPK: {user_gpa}
- Keahlian: {user_skills}
- Pengalaman: {user_experience}

INFORMASI LOWONGAN:
- Perusahaan: {company}
- Posisi: {job_title}

Deskripsi Pekerjaan:
{job_description}

Persyaratan:
{requirements}

Tulis cover letter yang:
1. Profesional dan menarik perhatian HRD
2. Menunjukkan kesesuaian skills dan pengalaman pelamar dengan posisi
3. Highlight keahlian teknis yang relevan dengan requirement
4. Tunjukkan antusiasme dan motivasi yang kuat
5. Maksimal 3-4 paragraf (tidak terlalu panjang)
6. Gunakan bahasa Indonesia yang formal namun tetap hangat
7. JANGAN menulis alamat, tanggal, atau salam pembuka "Kepada Yth" - langsung mulai dari paragraf pembuka

Format output (langsung paragraf tanpa header):
[Paragraf pembuka yang menarik dan menunjukkan antusiasme]

[Paragraf kedua menjelaskan kesesuaian skills dan pengalaman dengan posisi]

[Paragraf penutup yang kuat dengan call-to-action]
"""
        
        cover_letter = generate_ai_content(prompt)
        
        return jsonify({
            'success': True,
            'cover_letter': cover_letter,
            'provider': AI_PROVIDER.upper()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    active_model = GROQ_MODEL if AI_PROVIDER == 'groq' else GEMINI_MODEL
    return jsonify({
        'status': 'healthy',
        'service': 'AI Job Matcher Service',
        'provider': AI_PROVIDER.upper(),
        'model': active_model
    })


if __name__ == '__main__':
    active_model = GROQ_MODEL if AI_PROVIDER == 'groq' else GEMINI_MODEL
    print("=== Starting AI Service on http://localhost:5001 ===")
    print(f"Provider Active : {AI_PROVIDER.upper()} ({active_model})")
    print("Endpoints available:")
    print("   - POST /api/summarize-job")
    print("   - POST /api/predict-interview")
    print("   - POST /api/generate-cover-letter")
    print("   - GET /health")
    app.run(host='0.0.0.0', port=5001, debug=True)
