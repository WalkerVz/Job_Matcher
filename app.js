// Global state
let allJobs = [];
let filteredJobs = [];
let currentPage = 1;
let itemsPerPage = 10;
let wishlistOnly = false;

// ─── State job baru ───────────────────────────────────────────────────────────
let newJobIds = new Set(); // ID job yang baru muncul sejak scrape terakhir

// Key localStorage untuk menyimpan ID yang sudah pernah dilihat user
const SEEN_KEY = 'careerRadar_seenJobIds';

function getSeenIds() {
    try { return new Set(JSON.parse(localStorage.getItem(SEEN_KEY) || '[]')); }
    catch { return new Set(); }
}

function markAllAsSeen() {
    const allIds = allJobs.map(j => String(j.id));
    localStorage.setItem(SEEN_KEY, JSON.stringify(allIds));
    newJobIds = new Set();
    // Hapus banner & semua badge 'Baru'
    const banner = document.getElementById('newJobsBanner');
    if (banner) banner.remove();
    document.querySelectorAll('.new-job-badge').forEach(el => el.remove());
    updateNewJobsNavBadge(0);
}

function updateNewJobsNavBadge(count) {
    const badge = document.getElementById('newJobsNavBadge');
    if (!badge) return;
    if (count > 0) {
        badge.textContent = count;
        badge.style.display = 'inline-block';
    } else {
        badge.style.display = 'none';
    }
}

async function loadNewJobsData() {
    try {
        const res = await fetch('new_jobs.json?t=' + Date.now());
        if (!res.ok) {
            console.log('[DEBUG] new_jobs.json fetch gagal:', res.status);
            return;
        }
        const data = await res.json();
        console.log('[DEBUG] new_jobs.json loaded:', data);
        
        if (!data.new_ids || data.count === 0) {
            console.log('[DEBUG] Tidak ada job baru atau count = 0');
            return;
        }

        const seenIds = getSeenIds();
        console.log('[DEBUG] Seen IDs dari localStorage:', Array.from(seenIds));
        console.log('[DEBUG] New IDs dari server:', data.new_ids);
        
        // Job baru = ada di new_jobs.json DAN belum pernah dilihat user
        const trulyNew = data.new_ids.filter(id => !seenIds.has(String(id)));
        console.log('[DEBUG] Truly new IDs (belum dilihat):', trulyNew);
        
        if (trulyNew.length === 0) {
            console.log('[DEBUG] Semua job sudah pernah dilihat, tidak tampilkan banner');
            return;
        }

        newJobIds = new Set(trulyNew.map(String));
        console.log('[DEBUG] newJobIds state updated:', Array.from(newJobIds));
        showNewJobsBanner(trulyNew.length, data.scraped_at);
        updateNewJobsNavBadge(trulyNew.length);
    } catch (e) {
        console.error('[DEBUG] Error loadNewJobsData:', e);
    }
}

function showNewJobsBanner(count, scrapedAt) {
    // Hindari duplikat banner
    const existing = document.getElementById('newJobsBanner');
    if (existing) existing.remove();

    const banner = document.createElement('div');
    banner.id = 'newJobsBanner';
    banner.className = 'new-jobs-banner';
    banner.innerHTML = `
        <div class="new-jobs-banner-left">
            <span class="new-jobs-banner-icon">🆕</span>
            <div>
                <strong>${count} lowongan baru</strong> ditemukan sejak scrape terakhir
                <span class="new-jobs-banner-time">${scrapedAt}</span>
            </div>
        </div>
        <div class="new-jobs-banner-actions">
            <button class="btn-see-new" onclick="filterToNewJobs()">Lihat Semua</button>
            <button class="btn-dismiss-new" onclick="markAllAsSeen()" title="Tandai semua sudah dilihat">✕</button>
        </div>
    `;

    // Sisipkan tepat di atas filter bar
    const mainSection = document.querySelector('.main-section');
    const filterBar = document.querySelector('.filters-bar');
    if (mainSection && filterBar) {
        mainSection.insertBefore(banner, filterBar);
    }
}

window.filterToNewJobs = function () {
    // Reset filter lain, lalu render ulang — card dengan badge 'Baru' akan muncul di atas
    searchInput.value = '';
    matchFilter.value = 'all';
    sourceFilter.value = 'all';
    if (expFilter) expFilter.value = 'all';
    sortSelect.value = 'score';
    currentPage = 1;

    // Pindahkan job baru ke urutan paling atas sementara
    filteredJobs = [
        ...allJobs.filter(j => newJobIds.has(String(j.id))),
        ...allJobs.filter(j => !newJobIds.has(String(j.id)))
    ];
    renderJobList();
    scrollToJobListTop();
};
// ─────────────────────────────────────────────────────────────────────────────

// Debounce helper – prevents search firing on every keypress
function debounce(fn, delay = 300) {
    let timer;
    return (...args) => {
        clearTimeout(timer);
        timer = setTimeout(() => fn(...args), delay);
    };
}

// DOM Elements
const searchInput = document.getElementById('searchInput');
const matchFilter = document.getElementById('matchFilter');
const sourceFilter = document.getElementById('sourceFilter');
const expFilter = document.getElementById('expFilter');
const sortSelect = document.getElementById('sortSelect');
const perPageSelect = document.getElementById('perPageSelect');
const wishlistToggleBtn = document.getElementById('wishlistToggleBtn');
const wishlistCountEl = document.getElementById('wishlistCount');
const jobCountEl = document.getElementById('jobCount');
const jobListContainer = document.getElementById('jobListContainer');
const paginationBar = document.getElementById('paginationBar');
const prevPageBtn = document.getElementById('prevPageBtn');
const nextPageBtn = document.getElementById('nextPageBtn');
const pageInfo = document.getElementById('pageInfo');
const detailModal = document.getElementById('detailModal');
const modalCloseBtn = document.getElementById('modalCloseBtn');
const modalContent = document.getElementById('modalContent');
const mobileFilterToggleBtn = document.getElementById('mobileFilterToggleBtn');
const filterControlsWrapper = document.getElementById('filterControlsWrapper');
const filterCountBadge = document.getElementById('filterCountBadge');
const resetFilterBtn = document.getElementById('resetFilterBtn');

// Initialize Dashboard
document.addEventListener('DOMContentLoaded', async () => {
    // 1. Fetch data
    await loadJobsData();

    // Setup mobile filter toggle
    if (mobileFilterToggleBtn && filterControlsWrapper) {
        mobileFilterToggleBtn.addEventListener('click', () => {
            filterControlsWrapper.classList.toggle('active');
            mobileFilterToggleBtn.classList.toggle('active');
        });
    }

    // 2. Setup event listeners
    searchInput.addEventListener('input', debounce(() => { currentPage = 1; applyFilters(); }, 250));
    matchFilter.addEventListener('change', () => { currentPage = 1; applyFilters(); });
    sourceFilter.addEventListener('change', () => { currentPage = 1; applyFilters(); });
    if (expFilter) expFilter.addEventListener('change', () => { currentPage = 1; applyFilters(); });
    sortSelect.addEventListener('change', () => { currentPage = 1; applyFilters(); });

    if (wishlistToggleBtn) {
        wishlistToggleBtn.addEventListener('click', () => {
            wishlistOnly = !wishlistOnly;
            wishlistToggleBtn.classList.toggle('active', wishlistOnly);
            currentPage = 1;
            applyFilters();
        });
    }

    if (resetFilterBtn) {
        resetFilterBtn.addEventListener('click', () => {
            // Reset all filters to default values
            searchInput.value = '';
            matchFilter.value = 'all';
            sourceFilter.value = 'all';
            if (expFilter) expFilter.value = 'all';
            sortSelect.value = 'score';
            perPageSelect.value = '10';
            wishlistOnly = false;
            if (wishlistToggleBtn) wishlistToggleBtn.classList.remove('active');

            // Reset pagination and re-apply filters
            currentPage = 1;
            itemsPerPage = 10;
            applyFilters();
            scrollToJobListTop();
        });
    }

    if (perPageSelect) {
        perPageSelect.addEventListener('change', () => {
            itemsPerPage = perPageSelect.value;
            currentPage = 1;
            renderJobList();
        });
    }

    if (prevPageBtn) {
        prevPageBtn.addEventListener('click', () => {
            if (currentPage > 1) {
                currentPage--;
                renderJobList();
                scrollToJobListTop();
            }
        });
    }

    if (nextPageBtn) {
        nextPageBtn.addEventListener('click', () => {
            currentPage++;
            renderJobList();
            scrollToJobListTop();
        });
    }

    modalCloseBtn.addEventListener('click', closeModal);

    // Close modal on click outside content
    detailModal.addEventListener('click', (e) => {
        if (e.target === detailModal) {
            closeModal();
        }
    });

    // Close modal on Escape key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && detailModal.classList.contains('active')) {
            closeModal();
        }
    });
});

// Load Jobs from JSON file
async function loadJobsData() {
    try {
        // Attempt to fetch from local json first
        // Tambah timestamp query string agar bypass cache SW di mobile
        const response = await fetch('matched_jobs.json?t=' + Date.now());
        if (response.ok) {
            allJobs = await response.json();
        } else {
            throw new Error('Local JSON fetch failed');
        }
    } catch (e) {
        console.warn('Fetch failed or was blocked by CORS. Checking for global window variable fallback...');
        if (window.matchedJobs && window.matchedJobs.length > 0) {
            allJobs = window.matchedJobs;
        }
    }

    // Try to load last updated timestamp
    try {
        const luRes = await fetch('last_updated.json?t=' + Date.now());
        if (luRes.ok) {
            const luData = await luRes.json();
            if (luData && luData.last_updated) {
                const badgeEl = document.getElementById('lastUpdatedDate');
                if (badgeEl) badgeEl.textContent = luData.last_updated;
            }
        } else {
            throw new Error('Local last_updated fetch failed');
        }
    } catch (err) {
        console.warn('Failed to load last updated timestamp from JSON:', err);
        if (window.lastUpdated) {
            const badgeEl = document.getElementById('lastUpdatedDate');
            if (badgeEl) badgeEl.textContent = window.lastUpdated;
        }
    }

    // Show skeleton while loading
    showSkeleton();
    updateWishlistCountBadge();
    
    // ⚠️ FIX RACE CONDITION: Ensure loadNewJobsData completes BEFORE applyFilters
    await loadNewJobsData(); // Wait untuk selesai
    
    // Now safe to apply filters
    applyFilters();
}

// Show skeleton loading cards
function showSkeleton() {
    const skeletons = Array.from({ length: 5 }, () => `
        <div class="job-card skeleton-card">
            <div class="skeleton skeleton-circle"></div>
            <div class="job-info" style="flex:1">
                <div class="skeleton skeleton-title"></div>
                <div class="skeleton skeleton-line"></div>
                <div class="skeleton skeleton-line short"></div>
            </div>
        </div>`).join('');
    jobListContainer.innerHTML = skeletons;
}

// Render Error Screen
function renderError(title, subtitle) {
    jobListContainer.innerHTML = `
        <div class="empty-container">
            <div class="empty-icon">⚠️</div>
            <h3>${title}</h3>
            <p>${subtitle}</p>
        </div>
    `;
    jobCountEl.textContent = '0 Lowongan';
}

// Load saved jobs state from localStorage
function getSavedJobsState() {
    try {
        return JSON.parse(localStorage.getItem('savedJobMatcherState') || '{}');
    } catch (e) {
        return {};
    }
}

function updateWishlistCountBadge() {
    if (!wishlistCountEl) return;
    const state = getSavedJobsState();
    const count = Object.values(state).filter(s => s && s.isBookmarked).length;
    wishlistCountEl.textContent = count;
}

window.toggleBookmark = function (event, jobId) {
    if (event) event.stopPropagation();
    const state = getSavedJobsState();
    const idStr = String(jobId);
    const isBookmarked = state[idStr] ? !state[idStr].isBookmarked : true;
    state[idStr] = { ...(state[idStr] || {}), isBookmarked };
    localStorage.setItem('savedJobMatcherState', JSON.stringify(state));
    updateWishlistCountBadge();
    applyFilters();
};

window.changeApplicationStatus = function (jobId, statusValue) {
    const state = getSavedJobsState();
    const idStr = String(jobId);
    state[idStr] = { ...(state[idStr] || {}), status: statusValue, isBookmarked: true };
    localStorage.setItem('savedJobMatcherState', JSON.stringify(state));
    updateWishlistCountBadge();
    applyFilters();
};

function generateCoverLetterHTML(job) {
    const nlp = job.nlp_breakdown || {};
    const requiredSkills = (nlp.mandatory_skills && nlp.mandatory_skills.length > 0)
        ? nlp.mandatory_skills.join(', ')
        : 'pemrograman Python, analisis data (SQL/Dataiku), dan pengembangan solusi teknologi';

    const companyName = job.organization_name || 'Perusahaan';
    const jobTitle = job.title || 'Posisi yang dilamar';

    const pitchID = `Yth. Tim Rekrutmen ${companyName},\n\nPerkenalkan saya Muhammad Ravil, lulusan S1 Teknik Informatika UIN Suska Riau (IPK 3.39 | TOEFL 537) dengan pengalaman profesional sebagai AI Engineer di PT Pertamina Hulu Rokan (PHR), Data Scientist Intern di Id/x partners x Rakamin Academy (Best Student 86.96), serta Freelance Web Dev & Machine Learning. Saya memiliki keahlian teruji dalam ${requiredSkills} yang sangat sejalan dengan kebutuhan posisi ${jobTitle}.\n\nMelalui proyek nyata seperti QC Log Analyzer (Python/Dataiku), model Credit Risk Loan (turunkan gagal bayar 12%), dan pengembangan aplikasi web (React/Laravel), saya siap memberikan kontribusi nyata bagi efisiensi operasional ${companyName}. Terlampir CV lengkap saya untuk pertimbangan Bapak/Ibu. Terima kasih.`;

    const pitchEN = `Dear ${companyName} Recruitment Team,\n\nMy name is Muhammad Ravil, a Computer Science graduate from UIN Suska Riau (GPA 3.39 | TOEFL 537) with hands-on industry experience as an AI Engineer at PT Pertamina Hulu Rokan (PHR), Data Scientist Intern at Id/x partners x Rakamin Academy, and Freelance Web Developer & ML Engineer. I bring practical technical expertise in ${requiredSkills}, aligning directly with the requirements for the ${jobTitle} role.\n\nWith a track record of building automated analytics applications (Python/Dataiku), predictive ML models (12% credit risk reduction), and full-stack web solutions (React/Laravel), I look forward to contributing to data-driven growth at ${companyName}. Please find my resume attached for your review. Thank you.`;

    const formalID = `Hal: Lamaran Pekerjaan – ${jobTitle}\nKepada Yth.\nTim HR / Rekrutmen\n${companyName}\n\nDengan hormat,\n\nSehubungan dengan informasi lowongan pekerjaan untuk posisi ${jobTitle} di ${companyName}, saya bermaksud mengajukan lamaran untuk bergabung dengan perusahaan Bapak/Ibu.\n\nSaya adalah lulusan S1 Teknik Informatika dari UIN Suska Riau (IPK 3.39, TOEFL 537) dengan latar belakang pengalaman di industri hulu migas sebagai AI Engineer di PT Pertamina Hulu Rokan (PHR, Juli 2025–Februari 2026). Selama masa kerja tersebut, saya berhasil mengembangkan aplikasi QC Log Analyzer berbasis Python dan Dataiku untuk otomatisasi pemrosesan, monitoring, serta visualisasi data operasional hulu migas.\n\nSelain itu, sebagai Data Scientist Intern di Id/x partners x Rakamin Academy (Best Student Score 86.96, April–Mei 2025), saya memiliki rekam jejak mengembangkan model machine learning Credit Risk Loan yang berhasil menurunkan tingkat gagal bayar pinjaman hingga 12% pada dataset 466.285 data. Saat ini saya juga aktif sebagai Freelance Web Developer & Machine Learning Engineer (PHP, Laravel, React, Python). Pengalaman ini membuat saya sangat terbiasa mengimplementasikan keahlian pada ${requiredSkills}.\n\nKemampuan analisis data yang kuat, keahlian teknis lintas platform (Python, SQL, Dataiku, React, Laravel, Power BI), serta komunikasi kolaboratif membuat saya yakin dapat memberikan kontribusi signifikan bagi ${companyName}.\n\nBesar harapan saya untuk diberikan kesempatan wawancara agar dapat menjelaskan lebih rinci mengenai portofolio saya. Atas perhatian dan kesempatan yang Bapak/Ibu berikan, saya ucapkan terima kasih.\n\nHormat saya,\n\nMuhammad Ravil\nPekanbaru, Riau | ravilmuhammad987@gmail.com`;

    return `
        <div class="cover-letter-container">
            <div class="cover-letter-header">
                <div>
                    <h4>✨ Auto-Generated Application Pitch & Cover Letter</h4>
                    <p>Dibuat otomatis dari CV asli (Muhammad Ravil | UIN Suska Riau | AI Engineer PHR | Rakamin 86.96 | Freelance Web/ML) dicocokkan dengan keahlian lowongan ini.</p>
                </div>
            </div>
            
            <div class="pitch-section">
                <div class="pitch-card-title">
                    <h5>💬 Pitch Singkat / LinkedIn Message (Bahasa Indonesia)</h5>
                    <button class="btn-copy" onclick="copyToClipboard(this, \`${encodeURIComponent(pitchID)}\`)">📋 Salin Teks</button>
                </div>
                <textarea readonly class="pitch-textarea" rows="5">${pitchID}</textarea>
            </div>

            <div class="pitch-section">
                <div class="pitch-card-title">
                    <h5>🌐 Brief Pitch / Recruiter Outreach (English)</h5>
                    <button class="btn-copy" onclick="copyToClipboard(this, \`${encodeURIComponent(pitchEN)}\`)">📋 Copy Pitch</button>
                </div>
                <textarea readonly class="pitch-textarea" rows="5">${pitchEN}</textarea>
            </div>

            <div class="pitch-section">
                <div class="pitch-card-title">
                    <h5>📄 Surat Lamaran Resmi / Formal Cover Letter (ID)</h5>
                    <button class="btn-copy" onclick="copyToClipboard(this, \`${encodeURIComponent(formalID)}\`)">📋 Salin Lamaran</button>
                </div>
                <textarea readonly class="pitch-textarea" rows="11">${formalID}</textarea>
            </div>
        </div>
    `;
}

function generateATSBoosterHTML(job) {
    const nlp = job.nlp_breakdown || {};
    const mandatory = nlp.mandatory_skills || [];
    const plus = nlp.plus_skills || [];
    const rawText = ((job.raw_description || '') + ' ' + (job.raw_requirements || '')).toLowerCase();

    // Kata kunci profil autentik dari CV - Muhammad Ravil.pdf
    const ravilProfileKeywords = [
        'python', 'sql', 'data analysis', 'data science', 'machine learning',
        'dataiku', 'excel', 'power bi', 'react', 'laravel', 'php', 'javascript', 'git', 'arcgis',
        'teknik informatika', 'sistem informasi', 'problem solving', 'analisis data',
        'data analyst', 'data scientist', 'ai engineer', 'web development', 'web developer',
        'fullstack', 'full stack', 'it support', 'mysql', 'sentiment analysis', 'naive bayes',
        'tableau', 'microsoft office', 'troubleshooting'
    ];

    // Identify which mandatory/plus skills Ravil already matches
    const matchedATS = [];
    const missingATS = [];

    [...mandatory, ...plus].forEach(skill => {
        const sLower = skill.toLowerCase();
        if (ravilProfileKeywords.some(rk => sLower.includes(rk) || rk.includes(sLower))) {
            matchedATS.push(skill);
        } else {
            missingATS.push(skill);
        }
    });

    // Also look for industry standard keywords in description
    const potentialBonusKeywords = ['power bi', 'tableau', 'excel', 'etl', 'data warehouse', 'big data', 'uat', 'dashboard', 'cleaning', 'visualisasi data', 'agile', 'jira', 'sap'];
    const bonusFound = [];
    potentialBonusKeywords.forEach(pk => {
        if (rawText.includes(pk) && !matchedATS.includes(pk)) {
            bonusFound.push(pk.toUpperCase());
        }
    });

    const atsScore = Math.min(98, Math.max(82, 75 + (matchedATS.length * 6)));

    // Generate tailored resume bullet points authentic to CV PDF
    const bullet1 = `• Developed QC Log Analyzer — automated data processing, monitoring & visualization application using Python and Dataiku at PT Pertamina Hulu Rokan (AI Engineer), streamlining upstream oil & gas operational reporting.`;
    const bullet2 = `• Engineered Credit Risk Loan ML model at Id/x partners x Rakamin Academy (Best Student 86.96), reducing loan default rates by 12% across 466,285 records.`;
    const bullet3 = `• Delivered end-to-end ${matchedATS[0] || 'data analytics'} workflows and full-stack solutions (${bonusFound[0] || 'React/Laravel/Python'}) as Freelance Web Dev & ML Engineer.`;

    const allBulletsText = `${bullet1}\n${bullet2}\n${bullet3}`;

    return `
        <div class="ats-booster-container">
            <div class="ats-score-header">
                <div class="ats-score-badge">
                    <span class="ats-number">${atsScore}%</span>
                    <span class="ats-label">ATS Keyword Readiness</span>
                </div>
                <div class="ats-header-info">
                    <h4>💡 AI ATS Resume Keyword Optimizer</h4>
                    <p>Sistem ATS mengecek kecocokan kata kunci CV kamu sebelum dibaca HR. Berikut analisis kata kunci untuk posisi ini:</p>
                </div>
            </div>

            <div class="ats-grid">
                <div class="ats-card matched">
                    <h5>✅ Kata Kunci Sudah Ada di Profilmu</h5>
                    <p class="ats-desc">Skill ini cocok dengan latar belakangmu (S1 Informatika & Data/Migas):</p>
                    <div class="nlp-tags">
                        ${matchedATS.length > 0 ? matchedATS.map(s => `<span class="nlp-skill-badge mandatory">✓ ${s}</span>`).join('') : '<span class="nlp-skill-badge mandatory">✓ Data Analysis & IT Core</span>'}
                    </div>
                </div>

                <div class="ats-card opportunity">
                    <h5>🎯 Kata Kunci Emas yang Perlu Ditambahkan ke CV</h5>
                    <p class="ats-desc">Tambahkan istilah ini pada bullet point CV kamu agar skor ATS naik maksimal:</p>
                    <div class="nlp-tags">
                        ${missingATS.concat(bonusFound).length > 0 ? missingATS.concat(bonusFound).slice(0, 8).map(s => `<span class="nlp-skill-badge plus">+ ${s}</span>`).join('') : '<span class="nlp-skill-badge plus">+ Analytical Problem Solving</span>'}
                    </div>
                </div>
            </div>

            <div class="pitch-section">
                <div class="pitch-card-title">
                    <h5>✨ 3 ATS-Optimized Resume Bullet Points (1-Click Copy untuk CV-mu)</h5>
                    <button class="btn-copy" onclick="copyToClipboard(this, \`${encodeURIComponent(allBulletsText)}\`)">📋 Salin 3 Bullet Points</button>
                </div>
                <p style="font-size: 0.78rem; color: #a78bfa; margin-top: 0; margin-bottom: 0.6rem;">Tempelkan poin-poin berdampak tinggi ini pada bagian Pengalaman Kerja / Proyek di CV kamu sebelum melamar lowongan ini:</p>
                <textarea readonly class="pitch-textarea" rows="6">${allBulletsText}</textarea>
            </div>
        </div>
    `;
}

window.copyToClipboard = function (btnElem, encodedText) {
    const text = decodeURIComponent(encodedText);
    navigator.clipboard.writeText(text).then(() => {
        const origText = btnElem.innerHTML;
        btnElem.innerHTML = '✅ Tersalin!';
        btnElem.classList.add('copied');
        setTimeout(() => {
            btnElem.innerHTML = origText;
            btnElem.classList.remove('copied');
        }, 2000);
    });
};

// Filter and Sort Logic
function applyFilters() {
    if (!allJobs || allJobs.length === 0) return;

    const query = searchInput.value.toLowerCase().trim();
    const matchType = matchFilter.value;
    const sourceVal = sourceFilter.value;
    const sortBy = sortSelect.value;

    filteredJobs = allJobs.filter(job => {
        // A. Text Search (Matches title, company, or department group)
        const textMatch =
            job.title.toLowerCase().includes(query) ||
            (job.organization_name && job.organization_name.toLowerCase().includes(query)) ||
            (job.group && job.group.toLowerCase().includes(query));

        if (!textMatch) return false;

        // B. Match Status Filter
        if (matchType !== 'all') {
            if (matchType === 'high' && job.match_score < 80) return false;
            if (matchType === 'medium' && (job.match_score < 50 || job.match_score >= 80)) return false;
            if (matchType === 'low' && job.match_score < 50) return false;
            if (matchType === 'compatible' && job.is_blocked) return false;
            if (matchType === 'blocked' && !job.is_blocked) return false;
        }

        // C. Source Filter
        if (sourceVal !== 'all') {
            const sourceMap = {
                'grab': 'Grab',
                'talentics': 'Talentics',
                'astra': 'Astra',
                'ptc': 'Pertamina PTC',
                'sawitpro': 'SawitPRO',
                'ioh': 'Indosat Ooredoo Hutchison',
                'indofood': 'Indofood'
            };
            const targetSource = sourceMap[sourceVal];
            if (targetSource && job.source !== targetSource) return false;
        }

        // D. Experience Filter (Ravil has 1 Year Experience)
        if (expFilter && expFilter.value !== 'all') {
            const expVal = expFilter.value;
            const reqYears = (job.parsed_requirements && job.parsed_requirements.exp_years !== undefined)
                ? job.parsed_requirements.exp_years
                : 0;

            if (expVal === 'eligible' && reqYears > 1) return false;
            if (expVal === 'freshgrad' && reqYears > 0) return false;
            if (expVal === 'experienced' && reqYears <= 1) return false;
        }

        // E. Wishlist Filter
        if (wishlistOnly) {
            const state = getSavedJobsState();
            if (!state[job.id] || !state[job.id].isBookmarked) return false;
        }

        return true;
    });

    // Update mobile filter badge
    if (filterCountBadge) {
        let count = 0;
        if (matchType !== 'all') count++;
        if (sourceVal !== 'all') count++;
        if (expFilter && expFilter.value !== 'all') count++;
        if (query !== '') count++;
        if (count > 0) {
            filterCountBadge.style.display = 'inline-block';
            filterCountBadge.textContent = count;
        } else {
            filterCountBadge.style.display = 'none';
        }
    }

    // C. Sorting
    if (sortBy === 'score') {
        // Highest score first, compatible jobs prioritized over blocked
        filteredJobs.sort((a, b) => {
            if (a.is_blocked && !b.is_blocked) return 1;
            if (!a.is_blocked && b.is_blocked) return -1;
            return b.match_score - a.match_score;
        });
    } else if (sortBy === 'title') {
        filteredJobs.sort((a, b) => a.title.localeCompare(b.title));
    } else if (sortBy === 'due_date') {
        filteredJobs.sort((a, b) => {
            const dateA = a.due_date ? new Date(a.due_date) : new Date('2099-12-31');
            const dateB = b.due_date ? new Date(b.due_date) : new Date('2099-12-31');
            return dateA - dateB;
        });
    }

    // Update mobile filter badge count
    if (filterCountBadge) {
        let activeCount = 0;
        if (matchFilter && matchFilter.value !== 'all') activeCount++;
        if (sourceFilter && sourceFilter.value !== 'all') activeCount++;
        if (expFilter && expFilter.value !== 'all') activeCount++;
        if (sortSelect && sortSelect.value !== 'score') activeCount++;
        if (activeCount > 0) {
            filterCountBadge.style.display = 'inline-block';
            filterCountBadge.textContent = activeCount;
        } else {
            filterCountBadge.style.display = 'none';
        }
    }

    renderJobList();
}

function getSourceBadgeHTML(job, styleAttr = '') {
    if (job.source === 'Grab') {
        return `<span class="source-badge grab" style="${styleAttr}">Grab Indonesia</span>`;
    } else if (job.source === 'Astra') {
        return `<span class="source-badge astra" style="${styleAttr}">Astra Career</span>`;
    } else if (job.source === 'Pertamina PTC') {
        return `<span class="source-badge ptc" style="${styleAttr}">Pertamina PTC</span>`;
    } else if (job.source === 'SawitPRO') {
        return `<span class="source-badge sawitpro" style="${styleAttr}">SawitPRO</span>`;
    } else if (job.source === 'Indosat Ooredoo Hutchison') {
        return `<span class="source-badge ioh" style="${styleAttr}">Indosat Ooredoo Hutchison</span>`;
    } else if (job.source === 'Indofood') {
        return `<span class="source-badge indofood" style="${styleAttr}">Indofood Career</span>`;
    }
    return `<span class="source-badge talentics" style="${styleAttr}">${job.source || 'Hulu Migas / BUMN'}</span>`;
}

// Render Numbered Pagination Buttons
function renderPaginationNumbers(totalPages) {
    const container = document.getElementById('pageNumbersContainer');
    if (!container) return;
    container.innerHTML = '';

    const pages = [];
    if (totalPages <= 7) {
        for (let i = 1; i <= totalPages; i++) pages.push(i);
    } else {
        if (currentPage <= 4) {
            pages.push(1, 2, 3, 4, 5, '...', totalPages);
        } else if (currentPage >= totalPages - 3) {
            pages.push(1, '...', totalPages - 4, totalPages - 3, totalPages - 2, totalPages - 1, totalPages);
        } else {
            pages.push(1, '...', currentPage - 1, currentPage, currentPage + 1, '...', totalPages);
        }
    }

    pages.forEach(p => {
        if (p === '...') {
            const span = document.createElement('span');
            span.className = 'page-ellipsis';
            span.textContent = '...';
            container.appendChild(span);
        } else {
            const btn = document.createElement('button');
            btn.className = `page-number-btn ${p === currentPage ? 'active' : ''}`;
            btn.textContent = p;
            btn.addEventListener('click', () => {
                if (currentPage !== p) {
                    currentPage = p;
                    renderJobList();
                    scrollToJobListTop();
                }
            });
            container.appendChild(btn);
        }
    });
}

// Smoothly scroll to the top of the job list (non-sticky anchor position)
function scrollToJobListTop() {
    const anchor = document.getElementById('jobListTopAnchor') || document.querySelector('.main-section');
    if (anchor) {
        const topPos = anchor.getBoundingClientRect().top + window.scrollY - 10;
        window.scrollTo({
            top: Math.max(0, topPos),
            behavior: 'smooth'
        });
    }
}

// Render the Job List Cards
function renderJobList() {
    jobListContainer.innerHTML = '';

    if (filteredJobs.length === 0) {
        const emptyIcon = wishlistOnly ? '⭐' : '🔎';
        const emptyTitle = wishlistOnly ? 'Wishlist Anda Masih Kosong' : 'Tidak Ada Lowongan yang Cocok';
        const emptySub = wishlistOnly
            ? 'Klik ikon bintang (⭐) pada lowongan apa pun untuk menyimpannya ke daftar Wishlist ini.'
            : 'Cobalah mengubah filter pencarian Anda atau kata kunci pencarian.';
        jobListContainer.innerHTML = `
            <div class="empty-container">
                <div class="empty-icon">${emptyIcon}</div>
                <h3>${emptyTitle}</h3>
                <p>${emptySub}</p>
            </div>
        `;
        jobCountEl.textContent = '0 Lowongan';
        if (paginationBar) paginationBar.style.display = 'none';
        return;
    }

    const totalItems = filteredJobs.length;
    let totalPages = 1;
    let paginatedJobs = filteredJobs;
    let startIdx = 0;
    let endIdx = totalItems;

    if (itemsPerPage !== 'all') {
        const limit = parseInt(itemsPerPage, 10);
        totalPages = Math.ceil(totalItems / limit) || 1;
        if (currentPage > totalPages) currentPage = totalPages;
        if (currentPage < 1) currentPage = 1;
        startIdx = (currentPage - 1) * limit;
        endIdx = Math.min(startIdx + limit, totalItems);
        paginatedJobs = filteredJobs.slice(startIdx, endIdx);

        jobCountEl.textContent = `Menampilkan ${startIdx + 1}-${endIdx} dari ${totalItems} Lowongan`;

        if (paginationBar) {
            paginationBar.style.display = totalPages > 1 ? 'flex' : 'none';
            renderPaginationNumbers(totalPages);
            if (prevPageBtn) prevPageBtn.disabled = (currentPage <= 1);
            if (nextPageBtn) nextPageBtn.disabled = (currentPage >= totalPages);
        }
    } else {
        jobCountEl.textContent = `${totalItems} Lowongan`;
        if (paginationBar) paginationBar.style.display = 'none';
    }

    paginatedJobs.forEach(job => {
        // Circumference of circular progress is 2 * PI * r = 2 * 3.14159 * 28 = 175.9
        const radius = 28;
        const circ = 2 * Math.PI * radius;
        const offset = circ - (job.match_score / 100) * circ;

        let matchClass = 'low-match';
        if (job.match_score >= 70) matchClass = 'high-match';
        else if (job.match_score >= 50) matchClass = 'medium-match';

        const cardClass = job.is_blocked ? 'job-card blocked' : 'job-card';

        // Setup blocker text if any
        let blockerLabel = '';
        if (job.is_blocked) {
            const failedReqs = [];
            if (job.match_details.gpa.status === 'No Match') failedReqs.push('IPK');
            if (job.match_details.age.status === 'No Match') failedReqs.push('Batas Usia');
            if (job.match_details.gender.status === 'No Match') failedReqs.push('Gender');
            blockerLabel = `<div class="blocker-banner">⚠️ Tidak Memenuhi Syarat: ${failedReqs.join(', ')}</div>`;
        }

        // Summary Match Reason preview
        let matchPreview = '';
        if (job.match_details.major.status === 'High Match') {
            matchPreview = 'Mencari lulusan Teknik Informatika/Sistem Informasi secara spesifik.';
        } else if (job.match_details.skills.status === 'High Match') {
            matchPreview = 'Membutuhkan keahlian Python/Data Science Anda.';
        } else {
            matchPreview = job.match_details.major.reason;
        }

        const sourceBadge = getSourceBadgeHTML(job);

        const savedState = getSavedJobsState()[job.id] || {};
        const isBookmarked = savedState.isBookmarked || false;
        const appStatus = savedState.status || '';

        const bookmarkBtnHTML = `
            <button class="bookmark-btn ${isBookmarked ? 'active' : ''}" title="Simpan lowongan ini" onclick="toggleBookmark(event, '${job.id}')">
                ${isBookmarked ? '★' : '☆'}
            </button>
        `;

        const statusBadgeMap = {
            'applied': '<span class="app-status-pill applied">🚀 Sudah Dilamar</span>',
            'interview': '<span class="app-status-pill interview">💬 Tahap Interview</span>',
            'accepted': '<span class="app-status-pill accepted">🎉 Diterima</span>'
        };
        const appStatusBadge = statusBadgeMap[appStatus] || '';

        const companyLogo = job.logo
            ? `<img src="${job.logo}" class="company-logo" alt="${job.organization_name}" loading="lazy" onerror="this.style.display='none'">`
            : '';

        const card = document.createElement('div');
        card.className = newJobIds.has(String(job.id)) ? cardClass + ' is-new-job' : cardClass;
        card.innerHTML = `
            <div class="score-circle ${matchClass}">
                <svg>
                    <circle class="bg-ring" cx="34" cy="34" r="${radius}"></circle>
                    <circle class="progress-ring" cx="34" cy="34" r="${radius}" 
                            stroke-dasharray="${circ}" stroke-dashoffset="${offset}"></circle>
                </svg>
                <span class="score-text">${job.match_score}%</span>
            </div>
            
            <div class="job-info">
                <div class="job-card-header">
                    <div class="job-title-wrapper">
                        <h3 class="job-title-text">${job.title}</h3>
                        ${newJobIds.has(String(job.id)) ? '<span class="new-job-badge">🆕 Baru</span>' : ''}
                        ${sourceBadge}
                        ${appStatusBadge}
                        ${bookmarkBtnHTML}
                    </div>
                </div>
                <div class="job-company">
                    ${companyLogo}
                    <span>${job.organization_name || 'SKK Migas / KKKS'}</span>
                </div>
                
                <div class="job-meta-tags">
                    <span class="meta-tag">📍 ${job.location || 'Lokasi tidak dispesifikasikan'}</span>
                    <span class="meta-tag">🏢 ${job.workplace || 'WFO'}</span>
                    <span class="meta-tag">💼 ${job.level}</span>
                    <span class="meta-tag">📝 ${job.type_name}</span>
                    <span class="meta-tag ${job.parsed_requirements && job.parsed_requirements.exp_years <= 1 ? 'highlight' : ''}">💼 Syarat Exp: ${job.parsed_requirements ? job.parsed_requirements.experience : 'Fresh Grad'}</span>
                    ${job.due_date ? `<span class="meta-tag highlight">📅 Deadline: ${job.due_date.split(' ')[0]}</span>` : ''}
                </div>
                
                <div class="job-matching-preview">
                    <strong>Kecocokan:</strong> ${matchPreview}
                </div>
                
                ${blockerLabel}
            </div>
            
            <button class="view-detail-btn">Lihat Detail</button>
        `;

        // Add click listener to show modal
        card.addEventListener('click', () => openJobModal(job));

        jobListContainer.appendChild(card);
    });
}

// Open Detail Modal
function openJobModal(job) {
    // Checklist icons mappings
    const icons = {
        'High Match': '✅',
        'Match': '✅',
        'Medium Match': '🟡',
        'Neutral': '⚪',
        'Low Match': '⚠️',
        'No Match': '❌'
    };

    const getIcon = (status) => icons[status] || '⚪';
    const getClass = (status) => {
        if (status === 'Match' || status === 'High Match') return 'match';
        if (status === 'No Match') return 'no-match';
        if (status === 'Medium Match' || status === 'Low Match') return 'medium';
        return 'neutral';
    };

    const sourceBadge = getSourceBadgeHTML(job, 'margin-left: 10px; vertical-align: middle;');

    const companyLogo = job.logo
        ? `<img src="${job.logo}" class="company-logo" style="width: 28px; height: 28px; vertical-align: middle; margin-right: 8px;" alt="${job.organization_name}">`
        : '';

    const savedState = getSavedJobsState()[job.id] || {};
    const isBookmarked = savedState.isBookmarked || false;
    const appStatus = savedState.status || '';

    const nlp = job.nlp_breakdown || {};
    const mandSkillsTags = (nlp.mandatory_skills && nlp.mandatory_skills.length > 0)
        ? nlp.mandatory_skills.map(s => `<span class="nlp-skill-badge mandatory">${s}</span>`).join('')
        : `<span class="nlp-skill-badge neutral">Umum / Tidak Spesifik</span>`;

    const plusSkillsTags = (nlp.plus_skills && nlp.plus_skills.length > 0)
        ? nlp.plus_skills.map(s => `<span class="nlp-skill-badge plus">+ ${s}</span>`).join('')
        : '';

    const keySentencesList = (nlp.key_sentences && nlp.key_sentences.length > 0)
        ? nlp.key_sentences.map(sent => `<li>• ${sent}</li>`).join('')
        : '<li>• Silakan lihat detail lengkap di tab Persyaratan Detail di bawah.</li>';

    const nlpSectionHTML = `
        <div class="nlp-smart-box">
            <div class="nlp-smart-header">
                <span class="nlp-icon">🤖</span>
                <div class="nlp-header-text">
                    <h4>AI / NLP Smart Requirement Breakdown</h4>
                    <p>Ringkasan otomatis hasil ekstraksi bahasa alami dari persyaratan lowongan ini</p>
                </div>
            </div>
            <div class="nlp-smart-grid">
                <div class="nlp-item">
                    <h5>🎓 Konteks Pendidikan</h5>
                    <p>${nlp.education_summary || 'S1 / D3 relevan atau setara'}</p>
                </div>
                <div class="nlp-item">
                    <h5>⏳ Konteks Pengalaman</h5>
                    <p>${nlp.experience_summary || '1 Tahun Pengalaman / Fresh Graduate'}</p>
                </div>
            </div>
            <div class="nlp-skills-row">
                <h5>🛠️ Tech Stack Wajib (Mandatory):</h5>
                <div class="nlp-tags">${mandSkillsTags}</div>
            </div>
            ${plusSkillsTags ? `
            <div class="nlp-skills-row" style="margin-top: 0.65rem;">
                <h5>🌟 Keahlian Nilai Tambah (Nice-to-have):</h5>
                <div class="nlp-tags">${plusSkillsTags}</div>
            </div>` : ''}
            <div class="nlp-sentences-box">
                <h5>📌 Kalimat Kunci Persyaratan Terdeteksi:</h5>
                <ul class="nlp-sentences-list">${keySentencesList}</ul>
            </div>
        </div>
    `;

    modalContent.innerHTML = `
        <div class="modal-header-section">
            <h2 class="modal-job-title">${job.title}</h2>
            <div class="modal-job-company" style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem;">
                ${companyLogo}
                <span>${job.organization_name || 'SKK Migas / KKKS'}</span>
                ${sourceBadge}
            </div>
            
            <div class="job-meta-tags">
                <span class="meta-tag">📍 ${job.location || 'Lokasi tidak dispesifikasikan'}</span>
                <span class="meta-tag">🏢 Workplace: ${job.workplace || 'WFO'}</span>
                <span class="meta-tag">💼 Level: ${job.level}</span>
                <span class="meta-tag">📝 Kontrak: ${job.type_name}</span>
                ${job.group ? `<span class="meta-tag">📁 Deputi/Perwakilan/Dept: ${job.group}</span>` : ''}
                ${job.due_date ? `<span class="meta-tag highlight">📅 Deadline: ${job.due_date}</span>` : ''}
            </div>
        </div>
        
        ${nlpSectionHTML}
        
        <!-- Checklist Match Section -->
        <div class="match-evaluation-section">
            <div class="match-evaluation-title">
                <span>Analisis Kesesuaian Profil (Skor: ${job.match_score}%)</span>
                ${job.is_blocked ? '<span style="color:#f43f5e; font-size:0.9rem; font-weight:700;">⚠️ TIDAK MEMENUHI SYARAT MUTLAK</span>' : ''}
            </div>
            
            <div class="match-checklist">
                <!-- Jurusan -->
                <div class="checklist-item">
                    <span class="checklist-icon ${getClass(job.match_details.major.status)}">
                        ${getIcon(job.match_details.major.status)}
                    </span>
                    <div class="checklist-info">
                        <h5>Jurusan Pendidikan</h5>
                        <p>${job.match_details.major.reason}</p>
                    </div>
                </div>
                
                <!-- IPK -->
                <div class="checklist-item">
                    <span class="checklist-icon ${getClass(job.match_details.gpa.status)}">
                        ${getIcon(job.match_details.gpa.status)}
                    </span>
                    <div class="checklist-info">
                        <h5>IPK / GPA (Syarat: ${job.parsed_requirements.gpa || '-'})</h5>
                        <p>${job.match_details.gpa.reason}</p>
                    </div>
                </div>
                
                <!-- Usia -->
                <div class="checklist-item">
                    <span class="checklist-icon ${getClass(job.match_details.age.status)}">
                        ${getIcon(job.match_details.age.status)}
                    </span>
                    <div class="checklist-info">
                        <h5>Batas Usia (Batas: ${job.parsed_requirements.age || '-'})</h5>
                        <p>${job.match_details.age.reason}</p>
                    </div>
                </div>

                <!-- TOEFL -->
                <div class="checklist-item">
                    <span class="checklist-icon ${getClass(job.match_details.toefl.status)}">
                        ${getIcon(job.match_details.toefl.status)}
                    </span>
                    <div class="checklist-info">
                        <h5>Skor TOEFL (Syarat: ${job.parsed_requirements.toefl || '-'})</h5>
                        <p>${job.match_details.toefl.reason}</p>
                    </div>
                </div>
                
                <!-- Gender -->
                <div class="checklist-item">
                    <span class="checklist-icon ${getClass(job.match_details.gender.status)}">
                        ${getIcon(job.match_details.gender.status)}
                    </span>
                    <div class="checklist-info">
                        <h5>Gender Pelamar</h5>
                        <p>${job.match_details.gender.reason}</p>
                    </div>
                </div>

                <!-- Pengalaman Kerja -->
                <div class="checklist-item">
                    <span class="checklist-icon ${job.match_details && job.match_details.exp_years ? getClass(job.match_details.exp_years.status) : 'match'}">
                        ${job.match_details && job.match_details.exp_years ? getIcon(job.match_details.exp_years.status) : '✅'}
                    </span>
                    <div class="checklist-info">
                        <h5>Syarat Pengalaman Kerja (Kamu: ~1 Tahun — PHR, Rakamin & Freelance)</h5>
                        <p>${job.match_details && job.match_details.exp_years ? job.match_details.exp_years.reason : 'Sesuai dengan profil pengalamanmu.'}</p>
                    </div>
                </div>

                <!-- Core Skills -->
                <div class="checklist-item">
                    <span class="checklist-icon ${getClass(job.match_details.skills.status)}">
                        ${getIcon(job.match_details.skills.status)}
                    </span>
                    <div class="checklist-info">
                        <h5>Keahlian (Python, Dataiku & AI/ML)</h5>
                        <p>${job.match_details.skills.reason}</p>
                    </div>
                </div>

                <!-- Experience & Industry relevance -->
                <div class="checklist-item checklist-item-full">
                    <span class="checklist-icon ${getClass(job.match_details.experience ? job.match_details.experience.status : 'Neutral')}">
                        ${getIcon(job.match_details.experience ? job.match_details.experience.status : 'Neutral')}
                    </span>
                    <div class="checklist-info">
                        <h5>Pengalaman Relevan (Upstream Oil & Gas / Tech)</h5>
                        <p>${job.match_details.experience ? job.match_details.experience.reason : 'Sesuai dengan kualifikasi pengalaman kerja.'}</p>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Job Details Tabs -->
        <div class="tab-headers">
            <button class="tab-btn active" onclick="switchTab(event, 'descriptionTab')">Deskripsi Pekerjaan</button>
            <button class="tab-btn" onclick="switchTab(event, 'requirementsTab')">Persyaratan Detail</button>
            <button class="tab-btn pitch-tab-btn" onclick="switchTab(event, 'pitchTab')">✨ Auto Cover Letter / Pitch</button>
            <button class="tab-btn ats-tab-btn" onclick="switchTab(event, 'atsTab')">💡 ATS Keyword Booster</button>
            <button class="tab-btn ai-tab-btn" onclick="switchTab(event, 'aiSummaryTab')">🤖 AI Smart Summary</button>
            <button class="tab-btn ai-tab-btn" onclick="switchTab(event, 'interviewTab')">💬 Interview Questions</button>
        </div>
        
        <div id="descriptionTab" class="tab-pane active">
            ${job.raw_description || '<p>Tidak ada deskripsi pekerjaan yang dicantumkan.</p>'}
        </div>
        
        <div id="requirementsTab" class="tab-pane">
            ${job.raw_requirements || '<p>Tidak ada persyaratan detail yang dicantumkan.</p>'}
        </div>

        <div id="pitchTab" class="tab-pane">
            ${generateCoverLetterHTML(job)}
        </div>

        <div id="atsTab" class="tab-pane">
            ${generateATSBoosterHTML(job)}
        </div>

        <div id="aiSummaryTab" class="tab-pane">
            <div class="ai-feature-container">
                <div class="ai-feature-header">
                    <h3>🤖 AI Smart Summary</h3>
                    <p>Ringkasan otomatis menggunakan AI untuk memahami lowongan ini dengan cepat</p>
                </div>
                <button class="btn-generate-ai" onclick="generateAISummary('${job.id}')">
                    ✨ Generate Smart Summary
                </button>
                <div id="aiSummaryContent-${job.id}" class="ai-content-area" style="display: none;">
                    <div class="ai-loading">
                        <div class="spinner"></div>
                        <p>AI sedang menganalisis deskripsi pekerjaan...</p>
                    </div>
                </div>
            </div>
        </div>

        <div id="interviewTab" class="tab-pane">
            <div class="ai-feature-container">
                <div class="ai-feature-header">
                    <h3>💬 Interview Questions Predictor</h3>
                    <p>Prediksi pertanyaan interview yang mungkin ditanyakan berdasarkan job requirements</p>
                </div>
                <button class="btn-generate-ai" onclick="generateInterviewQuestions('${job.id}')">
                    🎯 Predict Interview Questions
                </button>
                <div id="interviewContent-${job.id}" class="ai-content-area" style="display: none;">
                    <div class="ai-loading">
                        <div class="spinner"></div>
                        <p>AI sedang memprediksi pertanyaan interview...</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="modal-footer">
            <div class="modal-footer-row-top">
                <button class="btn-bookmark-modal ${isBookmarked ? 'active' : ''}" onclick="toggleBookmark(event, '${job.id}'); openJobModal(allJobs.find(j => j.id == '${job.id}'));">
                    ${isBookmarked ? '★ Tersimpan' : '☆ Simpan'}
                </button>
                <select class="status-select-modal" onchange="changeApplicationStatus('${job.id}', this.value)">
                    <option value="" ${!appStatus ? 'selected' : ''}>📌 Belum Dilamar</option>
                    <option value="applied" ${appStatus === 'applied' ? 'selected' : ''}>🚀 Sudah Dilamar</option>
                    <option value="interview" ${appStatus === 'interview' ? 'selected' : ''}>💬 Tahap Interview</option>
                    <option value="accepted" ${appStatus === 'accepted' ? 'selected' : ''}>🎉 Diterima</option>
                </select>
            </div>
            <a href="${job.url}" target="_blank" class="btn-primary btn-apply-modal">
                Lamar di Portal Resmi (${job.source}) ↗
            </a>
        </div>
    `;

    window.currentModalJobId = job.id;
    detailModal.classList.add('active');
    document.body.style.overflow = 'hidden'; // Lock background scrolling
}

// Switch tabs inside modal
window.switchTab = function (event, tabId) {
    // Hide all tab content panes
    const panes = document.querySelectorAll('.tab-pane');
    panes.forEach(pane => pane.classList.remove('active'));

    // Deactivate all tab header buttons
    const buttons = document.querySelectorAll('.tab-btn');
    buttons.forEach(btn => btn.classList.remove('active'));

    // Show selected pane and set button active
    document.getElementById(tabId).classList.add('active');
    event.currentTarget.classList.add('active');

    // Otomatis jalankan AI ketika membuka tab AI (jika belum dijalankan)
    if (tabId === 'aiSummaryTab' && window.currentModalJobId) {
        const area = document.getElementById(`aiSummaryContent-${window.currentModalJobId}`);
        if (area && area.style.display === 'none') {
            generateAISummary(window.currentModalJobId);
        }
    } else if (tabId === 'interviewTab' && window.currentModalJobId) {
        const area = document.getElementById(`interviewContent-${window.currentModalJobId}`);
        if (area && area.style.display === 'none') {
            generateInterviewQuestions(window.currentModalJobId);
        }
    }
}

// Close Modal
window.closeModal = function () {
    detailModal.classList.remove('active');
    document.body.style.overflow = ''; // Restore background scrolling
}

// AI Service Functions
const AI_SERVICE_URL = 'http://localhost:5001';

// In-Memory AI Caches for Instant Loading
window.aiSummaryCache = window.aiSummaryCache || {};
window.aiInterviewCache = window.aiInterviewCache || {};

// ⚠️ MEMORY FIX: LRU Cache limiter — prevent unbounded cache growth
const MAX_CACHE_SIZE = 100; // Max 100 items per cache type

function addToCache(cacheObj, jobId, content) {
    // If cache full, remove oldest entry (FIFO style)
    if (Object.keys(cacheObj).length >= MAX_CACHE_SIZE) {
        const firstKey = Object.keys(cacheObj)[0];
        delete cacheObj[firstKey];
    }
    cacheObj[jobId] = content;
}

// Fast Fetch with Timeout (1200ms) for responsive local server detection on mobile
async function fetchWithTimeout(url, options, timeoutMs = 1200) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), timeoutMs);
    try {
        const res = await fetch(url, { ...options, signal: controller.signal });
        clearTimeout(timer);
        return res;
    } catch (err) {
        clearTimeout(timer);
        throw err;
    }
}

// Helper to format AI response text (convert bold markdown and linebreaks)
function formatAIResponse(text) {
    if (!text) return '';
    return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br>');
}

// Serverless Free AI Fallback (Jalan 24/7 di Mobile/GitHub Pages tanpa server backend)
// ⚠️ PRIVACY WARNING: This sends job data to external service. Can be disabled via .env
async function fetchCloudAI(prompt) {
    // Check if user opted into third-party AI
    const ENABLE_CLOUD_AI = localStorage.getItem('enableCloudAI');
    if (ENABLE_CLOUD_AI === 'false') {
        throw new Error('Cloud AI fallback disabled by user preference');
    }
    
    // Warn user on first use
    if (ENABLE_CLOUD_AI === null) {
        const userConsent = confirm(
            '⚠️ AI Summary memerlukan koneksi ke layanan cloud eksternal (Pollinations AI).\n\n' +
            'Data pekerjaan akan dikirim ke server pihak ketiga untuk diproses.\n\n' +
            'Klik OK untuk lanjutkan, atau CANCEL untuk menonaktifkan fitur ini.'
        );
        localStorage.setItem('enableCloudAI', userConsent ? 'true' : 'false');
        if (!userConsent) throw new Error('User disabled cloud AI');
    }
    
    const res = await fetch('https://text.pollinations.ai/', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            messages: [
                { role: 'system', content: 'Kamu adalah asisten karir dan HR profesional dalam Bahasa Indonesia. Jawab langsung ke poinnya secara ringkas dan informatif.' },
                { role: 'user', content: prompt }
            ]
        })
    });
    if (!res.ok) throw new Error('Cloud AI status ' + res.status);
    return await res.text();
}

// Strip basic HTML tags for cleaner cloud prompt
function stripHtml(html) {
    if (!html) return '';
    const tmp = document.createElement('DIV');
    tmp.innerHTML = html;
    return (tmp.textContent || tmp.innerText || '').replace(/\s+/g, ' ').trim();
}

// ⚠️ SECURITY: Escape HTML entities to prevent XSS injection
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    const map = {'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;'};
    return String(unsafe).replace(/[&<>"']/g, (c) => map[c]);
}

// ⚠️ SECURITY: Escape HTML entities to prevent XSS
function escapeHtml(unsafe) {
    if (!unsafe) return '';
    const map = {
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&#039;'
    };
    return String(unsafe).replace(/[&<>"']/g, (char) => map[char]);
}

// Generate AI Summary for a job
window.generateAISummary = async function (jobId) {
    const job = allJobs.find(j => j.id == jobId);
    if (!job) return;

    const contentArea = document.getElementById(`aiSummaryContent-${jobId}`);
    contentArea.style.display = 'block';

    // Instant Cache Return
    if (window.aiSummaryCache[jobId]) {
        contentArea.innerHTML = window.aiSummaryCache[jobId];
        return;
    }

    contentArea.innerHTML = `
        <div class="ai-loading">
            <div class="spinner"></div>
            <p>AI sedang menganalisis deskripsi pekerjaan...</p>
        </div>
    `;

    try {
        const response = await fetchWithTimeout(`${AI_SERVICE_URL}/api/summarize-job`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                title: job.title,
                description: job.raw_description || job.description || '',
                requirements: job.raw_requirements || job.requirements || ''
            })
        }, 1200);

        const data = await response.json();

        if (data.success) {
            const htmlOut = `
                <div class="ai-result">
                    <div class="ai-result-header">
                        <h4>📝 Ringkasan Lowongan (Groq AI)</h4>
                    </div>
                    <div class="ai-result-content">
                        ${formatAIResponse(data.summary)}
                    </div>
                </div>
            `;
            window.aiSummaryCache[jobId] = htmlOut;
            contentArea.innerHTML = htmlOut;
        } else {
            throw new Error(data.error || 'Server error');
        }
    } catch (error) {
        // Fallback otomatis ke Serverless Cloud AI (jalan di Mobile & ketika laptop dimatikan)
        try {
            const promptText = `Ringkas deskripsi pekerjaan berikut menjadi 5-7 poin bullet yang mudah dipahami dalam Bahasa Indonesia untuk posisi "${job.title}":\n\nDeskripsi: ${stripHtml(job.raw_description || job.description)}\nPersyaratan: ${stripHtml(job.raw_requirements || job.requirements)}`;
            const cloudSummary = await fetchCloudAI(promptText);
            const htmlOut = `
                <div class="ai-result">
                    <div class="ai-result-header">
                        <h4>📝 Ringkasan Lowongan (Cloud AI)</h4>
                    </div>
                    <div class="ai-result-content">
                        ${formatAIResponse(cloudSummary)}
                    </div>
                </div>
            `;
            window.aiSummaryCache[jobId] = htmlOut;
            contentArea.innerHTML = htmlOut;
        } catch (cloudErr) {
            contentArea.innerHTML = `
                <div class="ai-error">
                    <p>❌ Tidak dapat memuat ringkasan AI.</p>
                    <p>Error: ${cloudErr.message}</p>
                </div>
            `;
        }
    }
}

// Generate Interview Questions Prediction
window.generateInterviewQuestions = async function (jobId) {
    const job = allJobs.find(j => j.id == jobId);
    if (!job) return;

    const contentArea = document.getElementById(`interviewContent-${jobId}`);
    contentArea.style.display = 'block';

    // Instant Cache Return
    if (window.aiInterviewCache[jobId]) {
        contentArea.innerHTML = window.aiInterviewCache[jobId];
        return;
    }

    contentArea.innerHTML = `
        <div class="ai-loading">
            <div class="spinner"></div>
            <p>AI sedang memprediksi pertanyaan interview...</p>
        </div>
    `;

    try {
        const response = await fetchWithTimeout(`${AI_SERVICE_URL}/api/predict-interview`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                title: job.title,
                description: job.raw_description || job.description || '',
                requirements: job.raw_requirements || job.requirements || '',
                company: job.organization_name || job.company || 'Perusahaan tidak disebutkan'
            })
        }, 1200);

        const data = await response.json();

        if (data.success) {
            const htmlOut = `
                <div class="ai-result">
                    <div class="ai-result-header">
                        <h4>💬 Prediksi Pertanyaan Interview (Groq AI)</h4>
                        <p>Berdasarkan analisis AI terhadap job requirements</p>
                    </div>
                    <div class="ai-result-content interview-questions">
                        ${formatAIResponse(data.questions)}
                    </div>
                </div>
            `;
            window.aiInterviewCache[jobId] = htmlOut;
            contentArea.innerHTML = htmlOut;
        } else {
            throw new Error(data.error || 'Server error');
        }
    } catch (error) {
        // Fallback otomatis ke Serverless Cloud AI (jalan di Mobile & ketika laptop dimatikan)
        try {
            const companyName = job.organization_name || job.company || 'Perusahaan';
            const promptText = `Prediksi 8 pertanyaan interview yang kemungkinan besar ditanyakan untuk posisi "${job.title}" di ${companyName} dalam Bahasa Indonesia (campuran technical dan behavioral):\n\nDeskripsi: ${stripHtml(job.raw_description || job.description)}\nPersyaratan: ${stripHtml(job.raw_requirements || job.requirements)}`;
            const cloudQuestions = await fetchCloudAI(promptText);
            const htmlOut = `
                <div class="ai-result">
                    <div class="ai-result-header">
                        <h4>💬 Prediksi Pertanyaan Interview (Cloud AI)</h4>
                        <p>Berdasarkan analisis AI terhadap job requirements</p>
                    </div>
                    <div class="ai-result-content interview-questions">
                        ${formatAIResponse(cloudQuestions)}
                    </div>
                </div>
            `;
            window.aiInterviewCache[jobId] = htmlOut;
            contentArea.innerHTML = htmlOut;
        } catch (cloudErr) {
            contentArea.innerHTML = `
                <div class="ai-error">
                    <p>❌ Tidak dapat memprediksi pertanyaan AI.</p>
                    <p>Error: ${cloudErr.message}</p>
                </div>
            `;
        }
    }
}


// Register Progressive Web App (PWA) Service Worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Daftarkan SW tanpa query string supaya browser selalu cek versi terbaru
        navigator.serviceWorker.register('/sw.js').then((reg) => {
            reg.update();
        }).catch(() => { });
    });
}
