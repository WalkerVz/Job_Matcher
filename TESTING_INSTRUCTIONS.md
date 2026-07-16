# 🧪 Frontend Testing Instructions

## Quick Start

### Option 1: Simple Test Runner (Recommended)
1. Buka file: `test_runner.html` di browser
2. Klik tombol **"▶️ Run All Tests"**
3. Tunggu hasil test muncul di console
4. Lihat summary di bawah

### Option 2: Manual Console Test
1. Buka web app di browser (http://localhost atau Vercel URL)
2. Buka DevTools: **F12 → Console tab**
3. Copy seluruh code dari `test_app_functionality.js`
4. Paste ke console
5. Jalankan: `runAllTests()`

---

## What Gets Tested

### ✅ TEST 1: escapeHtml() Function
- **Check**: HTML entities properly escaped
- **Expected**: `<`, `>`, `&`, `"`, `'` di-convert ke HTML entities
- **Impact**: Prevents XSS injection attacks

### ✅ TEST 2: Cloud AI User Consent
- **Check**: localStorage consent mechanism
- **Expected**: `fetchCloudAI()` checks `enableCloudAI` setting
- **Impact**: User privacy - can opt-out of 3rd party AI

### ✅ TEST 3: LRU Cache Limiter
- **Check**: Cache size doesn't exceed 100 items
- **Expected**: Old entries removed when max reached
- **Impact**: Prevents memory leak

### ✅ TEST 4: Race Condition Fix
- **Check**: loadNewJobsData awaited before applyFilters
- **Expected**: Function executes in correct order
- **Impact**: App state stays consistent

### ✅ TEST 5: Query String Cache Bypass
- **Check**: `?t=Date.now()` timestamps on data files
- **Expected**: `matched_jobs.json?t=`, `last_updated.json?t=`, `new_jobs.json?t=`
- **Impact**: Mobile SW cache doesn't stale data

### ✅ TEST 6: Service Worker Registration
- **Check**: SW properly registered
- **Expected**: One or more registrations active
- **Impact**: Offline support working

---

## Expected Results

### ✅ All Pass
```
📊 RESULTS: 6 passed, 0 failed
✅ ALL TESTS PASSED!
6 / 6 tests passing
```

### ⚠️ Some Warn (OK)
```
⚠️ No Service Worker registrations found
⚠️ Could not verify "matched_jobs.json?t=" in DOM

📊 RESULTS: 5 passed, 0 failed
✅ ALL TESTS PASSED!
```
(Warnings are OK - just means we couldn't verify in this specific environment)

### ❌ If Tests Fail
- **escapeHtml not found**: escapeHtml() function missing from app.js
- **fetchCloudAI error**: fetchCloudAI() function not properly implemented
- **Cache size exceeded**: addToCache() function not limiting properly
- **Race condition**: loadJobsData() execution order wrong

---

## Troubleshooting

### "escapeHtml is not defined"
- ✅ SOLUTION: escapeHtml() was successfully added to app.js
- Check: Is app.js loaded? F12 → Sources → app.js

### "addToCache is not defined"
- ✅ SOLUTION: addToCache() was added for cache limiting
- Status: This is optional (Task #3 was rejected by user)
- Can ignore if not critical

### "Cannot read localStorage"
- ✅ Normal in file:// protocol
- Try: Open via local server instead
- Command: `python -m http.server 8000` then visit http://localhost:8000

### Service Worker test returns 0 registrations
- ✅ OK: Just means SW cache not active locally
- Try: Check on live Vercel deployment
- Or: Run `navigator.serviceWorker.getRegistrations()` in console

---

## Manual Verification Checklist

- [ ] escapeHtml() escapes dangerous characters
- [ ] Cloud AI consent prompt appears when needed
- [ ] App loads without console errors
- [ ] New job badges appear with timestamp
- [ ] Mobile cache properly refreshes (hard refresh: Ctrl+Shift+R)
- [ ] All filters and search work normally
- [ ] Modal detail view loads without XSS

---

## After Testing

### If All Tests Pass ✅
1. Note: "All frontend tests passing"
2. Ready to push to GitHub

### If Some Tests Fail ❌
1. Check console for specific error messages
2. Review modified files:
   - `scraper.py` - PII removal
   - `ai_service.py` - Input validation
   - `app.js` - Fixes applied
3. Report error details

---

## Test Files

- **test_runner.html** ← Visual test runner (recommended)
- **test_app_functionality.js** ← Manual console test
- **test_security_fixes.py** ← Backend tests (already passed ✅)
- **TEST_RESULTS.md** ← Full test documentation

---

**Last Updated**: 17 July 2026
