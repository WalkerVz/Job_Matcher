@echo off
echo ========================================
echo    Ravil's Career Radar - Auto Update
echo ========================================
echo.

cd /d "d:\New folder (32)\job_matcher"

echo [1/3] Menjalankan scraper...
python scraper.py

echo.
echo [2/3] Menyimpan hasil ke git...
git add matched_jobs.json matched_jobs.js
git diff --quiet && git diff --staged --quiet && (
    echo Tidak ada perubahan data lowongan.
) || (
    git commit -m "update: manual scrape job vacancies"
    echo [3/3] Push ke GitHub...
    git push
    echo.
    echo Berhasil! Data lowongan terbaru sudah live di website.
)

echo.
echo ========================================
echo    Selesai! Tekan tombol apapun...
echo ========================================
pause
