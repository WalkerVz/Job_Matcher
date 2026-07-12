// Global state
let allJobs = [];
let filteredJobs = [];
let currentPage = 1;
let itemsPerPage = 25;
let wishlistOnly = false;

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
        const response = await fetch('matched_jobs.json');
        if (response.ok) {
            allJobs = await response.json();
        } else {
            throw new Error('Local JSON fetch failed');
        }
    } catch (e) {
        console.warn('Fetch failed or was blocked by CORS. Checking for global window variable fallback...');
        if (window.matchedJobs && window.matchedJobs.length > 0) {
            allJobs = window.matchedJobs;
        } else {
            // Show error/instructions to user
            renderError('Gagal memuat data lowongan.', 'Pastikan Anda telah menjalankan <code>scraper.py</code> atau jalankan server lokal (misalnya dengan <code>python -m http.server</code>) untuk menghindari pemblokiran CORS oleh peramban.');
            return;
        }
    }

    // Show skeleton while loading
    showSkeleton();
    updateWishlistCountBadge();
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

window.toggleBookmark = function(event, jobId) {
    if (event) event.stopPropagation();
    const state = getSavedJobsState();
    const idStr = String(jobId);
    const isBookmarked = state[idStr] ? !state[idStr].isBookmarked : true;
    state[idStr] = { ...(state[idStr] || {}), isBookmarked };
    localStorage.setItem('savedJobMatcherState', JSON.stringify(state));
    updateWishlistCountBadge();
    applyFilters();
};

window.changeApplicationStatus = function(jobId, statusValue) {
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
    
    const pitchID = `Yth. Tim Rekrutmen ${companyName},\n\nPerkenalkan saya Muhammad Ravil, lulusan S1 Teknik Informatika UIN Suska Riau (IPK 3.39 | TOEFL 537) dengan pengalaman profesional sebagai AI Engineer di PT Pertamina Hulu Rokan (PHR) serta Data Scientist Intern di Rakamin Academy. Saya memiliki keahlian teruji dalam ${requiredSkills} yang sangat sejalan dengan kebutuhan posisi ${jobTitle}.\n\nMelalui proyek nyata seperti otomatisasi aplikasi QC Log Analyzer dan pemodelan prediktif risiko kredit, saya siap memberikan kontribusi nyata bagi efisiensi operasional ${companyName}. Terlampir CV lengkap saya untuk pertimbangan Bapak/Ibu. Terima kasih.`;

    const pitchEN = `Dear ${companyName} Recruitment Team,\n\nMy name is Muhammad Ravil, a Computer Science graduate from UIN Suska Riau (GPA 3.39 | TOEFL 537) with hands-on industry experience as an AI Engineer at PT Pertamina Hulu Rokan (PHR) and Data Scientist Intern at Rakamin Academy. I bring practical technical expertise in ${requiredSkills}, aligning directly with the requirements for the ${jobTitle} role.\n\nWith a track record of building automated analytics applications (Python/Dataiku) and predictive machine learning models, I look forward to contributing to data-driven growth at ${companyName}. Please find my resume attached for your review. Thank you.`;

    const formalID = `Hal: Lamaran Pekerjaan – ${jobTitle}\nKepada Yth.\nTim HR / Rekrutmen\n${companyName}\n\nDengan hormat,\n\nSehubungan dengan informasi lowongan pekerjaan untuk posisi ${jobTitle} di ${companyName}, saya bermaksud mengajukan lamaran untuk bergabung dengan perusahaan Bapak/Ibu.\n\nSaya adalah lulusan S1 Teknik Informatika dari UIN Suska Riau (IPK 3.39, TOEFL 537) dengan latar belakang pengalaman di industri hulu migas sebagai AI Engineer di PT Pertamina Hulu Rokan (PHR). Selama masa kerja tersebut, saya berhasil mengembangkan aplikasi QC Log Analyzer berbasis Python dan Dataiku untuk otomatisasi pemrosesan serta visualisasi data operasional.\n\nSelain itu, sebagai Data Scientist Intern di Id/x partners x Rakamin Academy (Best Student Score 86.96), saya memiliki rekam jejak mengembangkan model machine learning yang berhasil menurunkan tingkat gagal bayar pinjaman hingga 12%. Pengalaman ini membuat saya sangat terbiasa mengimplementasikan keahlian pada ${requiredSkills}.\n\nKemampuan analisis data yang kuat, keahlian teknis lintas platform (Python, SQL, Dataiku, Web Dev), serta komunikasi kolaboratif membuat saya yakin dapat memberikan kontribusi signifikan bagi ${companyName}.\n\nBesar harapan saya untuk diberikan kesempatan wawancara agar dapat menjelaskan lebih rinci mengenai portofolio saya. Atas perhatian dan kesempatan yang Bapak/Ibu berikan, saya ucapkan terima kasih.\n\nHormat saya,\n\nMuhammad Ravil`;

    return `
        <div class="cover-letter-container">
            <div class="cover-letter-header">
                <div>
                    <h4>✨ Auto-Generated Application Pitch & Cover Letter</h4>
                    <p>Dibuat otomatis dari profil asli CV-mu (Muhammad Ravil | UIN Suska Riau | IPK 3.39 | AI Engineer PHR & Rakamin) dicocokkan dengan keahlian lowongan ini.</p>
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

    // Ravil's authentic profile keywords from CV PDF
    const ravilProfileKeywords = [
        'python', 'sql', 'data analysis', 'data science', 'machine learning', 
        'dataiku', 'excel', 'power bi', 'react', 'laravel', 'php', 'git', 'arcgis',
        'teknik informatika', 'sistem informasi', 'problem solving', 'analisis data', 
        'data analyst', 'ai engineer', 'web development', 'web developer'
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
    const bullet1 = `• Developed automated data processing & monitoring applications (QC Log Analyzer) using Python and Dataiku at PT Pertamina Hulu Rokan, streamlining operational reporting.`;
    const bullet2 = `• Engineered machine learning classification & predictive models (Credit Risk Loan project) reducing loan default rates by 12% across 466,285 records.`;
    const bullet3 = `• Spearheaded end-to-end ${matchedATS[0] || 'data analytics'} workflows and dashboard reporting (${bonusFound[0] || 'SQL/Power BI'}) to drive cross-functional operational efficiency.`;

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

window.copyToClipboard = function(btnElem, encodedText) {
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
                'ioh': 'Indosat Ooredoo Hutchison'
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

        let sourceBadge = `<span class="source-badge talentics">Hulu Migas</span>`;
        if (job.source === 'Grab') sourceBadge = `<span class="source-badge grab">Grab Indonesia</span>`;
        else if (job.source === 'Astra') sourceBadge = `<span class="source-badge astra">Astra Career</span>`;
        else if (job.source === 'Pertamina PTC') sourceBadge = `<span class="source-badge ptc">Pertamina PTC</span>`;
        else if (job.source === 'SawitPRO') sourceBadge = `<span class="source-badge sawitpro">SawitPRO</span>`;
        else if (job.source === 'Indosat Ooredoo Hutchison') sourceBadge = `<span class="source-badge ioh">Indosat Ooredoo Hutchison</span>`;

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
        card.className = cardClass;
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

    let sourceBadge = `<span class="source-badge talentics" style="margin-left: 10px; vertical-align: middle;">Hulu Migas</span>`;
    if (job.source === 'Grab') {
        sourceBadge = `<span class="source-badge grab" style="margin-left: 10px; vertical-align: middle;">Grab Indonesia</span>`;
    } else if (job.source === 'Astra') {
        sourceBadge = `<span class="source-badge astra" style="margin-left: 10px; vertical-align: middle;">Astra Career</span>`;
    } else if (job.source === 'Pertamina PTC') {
        sourceBadge = `<span class="source-badge ptc" style="margin-left: 10px; vertical-align: middle;">Pertamina PTC</span>`;
    } else if (job.source === 'SawitPRO') {
        sourceBadge = `<span class="source-badge sawitpro" style="margin-left: 10px; vertical-align: middle;">SawitPRO</span>`;
    }

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
                        <h5>Syarat Pengalaman Kerja (Kamu: 1 Tahun)</h5>
                        <p>${job.match_details && job.match_details.exp_years ? job.match_details.exp_years.reason : 'Sesuai dengan profil pengalamanmu.'}</p>
                    </div>
                </div>

                <!-- Core Skills -->
                <div class="checklist-item">
                    <span class="checklist-icon ${getClass(job.match_details.skills.status)}">
                        ${getIcon(job.match_details.skills.status)}
                    </span>
                    <div class="checklist-info">
                        <h5>Keahlian (Python & Data Science)</h5>
                        <p>${job.match_details.skills.reason}</p>
                    </div>
                </div>

                <!-- Experience & Industry relevance -->
                <div class="checklist-item checklist-item-full">
                    <span class="checklist-icon ${getClass(job.match_details.experience.status)}">
                        ${getIcon(job.match_details.experience.status)}
                    </span>
                    <div class="checklist-info">
                        <h5>Pengalaman Relevan (Upstream Oil & Gas / Tech)</h5>
                        <p>${job.match_details.experience.reason}</p>
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
        
        <div class="modal-footer">
            <div class="modal-footer-left">
                <button class="btn-bookmark-modal ${isBookmarked ? 'active' : ''}" onclick="toggleBookmark(event, '${job.id}'); openJobModal(allJobs.find(j => j.id == '${job.id}'));">
                    ${isBookmarked ? '★ Tersimpan' : '☆ Simpan ke Wishlist'}
                </button>
                <select class="status-select-modal" onchange="changeApplicationStatus('${job.id}', this.value)">
                    <option value="" ${!appStatus ? 'selected' : ''}>📌 Belum Dilamar</option>
                    <option value="applied" ${appStatus === 'applied' ? 'selected' : ''}>🚀 Sudah Dilamar</option>
                    <option value="interview" ${appStatus === 'interview' ? 'selected' : ''}>💬 Tahap Interview</option>
                    <option value="accepted" ${appStatus === 'accepted' ? 'selected' : ''}>🎉 Diterima</option>
                </select>
            </div>
            <div class="modal-footer-right">
                <button class="btn-secondary" onclick="closeModal()">Tutup</button>
                <a href="${job.url}" target="_blank" class="btn-primary">
                    Lamar di Portal Resmi (${job.source}) ↗
                </a>
            </div>
        </div>
    `;

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
}

// Close Modal
window.closeModal = function () {
    detailModal.classList.remove('active');
    document.body.style.overflow = ''; // Restore background scrolling
}

// Register Progressive Web App (PWA) Service Worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        navigator.serviceWorker.register('sw.js?v=4').then((reg) => {
            reg.update();
        }).catch(() => {});
    });
}
