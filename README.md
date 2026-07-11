# 🚀 Automated Job Matcher & Scraper

Platform pencocokan lowongan kerja otomatis berbasis web yang mengambil data secara langsung (*scraping*) dari portal karir resmi **Hulu Migas (Talentics)**, **Pertamina Training & Consulting (PTC)**, **SawitPRO**, dan **Astra Careers**, kemudian mengevaluasinya dengan algoritma *scoring* yang disesuaikan untuk profil **Python Developer & Data Analyst (1 Tahun Pengalaman)**.

---

## ✨ Fitur Utama

- **Scraper Otomatis 4 Portal Karir Resmi**:
  - 🏛️ **SKK Migas & KKKS (Talentics)** (`jobs.talentics.id`)
  - 🌟 **Astra Careers** (`career.astra.co.id`)
  - 🛢️ **Pertamina Training & Consulting (PTC)** (`recruitment.pertamina-ptc.com`)
  - 🌴 **SawitPRO** (`sawitpro.id/jobs`)
- **Algoritma Scoring & Filtering Otomatis**:
  - Mengevaluasi kecocokan jurusan IT/Informatika/Sistem Informasi & keahlian Python/Data Science.
  - Membandingkan syarat pengalaman kerja dengan profil 1 tahun pengalaman (PHR Intern).
  - Mendeteksi *blocker* persyaratan seperti IPK minimal, batas usia, atau spesifikasi gender.
- **Antarmuka (UI) Modern & Responsif**:
  - Desain bertema *Dark Mode* mewah dengan efek *Glassmorphism*.
  - **Sticky Filter Bar**: Filter pencarian tetap menempel di atas layar saat *scroll*.
  - **Pilihan Per Page & Pagination**: Opsi jumlah item per halaman (10, 25, 50, 100, atau semua).
  - Penuh optimalisasi untuk tampilan Desktop, Tablet, dan Smartphone.

---

## 🛠️ Cara Menjalankan Scraper Secara Lokal

1. Pastikan Anda memiliki **Python 3.10+** terinstal.
2. Install *library* yang dibutuhkan:
   ```bash
   pip install requests beautifulsoup4
   ```
3. Jalankan script scraper:
   ```bash
   python scraper.py
   ```
   Script akan mengambil lowongan terbaru dari 4 portal karir dan memperbarui file `matched_jobs.json` serta `matched_jobs.js`.

4. Buka file `index.html` langsung di browser Anda untuk melihat hasilnya!

---

## 🌐 Deploy ke Vercel (Gratis & Otomatis)

Proyek ini sangat mudah di-deploy ke **Vercel** karena merupakan aplikasi web statis (*Static Web App*):

1. **Push Proyek ke GitHub**:
   ```bash
   git init
   git add .
   git commit -m "Initial commit: Automated Job Matcher"
   git branch -M main
   git remote add origin https://github.com/USERNAME/NAMA-REPO.git
   git push -u origin main
   ```
2. **Hubungkan ke Vercel**:
   - Buka [vercel.com](https://vercel.com/) dan login menggunakan akun GitHub Anda.
   - Klik **Add New Project** $\rightarrow$ Pilih repository GitHub ini.
   - Framework Preset: biarkan **Other / Static**.
   - Klik **Deploy**. Website akan langsung online!
