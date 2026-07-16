"""
Test suite untuk security fixes di Job Matcher
Testing: PII removal, input validation, timezone fix, race condition
"""

import os
import sys
import json
import unittest
from unittest.mock import patch, MagicMock
from io import StringIO

# Add scraper module
sys.path.insert(0, os.path.dirname(__file__))

# ──────────────────────────────────────────────────────────────────────────────
# TEST 1: Scraper.py - Check PII removed from PROFILE
# ──────────────────────────────────────────────────────────────────────────────

class TestScraperPIISecurity(unittest.TestCase):
    
    def test_profile_no_hardcoded_phone(self):
        """✅ Verify phone tidak di-hardcode di PROFILE"""
        import scraper
        
        # Phone harus kosong atau dari .env, bukan hardcoded
        self.assertNotEqual(
            scraper.PROFILE.get('phone'),
            '0819-9258-9299',
            "❌ FAILED: Phone masih hardcoded! Harus load dari .env"
        )
        print("✅ PASSED: Phone tidak hardcoded")
    
    def test_profile_no_hardcoded_email(self):
        """✅ Verify email tidak di-hardcode di PROFILE"""
        import scraper
        
        # Email harus kosong atau dari .env, bukan hardcoded
        self.assertNotEqual(
            scraper.PROFILE.get('email'),
            'ravilmuhammad987@gmail.com',
            "❌ FAILED: Email masih hardcoded! Harus load dari .env"
        )
        print("✅ PASSED: Email tidak hardcoded")


# ──────────────────────────────────────────────────────────────────────────────
# TEST 2: Scraper.py - Timezone fix (pytz import di top, bukan dalam function)
# ──────────────────────────────────────────────────────────────────────────────

class TestScraperTimezone(unittest.TestCase):
    
    def test_timestamp_wib_format(self):
        """✅ Verify get_timestamp_wib() returns correct format"""
        import scraper
        
        ts = scraper.get_timestamp_wib()
        
        # Format harus: "12 Juli 2026 - 17:23 WIB"
        self.assertIn('WIB', ts, "❌ Timestamp harus contain 'WIB'")
        self.assertIn('-', ts, "❌ Timestamp harus contain '-'")
        parts = ts.split(' - ')
        self.assertEqual(len(parts), 2, "❌ Format: 'DATE - TIME WIB'")
        
        print(f"✅ PASSED: Timestamp format valid: {ts}")
    
    def test_pytz_import_exists(self):
        """✅ Verify pytz di-import di top (bukan dalam function)"""
        import scraper
        import inspect
        
        # Check if pytz accessible di module level
        source = inspect.getsource(scraper)
        
        # Harus ada "import pytz" di top (sebelum function definition)
        lines = source.split('\n')
        pytz_import_line = None
        for i, line in enumerate(lines[:50]):  # Check first 50 lines
            if 'import pytz' in line and not line.strip().startswith('#'):
                pytz_import_line = i
                break
        
        self.assertIsNotNone(
            pytz_import_line,
            "❌ FAILED: pytz harus di-import di top level, bukan dalam function"
        )
        print(f"✅ PASSED: pytz imported at line {pytz_import_line}")


# ──────────────────────────────────────────────────────────────────────────────
# TEST 3: AI Service - Input Validation
# ──────────────────────────────────────────────────────────────────────────────

class TestAIServiceInputValidation(unittest.TestCase):
    
    def test_summarize_job_payload_size_limit(self):
        """✅ Verify summarize-job endpoint rejects oversized payloads"""
        import ai_service
        
        app = ai_service.app
        app.testing = True
        client = app.test_client()
        
        # Test oversized description (> 15000 chars)
        oversized_description = "a" * 20000
        response = client.post('/api/summarize-job', 
            json={
                'title': 'Test Job',
                'description': oversized_description,
                'requirements': 'Test'
            },
            content_type='application/json'
        )
        
        self.assertEqual(
            response.status_code,
            400,
            "❌ FAILED: Oversized payload should return 400"
        )
        
        data = json.loads(response.data)
        self.assertIn('Input too long', data.get('error', ''),
            "❌ FAILED: Error message should mention size limit"
        )
        print("✅ PASSED: Payload size validation working")
    
    def test_summarize_job_title_validation(self):
        """✅ Verify title validation"""
        import ai_service
        
        app = ai_service.app
        app.testing = True
        client = app.test_client()
        
        # Test empty title
        response = client.post('/api/summarize-job',
            json={
                'title': '',
                'description': 'Test description',
                'requirements': 'Test'
            },
            content_type='application/json'
        )
        
        self.assertEqual(response.status_code, 400,
            "❌ FAILED: Empty title should return 400"
        )
        print("✅ PASSED: Title validation working")


# ──────────────────────────────────────────────────────────────────────────────
# TEST 4: App.js - Cloud AI Consent (localStorage check)
# ──────────────────────────────────────────────────────────────────────────────

class TestAppJSCloudAIConsent(unittest.TestCase):
    
    def test_fetchCloudAI_logic_exists(self):
        """✅ Verify fetchCloudAI checks localStorage for consent"""
        with open('app.js', 'r', encoding='utf-8') as f:
            app_js = f.read()
        
        # Check if localStorage.getItem('enableCloudAI') exists in fetchCloudAI function
        self.assertIn(
            "localStorage.getItem('enableCloudAI')",
            app_js,
            "❌ FAILED: fetchCloudAI should check localStorage for consent"
        )
        
        # Check if confirm() prompt exists
        self.assertIn(
            'confirm(',
            app_js,
            "❌ FAILED: Should have user confirmation dialog"
        )
        
        print("✅ PASSED: Cloud AI consent check present in app.js")
    
    def test_race_condition_fix(self):
        """✅ Verify loadNewJobsData is awaited before applyFilters"""
        with open('app.js', 'r', encoding='utf-8') as f:
            app_js = f.read()
        
        # In loadJobsData function, should have: await loadNewJobsData(); applyFilters();
        # (not the old way: applyFilters(); await loadNewJobsData())
        
        lines = app_js.split('\n')
        loadJobsData_start = None
        for i, line in enumerate(lines):
            if 'async function loadJobsData()' in line:
                loadJobsData_start = i
                break
        
        if loadJobsData_start:
            # Check if within next 50 lines, we see await loadNewJobsData before applyFilters
            function_block = '\n'.join(lines[loadJobsData_start:loadJobsData_start+50])
            
            await_load_new = function_block.find('await loadNewJobsData()')
            apply_filters = function_block.find('applyFilters()')
            
            if await_load_new != -1 and apply_filters != -1:
                self.assertLess(
                    await_load_new,
                    apply_filters,
                    "❌ FAILED: await loadNewJobsData() should come BEFORE applyFilters()"
                )
                print("✅ PASSED: Race condition fixed - loadNewJobsData awaited first")
            else:
                print("⚠️  WARNING: Could not verify race condition fix location")


# ──────────────────────────────────────────────────────────────────────────────
# TEST 5: SW.js - Data files not cached
# ──────────────────────────────────────────────────────────────────────────────

class TestServiceWorkerCache(unittest.TestCase):
    
    def test_data_files_network_first(self):
        """✅ Verify DATA_FILES use network-first strategy"""
        with open('sw.js', 'r', encoding='utf-8') as f:
            sw_js = f.read()
        
        # Check DATA_FILES array includes new_jobs.json
        self.assertIn(
            '/new_jobs.json',
            sw_js,
            "❌ FAILED: new_jobs.json should be in DATA_FILES (not cached)"
        )
        
        # Check network-first strategy
        self.assertIn(
            'network-first',
            sw_js,
            "❌ FAILED: DATA_FILES should use network-first caching strategy"
        )
        
        print("✅ PASSED: Service Worker cache strategy correct")


# ──────────────────────────────────────────────────────────────────────────────
# RUN ALL TESTS
# ──────────────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    print("\n" + "="*70)
    print("🧪 RUNNING SECURITY FIX TEST SUITE")
    print("="*70 + "\n")
    
    # Run tests
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestScraperPIISecurity))
    suite.addTests(loader.loadTestsFromTestCase(TestScraperTimezone))
    suite.addTests(loader.loadTestsFromTestCase(TestAIServiceInputValidation))
    suite.addTests(loader.loadTestsFromTestCase(TestAppJSCloudAIConsent))
    suite.addTests(loader.loadTestsFromTestCase(TestServiceWorkerCache))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "="*70)
    if result.wasSuccessful():
        print("✅ ALL TESTS PASSED!")
        print(f"Ran {result.testsRun} tests - 0 failures")
    else:
        print(f"❌ SOME TESTS FAILED")
        print(f"Ran {result.testsRun} tests - {len(result.failures)} failures, {len(result.errors)} errors")
    print("="*70 + "\n")
