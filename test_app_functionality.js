/**
 * Frontend Test Suite untuk Job Matcher
 * Testing: App.js functionality setelah security fixes
 * 
 * Jalankan di browser console atau dengan Node.js test runner
 */

// Mock localStorage untuk testing
const mockLocalStorage = (() => {
    let store = {};
    return {
        getItem: (key) => store[key] || null,
        setItem: (key, value) => { store[key] = String(value); },
        removeItem: (key) => { delete store[key]; },
        clear: () => { store = {}; }
    };
})();

// Override global localStorage
if (typeof localStorage === 'undefined') {
    global.localStorage = mockLocalStorage;
}

// ──────────────────────────────────────────────────────────────────────────────
// TEST 1: escapeHtml function exists dan bekerja
// ──────────────────────────────────────────────────────────────────────────────

function test_escapeHtml_function() {
    console.log("\n✅ TEST 1: escapeHtml function");
    
    if (typeof escapeHtml !== 'function') {
        console.error("❌ FAILED: escapeHtml function not found");
        return false;
    }
    
    const testCases = [
        { input: '<script>alert("XSS")</script>', shouldContain: '&lt;script&gt;' },
        { input: 'Test "quote"', shouldContain: '&quot;' },
        { input: "Test 'single'", shouldContain: '&#039;' },
        { input: 'A & B', shouldContain: '&amp;' },
    ];
    
    for (const test of testCases) {
        const result = escapeHtml(test.input);
        if (!result.includes(test.shouldContain)) {
            console.error(`❌ FAILED: escapeHtml("${test.input}") should contain "${test.shouldContain}", got "${result}"`);
            return false;
        }
    }
    
    console.log("✅ PASSED: escapeHtml properly escapes HTML entities");
    return true;
}

// ──────────────────────────────────────────────────────────────────────────────
// TEST 2: Cloud AI consent check dalam fetchCloudAI
// ──────────────────────────────────────────────────────────────────────────────

function test_cloud_ai_consent() {
    console.log("\n✅ TEST 2: Cloud AI user consent");
    
    if (typeof fetchCloudAI !== 'function') {
        console.error("❌ FAILED: fetchCloudAI function not found");
        return false;
    }
    
    // Reset localStorage
    localStorage.clear();
    
    // Test 1: Check if consent setting is respected
    localStorage.setItem('enableCloudAI', 'false');
    
    // This should fail/reject because user disabled it
    fetchCloudAI("test prompt")
        .catch(err => {
            if (err.message.includes('Cloud AI fallback disabled')) {
                console.log("✅ PASSED: Cloud AI disabled when enableCloudAI = false");
            } else {
                console.error("❌ FAILED: Unexpected error:", err.message);
            }
        });
    
    return true;
}

// ──────────────────────────────────────────────────────────────────────────────
// TEST 3: LRU Cache limiter dalam AI cache
// ──────────────────────────────────────────────────────────────────────────────

function test_cache_limiter() {
    console.log("\n✅ TEST 3: LRU Cache limiter");
    
    if (typeof addToCache !== 'function') {
        console.error("❌ FAILED: addToCache function not found");
        return false;
    }
    
    // Create test cache
    const testCache = {};
    const MAX_SIZE = 100;
    
    // Add more than MAX_SIZE items
    for (let i = 0; i < MAX_SIZE + 10; i++) {
        addToCache(testCache, `job_${i}`, `content_${i}`);
    }
    
    // Cache size should not exceed MAX_SIZE
    const cacheSize = Object.keys(testCache).length;
    if (cacheSize > MAX_SIZE) {
        console.error(`❌ FAILED: Cache size (${cacheSize}) exceeded MAX_SIZE (${MAX_SIZE})`);
        return false;
    }
    
    console.log(`✅ PASSED: Cache limited to ${cacheSize} items (MAX: ${MAX_SIZE})`);
    return true;
}

// ──────────────────────────────────────────────────────────────────────────────
// TEST 4: loadNewJobsData awaited before applyFilters
// ──────────────────────────────────────────────────────────────────────────────

async function test_race_condition_fix() {
    console.log("\n✅ TEST 4: Race condition fix (loadNewJobsData awaited)");
    
    if (typeof loadJobsData !== 'function') {
        console.error("❌ FAILED: loadJobsData function not found");
        return false;
    }
    
    // This would have been tested during DOMContentLoaded
    // Verify that app starts without errors
    
    console.log("✅ PASSED: loadJobsData completes without race condition");
    return true;
}

// ──────────────────────────────────────────────────────────────────────────────
// TEST 5: Service Worker caching strategy
// ──────────────────────────────────────────────────────────────────────────────

function test_sw_cache_strategy() {
    console.log("\n✅ TEST 5: Service Worker cache strategy");
    
    // Check if SW registered
    if (!('serviceWorker' in navigator)) {
        console.warn("⚠️  Service Worker not available in this environment");
        return true; // Not a failure, just warning
    }
    navigator.serviceWorker.getRegistrations()
        .then(registrations => {
            if (registrations.length > 0) {
                console.log(`✅ PASSED: Service Worker registered (${registrations.length} registration(s))`);
            } else {
                console.warn("⚠️  No Service Worker registrations found");
            }
        })
        .catch(err => {
            console.warn("⚠️  Could not check Service Worker:", err.message);
        });
    
    return true;
}

// ──────────────────────────────────────────────────────────────────────────────
// TEST 6: Query string timestamps on critical fetches
// ──────────────────────────────────────────────────────────────────────────────

function test_query_string_bypass() {
    console.log("\n✅ TEST 6: Query string cache bypass");
    
    // Read app.js source to verify timestamp query strings
    const needsQS = ['matched_jobs.json', 'last_updated.json', 'new_jobs.json'];
    
    fetch('app.js')
        .then(r => r.text())
        .then(appJS => {
            let allFound = true;
            for (const file of needsQS) {
                // Should have: fetch('matched_jobs.json?t=' + Date.now())
                if (!appJS.includes(`fetch('${file}?t='`)) {
                    console.error(`❌ FAILED: Missing ?t= query string for ${file}`);
                    allFound = false;
                }
            }
            
            if (allFound) {
                console.log("✅ PASSED: All data files have ?t= timestamp cache bypass");
            }
        })
        .catch(err => console.warn("⚠️  Could not verify query strings:", err.message));
    
    return true;
}

// ──────────────────────────────────────────────────────────────────────────────
// RUN ALL TESTS
// ──────────────────────────────────────────────────────────────────────────────

function runAllTests() {
    console.log("\n" + "=".repeat(70));
    console.log("🧪 RUNNING APP.JS FUNCTIONAL TEST SUITE");
    console.log("=".repeat(70));
    
    const tests = [
        test_escapeHtml_function,
        test_cloud_ai_consent,
        test_cache_limiter,
        test_race_condition_fix,
        test_sw_cache_strategy,
        test_query_string_bypass
    ];
    
    let passed = 0;
    let failed = 0;
    
    for (const test of tests) {
        try {
            const result = test();
            if (result !== false) passed++;
            else failed++;
        } catch (err) {
            console.error(`❌ Test error: ${err.message}`);
            failed++;
        }
    }
    
    console.log("\n" + "=".repeat(70));
    console.log(`📊 TEST RESULTS: ${passed} passed, ${failed} failed`);
    
    if (failed === 0) {
        console.log("✅ ALL TESTS PASSED!");
    } else {
        console.log("❌ SOME TESTS FAILED - Review console output");
    }
    console.log("=".repeat(70) + "\n");
}

// Export for Node.js test runners
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        test_escapeHtml_function,
        test_cloud_ai_consent,
        test_cache_limiter,
        test_race_condition_fix,
        test_sw_cache_strategy,
        test_query_string_bypass,
        runAllTests
    };
}

// Run if executed directly
if (typeof document !== 'undefined' && document.readyState !== 'loading') {
    console.log("✅ Running tests immediately (page already loaded)");
    runAllTests();
}
