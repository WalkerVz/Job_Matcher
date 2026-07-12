// Global state
let allJobs = [];
let filteredJobs = [];
let currentPage = 1;
let itemsPerPage = 25;

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
        jobListContainer.innerHTML = `
            <div class="empty-container">
                <div class="empty-icon">🔎</div>
                <h3>Tidak Ada Lowongan yang Cocok</h3>
                <p>Cobalah mengubah filter pencarian Anda atau kata kunci pencarian.</p>
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
        </div>
        
        <div id="descriptionTab" class="tab-pane active">
            ${job.raw_description || '<p>Tidak ada deskripsi pekerjaan yang dicantumkan.</p>'}
        </div>
        
        <div id="requirementsTab" class="tab-pane">
            ${job.raw_requirements || '<p>Tidak ada persyaratan detail yang dicantumkan.</p>'}
        </div>
        
        <div class="modal-footer">
            <button class="btn-secondary" onclick="closeModal()">Tutup</button>
            <a href="${job.url}" target="_blank" class="btn-primary">
                Lamar di Portal Resmi (${job.source}) ↗
            </a>
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
