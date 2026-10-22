# ⚡ Ravil's Career Radar & Automated Job Matcher

Platform cerdas pencocokan lowongan kerja otomatis (*AI-Powered Job Opportunity Radar*) yang mengambil data secara langsung (*scraping*) dari 7 portal karir resmi terkemuka di Indonesia, mengevaluasi kecocokannya dengan profil **AI Engineer & Data Scientist (Muhammad Ravil)**, serta dilengkapi fitur analisis AI (Ringkasan Lowongan, Prediksi Interview, Skills Gap, Cover Letter Generator).

---

## 📁 Struktur Direktori Project

```text
job_matcher/
├── docs/                             # 📚 Dokumentasi Lengkap
│   ├── SETUP_GUIDE.md                # Panduan instalasi dan konfigurasi API
│   ├── FEATURES_SUMMARY.md           # Rincian fitur lengkap platform
│   └── SCRAPER_UPGRADE.md            # Dokumentasi arsitektur scraper
├── tests/                            # 🧪 Script Pengujian & Eksperimen
│   ├── test_micro1.py
│   ├── test_opentrain.py
│   ├── test_opentrain_v2.py
│   └── test_selenium_opentrain.py
│
├── config.py                         # ⚙️ Konfigurasi terpusat (Profil & Konstanta)
├── scraper.py                        # 🕷️ Mesin scraping concurrent & scoring engine
├── ai_service.py                     # 🤖 Flask API AI Service (Groq & Gemini)
│
├── nlp_analyzer.py                   # 🧠 NLP requirement analyzer & cover letter generator
├── skills_gap_analyzer.py            # 📊 Analisis kesenjangan skill kandidat vs requirement
├── interview_prep.py                 # 💬 Generator simulasi pertanyaan interview teknis & HR
├── application_tracker.py            # 📌 Pelacak status lamaran kerja
├── rescore_jobs.py                   # 🔄 Script CLI untuk kalkulasi ulang skor lowongan
├── add_job_entry.py                  # ➕ Script CLI untuk tambah lowongan manual
│
├── index.html                        # 🌐 Antarmuka web utama (Dashboard Radar Karir)
├── app.js                            # ⚡ Logika interaksi frontend, filter, & integrasi AI
├── style.css                         # 🎨 Desain modern Dark Mode Glassmorphism
├── manifest.json                     # 📱 Konfigurasi Progressive Web App (PWA)
├── sw.js                             # 📶 Service Worker untuk performa offline
├── icon.svg                          # ⚡ Ikon aplikasi
│
├── matched_jobs.json                 # 💾 Database hasil kurasi lowongan (JSON)
├── matched_jobs.js                   # 💾 Fallback global variable browser
├── last_updated.json                 # 🕒 Metadata waktu update terakhir
├── new_jobs.json                     # 🆕 Deteksi lowongan baru sejak run sebelumnya
│
├── requirements.txt                  # 📦 Dependensi Python
├── vercel.json                       # 🚀 Konfigurasi deployment & header keamanan Vercel
├── .env.example                      # 🔐 Template variabel environment
└── README.md                         # 📖 Dokumentasi utama project
```

---

## ✨ Fitur Utama

### 1. 🕷️ Multi-Source Scraper (9 Portal Karir)
- 🌟 **Astra Careers** (`career.astra.co.id`) — Lowongan IT, Engineering, Data
- 🟣 **OpenTrain.ai** (`opentrain.ai`) — Remote AI Training, LLM Evaluation & RLHF roles
- 🟢 **Grab Careers Indonesia** (`grab.careers`)
- 🟡 **Indosat Ooredoo Hutchison (IOH)** (`careers.ioh.co.id`)
- 🏛️ **SKK Migas & KKKS / Hulu Migas (Talentics)** (`jobs.talentics.id`)
- 🛢️ **Pertamina Training & Consulting (PTC)** (`recruitment.pertamina-ptc.com`)
- 🌴 **SawitPRO** (`sawitpro.id/jobs`)
- 🍲 **Indofood Careers** (`career.indofood.com`)
- 🌐 **micro1** (`microonejobs.com`) — Remote Software Engineering & AI roles

### 2. 🎯 Smart Matching & Filtering Engine
- **Major Matching**: Memfilter otomatis jurusan Teknik Informatika, Sistem Informasi, dan Ilmu Komputer.
- **Skills Scoring**: Menghitung bobot keahlian Python, Machine Learning, Data Science, SQL, AI, Power BI, Laravel, React, dll.
- **Experience & Blocker Detection**: Memvalidasi kesesuaian pengalaman kerja (1 tahun, mantan AI Engineer Pertamina Hulu Rokan & Id/x partners), syarat IPK minimal, TOEFL, dan batas usia.

### 3. 🤖 AI Intelligence Layer
- **Groq Llama-3.3-70B / Google Gemini 2.0 Flash**: Ringkasan lowongan instan dan prediksi 8 pertanyaan interview beserta contoh jawaban profesional.
- **Serverless Cloud AI Fallback**: Fallback otomatis berjalan di mobile tanpa server lokal via Pollinations AI.
- **Skills Gap Visualizer**: Menunjukkan perbandingan *Matched Skills*, *Skills to Learn*, dan *Level Up*.

### 4. 📱 Progressive Web App (PWA) & Glassmorphism UI
- Desain *Dark Mode* elegan dengan efek *Glassmorphism*.
- Sticky filter bar, quick search, filter sumber lowongan, pengurutan cerdas, dan navigasi badge lowongan baru (🆕).
- Dapat diinstal di Android & iOS sebagai aplikasi PWA mandiri.

---

## 🚀 Panduan Memulai

### 1. Prasyarat
- Python 3.10 atau versi lebih baru
- Browser modern (Chrome, Edge, Firefox, atau Safari)

### 2. Instalasi
```bash
# Clone repository
git clone https://github.com/WalkerVz/Job_Matcher.git
cd Job_Matcher

# Buat virtual environment (opsional namun direkomendasikan)
python -m venv .venv
source .venv/bin/activate  # Linux/Mac
.venv\Scripts\activate     # Windows

# Install dependensi
pip install -r requirements.txt
```

### 3. Konfigurasi Environment (`.env`)
Salin template konfigurasi:
```bash
cp .env.example .env
```
Isi API Key opsional (Groq API Key gratis dari [console.groq.com](https://console.groq.com)):
```env
AI_PROVIDER=groq
GROQ_API_KEY=gsk_your_groq_api_key_here
USER_NAME="Muhammad Ravil"
USER_LOCATION="Pekanbaru, Riau"
```

### 4. Menjalankan Scraper
```bash
python scraper.py
```
Hasil scraping akan tersimpan otomatis ke `matched_jobs.json` dan `matched_jobs.js`.

### 5. Menjalankan AI Service (Opsional)
```bash
python ai_service.py
```
Server Flask lokal akan aktif di port `5001`.

### 6. Membuka Dashboard Web
Cukup buka file `index.html` langsung di browser, atau gunakan local web server:
```bash
python -m http.server 8000
```
Buka browser pada `http://localhost:8000`.

---

## 🌐 Deployment (Vercel)

Proyek ini telah dikonfigurasi dengan [vercel.json](vercel.json) yang menerapkan *Security Headers* (CSP, HSTS, X-Content-Type-Options, dll.):

1. Hubungkan repository GitHub ini ke akun [Vercel](https://vercel.com).
2. Framework Preset: **Other / Static**.
3. Root Directory: `./`.
4. Klik **Deploy** — website akan langsung online dan terupdate otomatis setiap kali ada push baru ke branch `main`.

---

## 📚 Dokumentasi Terkait
- [Panduan Lengkap Setup & Integrasi API](docs/SETUP_GUIDE.md)
- [Ringkasan Rinci Fitur Platform](docs/FEATURES_SUMMARY.md)
- [Dokumentasi Peningkatan Arsitektur Scraper](docs/SCRAPER_UPGRADE.md)
