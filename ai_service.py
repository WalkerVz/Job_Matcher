"""
AI Service for Job Matcher - powered by Google Gemini API
Provides intelligent features: job summarization and interview question prediction
"""

from dotenv import load_dotenv
import os
import google.generativeai as genai
from flask import Flask, request, jsonify
from flask_cors import CORS

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)
CORS(app)

# Configure Gemini API - read from environment variable
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-2.0-flash')

@app.route('/api/summarize-job', methods=['POST'])
def summarize_job():
    """
    Summarize lengthy job descriptions into concise bullet points
    """
    try:
        data = request.json
        job_title = data.get('title', '')
        job_description = data.get('description', '')
        requirements = data.get('requirements', '')
        
        if not job_description:
            return jsonify({'error': 'Job description is required'}), 400
        
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
        
        response = model.generate_content(prompt)
        summary = response.text.strip()
        
        return jsonify({
            'success': True,
            'summary': summary
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
        data = request.json
        job_title = data.get('title', '')
        job_description = data.get('description', '')
        requirements = data.get('requirements', '')
        company = data.get('company', '')
        
        if not job_title:
            return jsonify({'error': 'Job title is required'}), 400
        
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
        
        response = model.generate_content(prompt)
        questions = response.text.strip()
        
        return jsonify({
            'success': True,
            'questions': questions
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'AI Job Matcher Service',
        'model': 'gemini-1.5-flash'
    })


if __name__ == '__main__':
    print("=== Starting AI Service on http://localhost:5001 ===")
    print("Endpoints available:")
    print("   - POST /api/summarize-job")
    print("   - POST /api/predict-interview")
    print("   - GET /health")
    app.run(host='0.0.0.0', port=5001, debug=True)
