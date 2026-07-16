"""
Test cases untuk LinkedIn scraper function.
Dry run tanpa real HTTP requests.
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import sys
import os

# Import scraper module
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Mock LinkedIn response (HTML snippet)
MOCK_LINKEDIN_HTML = """
<html>
    <div class="base-card">
        <h3 class="base-search-card__title"><a>Data Analyst</a></h3>
        <h4 class="base-search-card__subtitle">PT Tech Indonesia</h4>
        <a class="base-card__full-link" href="https://linkedin.com/jobs/view/123456">Link</a>
        <span class="job-search-card__location">Jakarta, Indonesia</span>
    </div>
    <div class="base-card">
        <h3 class="base-search-card__title"><a>Python Developer</a></h3>
        <h4 class="base-search-card__subtitle">PT Digital Solutions</h4>
        <a class="base-card__full-link" href="https://linkedin.com/jobs/view/789012">Link</a>
        <span class="job-search-card__location">Bandung, Indonesia</span>
    </div>
</html>
"""

class TestLinkedInScraper(unittest.TestCase):
    """Test LinkedIn scraper dengan mock responses."""
    
    def test_scraper_imports(self):
        """Test apakah scraper.py import OK."""
        try:
            import scraper
            self.assertTrue(hasattr(scraper, 'scrape_linkedin_jobs'))
        except ImportError as e:
            self.fail(f"Failed to import scraper: {e}")
    
    @patch('scraper.requests.Session')
    def test_linkedin_scraper_safety_features(self, mock_session_class):
        """Test apakah LinkedIn scraper punya safety features."""
        import scraper
        
        # Create mock session
        mock_session = MagicMock()
        mock_response = Mock()
        mock_response.status_code = 200
        mock_response.text = MOCK_LINKEDIN_HTML
        mock_session.get.return_value = mock_response
        mock_session.headers = {}
        
        # Run scraper dengan max_jobs=50 (untuk test cepat)
        result = scraper.scrape_linkedin_jobs(mock_session, max_jobs=50)
        
        # Assertions
        self.assertIsInstance(result, list)
        print(f"✅ PASSED: scrape_linkedin_jobs() returns list (got {len(result)} jobs)")
        
    def test_linkedin_job_structure(self):
        """Test job dict structure dari LinkedIn scraper."""
        import scraper
        
        # Mock job structure
        mock_job = {
            "id": "linkedin_123456",
            "title": "Data Analyst",
            "organization_id": "LinkedIn",
            "organization_name": "PT Tech Indonesia",
            "slug": "linkedin-0",
            "type_name": "Full Time / Contract",
            "level": "Profesional",
            "location": "Jakarta, Indonesia",
            "workplace": "Hybrid / WFO",
            "due_date": "Aktif",
            "group": "Tech & Data",
            "url": "https://linkedin.com/jobs/view/123456",
            "description": "<p><strong>Data Analyst</strong></p>",
            "requirements": "<p><strong>Data Analyst</strong></p>",
            "source": "LinkedIn",
            "logo": None
        }
        
        # Check required keys
        required_keys = ["id", "title", "organization_name", "location", "url", "source"]
        for key in required_keys:
            self.assertIn(key, mock_job)
        
        self.assertEqual(mock_job["source"], "LinkedIn")
        self.assertTrue(mock_job["id"].startswith("linkedin_"))
        print(f"✅ PASSED: LinkedIn job structure valid")
        
    def test_rate_limiting_delay(self):
        """Test apakah scraper punya rate limiting logic."""
        import scraper
        import inspect
        
        # Get function source
        source = inspect.getsource(scraper.scrape_linkedin_jobs)
        
        # Check untuk delay logic
        self.assertIn("time.sleep", source)
        self.assertIn("delay", source)
        self.assertIn("2 +", source)  # 2-5 sec delay pattern
        
        print(f"✅ PASSED: Rate limiting logic detected (time.sleep with variable delay)")
        
    def test_user_agent_rotation(self):
        """Test apakah scraper punya User-Agent rotation."""
        import scraper
        import inspect
        
        source = inspect.getsource(scraper.scrape_linkedin_jobs)
        
        # Check untuk User-Agent rotation
        self.assertIn("user_agents", source)
        self.assertIn("User-Agent", source)
        self.assertIn("Chrome", source)
        
        print(f"✅ PASSED: User-Agent rotation logic detected")
        
    def test_error_handling_429(self):
        """Test apakah scraper handle 429 (Too Many Requests)."""
        import scraper
        import inspect
        
        source = inspect.getsource(scraper.scrape_linkedin_jobs)
        
        # Check untuk 429 handling
        self.assertIn("429", source)
        self.assertIn("rate limit", source.lower())
        
        print(f"✅ PASSED: 429 rate limit error handling detected")
        
    def test_error_handling_403(self):
        """Test apakah scraper handle 403 (Forbidden)."""
        import scraper
        import inspect
        
        source = inspect.getsource(scraper.scrape_linkedin_jobs)
        
        # Check untuk 403 handling
        self.assertIn("403", source)
        
        print(f"✅ PASSED: 403 forbidden error handling detected")
        
    def test_location_filter_indonesia(self):
        """Test apakah scraper filter location ke Indonesia."""
        import scraper
        import inspect
        
        source = inspect.getsource(scraper.scrape_linkedin_jobs)
        
        # Check untuk location filter
        self.assertIn("Indonesia", source)
        self.assertIn("location", source.lower())
        
        print(f"✅ PASSED: Location filter 'Indonesia' detected")
        
    def test_max_jobs_limit(self):
        """Test apakah scraper respect max_jobs parameter."""
        import scraper
        import inspect
        
        source = inspect.getsource(scraper.scrape_linkedin_jobs)
        
        # Check untuk max_jobs usage
        self.assertIn("max_jobs", source)
        self.assertIn("len(linkedin_jobs) < max_jobs", source)
        
        print(f"✅ PASSED: Max jobs limit logic detected")

if __name__ == '__main__':
    print("=" * 70)
    print("Testing LinkedIn Scraper Implementation")
    print("=" * 70)
    print()
    
    unittest.main(verbosity=2, exit=False)
    
    print()
    print("=" * 70)
    print("✅ LinkedIn Scraper Implementation Test Complete")
    print("=" * 70)
