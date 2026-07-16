"""
Skills Gap Analyzer for Job Matcher
Compares user skills vs job requirements and provides learning recommendations
"""

from typing import Dict, List, Tuple
import json
from nlp_analyzer import RequirementAnalyzer


class SkillsGapAnalyzer:
    """Analyze skill gaps between user profile and job requirements"""
    
    def __init__(self, user_skills: List[str]):
        """
        Initialize with user's current skills
        
        Args:
            user_skills: List of user's skills [e.g., 'Python', 'SQL', 'Power BI']
        """
        self.user_skills = [s.lower().strip() for s in user_skills]
        self.skill_categories = {
            'Languages': ['python', 'javascript', 'java', 'c++', 'r', 'golang', 'php', 'rust'],
            'Data Science': ['machine learning', 'deep learning', 'nlp', 'computer vision', 'data science', 'advanced ml'],
            'BI Tools': ['tableau', 'power bi', 'looker', 'qlik', 'metabase', 'superset'],
            'Databases': ['sql', 'mysql', 'postgresql', 'mongodb', 'redis', 'cassandra', 'elasticsearch'],
            'Tools & Platforms': ['docker', 'kubernetes', 'git', 'aws', 'gcp', 'azure', 'jenkins', 'dataiku'],
            'Soft Skills': ['komunikasi', 'teamwork', 'leadership', 'problem solving', 'analytical thinking']
        }
    
    def normalize_skill(self, skill: str) -> str:
        """Normalize skill name untuk comparison"""
        normalized = skill.lower().strip()
        # Handle variations
        variations = {
            'ml': 'machine learning',
            'bi': 'business intelligence',
            'etl': 'data pipeline',
            'ai': 'artificial intelligence',
            'dw': 'data warehouse',
            'db': 'database'
        }
        return variations.get(normalized, normalized)
    
    def find_skill_category(self, skill: str) -> str:
        """Determine which category a skill belongs to"""
        normalized = self.normalize_skill(skill)
        for category, skills in self.skill_categories.items():
            if any(normalized in s.lower() or s.lower() in normalized for s in skills):
                return category
        return 'Other'
    
    def calculate_skill_similarity(self, skill1: str, skill2: str) -> float:
        """
        Calculate similarity between two skills (0-1)
        Higher = more similar
        """
        s1 = self.normalize_skill(skill1)
        s2 = self.normalize_skill(skill2)
        
        # Exact match
        if s1 == s2:
            return 1.0
        
        # Partial match (skill1 is subset of skill2 or vice versa)
        if s1 in s2 or s2 in s1:
            return 0.7
        
        # Same category but different skills
        cat1 = self.find_skill_category(skill1)
        cat2 = self.find_skill_category(skill2)
        if cat1 == cat2 and cat1 != 'Other':
            return 0.4
        
        return 0.0
    
    def analyze_gap(self, job_requirements: List[str]) -> Dict:
        """
        Analyze skill gap between user and job requirements
        
        Returns:
        {
            'matched_skills': [{'user_skill': 'Python', 'job_requirement': 'Python', 'similarity': 1.0}],
            'missing_skills': [{'skill': 'Docker', 'category': 'Tools', 'priority': 'HIGH'}],
            'advanced_skills': [{'user_skill': 'Basic Python', 'job_requirement': 'Advanced Python'}],
            'match_percentage': 60.0,
            'recommendations': [...]
        }
        """
        
        # Normalize job requirements
        job_skills = [self.normalize_skill(s) for s in job_requirements]
        
        matched_skills = []
        advanced_skills = []
        missing_skills = []
        skill_matches = {}
        
        # Find matches and gaps
        for job_skill in job_skills:
            best_match = None
            best_similarity = 0
            
            for user_skill in self.user_skills:
                similarity = self.calculate_skill_similarity(user_skill, job_skill)
                if similarity > best_similarity:
                    best_similarity = similarity
                    best_match = user_skill
            
            if best_similarity >= 0.7:
                # Good match
                matched_skills.append({
                    'user_skill': best_match,
                    'job_requirement': job_skill,
                    'similarity': round(best_similarity, 2)
                })
                skill_matches[job_skill] = best_match
            elif best_similarity >= 0.4:
                # Partial match (related skill but not exact)
                advanced_skills.append({
                    'user_skill': best_match,
                    'job_requirement': job_skill,
                    'gap': 'Need to level up from ' + best_match
                })
                skill_matches[job_skill] = best_match
            else:
                # No match
                missing_skills.append({
                    'skill': job_skill,
                    'category': self.find_skill_category(job_skill),
                    'priority': self._calculate_priority(job_skill, job_skills)
                })
        
        # Calculate match percentage
        match_percentage = (len(matched_skills) / len(job_skills) * 100) if job_skills else 0
        
        return {
            'matched_skills': matched_skills,
            'missing_skills': missing_skills,
            'advanced_skills': advanced_skills,
            'total_job_skills': len(job_skills),
            'matched_count': len(matched_skills),
            'missing_count': len(missing_skills),
            'match_percentage': round(match_percentage, 1),
            'recommendations': self.generate_recommendations(missing_skills, advanced_skills)
        }
    
    def _calculate_priority(self, skill: str, all_skills: List[str]) -> str:
        """
        Determine priority level for learning a skill
        HIGH: appears in 50%+ of jobs
        MEDIUM: appears in 25-50% of jobs
        LOW: appears in <25% of jobs
        """
        # Count occurrences (simplified - assumes 3 recent jobs for demo)
        occurrences = sum(1 for s in all_skills if self.normalize_skill(s) == self.normalize_skill(skill))
        percentage = (occurrences / len(all_skills) * 100) if all_skills else 0
        
        if percentage >= 50:
            return 'HIGH'
        elif percentage >= 25:
            return 'MEDIUM'
        else:
            return 'LOW'
    
    def generate_recommendations(self, missing_skills: List[Dict], advanced_skills: List[Dict]) -> List[Dict]:
        """
        Generate learning recommendations based on missing and advanced skills
        """
        recommendations = []
        
        # High priority missing skills
        high_priority = [s for s in missing_skills if s['priority'] == 'HIGH']
        for skill in high_priority[:3]:  # Top 3
            recommendations.append({
                'skill': skill['skill'],
                'reason': f"High demand skill - appears in 50%+ of jobs",
                'priority': 'HIGH',
                'resources': self._get_learning_resources(skill['skill'])
            })
        
        # Advanced skills to level up
        for skill in advanced_skills[:2]:  # Top 2
            recommendations.append({
                'skill': skill['job_requirement'],
                'reason': f"You have {skill['user_skill']} but job requires advanced version",
                'priority': 'MEDIUM',
                'resources': self._get_learning_resources(skill['job_requirement'])
            })
        
        return recommendations
    
    def _get_learning_resources(self, skill: str) -> List[Dict]:
        """Get recommended learning resources for a skill"""
        resources_db = {
            'python': [
                {'type': 'Course', 'name': 'Python for Data Analysis', 'platform': 'Udemy'},
                {'type': 'Tutorial', 'name': 'Real Python', 'platform': 'Real Python'},
                {'type': 'Book', 'name': 'Fluent Python', 'platform': 'O\'Reilly'}
            ],
            'docker': [
                {'type': 'Course', 'name': 'Docker Mastery', 'platform': 'Udemy'},
                {'type': 'Tutorial', 'name': 'Docker Official Docs', 'platform': 'Docker'},
                {'type': 'YouTube', 'name': 'Docker Crash Course', 'platform': 'freeCodeCamp'}
            ],
            'tableau': [
                {'type': 'Course', 'name': 'Tableau 2024 A-Z', 'platform': 'Udemy'},
                {'type': 'Tutorial', 'name': 'Tableau Public Gallery', 'platform': 'Tableau'},
                {'type': 'YouTube', 'name': 'Tableau Tutorial', 'platform': 'Maven Analytics'}
            ],
            'kubernetes': [
                {'type': 'Course', 'name': 'Kubernetes for Developers', 'platform': 'Udemy'},
                {'type': 'Tutorial', 'name': 'Kubernetes Official Docs', 'platform': 'Kubernetes'},
                {'type': 'YouTube', 'name': 'Kubernetes Tutorial', 'platform': 'freeCodeCamp'}
            ],
            'aws': [
                {'type': 'Course', 'name': 'AWS Solutions Architect', 'platform': 'Udemy'},
                {'type': 'Tutorial', 'name': 'AWS Official Training', 'platform': 'AWS'},
                {'type': 'YouTube', 'name': 'AWS Tutorials', 'platform': 'Adrian Cantrill'}
            ],
            'machine learning': [
                {'type': 'Course', 'name': 'Machine Learning A-Z', 'platform': 'Udemy'},
                {'type': 'Tutorial', 'name': 'Scikit-learn Documentation', 'platform': 'Scikit-learn'},
                {'type': 'YouTube', 'name': '3Blue1Brown ML Series', 'platform': 'YouTube'}
            ]
        }
        
        # Fuzzy match if exact skill not found
        skill_lower = skill.lower()
        for key in resources_db:
            if key in skill_lower or skill_lower in key:
                return resources_db[key]
        
        # Default resources
        return [
            {'type': 'Course', 'name': f'{skill} Mastery Course', 'platform': 'Udemy'},
            {'type': 'Tutorial', 'name': f'{skill} Official Documentation', 'platform': 'Official'},
            {'type': 'YouTube', 'name': f'{skill} Tutorial', 'platform': 'YouTube'}
        ]
    
    def format_gap_analysis_html(self, gap_analysis: Dict) -> str:
        """Format gap analysis untuk display di HTML"""
        
        html = f"""
        <div class="skills-gap-container">
            <div class="gap-header">
                <h3>📊 Skills Gap Analysis</h3>
                <div class="match-percentage">
                    <span class="percent-number">{gap_analysis['match_percentage']}%</span>
                    <span class="percent-label">Match Rate</span>
                </div>
            </div>
            
            <div class="gap-stats">
                <div class="stat-box matched">
                    <strong>{gap_analysis['matched_count']}</strong>
                    <span>Matched Skills</span>
                </div>
                <div class="stat-box missing">
                    <strong>{gap_analysis['missing_count']}</strong>
                    <span>Missing Skills</span>
                </div>
                <div class="stat-box total">
                    <strong>{gap_analysis['total_job_skills']}</strong>
                    <span>Total Required</span>
                </div>
            </div>
            
            <div class="gap-details">
                {"<div class='matched-section'><h4>✅ Your Matched Skills</h4>" if gap_analysis['matched_skills'] else ""}
                {self._format_matched_skills(gap_analysis['matched_skills'])}
                {"</div>" if gap_analysis['matched_skills'] else ""}
                
                {"<div class='missing-section'><h4>❌ Skills to Learn</h4>" if gap_analysis['missing_skills'] else ""}
                {self._format_missing_skills(gap_analysis['missing_skills'])}
                {"</div>" if gap_analysis['missing_skills'] else ""}
                
                {"<div class='advanced-section'><h4>⚡ Level Up These Skills</h4>" if gap_analysis['advanced_skills'] else ""}
                {self._format_advanced_skills(gap_analysis['advanced_skills'])}
                {"</div>" if gap_analysis['advanced_skills'] else ""}
                
                {"<div class='recommendations-section'><h4>🎓 Learning Recommendations</h4>" if gap_analysis['recommendations'] else ""}
                {self._format_recommendations(gap_analysis['recommendations'])}
                {"</div>" if gap_analysis['recommendations'] else ""}
            </div>
        </div>
        """
        
        return html
    
    def _format_matched_skills(self, matched_skills: List[Dict]) -> str:
        """Format matched skills list"""
        if not matched_skills:
            return "<p style='color: #888;'>No matched skills found</p>"
        
        html = '<ul class="skills-list matched-list">'
        for skill in matched_skills:
            html += f"""
            <li class="skill-item matched">
                <span class="skill-name">{skill['user_skill']}</span>
                <span class="skill-match">Matches: {skill['job_requirement']}</span>
                <span class="match-score">{skill['similarity']*100:.0f}%</span>
            </li>
            """
        html += '</ul>'
        return html
    
    def _format_missing_skills(self, missing_skills: List[Dict]) -> str:
        """Format missing skills list"""
        if not missing_skills:
            return "<p style='color: #888;'>All skills covered!</p>"
        
        html = '<ul class="skills-list missing-list">'
        for skill in missing_skills:
            priority_color = {'HIGH': '#ff6b6b', 'MEDIUM': '#ffa500', 'LOW': '#888888'}.get(skill['priority'], '#888')
            html += f"""
            <li class="skill-item missing">
                <span class="skill-name">{skill['skill']}</span>
                <span class="skill-category">{skill['category']}</span>
                <span class="priority-badge" style="background: {priority_color};">{skill['priority']}</span>
            </li>
            """
        html += '</ul>'
        return html
    
    def _format_advanced_skills(self, advanced_skills: List[Dict]) -> str:
        """Format advanced skills that need leveling up"""
        if not advanced_skills:
            return ""
        
        html = '<ul class="skills-list advanced-list">'
        for skill in advanced_skills:
            html += f"""
            <li class="skill-item advanced">
                <span class="current-skill">{skill['user_skill']}</span>
                <span class="arrow">→</span>
                <span class="target-skill">{skill['job_requirement']}</span>
            </li>
            """
        html += '</ul>'
        return html
    
    def _format_recommendations(self, recommendations: List[Dict]) -> str:
        """Format learning recommendations"""
        if not recommendations:
            return "<p style='color: #888;'>No recommendations at this time</p>"
        
        html = '<div class="recommendations-list">'
        for rec in recommendations:
            resources_html = ''.join([
                f"<span class='resource-tag'>{r['type']}: {r['platform']}</span>"
                for r in rec['resources'][:2]  # Show top 2 resources
            ])
            html += f"""
            <div class="recommendation-item">
                <div class="rec-header">
                    <strong>{rec['skill']}</strong>
                    <span class="rec-priority" style="color: {'#ff6b6b' if rec['priority']=='HIGH' else '#ffa500'};">{rec['priority']} PRIORITY</span>
                </div>
                <p class="rec-reason">{rec['reason']}</p>
                <div class="rec-resources">{resources_html}</div>
            </div>
            """
        html += '</div>'
        return html


# Test the module
if __name__ == '__main__':
    # Sample user profile
    user_skills = ['Python', 'SQL', 'Pandas', 'Power BI', 'Basic ML']
    
    # Sample job requirements (from a job scrape)
    job_requirements = ['Python', 'SQL', 'Tableau', 'Advanced ML', 'Docker', 'AWS']
    
    # Analyze
    analyzer = SkillsGapAnalyzer(user_skills)
    gap_analysis = analyzer.analyze_gap(job_requirements)
    
    print("\n=== SKILLS GAP ANALYSIS ===")
    print(f"Match Percentage: {gap_analysis['match_percentage']}%")
    print(f"Matched Skills: {gap_analysis['matched_count']}/{gap_analysis['total_job_skills']}")
    print(f"\nMatched Skills: {gap_analysis['matched_skills']}")
    print(f"\nMissing Skills: {gap_analysis['missing_skills']}")
    print(f"\nAdvanced Skills: {gap_analysis['advanced_skills']}")
    print(f"\nRecommendations: {len(gap_analysis['recommendations'])} recommendations")
    
    # Format for HTML
    html_output = analyzer.format_gap_analysis_html(gap_analysis)
    print("\n=== HTML OUTPUT ===")
    print(html_output[:500] + "...")
