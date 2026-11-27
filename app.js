// Global state
let allJobs = [];
let filteredJobs = [];
let currentPage = 1;
let itemsPerPage = 10;
let wishlistOnly = false;

// ─── Security, Formatting & Date Utilities ────────────────────────────────────
function escapeHtml(unsafe) {
    if (unsafe === null || unsafe === undefined) return '';
    const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
    return String(unsafe).replace(/[&<>"']/g, (c) => map[c]);
}

function sanitizeUrl(url) {
    if (!url) return '#';
    const trimmed = String(url).trim();
    if (/^(?:https?:|mailto:)/i.test(trimmed)) return trimmed;
    return '#';
}

function sanitizeHtml(rawHtml) {
    if (!rawHtml) return '';
    const template = document.createElement('template');
    template.innerHTML = rawHtml;
    const forbidden = template.content.querySelectorAll('script, iframe, object, embed, style, link, meta');
    forbidden.forEach(el => el.remove());

    const walker = document.createTreeWalker(template.content, NodeFilter.SHOW_ELEMENT);
    let node;
    while ((node = walker.nextNode())) {
        for (const attr of Array.from(node.attributes)) {
            const name = attr.name.toLowerCase();
            const val = attr.value.trim().toLowerCase();
            if (name.startsWith('on') || ((name === 'href' || name === 'src') && val.startsWith('javascript:'))) {
                node.removeAttribute(attr.name);
            }
        }
    }
    return template.innerHTML;
}

function showToast(message, durationMs = 2400) {
    let toast = document.getElementById('appToastNotification');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'appToastNotification';
        toast.className = 'toast-notification';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add('visible');
    clearTimeout(toast._hideTimer);
    toast._hideTimer = setTimeout(() => toast.classList.remove('visible'), durationMs);
}

function formatLocationShort(loc) {
    if (!loc) return 'Lokasi tidak dispesifikasikan';
    const cleaned = String(loc).replace(/\s+/g, ' ').trim();
    if (cleaned.length <= 65) return cleaned;
    if (cleaned.includes('(+') && cleaned.includes('lokasi lainnya)')) return cleaned;
    const parts = cleaned.split(/\s*,\s*/).filter(Boolean);
    if (parts.length > 3) {
        return `${parts.slice(0, 3).join(', ')} (+${parts.length - 3} lokasi)`;
    }
    return cleaned.slice(0, 62) + '...';
}

const ID_MONTH_MAP = {
    jan: 0, januari: 0, january: 0,
    feb: 1, februari: 1, february: 1,
    mar: 2, maret: 2, march: 2,
    apr: 3, april: 3,
    mei: 4, may: 4,
    jun: 5, juni: 5, june: 5,
    jul: 6, juli: 6, july: 6,
    agu: 7, ags: 7, agustus: 7, aug: 7, august: 7,
    sep: 8, sept: 8, september: 8,
    okt: 9, oktober: 9, oct: 9, october: 9,
    nov: 10, november: 10,
    des: 11, desember: 11, dec: 11, december: 11
};

function parseJobDate(dateStr) {
    if (!dateStr) return { timestamp: Number.MAX_SAFE_INTEGER - 1, isDeadline: false, isExpired: false };
    const raw = String(dateStr).trim();
    const lower = raw.toLowerCase();
    if (lower === 'aktif' || lower === 'active') {
        return { timestamp: Number.MAX_SAFE_INTEGER - 2, isDeadline: false, isExpired: false };
    }

    let parsedDate = null;
    // ISO YYYY-MM-DD
    const isoMatch = raw.match(/^(\d{4})-(\d{2})-(\d{2})/);
    if (isoMatch) {
        parsedDate = new Date(Number(isoMatch[1]), Number(isoMatch[2]) - 1, Number(isoMatch[3]), 23, 59, 59);
    } else {
        // Format "07 Des 2026" / "13 December 2026"
        const idMatch = raw.match(/^(\d{1,2})\s+([a-zA-Z]+)\s+(\d{4})/);
        if (idMatch) {
            const monthIdx = ID_MONTH_MAP[idMatch[2].toLowerCase()];
            if (monthIdx !== undefined) {
                parsedDate = new Date(Number(idMatch[3]), monthIdx, Number(idMatch[1]), 23, 59, 59);
            }
        }
    }

    if (parsedDate && !isNaN(parsedDate.getTime())) {
        const ts = parsedDate.getTime();
        const todayStart = new Date();
        todayStart.setHours(0, 0, 0, 0);
        return { timestamp: ts, isDeadline: true, isExpired: ts < todayStart.getTime() };
    }

    // Relative strings ("2 minggu yang lalu", "3 days ago") -> bukan deadline
    return { timestamp: Number.MAX_SAFE_INTEGER - 1, isDeadline: false, isExpired: false };
}

function prepareJobsIndex(jobs) {
    jobs.forEach(job => {
        const nlp = job.nlp_breakdown || {};
        const skills = [...(nlp.mandatory_skills || []), ...(nlp.preferred_skills || nlp.plus_skills || [])].join(' ');
        job._searchText = [
            job.title || '',
            job.organization_name || '',
            job.group || '',
            job.location || '',
            skills
        ].join(' ').toLowerCase();
        job._dueMeta = parseJobDate(job.due_date);
    });
}

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

function processNewJobsData(data) {
    if (!data || !data.new_ids || data.count === 0) return;
    const seenIds = getSeenIds();
    const trulyNew = data.new_ids.filter(id => !seenIds.has(String(id)));
    if (trulyNew.length === 0) return;

    newJobIds = new Set(trulyNew.map(String));
    showNewJobsBanner(trulyNew.length, data.scraped_at);
    updateNewJobsNavBadge(trulyNew.length);
}

function showNewJobsBanner(count, scrapedAt) {
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
                <span class="new-jobs-banner-time">${escapeHtml(scrapedAt || '')}</span>
            </div>
        </div>
        <div class="new-jobs-banner-actions">
            <button class="btn-see-new" onclick="filterToNewJobs()">Lihat Semua</button>
            <button class="btn-dismiss-new" onclick="markAllAsSeen()" title="Tandai semua sudah dilihat">✕</button>
        </div>
    `;

    const mainSection = document.querySelector('.main-section');
    const filterBar = document.querySelector('.filters-bar');
    if (mainSection && filterBar) {
        mainSection.insertBefore(banner, filterBar);
    }
}

window.filterToNewJobs = function () {
    searchInput.value = '';
    matchFilter.value = 'all';
    sourceFilter.value = 'all';
    if (expFilter) expFilter.value = 'all';
    sortSelect.value = 'score';
    wishlistOnly = false;
    if (wishlistToggleBtn) wishlistToggleBtn.classList.remove('active');
    currentPage = 1;

    filteredJobs = [
        ...allJobs.filter(j => newJobIds.has(String(j.id))),
        ...allJobs.filter(j => !newJobIds.has(String(j.id)))
    ];
    renderJobList();
    scrollToJobListTop();
};
// ─────────────────────────────────────────────────────────────────────────────

// Debounce helper – prevents search firing on every keypress
function debounce(fn, delay = 250) {
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
    // Setup single delegated click listener for job cards
    if (jobListContainer) {
        jobListContainer.addEventListener('click', (e) => {
            if (e.target.closest('.bookmark-btn')) return;
            const card = e.target.closest('.job-card[data-job-id]');
            if (!card) return;
            const job = allJobs.find(j => String(j.id) === card.dataset.jobId);
            if (job) openJobModal(job);
        });
    }

    // Fetch data (skeleton renders immediately inside loadJobsData)
    await loadJobsData();

    // Setup mobile filter toggle
    if (mobileFilterToggleBtn && filterControlsWrapper) {
        mobileFilterToggleBtn.addEventListener('click', () => {
            filterControlsWrapper.classList.toggle('active');
            mobileFilterToggleBtn.classList.toggle('active');
        });
    }

    // Setup event listeners
    searchInput.addEventListener('input', debounce(() => { currentPage = 1; applyFilters(); }, 200));
    matchFilter.addEventListener('change', () => { currentPage = 1; applyFilters(); });
    sourceFilter.addEventListener('change', () => { currentPage = 1; applyFilters(); });
    if (expFilter) expFilter.addEventListener('change', () => { currentPage = 1; applyFilters(); });
    sortSelect.addEventListener('change', () => { currentPage = 1; applyFilters(); });

    if (wishlistToggleBtn) {
        wishlistToggleBtn.addEventListener('click', () => {
            wishlistOnly = !wishlistOnly;
            wishlistToggleBtn.classList.toggle('active', wishlistOnly);
            currentPage = 1;

            if (wishlistOnly) {
                if (matchFilter) matchFilter.value = 'all';
                if (sourceFilter) sourceFilter.value = 'all';
                if (expFilter) expFilter.value = 'all';
                if (searchInput) searchInput.value = '';
            }

            applyFilters();
        });
    }

    if (resetFilterBtn) {
        resetFilterBtn.addEventListener('click', () => {
            searchInput.value = '';
            matchFilter.value = 'all';
            sourceFilter.value = 'all';
            if (expFilter) expFilter.value = 'all';
            sortSelect.value = 'score';
            perPageSelect.value = '10';
            wishlistOnly = false;
            if (wishlistToggleBtn) wishlistToggleBtn.classList.remove('active');

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

    detailModal.addEventListener('click', (e) => {
        if (e.target === detailModal) closeModal();
    });

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape' && detailModal.classList.contains('active')) {
            closeModal();
        }
    });
});

// Lazy fallback loader: hanya download matched_jobs.js (3+ MB) jika fetch JSON gagal (misal file://)
function loadFallbackJobsScript() {
    return new Promise((resolve, reject) => {
        if (window.matchedJobs && window.matchedJobs.length > 0) {
            resolve();
            return;
        }
        const script = document.createElement('script');
        script.src = 'matched_jobs.js?v=20261127_1';
        script.onload = resolve;
        script.onerror = reject;
        document.body.appendChild(script);
    });
}

// Load Jobs, Timestamp, and New-Jobs metadata in parallel
async function loadJobsData() {
    showSkeleton();
    const cacheBust = Date.now();

    const [jobsRes, luRes, newJobsRes] = await Promise.allSettled([
        fetch(`matched_jobs.json?t=${cacheBust}`, { cache: 'no-store' }),
        fetch(`last_updated.json?t=${cacheBust}`, { cache: 'no-store' }),
        fetch(`new_jobs.json?t=${cacheBust}`, { cache: 'no-store' })
    ]);

    let loadedFromJson = false;
    if (jobsRes.status === 'fulfilled' && jobsRes.value.ok) {
        try {
            allJobs = await jobsRes.value.json();
            loadedFromJson = Array.isArray(allJobs);
        } catch (err) {
            console.warn('Gagal parse matched_jobs.json:', err);
        }
    }

    if (!loadedFromJson) {
        console.warn('JSON fetch gagal atau diblokir CORS. Memuat fallback matched_jobs.js...');
        try {
            await loadFallbackJobsScript();
            if (window.matchedJobs && window.matchedJobs.length > 0) {
                allJobs = window.matchedJobs;
            }
        } catch (err) {
            console.error('Fallback matched_jobs.js gagal dimuat:', err);
        }
    }

    const badgeEl = document.getElementById('lastUpdatedDate');
    if (luRes.status === 'fulfilled' && luRes.value.ok) {
        try {
            const luData = await luRes.value.json();
            if (luData && luData.last_updated && badgeEl) {
                badgeEl.textContent = luData.last_updated;
            }
        } catch (err) {
            console.warn('Gagal parse last_updated.json:', err);
        }
    } else if (window.lastUpdated && badgeEl) {
        badgeEl.textContent = window.lastUpdated;
    }

    if (newJobsRes.status === 'fulfilled' && newJobsRes.value.ok) {
        try {
            const njData = await newJobsRes.value.json();
            processNewJobsData(njData);
        } catch (err) {
            console.warn('Gagal parse new_jobs.json:', err);
        }
    }

    if (!allJobs || allJobs.length === 0) {
        renderError('Gagal Memuat Lowongan', 'Pastikan matched_jobs.json tersedia atau jalankan server web lokal.');
        return;
    }

    prepareJobsIndex(allJobs);
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
            <h3>${escapeHtml(title)}</h3>
            <p>${escapeHtml(subtitle)}</p>
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

function getApplicationsState() {
    try {
        return JSON.parse(localStorage.getItem('jobMatcher_applications') || '{}');
    } catch (e) {
        return {};
    }
}

function updateWishlistCountBadge() {
    if (!wishlistCountEl) return;
    const state = getSavedJobsState();
    const validJobIds = (allJobs && allJobs.length > 0) ? new Set(allJobs.map(j => String(j.id))) : null;
    const count = Object.keys(state).filter(id => {
        const item = state[id];
        if (!item || !item.isBookmarked) return false;
        if (validJobIds && !validJobIds.has(String(id))) return false;
        return true;
    }).length;
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
    const idStr = String(jobId);
    const shouldBookmark = (statusValue !== 'not_applied' && statusValue !== 'rejected');
    const state = getSavedJobsState();
    state[idStr] = { ...(state[idStr] || {}), status: statusValue, isBookmarked: shouldBookmark };
    localStorage.setItem('savedJobMatcherState', JSON.stringify(state));

    const applicationsKey = 'jobMatcher_applications';
    const applications = getApplicationsState();

    if (!applications[idStr]) {
        const job = allJobs.find(j => String(j.id) === idStr);
        applications[idStr] = {
            jobId: jobId,
            jobTitle: job ? job.title : 'Unknown',
            company: job ? (job.organization_name || job.company || 'Unknown') : 'Unknown',
            appliedDate: new Date().toISOString().split('T')[0],
            status: statusValue,
            interviewDates: [],
            notes: '',
            followUpDate: null
        };
    } else {
        applications[idStr].status = statusValue;
    }

    localStorage.setItem(applicationsKey, JSON.stringify(applications));
    const trackerSelect = document.getElementById(`appStatus_${idStr}`);
    if (trackerSelect) trackerSelect.value = statusValue;
    updateWishlistCountBadge();
    refreshJobCardUI(idStr);
    showToast('📌 Status lamaran diperbarui');
};

function generateCoverLetterHTML(job) {
    const nlp = job.nlp_breakdown || {};
    const requiredSkills = (nlp.mandatory_skills && nlp.mandatory_skills.length > 0)
        ? nlp.mandatory_skills.join(', ')
        : 'pemrograman Python, analisis data (SQL/Dataiku), dan pengembangan solusi teknologi';

    const companyName = job.organization_name || 'Perusahaan';
    const jobTitle = job.title || 'Posisi yang dilamar';

    const pitchID = `Yth. Tim Rekrutmen ${companyName},\n\nPerkenalkan saya Muhammad Ravil, lulusan S1 Teknik Informatika UIN Suska Riau (IPK 3.39 | TOEFL 537) dengan pengalaman profesional sebagai Data Science Intern di PT Pertamina Hulu Rokan (PHR), IT Support di Universitas Abdurrab, Data Scientist Intern di Id/x partners x Rakamin Academy (Best Student 86.96), serta Freelance Web Dev & Machine Learning. Saya memiliki keahlian teruji dalam ${requiredSkills} yang sangat sejalan dengan kebutuhan posisi ${jobTitle}.\n\nMelalui proyek nyata seperti QC Log Analyzer (Python/Dataiku), model Credit Risk Loan (turunkan gagal bayar 12%), dan pengembangan aplikasi web (React/Laravel), saya siap memberikan kontribusi nyata bagi efisiensi operasional ${companyName}. Terlampir CV lengkap saya untuk pertimbangan Bapak/Ibu. Terima kasih.`;

    const pitchEN = `Dear ${companyName} Recruitment Team,\n\nMy name is Muhammad Ravil, a Computer Science graduate from UIN Suska Riau (GPA 3.39 | TOEFL 537) with hands-on industry experience in Data Science at PT Pertamina Hulu Rokan (PHR), IT Support at Universitas Abdurrab, Data Scientist Intern at Id/x partners x Rakamin Academy, and Freelance Web Developer & ML Engineer. I bring practical technical expertise in ${requiredSkills}, aligning directly with the requirements for the ${jobTitle} role.\n\nWith a track record of building automated analytics applications (Python/Dataiku), predictive ML models (12% credit risk reduction), and full-stack web solutions (React/Laravel), I look forward to contributing to data-driven growth at ${companyName}. Please find my resume attached for your review. Thank you.`;

    const formalID = `Hal: Lamaran Pekerjaan – ${jobTitle}\nKepada Yth.\nTim HR / Rekrutmen\n${companyName}\n\nDengan hormat,\n\nSehubungan dengan informasi lowongan pekerjaan untuk posisi ${jobTitle} di ${companyName}, saya bermaksud mengajukan lamaran untuk bergabung dengan perusahaan Bapak/Ibu.\n\nSaya adalah lulusan S1 Teknik Informatika dari UIN Suska Riau (IPK 3.39, TOEFL 537) dengan latar belakang pengalaman di industri hulu migas sebagai Data Science Intern di PT Pertamina Hulu Rokan (PHR, Juli 2025–Februari 2026) serta IT Support (Hardware & Software) di Universitas Abdurrab. Selama di PHR, saya mengembangkan aplikasi QC Log Analyzer berbasis Python dan Dataiku untuk otomatisasi pemrosesan, monitoring, serta visualisasi data operasional hulu migas.\n\nSelain itu, sebagai Data Scientist Intern di Id/x partners x Rakamin Academy (Best Student Score 86.96, April–Mei 2025), saya memiliki rekam jejak mengembangkan model machine learning Credit Risk Loan yang berhasil menurunkan tingkat gagal bayar pinjaman hingga 12% pada dataset 466.285 data. Saya juga aktif sebagai Freelance Web Developer & Machine Learning Engineer (PHP, Laravel, React, Python). Pengalaman ini membuat saya sangat terbiasa mengimplementasikan keahlian pada ${requiredSkills}.\n\nKemampuan analisis data yang kuat, keahlian teknis lintas platform (Python, SQL, Dataiku, React, Laravel, Power BI), serta troubleshooting IT yang solid membuat saya yakin dapat memberikan kontribusi signifikan bagi ${companyName}.\n\nBesar harapan saya untuk diberikan kesempatan wawancara agar dapat menjelaskan lebih rinci mengenai portofolio saya. Atas perhatian dan kesempatan yang Bapak/Ibu berikan, saya ucapkan terima kasih.\n\nHormat saya,\n\nMuhammad Ravil\nPekanbaru, Riau | ravilmuhammad987@gmail.com`;

    return `
        <div class="cover-letter-container">
            <div class="cover-letter-header">
                <div>
                    <h4>✨ Auto-Generated Application Pitch & Cover Letter</h4>
                    <p>Dibuat otomatis dari CV asli (Muhammad Ravil | UIN Suska Riau | IT Support Abdurrab | Data Science PHR | Rakamin 86.96) dicocokkan dengan keahlian lowongan ini.</p>
                </div>
            </div>
            
            <div class="pitch-section">
                <div class="pitch-card-title">
                    <h5>💬 Pitch Singkat / LinkedIn Message (Bahasa Indonesia)</h5>
                    <button class="btn-copy" onclick="copySiblingTextarea(this)">📋 Salin Teks</button>
                </div>
                <textarea readonly class="pitch-textarea" rows="5">${escapeHtml(pitchID)}</textarea>
            </div>

            <div class="pitch-section">
                <div class="pitch-card-title">
                    <h5>🌐 Brief Pitch / Recruiter Outreach (English)</h5>
                    <button class="btn-copy" onclick="copySiblingTextarea(this)">📋 Copy Pitch</button>
                </div>
                <textarea readonly class="pitch-textarea" rows="5">${escapeHtml(pitchEN)}</textarea>
            </div>

            <div class="pitch-section">
                <div class="pitch-card-title">
                    <h5>📄 Surat Lamaran Resmi / Formal Cover Letter (ID)</h5>
                    <button class="btn-copy" onclick="copySiblingTextarea(this)">📋 Salin Lamaran</button>
                </div>
                <textarea readonly class="pitch-textarea" rows="11">${escapeHtml(formalID)}</textarea>
            </div>
        </div>
    `;
}

function generateATSBoosterHTML(job) {
    const nlp = job.nlp_breakdown || {};
    const mandatory = nlp.mandatory_skills || [];
    const plus = nlp.preferred_skills || nlp.plus_skills || [];
    const rawText = ((job.raw_description || '') + ' ' + (job.raw_requirements || '')).toLowerCase();

    const ravilProfileKeywords = [
        'python', 'sql', 'data analysis', 'data science', 'machine learning',
        'dataiku', 'excel', 'power bi', 'react', 'laravel', 'php', 'javascript', 'git', 'arcgis',
        'teknik informatika', 'sistem informasi', 'problem solving', 'analisis data',
        'data analyst', 'data scientist', 'ai engineer', 'web development', 'web developer',
        'fullstack', 'full stack', 'it support', 'mysql', 'sentiment analysis', 'naive bayes',
        'tableau', 'microsoft office', 'troubleshooting', 'hardware', 'software', 'network'
    ];

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

    const potentialBonusKeywords = ['power bi', 'tableau', 'excel', 'etl', 'data warehouse', 'big data', 'uat', 'dashboard', 'cleaning', 'visualisasi data', 'agile', 'jira', 'sap'];
    const bonusFound = [];
    potentialBonusKeywords.forEach(pk => {
        const alreadyMatched = matchedATS.some(m => m.toLowerCase() === pk);
        if (rawText.includes(pk) && !alreadyMatched) {
            bonusFound.push(pk.toUpperCase());
        }
    });

    const atsScore = Math.min(98, Math.max(78, 72 + (matchedATS.length * 6)));

    const bullet1 = `• Developed QC Log Analyzer — automated data processing, monitoring & visualization application using Python and Dataiku at PT Pertamina Hulu Rokan, streamlining upstream oil & gas operational reporting.`;
    const bullet2 = `• Engineered Credit Risk Loan ML model at Id/x partners x Rakamin Academy (Best Student 86.96), reducing loan default rates by 12% across 466,285 records.`;
    const bullet3 = `• Resolved hardware, software, OS & lab network issues across 50+ IT devices at Universitas Abdurrab and delivered ${matchedATS[0] || 'data analytics'} & full-stack solutions (${bonusFound[0] || 'React/Laravel/Python'}).`;

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
                    <p class="ats-desc">Skill ini cocok dengan latar belakangmu (S1 Informatika & Data/IT):</p>
                    <div class="nlp-tags">
                        ${matchedATS.length > 0 ? matchedATS.map(s => `<span class="nlp-skill-badge mandatory">✓ ${escapeHtml(s)}</span>`).join('') : '<span class="nlp-skill-badge mandatory">✓ Data Analysis & IT Core</span>'}
                    </div>
                </div>

                <div class="ats-card opportunity">
                    <h5>🎯 Kata Kunci Emas yang Perlu Ditambahkan ke CV</h5>
                    <p class="ats-desc">Tambahkan istilah ini pada bullet point CV kamu agar skor ATS naik maksimal:</p>
                    <div class="nlp-tags">
                        ${missingATS.concat(bonusFound).length > 0 ? missingATS.concat(bonusFound).slice(0, 8).map(s => `<span class="nlp-skill-badge plus">+ ${escapeHtml(s)}</span>`).join('') : '<span class="nlp-skill-badge plus">+ Analytical Problem Solving</span>'}
                    </div>
                </div>
            </div>

            <div class="pitch-section">
                <div class="pitch-card-title">
                    <h5>✨ 3 ATS-Optimized Resume Bullet Points (1-Click Copy untuk CV-mu)</h5>
                    <button class="btn-copy" onclick="copySiblingTextarea(this)">📋 Salin 3 Bullet Points</button>
                </div>
                <p style="font-size: 0.78rem; color: #a78bfa; margin-top: 0; margin-bottom: 0.6rem;">Tempelkan poin-poin berdampak tinggi ini pada bagian Pengalaman Kerja / Proyek di CV kamu sebelum melamar lowongan ini:</p>
                <textarea readonly class="pitch-textarea" rows="6">${escapeHtml(allBulletsText)}</textarea>
            </div>
        </div>
    `;
}

window.copySiblingTextarea = function (btnElem) {
    const section = btnElem.closest('.pitch-section');
    const textarea = section ? section.querySelector('textarea') : null;
    if (!textarea) return;
    navigator.clipboard.writeText(textarea.value).then(() => {
        const origText = btnElem.innerHTML;
        btnElem.innerHTML = '✅ Tersalin!';
        btnElem.classList.add('copied');
        showToast('📋 Teks berhasil disalin ke clipboard');
        setTimeout(() => {
            btnElem.innerHTML = origText;
            btnElem.classList.remove('copied');
        }, 2000);
    });
};

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
    const expVal = expFilter ? expFilter.value : 'all';
    const sortBy = sortSelect.value;

    // Parse localStorage ONCE outside filter loop (menghindari ratusan JSON.parse per render)
    const savedState = wishlistOnly ? getSavedJobsState() : null;
    const sourceMap = {
        'linkedin': 'LinkedIn',
        'grab': 'Grab',
        'talentics': 'Talentics',
        'astra': 'Astra',
        'ptc': 'Pertamina PTC',
        'sawitpro': 'SawitPRO',
        'ioh': 'Indosat Ooredoo Hutchison',
        'indofood': 'Indofood',
        'opentrain': 'OpenTrain.ai',
        'micro1': 'micro1'
    };
    const targetSource = sourceVal !== 'all' ? sourceMap[sourceVal] : null;

    filteredJobs = allJobs.filter(job => {
        if (query && !(job._searchText || '').includes(query)) {
            return false;
        }

        if (matchType !== 'all') {
            if (matchType === 'high' && job.match_score < 80) return false;
            if (matchType === 'medium' && (job.match_score < 50 || job.match_score >= 80)) return false;
            if (matchType === 'low' && job.match_score >= 50) return false;
            if (matchType === 'compatible' && job.is_blocked) return false;
            if (matchType === 'blocked' && !job.is_blocked) return false;
        }

        if (targetSource) {
            if (sourceVal === 'linkedin') {
                if (job.source !== 'LinkedIn' && job.source !== 'JobSpy (LinkedIn)') return false;
            } else if (job.source !== targetSource) {
                return false;
            }
        }

        if (expVal !== 'all') {
            const reqYears = (job.parsed_requirements && job.parsed_requirements.exp_years !== undefined)
                ? job.parsed_requirements.exp_years
                : 0;
            if (expVal === 'eligible' && reqYears > 1) return false;
            if (expVal === 'freshgrad' && reqYears > 0) return false;
            if (expVal === 'experienced' && reqYears <= 1) return false;
        }

        if (wishlistOnly) {
            const item = savedState[String(job.id)];
            if (!item || !item.isBookmarked) return false;
        }

        return true;
    });

    // Update mobile filter badge (dihitung sekali secara akurat)
    if (filterCountBadge) {
        let activeCount = 0;
        if (matchType !== 'all') activeCount++;
        if (sourceVal !== 'all') activeCount++;
        if (expVal !== 'all') activeCount++;
        if (sortBy !== 'score') activeCount++;
        if (wishlistOnly) activeCount++;
        if (query !== '') activeCount++;
        if (activeCount > 0) {
            filterCountBadge.style.display = 'inline-block';
            filterCountBadge.textContent = activeCount;
        } else {
            filterCountBadge.style.display = 'none';
        }
    }

    // Sorting
    if (sortBy === 'score') {
        filteredJobs.sort((a, b) => {
            if (a.is_blocked && !b.is_blocked) return 1;
            if (!a.is_blocked && b.is_blocked) return -1;
            return b.match_score - a.match_score;
        });
    } else if (sortBy === 'title') {
        filteredJobs.sort((a, b) => (a.title || '').localeCompare(b.title || ''));
    } else if (sortBy === 'due_date') {
        filteredJobs.sort((a, b) => {
            const metaA = a._dueMeta || parseJobDate(a.due_date);
            const metaB = b._dueMeta || parseJobDate(b.due_date);
            // Push expired deadlines to the bottom, upcoming deadlines first
            if (metaA.isExpired !== metaB.isExpired) return metaA.isExpired ? 1 : -1;
            return metaA.timestamp - metaB.timestamp;
        });
    }

    renderJobList();
}

function getSourceBadgeHTML(job, styleAttr = '') {
    const styleStr = styleAttr ? ` style="${styleAttr}"` : '';
    if (job.source === 'LinkedIn' || job.source === 'JobSpy (LinkedIn)') {
        return `<span class="source-badge linkedin"${styleStr}>LinkedIn</span>`;
    } else if (job.source === 'Grab') {
        return `<span class="source-badge grab"${styleStr}>Grab Indonesia</span>`;
    } else if (job.source === 'Astra') {
        return `<span class="source-badge astra"${styleStr}>Astra Career</span>`;
    } else if (job.source === 'Pertamina PTC') {
        return `<span class="source-badge ptc"${styleStr}>Pertamina PTC</span>`;
    } else if (job.source === 'SawitPRO') {
        return `<span class="source-badge sawitpro"${styleStr}>SawitPRO</span>`;
    } else if (job.source === 'Indosat Ooredoo Hutchison') {
        return `<span class="source-badge ioh"${styleStr}>Indosat Ooredoo Hutchison</span>`;
    } else if (job.source === 'Indofood') {
        return `<span class="source-badge indofood"${styleStr}>Indofood Career</span>`;
    } else if (job.source === 'OpenTrain.ai') {
        return `<span class="source-badge opentrain"${styleStr}>OpenTrain.ai (Remote)</span>`;
    } else if (job.source === 'micro1') {
        return `<span class="source-badge micro1"${styleStr}>micro1 (Remote)</span>`;
    }
    return `<span class="source-badge talentics"${styleStr}>${escapeHtml(job.source || 'Talentics')}</span>`;
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

// Render the Job List Cards (Batch DocumentFragment + 1x localStorage parse)
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

    // Parse localStorage ONCE untuk seluruh halaman (menghindari N× JSON.parse)
    const allSavedState = getSavedJobsState();
    const applications = getApplicationsState();
    const radius = 28;
    const circ = 2 * Math.PI * radius;
    const statusBadgeMap = {
        'applied': '<span class="app-status-pill applied">🚀 Sudah Dilamar</span>',
        'interview': '<span class="app-status-pill interview">💬 Tahap Interview</span>',
        'accepted': '<span class="app-status-pill accepted">🎉 Diterima</span>'
    };

    const fragment = document.createDocumentFragment();

    paginatedJobs.forEach(job => {
        const clampedScore = Math.max(0, Math.min(100, Number(job.match_score) || 0));
        const offset = circ - (clampedScore / 100) * circ;

        let matchClass = 'low-match';
        if (clampedScore >= 70) matchClass = 'high-match';
        else if (clampedScore >= 50) matchClass = 'medium-match';

        const cardClass = job.is_blocked ? 'job-card blocked' : 'job-card';

        let blockerLabel = '';
        if (job.is_blocked) {
            const failedReqs = [];
            if (job.match_details.gpa.status === 'No Match') failedReqs.push('IPK');
            if (job.match_details.age.status === 'No Match') failedReqs.push('Batas Usia');
            if (job.match_details.gender.status === 'No Match') failedReqs.push('Gender');
            blockerLabel = `<div class="blocker-banner">⚠️ Tidak Memenuhi Syarat: ${failedReqs.join(', ')}</div>`;
        }

        let matchPreview = '';
        if (job.match_details.major.status === 'High Match') {
            matchPreview = 'Sesuai latar belakang Teknik Informatika, Data, atau IT.';
        } else if (job.match_details.skills.status === 'High Match') {
            matchPreview = 'Membutuhkan keahlian inti Anda (Python/Data/IT/Web).';
        } else {
            matchPreview = escapeHtml(job.match_details.major.reason);
        }

        const sourceBadge = getSourceBadgeHTML(job);
        const idStr = String(job.id);
        const savedState = allSavedState[idStr] || {};
        const isBookmarked = savedState.isBookmarked || false;
        const appStatus = applications[idStr] ? applications[idStr].status : (savedState.status || '');

        const bookmarkBtnHTML = `
            <button class="bookmark-btn ${isBookmarked ? 'active' : ''}" title="Simpan lowongan ini" onclick="toggleBookmark(event, '${escapeHtml(idStr)}')">
                ${isBookmarked ? '★' : '☆'}
            </button>
        `;

        const appStatusBadge = statusBadgeMap[appStatus] || '';
        const safeLogo = job.logo && /^https?:\/\//i.test(job.logo) ? escapeHtml(job.logo) : '';
        const companyLogo = safeLogo
            ? `<img src="${safeLogo}" class="company-logo" alt="${escapeHtml(job.organization_name)}" loading="lazy" decoding="async" onerror="this.style.display='none'">`
            : '';

        const isExpired = job._dueMeta && job._dueMeta.isExpired;
        const dueLabel = job.due_date ? escapeHtml(String(job.due_date).split(' ')[0]) : '';
        const dueMetaTag = dueLabel
            ? `<span class="meta-tag ${isExpired ? 'expired' : 'highlight'}">${isExpired ? '⌛ Tutup:' : '📅 Deadline:'} ${dueLabel}</span>`
            : '';

        const card = document.createElement('div');
        card.className = newJobIds.has(idStr) ? cardClass + ' is-new-job' : cardClass;
        card.dataset.jobId = idStr;
        card.innerHTML = `
            <div class="score-circle ${matchClass}">
                <svg>
                    <circle class="bg-ring" cx="34" cy="34" r="${radius}"></circle>
                    <circle class="progress-ring" cx="34" cy="34" r="${radius}" 
                            stroke-dasharray="${circ}" stroke-dashoffset="${offset}"></circle>
                </svg>
                <span class="score-text">${clampedScore}%</span>
            </div>
            
            <div class="job-info">
                <div class="job-card-header">
                    <div class="job-title-wrapper">
                        <h3 class="job-title-text">${escapeHtml(job.title)}</h3>
                        ${newJobIds.has(idStr) ? '<span class="new-job-badge">🆕 Baru</span>' : ''}
                        ${sourceBadge}
                        ${appStatusBadge}
                        ${bookmarkBtnHTML}
                    </div>
                </div>
                <div class="job-company">
                    ${companyLogo}
                    <span>${escapeHtml(job.organization_name || 'SKK Migas / KKKS')}</span>
                </div>
                
                <div class="job-meta-tags">
                    <span class="meta-tag">📍 ${escapeHtml(formatLocationShort(job.location))}</span>
                    <span class="meta-tag">🏢 ${escapeHtml(job.workplace || 'WFO')}</span>
                    <span class="meta-tag">💼 ${escapeHtml(job.level)}</span>
                    <span class="meta-tag">📝 ${escapeHtml(job.type_name)}</span>
                    <span class="meta-tag ${job.parsed_requirements && job.parsed_requirements.exp_years <= 1 ? 'highlight' : ''}">💼 Syarat Exp: ${escapeHtml(job.parsed_requirements ? job.parsed_requirements.experience : 'Fresh Grad')}</span>
                    ${dueMetaTag}
                </div>
                
                <div class="job-matching-preview">
                    <strong>Kecocokan:</strong> ${matchPreview}
                </div>
                
                ${blockerLabel}
            </div>
            
            <button class="view-detail-btn">Lihat Detail</button>
        `;

        fragment.appendChild(card);
    });

    jobListContainer.appendChild(fragment);
}

// Open Detail Modal
function openJobModal(job) {
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

    const idStr = String(job.id);
    const sourceBadge = getSourceBadgeHTML(job, 'margin-left: 10px; vertical-align: middle;');
    const safeLogo = job.logo && /^https?:\/\//i.test(job.logo) ? escapeHtml(job.logo) : '';
    const companyLogo = safeLogo
        ? `<img src="${safeLogo}" class="company-logo" style="width: 28px; height: 28px; vertical-align: middle; margin-right: 8px;" alt="${escapeHtml(job.organization_name)}">`
        : '';

    const savedState = getSavedJobsState()[idStr] || {};
    const applications = getApplicationsState();
    const isBookmarked = savedState.isBookmarked || false;
    const appStatus = (applications[idStr] && applications[idStr].status) || savedState.status || 'not_applied';

    const nlp = job.nlp_breakdown || {};
    const mandSkillsTags = (nlp.mandatory_skills && nlp.mandatory_skills.length > 0)
        ? nlp.mandatory_skills.map(s => `<span class="nlp-skill-badge mandatory">${escapeHtml(s)}</span>`).join('')
        : `<span class="nlp-skill-badge neutral">Umum / Tidak Spesifik</span>`;

    const prefSkillsArr = nlp.preferred_skills || nlp.plus_skills || [];
    const plusSkillsTags = prefSkillsArr.length > 0
        ? prefSkillsArr.map(s => `<span class="nlp-skill-badge plus">+ ${escapeHtml(s)}</span>`).join('')
        : '';

    const keySentencesRaw = (nlp.key_sentences && nlp.key_sentences.length > 0)
        ? nlp.key_sentences
        : [
            ...(nlp.mandatory_requirements || []),
            ...(nlp.preferred_requirements || []),
            ...(nlp.key_responsibilities || [])
        ].slice(0, 5);

    const keySentencesList = keySentencesRaw.length > 0
        ? keySentencesRaw.map(sent => `<li>• ${escapeHtml(sent)}</li>`).join('')
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
                    <p>${escapeHtml(nlp.education_summary || 'S1 / D3 relevan atau setara')}</p>
                </div>
                <div class="nlp-item">
                    <h5>⏳ Konteks Pengalaman</h5>
                    <p>${escapeHtml(nlp.experience_summary || '1 Tahun Pengalaman / Fresh Graduate')}</p>
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

    const safeDesc = sanitizeHtml(job.raw_description) || '<p>Tidak ada deskripsi pekerjaan yang dicantumkan.</p>';
    const safeReqs = sanitizeHtml(job.raw_requirements || job.raw_description) || '<p>Tidak ada persyaratan detail yang dicantumkan.</p>';
    const clampedScore = Math.max(0, Math.min(100, Number(job.match_score) || 0));

    modalContent.innerHTML = `
        <div class="modal-header-section">
            <h2 class="modal-job-title">${escapeHtml(job.title)}</h2>
            <div class="modal-job-company" style="display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; margin-bottom: 1rem;">
                ${companyLogo}
                <span>${escapeHtml(job.organization_name || 'SKK Migas / KKKS')}</span>
                ${sourceBadge}
            </div>
            
            <div class="job-meta-tags">
                <span class="meta-tag">📍 ${escapeHtml(job.location || 'Lokasi tidak dispesifikasikan')}</span>
                <span class="meta-tag">🏢 Workplace: ${escapeHtml(job.workplace || 'WFO')}</span>
                <span class="meta-tag">💼 Level: ${escapeHtml(job.level)}</span>
                <span class="meta-tag">📝 Kontrak: ${escapeHtml(job.type_name)}</span>
                ${job.group ? `<span class="meta-tag">📁 Deputi/Perwakilan/Dept: ${escapeHtml(job.group)}</span>` : ''}
                ${job.due_date ? `<span class="meta-tag highlight">📅 Deadline: ${escapeHtml(job.due_date)}</span>` : ''}
            </div>
        </div>
        
        ${nlpSectionHTML}
        
        <!-- Checklist Match Section -->
        <div class="match-evaluation-section">
            <div class="match-evaluation-title">
                <span>Analisis Kesesuaian Profil (Skor: ${clampedScore}%)</span>
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
                        <p>${escapeHtml(job.match_details.major.reason)}</p>
                    </div>
                </div>
                
                <!-- IPK -->
                <div class="checklist-item">
                    <span class="checklist-icon ${getClass(job.match_details.gpa.status)}">
                        ${getIcon(job.match_details.gpa.status)}
                    </span>
                    <div class="checklist-info">
                        <h5>IPK / GPA (Syarat: ${escapeHtml(job.parsed_requirements.gpa || '-')})</h5>
                        <p>${escapeHtml(job.match_details.gpa.reason)}</p>
                    </div>
                </div>
                
                <!-- Usia -->
                <div class="checklist-item">
                    <span class="checklist-icon ${getClass(job.match_details.age.status)}">
                        ${getIcon(job.match_details.age.status)}
                    </span>
                    <div class="checklist-info">
                        <h5>Batas Usia (Batas: ${escapeHtml(job.parsed_requirements.age || '-')})</h5>
                        <p>${escapeHtml(job.match_details.age.reason)}</p>
                    </div>
                </div>

                <!-- TOEFL -->
                <div class="checklist-item">
                    <span class="checklist-icon ${getClass(job.match_details.toefl.status)}">
                        ${getIcon(job.match_details.toefl.status)}
                    </span>
                    <div class="checklist-info">
                        <h5>Skor TOEFL (Syarat: ${escapeHtml(job.parsed_requirements.toefl || '-')})</h5>
                        <p>${escapeHtml(job.match_details.toefl.reason)}</p>
                    </div>
                </div>
                
                <!-- Gender -->
                <div class="checklist-item">
                    <span class="checklist-icon ${getClass(job.match_details.gender.status)}">
                        ${getIcon(job.match_details.gender.status)}
                    </span>
                    <div class="checklist-info">
                        <h5>Gender Pelamar</h5>
                        <p>${escapeHtml(job.match_details.gender.reason)}</p>
                    </div>
                </div>

                <!-- Pengalaman Kerja -->
                <div class="checklist-item">
                    <span class="checklist-icon ${job.match_details && job.match_details.exp_years ? getClass(job.match_details.exp_years.status) : 'match'}">
                        ${job.match_details && job.match_details.exp_years ? getIcon(job.match_details.exp_years.status) : '✅'}
                    </span>
                    <div class="checklist-info">
                        <h5>Syarat Pengalaman Kerja (Kamu: ~1 Tahun — Abdurrab, PHR & Rakamin)</h5>
                        <p>${escapeHtml(job.match_details && job.match_details.exp_years ? job.match_details.exp_years.reason : 'Sesuai dengan profil pengalamanmu.')}</p>
                    </div>
                </div>

                <!-- Core Skills -->
                <div class="checklist-item">
                    <span class="checklist-icon ${getClass(job.match_details.skills.status)}">
                        ${getIcon(job.match_details.skills.status)}
                    </span>
                    <div class="checklist-info">
                        <h5>Keahlian (Python, Dataiku, AI/ML & IT)</h5>
                        <p>${escapeHtml(job.match_details.skills.reason)}</p>
                    </div>
                </div>

                <!-- Experience & Industry relevance -->
                <div class="checklist-item checklist-item-full">
                    <span class="checklist-icon ${getClass(job.match_details.experience ? job.match_details.experience.status : 'Neutral')}">
                        ${getIcon(job.match_details.experience ? job.match_details.experience.status : 'Neutral')}
                    </span>
                    <div class="checklist-info">
                        <h5>Pengalaman Relevan (Upstream Oil & Gas / Tech)</h5>
                        <p>${escapeHtml(job.match_details.experience ? job.match_details.experience.reason : 'Sesuai dengan kualifikasi pengalaman kerja.')}</p>
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
            <button class="tab-btn skill-gap-tab-btn" onclick="switchTab(event, 'skillsGapTab')">📊 Skills Gap</button>
            <button class="tab-btn tracker-tab-btn" onclick="switchTab(event, 'trackerTab')">📋 Application Tracker</button>
        </div>
        
        <div id="descriptionTab" class="tab-pane active">
            ${safeDesc}
        </div>
        
        <div id="requirementsTab" class="tab-pane">
            ${safeReqs}
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
                <button class="btn-generate-ai" onclick="generateAISummary('${escapeHtml(idStr)}')">
                    ✨ Generate Smart Summary
                </button>
                <div id="aiSummaryContent-${escapeHtml(idStr)}" class="ai-content-area" style="display: none;">
                    <div class="ai-loading">
                        <div class="spinner"></div>
                        <p>AI sedang menganalisis deskripsi pekerjaan...</p>
                    </div>
                </div>
            </div>
        </div>

        <div id="skillsGapTab" class="tab-pane">
            <div class="skills-gap-container">
                <div class="ai-feature-header">
                    <h3>📊 Skills Gap Analysis</h3>
                    <p>Bandingkan skill Anda dengan requirement pekerjaan ini</p>
                </div>
                <button class="btn-generate-ai" onclick="generateSkillsGap('${escapeHtml(idStr)}')">
                    📊 Analyze Skills Gap
                </button>
                <div id="skillsGapContent-${escapeHtml(idStr)}" class="ai-content-area" style="display: none;">
                    <div class="ai-loading">
                        <div class="spinner"></div>
                        <p>Menganalisis gap skills Anda...</p>
                    </div>
                </div>
            </div>
        </div>

        <div id="trackerTab" class="tab-pane">
            <div class="tracker-container">
                <div class="ai-feature-header">
                    <h3>📋 Application Tracker</h3>
                    <p>Kelola status lamaran dan progress interview Anda</p>
                </div>
                <button class="btn-generate-ai" onclick="openApplicationTracker('${escapeHtml(idStr)}')">
                    📋 Manage Application
                </button>
                <div id="trackerContent-${escapeHtml(idStr)}" class="tracker-content-area" style="display: none;"></div>
            </div>
        </div>
        
        <div class="modal-footer">
            <div class="modal-footer-row-top">
                <button class="btn-bookmark-modal ${isBookmarked ? 'active' : ''}" onclick="toggleBookmark(event, '${escapeHtml(idStr)}'); updateJobModalBookmarkButton('${escapeHtml(idStr)}');">
                    ${isBookmarked ? '★ Tersimpan' : '☆ Simpan'}
                </button>
                <select class="status-select-modal" onchange="changeApplicationStatus('${escapeHtml(idStr)}', this.value)">
                    <option value="not_applied" ${appStatus === 'not_applied' ? 'selected' : ''}>📌 Belum Dilamar</option>
                    <option value="applied" ${appStatus === 'applied' ? 'selected' : ''}>🚀 Sudah Dilamar</option>
                    <option value="interview" ${appStatus === 'interview' ? 'selected' : ''}>💬 Tahap Interview</option>
                    <option value="offer" ${appStatus === 'offer' ? 'selected' : ''}>📝 Dapat Offer</option>
                    <option value="accepted" ${appStatus === 'accepted' ? 'selected' : ''}>🎉 Diterima</option>
                    <option value="rejected" ${appStatus === 'rejected' ? 'selected' : ''}>❌ Ditolak</option>
                </select>
            </div>
            <a href="${escapeHtml(sanitizeUrl(job.url))}" target="_blank" rel="noopener noreferrer" class="btn-primary btn-apply-modal">
                Lamar di Portal Resmi (${escapeHtml(job.source)}) ↗
            </a>
        </div>
    `;

    window.currentModalJobId = job.id;
    detailModal.classList.add('active');
    document.body.style.overflow = 'hidden';
}

// Switch tabs inside modal (unified)
window.switchTab = function (event, tabId) {
    const panes = document.querySelectorAll('.tab-pane');
    panes.forEach(pane => pane.classList.remove('active'));

    const buttons = document.querySelectorAll('.tab-btn');
    buttons.forEach(btn => btn.classList.remove('active'));

    document.getElementById(tabId).classList.add('active');
    event.currentTarget.classList.add('active');

    const jid = window.currentModalJobId;
    if (!jid) return;

    if (tabId === 'aiSummaryTab') {
        const area = document.getElementById(`aiSummaryContent-${jid}`);
        if (area && area.style.display === 'none') generateAISummary(jid);
    } else if (tabId === 'interviewTab') {
        const area = document.getElementById(`interviewContent-${jid}`);
        if (area && area.style.display === 'none') generateInterviewQuestions(jid);
    } else if (tabId === 'skillsGapTab') {
        const area = document.getElementById(`skillsGapContent-${jid}`);
        if (area && area.style.display === 'none') generateSkillsGap(jid);
    } else if (tabId === 'trackerTab') {
        const area = document.getElementById(`trackerContent-${jid}`);
        if (area && area.style.display === 'none') openApplicationTracker(jid);
    }
};

// Close Modal
window.closeModal = function () {
    detailModal.classList.remove('active');
    document.body.style.overflow = '';
};

// AI Service Functions
const AI_SERVICE_URL = 'http://localhost:5001';

// In-Memory AI Caches for Instant Loading
window.aiSummaryCache = window.aiSummaryCache || {};
window.aiInterviewCache = window.aiInterviewCache || {};
window.skillsGapCache = window.skillsGapCache || {};

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

// Helper to format AI response text (convert bold markdown and linebreaks safely)
function formatAIResponse(text) {
    if (!text) return '';
    return escapeHtml(text)
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
        // Reset preference jika user ingin coba ulang
        const userRetry = confirm(
            '⚠️ Cloud AI fallback sebelumnya di-disable.\n\n' +
            'Klik OK untuk enable kembali dan coba lagi,\natau CANCEL untuk skip.'
        );
        if (!userRetry) throw new Error('Cloud AI fallback disabled by user preference');
        localStorage.setItem('enableCloudAI', 'true');
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


// Generate AI Summary for a job
window.generateAISummary = async function (jobId) {
    const job = allJobs.find(j => j.id == jobId);
    if (!job) return;

    const contentArea = document.getElementById(`aiSummaryContent-${jobId}`);
    if (!contentArea) return;
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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: job.title,
                description: job.raw_description || job.description || '',
                requirements: job.raw_requirements || job.requirements || ''
            })
        }, 1200);

        const data = await response.json();

        if (data.success) {
            const providerLabel = escapeHtml(data.provider || 'Local AI');
            const htmlOut = `
                <div class="ai-result">
                    <div class="ai-result-header">
                        <h4>📝 Ringkasan Lowongan (${providerLabel})</h4>
                    </div>
                    <div class="ai-result-content">
                        ${formatAIResponse(data.summary)}
                    </div>
                </div>
            `;
            addToCache(window.aiSummaryCache, jobId, htmlOut);
            contentArea.innerHTML = htmlOut;
        } else {
            throw new Error(data.error || 'Server error');
        }
    } catch (error) {
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
            addToCache(window.aiSummaryCache, jobId, htmlOut);
            contentArea.innerHTML = htmlOut;
        } catch (cloudErr) {
            contentArea.innerHTML = `
                <div class="ai-error">
                    <p>❌ Tidak dapat memuat ringkasan AI.</p>
                    <p>Error: ${escapeHtml(cloudErr.message)}</p>
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
    if (!contentArea) return;
    contentArea.style.display = 'block';

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
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                title: job.title,
                description: job.raw_description || job.description || '',
                requirements: job.raw_requirements || job.requirements || '',
                company: job.organization_name || job.company || 'Perusahaan tidak disebutkan',
                user_skills: localStorage.getItem('userSkills') || 'Python, SQL, Data Science, Machine Learning, Dataiku, Power BI, React, Laravel, IT Support',
                user_experience: 'IT Support (Universitas Abdurrab), Data Science Intern (PT Pertamina Hulu Rokan), Data Scientist Intern (Rakamin), Freelance Web/ML'
            })
        }, 1200);

        const data = await response.json();

        if (data.success) {
            const providerLabel = escapeHtml(data.provider || 'Local AI');
            const htmlOut = `
                <div class="ai-result">
                    <div class="ai-result-header">
                        <h4>💬 Prediksi Pertanyaan Interview (${providerLabel})</h4>
                        <p>Berdasarkan analisis AI terhadap job requirements</p>
                    </div>
                    <div class="ai-result-content interview-questions">
                        ${formatAIResponse(data.questions)}
                    </div>
                </div>
            `;
            addToCache(window.aiInterviewCache, jobId, htmlOut);
            contentArea.innerHTML = htmlOut;
        } else {
            throw new Error(data.error || 'Server error');
        }
    } catch (error) {
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
            addToCache(window.aiInterviewCache, jobId, htmlOut);
            contentArea.innerHTML = htmlOut;
        } catch (cloudErr) {
            contentArea.innerHTML = `
                <div class="ai-error">
                    <p>❌ Tidak dapat memprediksi pertanyaan AI.</p>
                    <p>Error: ${escapeHtml(cloudErr.message)}</p>
                </div>
            `;
        }
    }
}

// Generate Skills Gap Analysis
window.generateSkillsGap = async function (jobId) {
    const job = allJobs.find(j => j.id == jobId);
    if (!job) return;

    const contentArea = document.getElementById(`skillsGapContent-${jobId}`);
    if (!contentArea) return;
    contentArea.style.display = 'block';

    if (window.skillsGapCache && window.skillsGapCache[jobId]) {
        contentArea.innerHTML = window.skillsGapCache[jobId];
        return;
    }

    const combinedText = `${job.raw_requirements || ''} ${job.raw_description || ''}`;
    const extracted = extractSkillsFromText(combinedText);
    const nlp = job.nlp_breakdown || {};
    const nlpSkills = [...(nlp.mandatory_skills || []), ...(nlp.preferred_skills || nlp.plus_skills || [])];

    // Gabungkan skill dari NLP backend dan keyword extraction dengan deduplikasi case-insensitive
    const reqSkillMap = new Map();
    [...nlpSkills, ...extracted].forEach(s => {
        const key = s.toLowerCase();
        if (!reqSkillMap.has(key)) reqSkillMap.set(key, s);
    });
    const jobRequirements = Array.from(reqSkillMap.values());

    const defaultRavilSkills = 'Python,SQL,Data Science,Data Analysis,Machine Learning,Dataiku,Power BI,Excel,React,Laravel,PHP,JavaScript,Git,ArcGIS,IT Support,Troubleshooting,MySQL,Tableau';
    const userSkillsStr = localStorage.getItem('userSkills') || defaultRavilSkills;
    const userSkills = userSkillsStr.split(',').map(s => s.trim()).filter(Boolean);

    const matched = [];
    const missing = [];
    const advanced = [];

    const skillSimilarity = (skill1, skill2) => {
        const s1 = skill1.toLowerCase();
        const s2 = skill2.toLowerCase();
        if (s1 === s2) return 1.0;
        if (s1.length >= 3 && s2.length >= 3 && (s1.includes(s2) || s2.includes(s1))) return 0.7;
        return 0.0;
    };

    for (const reqSkill of jobRequirements) {
        let bestMatch = null;
        let bestScore = 0;

        for (const userSkill of userSkills) {
            const score = skillSimilarity(userSkill, reqSkill);
            if (score > bestScore) {
                bestScore = score;
                bestMatch = userSkill;
            }
        }

        if (bestScore >= 0.7) {
            matched.push({ user: bestMatch, required: reqSkill });
        } else if (bestScore >= 0.4) {
            advanced.push({ user: bestMatch, required: reqSkill });
        } else {
            missing.push(reqSkill);
        }
    }

    const matchPercentage = jobRequirements.length > 0
        ? Math.round((matched.length / jobRequirements.length) * 100)
        : 100;

    const htmlOut = `
        <div class="skills-gap-result">
            <div class="gap-header">
                <div class="match-percentage">
                    <span class="percent-number">${matchPercentage}%</span>
                    <span class="percent-label">Match Rate</span>
                </div>
            </div>
            
            <div class="gap-stats">
                <div class="stat-box matched">
                    <strong>${matched.length}</strong>
                    <span>Matched Skills</span>
                </div>
                <div class="stat-box missing">
                    <strong>${missing.length}</strong>
                    <span>Missing Skills</span>
                </div>
                <div class="stat-box total">
                    <strong>${jobRequirements.length}</strong>
                    <span>Total Required</span>
                </div>
            </div>

            ${matched.length > 0 ? `
            <div class="gap-section">
                <h4>✅ Your Matched Skills</h4>
                <ul class="skills-list">
                    ${matched.map(m => `<li class="skill-matched"><strong>${escapeHtml(m.user)}</strong> → ${escapeHtml(m.required)}</li>`).join('')}
                </ul>
            </div>
            ` : ''}

            ${missing.length > 0 ? `
            <div class="gap-section">
                <h4>❌ Skills to Learn</h4>
                <ul class="skills-list">
                    ${missing.map(m => `<li class="skill-missing">• ${escapeHtml(m)}</li>`).join('')}
                </ul>
            </div>
            ` : ''}

            ${advanced.length > 0 ? `
            <div class="gap-section">
                <h4>⚡ Level Up These Skills</h4>
                <ul class="skills-list">
                    ${advanced.map(a => `<li class="skill-advanced"><strong>${escapeHtml(a.user)}</strong> → Advanced ${escapeHtml(a.required)}</li>`).join('')}
                </ul>
            </div>
            ` : ''}
        </div>
    `;

    addToCache(window.skillsGapCache, jobId, htmlOut);
    contentArea.innerHTML = htmlOut;
}

// Helper: Extract skills from text using word-boundary regexes (fixes 'r'/'ai'/'rest' false matches)
const SKILL_EXTRACTION_RULES = [
    ['Python', /\bpython\b/i],
    ['JavaScript', /\bjavascript\b/i],
    ['TypeScript', /\btypescript\b/i],
    ['Java', /\bjava\b/i],
    ['C++', /(?:^|\W)c\+\+(?=$|\W)/i],
    ['C#', /(?:^|\W)c#(?=$|\W)/i],
    ['R', /\bR\b/],
    ['Go', /\b(?:golang|go)\b/i],
    ['PHP', /\bphp\b/i],
    ['Rust', /\brust\b/i],
    ['SQL', /\bsql\b/i],
    ['MySQL', /\bmysql\b/i],
    ['PostgreSQL', /\bpostgresql\b/i],
    ['MongoDB', /\bmongodb\b/i],
    ['Redis', /\bredis\b/i],
    ['Elasticsearch', /\belasticsearch\b/i],
    ['Machine Learning', /\bmachine learning\b/i],
    ['Deep Learning', /\bdeep learning\b/i],
    ['NLP', /\bnlp\b/i],
    ['Computer Vision', /\bcomputer vision\b/i],
    ['Data Science', /\bdata science\b/i],
    ['Data Analysis', /\bdata analy(?:sis|tics)\b/i],
    ['Tableau', /\btableau\b/i],
    ['Power BI', /\bpower\s?bi\b/i],
    ['Looker', /\blooker\b/i],
    ['Metabase', /\bmetabase\b/i],
    ['Docker', /\bdocker\b/i],
    ['Kubernetes', /\bkubernetes\b/i],
    ['Git', /\bgit\b/i],
    ['AWS', /\baws\b/i],
    ['GCP', /\bgcp\b/i],
    ['Azure', /\bazure\b/i],
    ['Dataiku', /\bdataiku\b/i],
    ['Pandas', /\bpandas\b/i],
    ['NumPy', /\bnumpy\b/i],
    ['Scikit-Learn', /\bscikit-learn\b/i],
    ['TensorFlow', /\btensorflow\b/i],
    ['PyTorch', /\bpytorch\b/i],
    ['React', /\breact(?:\.js)?\b/i],
    ['Laravel', /\blaravel\b/i],
    ['Vue', /\bvue(?:\.js)?\b/i],
    ['Node.js', /\bnode(?:\.js)?\b/i],
    ['Django', /\bdjango\b/i],
    ['Flask', /\bflask\b/i],
    ['REST API', /\brest\s?api\b/i],
    ['GraphQL', /\bgraphql\b/i],
    ['Microservices', /\bmicroservices\b/i],
    ['Agile', /\bagile\b/i],
    ['Scrum', /\bscrum\b/i],
    ['IT Support', /\bit support\b/i],
    ['ArcGIS', /\barcgis\b/i]
];

function extractSkillsFromText(text) {
    if (!text) return [];
    const foundSkills = [];
    for (const [label, regex] of SKILL_EXTRACTION_RULES) {
        if (regex.test(text)) {
            foundSkills.push(label);
        }
    }
    return foundSkills;
}

// Open Application Tracker
window.openApplicationTracker = function (jobId) {
    const job = allJobs.find(j => j.id == jobId);
    if (!job) return;

    const contentArea = document.getElementById(`trackerContent-${jobId}`);
    if (!contentArea) return;
    contentArea.style.display = 'block';

    const applications = getApplicationsState();
    const footerStatus = document.querySelector(`select.status-select-modal`)?.value || '';

    if (!applications[jobId]) {
        const initialStatus = footerStatus || 'not_applied';
        applications[jobId] = {
            jobId: jobId,
            jobTitle: job.title,
            company: job.organization_name || job.company || 'Unknown',
            appliedDate: new Date().toISOString().split('T')[0],
            status: initialStatus,
            interviewDates: [],
            notes: '',
            followUpDate: null
        };
    } else if (footerStatus && footerStatus !== applications[jobId].status) {
        applications[jobId].status = footerStatus;
    }

    const app = applications[jobId];
    const safeId = escapeHtml(String(jobId));

    const trackerHTML = `
        <div class="application-tracker-form">
            <div class="form-section">
                <label>📌 Application Status</label>
                <select class="form-select" id="appStatus_${safeId}" onchange="updateApplicationStatus('${safeId}', this.value)">
                    <option value="not_applied" ${app.status === 'not_applied' ? 'selected' : ''}>Belum Dilamar</option>
                    <option value="applied" ${app.status === 'applied' ? 'selected' : ''}>Sudah Dilamar</option>
                    <option value="interview" ${app.status === 'interview' ? 'selected' : ''}>Tahap Interview</option>
                    <option value="offer" ${app.status === 'offer' ? 'selected' : ''}>Dapat Offer</option>
                    <option value="accepted" ${app.status === 'accepted' ? 'selected' : ''}>Diterima</option>
                    <option value="rejected" ${app.status === 'rejected' ? 'selected' : ''}>Ditolak</option>
                </select>
            </div>

            <div class="form-section">
                <label>📅 Tanggal Dilamar</label>
                <input type="date" class="form-input" id="appliedDate_${safeId}" value="${escapeHtml(app.appliedDate)}" onchange="updateApplicationData('${safeId}', 'appliedDate', this.value)">
            </div>

            ${app.status !== 'not_applied' ? `
            <div class="form-section">
                <label>💬 Interview Dates</label>
                <div class="interview-list">
                    ${app.interviewDates.length > 0 ? app.interviewDates.map((int, idx) => `
                        <div class="interview-item">
                            <span>${escapeHtml(int.date)} - ${escapeHtml(int.type || 'Interview')}</span>
                            <button class="btn-remove" onclick="removeInterviewDate('${safeId}', ${idx})">✕</button>
                        </div>
                    `).join('') : '<p style="color: #888; font-size: 0.9rem;">Belum ada interview scheduled</p>'}
                </div>
                <button class="btn-add-interview" onclick="addInterviewDateForm('${safeId}')">+ Add Interview</button>
            </div>
            ` : ''}

            <div class="form-section">
                <label>📝 Notes</label>
                <textarea class="form-textarea" id="notes_${safeId}" placeholder="Catatan tentang aplikasi ini..." onchange="updateApplicationData('${safeId}', 'notes', this.value)">${escapeHtml(app.notes)}</textarea>
            </div>

            <div class="form-section">
                <label>📌 Follow-up Date</label>
                <input type="date" class="form-input" id="followUpDate_${safeId}" value="${escapeHtml(app.followUpDate || '')}" onchange="updateApplicationData('${safeId}', 'followUpDate', this.value)">
            </div>

            <div class="form-actions">
                <button class="btn-save" onclick="saveApplicationTracker('${safeId}')">💾 Save Progress</button>
                <button class="btn-view-all" onclick="showApplicationStats()">📊 View All Applications</button>
            </div>
        </div>
    `;

    contentArea.innerHTML = trackerHTML;
}

// Update application status
window.updateApplicationStatus = function (jobId, status) {
    const applicationsKey = 'jobMatcher_applications';
    const applications = getApplicationsState();

    if (!applications[jobId]) {
        const job = allJobs.find(j => j.id == jobId);
        applications[jobId] = {
            jobId: jobId,
            jobTitle: job ? job.title : 'Unknown',
            company: job ? (job.organization_name || job.company || 'Unknown') : 'Unknown',
            appliedDate: new Date().toISOString().split('T')[0],
            status: status,
            interviewDates: [],
            notes: '',
            followUpDate: null
        };
    } else {
        applications[jobId].status = status;
    }
    localStorage.setItem(applicationsKey, JSON.stringify(applications));

    const footerSelect = document.querySelector(`select.status-select-modal`);
    if (footerSelect) footerSelect.value = status;

    const state = getSavedJobsState();
    const shouldBookmark = (status !== 'not_applied' && status !== 'rejected');
    state[jobId] = { ...(state[jobId] || {}), status: status, isBookmarked: shouldBookmark };
    localStorage.setItem('savedJobMatcherState', JSON.stringify(state));

    updateWishlistCountBadge();
    refreshJobCardUI(jobId);
}

// Helper: Refresh job card UI status pill & active modal controls
function refreshJobCardUI(jobId) {
    applyFilters();

    if (detailModal && detailModal.classList.contains('active') && String(window.currentModalJobId) === String(jobId)) {
        updateJobModalFooterStatus(jobId);
        updateJobModalBookmarkButton(jobId);
    }
}

// Update footer status button di modal
function updateJobModalFooterStatus(jobId) {
    const applications = getApplicationsState();
    const footerSelect = document.querySelector('select.status-select-modal');
    if (footerSelect && applications[jobId]) {
        footerSelect.value = applications[jobId].status;
    }
}

// Update bookmark button di modal
window.updateJobModalBookmarkButton = function (jobId) {
    const state = getSavedJobsState();
    const isBookmarked = state[jobId] ? state[jobId].isBookmarked : false;

    const bookmarkBtn = document.querySelector('.btn-bookmark-modal');
    if (bookmarkBtn) {
        if (isBookmarked) {
            bookmarkBtn.classList.add('active');
            bookmarkBtn.innerHTML = '★ Tersimpan';
        } else {
            bookmarkBtn.classList.remove('active');
            bookmarkBtn.innerHTML = '☆ Simpan';
        }
    }
};

// Update application data
window.updateApplicationData = function (jobId, field, value) {
    const applicationsKey = 'jobMatcher_applications';
    const applications = getApplicationsState();

    if (applications[jobId]) {
        applications[jobId][field] = value;
        localStorage.setItem(applicationsKey, JSON.stringify(applications));
    }
}

// Add interview date
window.addInterviewDateForm = function (jobId) {
    const applicationsKey = 'jobMatcher_applications';
    const applications = getApplicationsState();

    if (applications[jobId]) {
        const interviewDate = prompt('Masukkan tanggal interview (YYYY-MM-DD):');
        const interviewType = prompt('Tipe interview? (Phone Screen / Technical / HR / Final):', 'Phone Screen');

        if (interviewDate) {
            applications[jobId].interviewDates.push({
                date: interviewDate,
                type: interviewType || 'Interview'
            });
            localStorage.setItem(applicationsKey, JSON.stringify(applications));
            window.openApplicationTracker(jobId);
        }
    }
}

// Remove interview date
window.removeInterviewDate = function (jobId, index) {
    const applicationsKey = 'jobMatcher_applications';
    const applications = getApplicationsState();

    if (applications[jobId]) {
        applications[jobId].interviewDates.splice(index, 1);
        localStorage.setItem(applicationsKey, JSON.stringify(applications));
        window.openApplicationTracker(jobId);
    }
}

// Save application tracker
window.saveApplicationTracker = function (jobId) {
    const applicationsKey = 'jobMatcher_applications';
    const applications = getApplicationsState();

    if (!applications[jobId]) {
        const job = allJobs.find(j => j.id == jobId);
        applications[jobId] = {
            jobId: jobId,
            jobTitle: job ? job.title : 'Unknown',
            company: job ? (job.organization_name || job.company || 'Unknown') : 'Unknown',
            appliedDate: new Date().toISOString().split('T')[0],
            status: 'not_applied',
            interviewDates: [],
            notes: '',
            followUpDate: null
        };
    }

    applications[jobId].status = document.getElementById(`appStatus_${jobId}`)?.value || applications[jobId].status;
    applications[jobId].appliedDate = document.getElementById(`appliedDate_${jobId}`)?.value || applications[jobId].appliedDate;
    applications[jobId].notes = document.getElementById(`notes_${jobId}`)?.value || '';
    applications[jobId].followUpDate = document.getElementById(`followUpDate_${jobId}`)?.value || '';

    localStorage.setItem(applicationsKey, JSON.stringify(applications));

    const footerSelect = document.querySelector(`select.status-select-modal`);
    if (footerSelect) footerSelect.value = applications[jobId].status;

    const state = getSavedJobsState();
    const shouldBookmark = (applications[jobId].status !== 'not_applied' && applications[jobId].status !== 'rejected');
    state[jobId] = { ...(state[jobId] || {}), status: applications[jobId].status, isBookmarked: shouldBookmark };
    localStorage.setItem('savedJobMatcherState', JSON.stringify(state));

    updateWishlistCountBadge();
    refreshJobCardUI(jobId);
    window.openApplicationTracker(jobId);

    showToast('✅ Progress lamaran berhasil disimpan!');
}

// Show application stats
window.showApplicationStats = function () {
    const applications = getApplicationsState();
    const statuses = { not_applied: 0, applied: 0, interview: 0, offer: 0, accepted: 0, rejected: 0 };

    for (const app of Object.values(applications)) {
        if (statuses[app.status] !== undefined) {
            statuses[app.status]++;
        }
    }

    const total = Object.keys(applications).length;
    const interviewRate = total > 0 ? Math.round((statuses.interview / total) * 100) : 0;
    const acceptanceRate = total > 0 ? Math.round((statuses.accepted / total) * 100) : 0;

    alert(`📋 Application Summary\n\n` +
        `Total Applications: ${total}\n` +
        `Applied: ${statuses.applied}\n` +
        `Interview: ${statuses.interview} (${interviewRate}%)\n` +
        `Offer: ${statuses.offer}\n` +
        `Accepted: ${statuses.accepted} (${acceptanceRate}%)\n` +
        `Rejected: ${statuses.rejected}`
    );
}


// Register Progressive Web App (PWA) Service Worker
if ('serviceWorker' in navigator) {
    window.addEventListener('load', () => {
        // Gunakan path relatif './sw.js' agar kompatibel di root domain maupun subpath GitHub Pages
        navigator.serviceWorker.register('./sw.js').then((reg) => {
            reg.update();
        }).catch((err) => {
            console.warn('[PWA] Service Worker registration failed:', err);
        });

        // Deteksi pergantian controller Service Worker (misal saat versi cache diperbarui)
        let refreshing = false;
        navigator.serviceWorker.addEventListener('controllerchange', () => {
            if (!refreshing) {
                refreshing = true;
                window.location.reload();
            }
        });
    });
}
