"""
Application Tracker for Job Matcher
Track job applications, interview timeline, and application metrics
"""

from typing import Dict, List, Optional
from datetime import datetime, timedelta
import json


class ApplicationTracker:
    """Track job applications and interview progress"""
    
    # Application statuses
    STATUS_NOT_APPLIED = 'not_applied'
    STATUS_APPLIED = 'applied'
    STATUS_INTERVIEW = 'interview'
    STATUS_OFFER = 'offer'
    STATUS_ACCEPTED = 'accepted'
    STATUS_REJECTED = 'rejected'
    
    VALID_STATUSES = [STATUS_NOT_APPLIED, STATUS_APPLIED, STATUS_INTERVIEW, STATUS_OFFER, STATUS_ACCEPTED, STATUS_REJECTED]
    
    def __init__(self):
        """Initialize application tracker"""
        self.applications = {}  # job_id -> application data
    
    def add_application(self, job_id: str, job_title: str, company: str, 
                       applied_date: Optional[str] = None, status: str = STATUS_APPLIED) -> Dict:
        """
        Add a new application
        
        Args:
            job_id: Unique job identifier
            job_title: Job position title
            company: Company name
            applied_date: Date applied (YYYY-MM-DD), defaults to today
            status: Application status
        
        Returns:
            Application record
        """
        if status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {status}. Must be one of {self.VALID_STATUSES}")
        
        if applied_date is None:
            applied_date = datetime.now().strftime('%Y-%m-%d')
        
        application = {
            'job_id': job_id,
            'job_title': job_title,
            'company': company,
            'applied_date': applied_date,
            'status': status,
            'interview_dates': [],
            'offer_date': None,
            'response_date': None,
            'notes': '',
            'follow_up_date': None,
            'created_at': datetime.now().isoformat()
        }
        
        self.applications[job_id] = application
        return application
    
    def update_status(self, job_id: str, new_status: str, date: Optional[str] = None) -> Dict:
        """
        Update application status
        
        Args:
            job_id: Job identifier
            new_status: New status
            date: Date of status update (YYYY-MM-DD), defaults to today
        
        Returns:
            Updated application record
        """
        if job_id not in self.applications:
            raise ValueError(f"Application not found for job_id: {job_id}")
        
        if new_status not in self.VALID_STATUSES:
            raise ValueError(f"Invalid status: {new_status}")
        
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        app = self.applications[job_id]
        app['status'] = new_status
        
        # Auto-set dates based on status
        if new_status == self.STATUS_INTERVIEW:
            if not app['interview_dates']:
                app['interview_dates'].append({'scheduled_date': date, 'completed': False})
        elif new_status in [self.STATUS_OFFER, self.STATUS_ACCEPTED]:
            app['offer_date'] = date
        elif new_status == self.STATUS_REJECTED:
            app['response_date'] = date
        
        return app
    
    def add_interview(self, job_id: str, interview_date: str, interview_type: str = 'Phone Screen',
                     interviewer: str = '', notes: str = '') -> Dict:
        """
        Add interview scheduled for an application
        
        Args:
            job_id: Job identifier
            interview_date: Interview date (YYYY-MM-DD or YYYY-MM-DD HH:MM)
            interview_type: Type of interview (Phone Screen, Technical, HR, Final)
            interviewer: Interviewer name
            notes: Interview notes
        
        Returns:
            Updated application record
        """
        if job_id not in self.applications:
            raise ValueError(f"Application not found for job_id: {job_id}")
        
        app = self.applications[job_id]
        
        interview = {
            'scheduled_date': interview_date,
            'type': interview_type,
            'interviewer': interviewer,
            'notes': notes,
            'completed': False,
            'result': None  # passed/failed/pending
        }
        
        app['interview_dates'].append(interview)
        
        # Auto-update status if not already in interview phase
        if app['status'] in [self.STATUS_NOT_APPLIED, self.STATUS_APPLIED]:
            app['status'] = self.STATUS_INTERVIEW
        
        return app
    
    def complete_interview(self, job_id: str, interview_index: int = 0, result: str = 'passed',
                          notes: str = '') -> Dict:
        """
        Mark interview as completed
        
        Args:
            job_id: Job identifier
            interview_index: Index of interview in list (0 = first interview)
            result: Interview result (passed, failed, pending)
            notes: Result notes
        
        Returns:
            Updated application record
        """
        if job_id not in self.applications:
            raise ValueError(f"Application not found for job_id: {job_id}")
        
        app = self.applications[job_id]
        
        if interview_index >= len(app['interview_dates']):
            raise ValueError(f"Interview index {interview_index} out of range")
        
        interview = app['interview_dates'][interview_index]
        interview['completed'] = True
        interview['result'] = result
        interview['notes'] = notes
        interview['completion_date'] = datetime.now().strftime('%Y-%m-%d')
        
        return app
    
    def add_note(self, job_id: str, note: str) -> Dict:
        """Add note to application"""
        if job_id not in self.applications:
            raise ValueError(f"Application not found for job_id: {job_id}")
        
        app = self.applications[job_id]
        app['notes'] = note
        return app
    
    def set_follow_up(self, job_id: str, follow_up_date: str) -> Dict:
        """
        Set follow-up reminder date
        
        Args:
            job_id: Job identifier
            follow_up_date: Follow-up date (YYYY-MM-DD)
        
        Returns:
            Updated application record
        """
        if job_id not in self.applications:
            raise ValueError(f"Application not found for job_id: {job_id}")
        
        self.applications[job_id]['follow_up_date'] = follow_up_date
        return self.applications[job_id]
    
    def get_application(self, job_id: str) -> Dict:
        """Get application record"""
        if job_id not in self.applications:
            raise ValueError(f"Application not found for job_id: {job_id}")
        return self.applications[job_id]
    
    def get_all_applications(self) -> List[Dict]:
        """Get all applications"""
        return list(self.applications.values())
    
    def get_by_status(self, status: str) -> List[Dict]:
        """Get all applications with specific status"""
        return [app for app in self.applications.values() if app['status'] == status]
    
    def calculate_metrics(self) -> Dict:
        """
        Calculate application metrics
        
        Returns:
        {
            'total_applied': 25,
            'interview_rate': '40%',  # interview / applied
            'acceptance_rate': '20%',  # accepted / applied
            'average_response_time': 5,  # days
            'status_breakdown': {'applied': 10, 'interview': 5, ...}
        }
        """
        all_apps = self.get_all_applications()
        
        if not all_apps:
            return {
                'total_applied': 0,
                'interview_rate': '0%',
                'acceptance_rate': '0%',
                'average_response_time': 0,
                'status_breakdown': {},
                'by_company': {}
            }
        
        # Count by status
        status_breakdown = {}
        for status in self.VALID_STATUSES:
            count = len(self.get_by_status(status))
            if count > 0:
                status_breakdown[status] = count
        
        # Calculate rates
        total_applied = len([a for a in all_apps if a['status'] != self.STATUS_NOT_APPLIED])
        interview_count = len(self.get_by_status(self.STATUS_INTERVIEW))
        offer_count = len(self.get_by_status(self.STATUS_OFFER))
        accepted_count = len(self.get_by_status(self.STATUS_ACCEPTED))
        
        interview_rate = (interview_count / total_applied * 100) if total_applied > 0 else 0
        acceptance_rate = (accepted_count / total_applied * 100) if total_applied > 0 else 0
        
        # Calculate average response time (from applied to interview/rejection)
        response_times = []
        for app in all_apps:
            if app['response_date'] or app['interview_dates']:
                applied = datetime.strptime(app['applied_date'], '%Y-%m-%d')
                if app['interview_dates'] and app['interview_dates'][0].get('scheduled_date'):
                    response = datetime.strptime(app['interview_dates'][0]['scheduled_date'].split()[0], '%Y-%m-%d')
                    response_times.append((response - applied).days)
                elif app['response_date']:
                    response = datetime.strptime(app['response_date'], '%Y-%m-%d')
                    response_times.append((response - applied).days)
        
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Count by company
        by_company = {}
        for app in all_apps:
            company = app['company']
            by_company[company] = by_company.get(company, 0) + 1
        
        return {
            'total_applied': total_applied,
            'interview_rate': f"{interview_rate:.1f}%",
            'acceptance_rate': f"{acceptance_rate:.1f}%",
            'average_response_time': round(avg_response_time),
            'status_breakdown': status_breakdown,
            'by_company': by_company,
            'top_companies': sorted(by_company.items(), key=lambda x: x[1], reverse=True)[:5]
        }
    
    def get_upcoming_follow_ups(self, days_ahead: int = 7) -> List[Dict]:
        """
        Get applications with upcoming follow-up dates
        
        Args:
            days_ahead: Number of days to look ahead (default 7 days)
        
        Returns:
            List of applications with follow-up dates in the next N days
        """
        today = datetime.now().date()
        end_date = today + timedelta(days=days_ahead)
        
        upcoming = []
        for app in self.get_all_applications():
            if app['follow_up_date']:
                follow_up = datetime.strptime(app['follow_up_date'], '%Y-%m-%d').date()
                if today <= follow_up <= end_date:
                    upcoming.append({
                        'job_id': app['job_id'],
                        'company': app['company'],
                        'job_title': app['job_title'],
                        'follow_up_date': app['follow_up_date'],
                        'days_until': (follow_up - today).days
                    })
        
        return sorted(upcoming, key=lambda x: x['days_until'])
    
    def format_tracker_html(self, metrics: Optional[Dict] = None) -> str:
        """Format tracker dashboard for HTML display"""
        
        if metrics is None:
            metrics = self.calculate_metrics()
        
        html = f"""
        <div class="tracker-dashboard">
            <div class="tracker-header">
                <h3>📋 Application Tracker</h3>
                <p>Track your job applications and interview progress</p>
            </div>
            
            <div class="tracker-metrics">
                <div class="metric-card total">
                    <div class="metric-number">{metrics['total_applied']}</div>
                    <div class="metric-label">Total Applied</div>
                </div>
                <div class="metric-card interview">
                    <div class="metric-number">{metrics['interview_rate']}</div>
                    <div class="metric-label">Interview Rate</div>
                </div>
                <div class="metric-card acceptance">
                    <div class="metric-number">{metrics['acceptance_rate']}</div>
                    <div class="metric-label">Acceptance Rate</div>
                </div>
                <div class="metric-card response">
                    <div class="metric-number">{metrics['average_response_time']} days</div>
                    <div class="metric-label">Avg Response Time</div>
                </div>
            </div>
            
            <div class="tracker-content">
                <div class="status-breakdown">
                    <h4>Status Breakdown</h4>
                    {self._format_status_breakdown(metrics['status_breakdown'])}
                </div>
                
                <div class="top-companies">
                    <h4>Top Companies</h4>
                    {self._format_top_companies(metrics['top_companies'])}
                </div>
            </div>
        </div>
        """
        
        return html
    
    def _format_status_breakdown(self, breakdown: Dict) -> str:
        """Format status breakdown"""
        status_labels = {
            'not_applied': '📌 Not Applied',
            'applied': '🚀 Applied',
            'interview': '💬 Interview',
            'offer': '📝 Offer',
            'accepted': '🎉 Accepted',
            'rejected': '❌ Rejected'
        }
        
        html = '<div class="status-list">'
        for status, count in breakdown.items():
            label = status_labels.get(status, status)
            html += f'<div class="status-item"><span>{label}</span><strong>{count}</strong></div>'
        html += '</div>'
        return html
    
    def _format_top_companies(self, companies: List[tuple]) -> str:
        """Format top companies"""
        if not companies:
            return "<p style='color: #888;'>No applications yet</p>"
        
        html = '<div class="companies-list">'
        for company, count in companies:
            html += f'<div class="company-item"><span>{company}</span><strong>{count}</strong></div>'
        html += '</div>'
        return html
    
    def to_json(self) -> str:
        """Export applications to JSON"""
        return json.dumps(self.applications, indent=2, default=str)
    
    def from_json(self, json_data: str):
        """Load applications from JSON"""
        self.applications = json.loads(json_data)


# Test the module
if __name__ == '__main__':
    # Initialize tracker
    tracker = ApplicationTracker()
    
    # Add applications
    tracker.add_application('job_1', 'Data Analyst', 'Astra Financial', '2024-01-10')
    tracker.add_application('job_2', 'Python Developer', 'PT Tokopedia', '2024-01-12')
    tracker.add_application('job_3', 'ML Engineer', 'Grab Indonesia', '2024-01-15')
    
    # Update statuses and add interviews
    tracker.update_status('job_1', 'interview', '2024-01-15')
    tracker.add_interview('job_1', '2024-01-18', 'Phone Screen', 'HR Manager', 'General fit interview')
    
    tracker.update_status('job_2', 'interview')
    tracker.add_interview('job_2', '2024-01-20', 'Technical Test', 'Tech Lead')
    tracker.add_interview('job_2', '2024-01-25', 'Final Interview', 'Head of Eng')
    
    # Mark interview as completed
    tracker.complete_interview('job_1', 0, 'passed', 'Good communication, interested')
    
    # Calculate metrics
    metrics = tracker.calculate_metrics()
    print("\n=== APPLICATION TRACKER METRICS ===")
    print(f"Total Applied: {metrics['total_applied']}")
    print(f"Interview Rate: {metrics['interview_rate']}")
    print(f"Acceptance Rate: {metrics['acceptance_rate']}")
    print(f"Avg Response Time: {metrics['average_response_time']} days")
    print(f"\nStatus Breakdown: {metrics['status_breakdown']}")
    print(f"Top Companies: {metrics['top_companies']}")
    
    # Get upcoming follow-ups
    tracker.set_follow_up('job_1', '2024-01-20')
    tracker.set_follow_up('job_2', '2024-01-22')
    upcoming = tracker.get_upcoming_follow_ups(7)
    print(f"\nUpcoming Follow-ups (next 7 days): {upcoming}")
