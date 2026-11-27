"""
AI Service for Job Matcher
Supports multiple AI Providers: Groq API (Free Llama-3.3-70B) & Google Gemini API
Provides intelligent features: job summarization and interview question prediction
"""

from collections import OrderedDict
import hashlib
import os
import threading
from dotenv import load_dotenv
import requests
from requests.adapters import HTTPAdapter
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS
from config import PROFILE, clean_html  # dari modul terpusat config.py

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

# Persistent HTTP session & cached Gemini model untuk latency rendah
_HTTP_SESSION = requests.Session()
_HTTP_SESSION.mount("https://", HTTPAdapter(pool_connections=10, pool_maxsize=10))
_GEMINI_MODEL_INSTANCE = genai.GenerativeModel(GEMINI_MODEL) if GEMINI_API_KEY else None

# Thread-safe LRU cache (mengurangi API calls berulang & menghemat kuota)
_AI_CACHE_MAX = 200
_AI_CACHE: OrderedDict = OrderedDict()
_AI_CACHE_LOCK = threading.Lock()


def _call_groq(prompt: str) -> str:
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
    resp = _HTTP_SESSION.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        try:
            err_info = resp.json().get('error', {}).get('message', resp.text)
        except Exception:
            err_info = resp.text
        raise RuntimeError(f"Groq API Error ({resp.status_code}): {err_info}")

    data = resp.json()
    return data['choices'][0]['message']['content'].strip()


def _call_gemini(prompt: str) -> str:
    if not GEMINI_API_KEY or _GEMINI_MODEL_INSTANCE is None:
        raise ValueError("GEMINI_API_KEY belum dikonfigurasi di file .env")
    response = _GEMINI_MODEL_INSTANCE.generate_content(prompt)
    return response.text.strip()


def generate_ai_content(prompt: str, cache_namespace: str = "default"):
    """Generate content with LRU caching and automatic secondary provider fallback."""
    cache_key = hashlib.sha256(f"{AI_PROVIDER}:{cache_namespace}:{prompt}".encode("utf-8")).hexdigest()
    with _AI_CACHE_LOCK:
        cached = _AI_CACHE.get(cache_key)
        if cached is not None:
            _AI_CACHE.move_to_end(cache_key)
            return cached

    if AI_PROVIDER == 'groq':
        providers = [('GROQ', _call_groq), ('GEMINI', _call_gemini)]
    elif AI_PROVIDER == 'gemini':
        providers = [('GEMINI', _call_gemini), ('GROQ', _call_groq)]
    else:
        raise ValueError(f"AI_PROVIDER '{AI_PROVIDER}' tidak dikenali. Pilih 'groq' atau 'gemini'")

    errors = []
    for name, caller in providers:
        try:
            text = caller(prompt)
            result = (text, name)
            with _AI_CACHE_LOCK:
                if len(_AI_CACHE) >= _AI_CACHE_MAX:
                    _AI_CACHE.popitem(last=False)
                _AI_CACHE[cache_key] = result
            return result
        except Exception as exc:
            errors.append(f"{name}: {exc}")

    raise RuntimeError(" | ".join(errors))


def _validate_job_payload(data: dict, require_text: bool = False):
    """Validasi dan sanitasi payload lowongan untuk semua endpoint AI."""
    job_title = str(data.get('title') or '').strip()
    if not job_title or len(job_title) > 500:
        return None, (jsonify({'success': False, 'error': 'Invalid or missing job title'}), 400)

    job_description = clean_html(data.get('description', ''))[:8000]
    requirements = clean_html(data.get('requirements', ''))[:8000]

    if require_text and not job_description and not requirements:
        return None, (jsonify({'success': False, 'error': 'Job description or requirements is required'}), 400)

    return {
        'title': job_title,
        'description': job_description,
        'requirements': requirements,
        'company': str(data.get('company') or '').strip()[:200],
    }, None


@app.route('/api/summarize-job', methods=['POST'])
def summarize_job():
    """
    Summarize lengthy job descriptions into concise bullet points
    """
    try:
        data = request.get_json(silent=True) or {}
        cleaned, err_resp = _validate_job_payload(data, require_text=True)
        if err_resp:
            return err_resp

        prompt = f"""
Kamu adalah asisten karir profesional. Ringkas deskripsi pekerjaan berikut menjadi 5-7 poin bullet yang mudah dipahami dalam Bahasa Indonesia.

Posisi: {cleaned['title']}

Deskripsi:
{cleaned['description']}

Persyaratan:
{cleaned['requirements']}

Format output:
- Gunakan bahasa Indonesia yang natural dan mudah dipahami
- Maksimal 7 bullet points
- Setiap poin fokus pada tanggung jawab utama atau benefit menarik
- Hindari jargon teknis yang berlebihan
- Highlight hal-hal yang menarik untuk fresh graduate IT

Output format (hanya bullet points, tanpa penjelasan tambahan):
"""

        summary, used_provider = generate_ai_content(prompt, cache_namespace="summarize")

        return jsonify({
            'success': True,
            'summary': summary,
            'provider': used_provider
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/predict-interview', methods=['POST'])
def predict_interview():
    """
    Predict likely interview questions based on job requirements + generate sample answers
    """
    try:
        data = request.get_json(silent=True) or {}
        cleaned, err_resp = _validate_job_payload(data, require_text=False)
        if err_resp:
            return err_resp

        default_skills = ', '.join(PROFILE.get('skills', [])[:15])
        user_skills = str(data.get('user_skills') or default_skills)[:1000]
        user_experience = str(data.get('user_experience') or PROFILE.get('experience', '1 tahun'))[:1500]

        prompt = f"""
Kamu adalah career coach dan interview coach profesional berpengalaman. Kamu akan:
1. Prediksi 8 pertanyaan interview yang kemungkinan ditanyakan
2. Untuk SETIAP pertanyaan, buatkan jawaban sample yang profesional

KONTEKS KANDIDAT:
- Posisi: {cleaned['title']}
- Perusahaan: {cleaned['company']}
- Keahlian: {user_skills}
- Pengalaman: {user_experience}

INFORMASI LOWONGAN:
Deskripsi: {cleaned['description']}
Persyaratan: {cleaned['requirements']}

INSTRUKSI:
1. Buat 8 pertanyaan interview yang:
   - Relevan dengan posisi dan requirement
   - Campuran technical dan behavioral questions
   - Disesuaikan untuk fresh graduate / 1 tahun pengalaman
   - Dalam Bahasa Indonesia yang natural

2. Untuk SETIAP pertanyaan, tambahkan:
   - Contoh jawaban profesional (2-3 kalimat)
   - Jawaban sesuai konteks candidate
   - Highlight keahlian yang relevan

FORMAT OUTPUT (PENTING - ikuti format ini persis):
**[nomor]. [Pertanyaan]**
**Jawaban Sample:** [Jawaban profesional 2-3 kalimat]

[Spasi]

**[nomor]. [Pertanyaan berikutnya]**
**Jawaban Sample:** [Jawaban profesional]

... (ulangi untuk semua 8 pertanyaan)

MULAI SEKARANG (output hanya list pertanyaan + jawaban, tanpa penjelasan):
"""

        response_text, used_provider = generate_ai_content(prompt, cache_namespace="interview")

        return jsonify({
            'success': True,
            'questions': response_text,
            'provider': used_provider
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
        cleaned, err_resp = _validate_job_payload(data, require_text=False)
        if err_resp:
            return err_resp

        default_skills = ', '.join(PROFILE.get('skills', [])[:15])
        user_major = str(data.get('user_major') or PROFILE.get('major', 'Teknik Informatika'))[:200]
        user_gpa = str(data.get('user_gpa') or PROFILE.get('gpa', '3.39'))[:20]
        user_skills = str(data.get('user_skills') or default_skills)[:1000]
        user_experience = str(data.get('user_experience') or PROFILE.get('experience', '1 tahun'))[:1500]

        prompt = f"""
Kamu adalah career coach profesional yang ahli menulis cover letter. Buatkan cover letter profesional dalam Bahasa Indonesia untuk lamaran ini.

INFORMASI PELAMAR (CV):
- Jurusan: {user_major}
- IPK: {user_gpa}
- Keahlian: {user_skills}
- Pengalaman: {user_experience}

INFORMASI LOWONGAN:
- Perusahaan: {cleaned['company']}
- Posisi: {cleaned['title']}

Deskripsi Pekerjaan:
{cleaned['description']}

Persyaratan:
{cleaned['requirements']}

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

        cover_letter, used_provider = generate_ai_content(prompt, cache_namespace="cover_letter")

        return jsonify({
            'success': True,
            'cover_letter': cover_letter,
            'provider': used_provider
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
        'model': active_model,
        'cache_entries': len(_AI_CACHE)
    })


if __name__ == '__main__':
    active_model = GROQ_MODEL if AI_PROVIDER == 'groq' else GEMINI_MODEL
    host = os.getenv('FLASK_HOST', '127.0.0.1')
    port = int(os.getenv('FLASK_PORT', '5001'))
    debug = os.getenv('FLASK_DEBUG', 'false').lower() == 'true'
    print(f"=== Starting AI Service on http://{host}:{port} ===")
    print(f"Provider Active : {AI_PROVIDER.upper()} ({active_model})")
    print("Endpoints available:")
    print("   - POST /api/summarize-job")
    print("   - POST /api/predict-interview")
    print("   - POST /api/generate-cover-letter")
    print("   - GET /health")
    app.run(host=host, port=port, debug=debug)
