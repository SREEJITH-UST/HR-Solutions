import openai
import re
import json
import requests
from typing import Dict, List, Any
from django.conf import settings

class ResumeAnalyzer:
    """AI-powered resume analysis service"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
        # Define skill frameworks for different roles
        self.skill_frameworks = {
            'Frontend Developer': {
                'critical': ['JavaScript', 'React', 'HTML', 'CSS', 'TypeScript'],
                'important': ['Vue.js', 'Angular', 'SASS/SCSS', 'Webpack', 'Git'],
                'nice_to_have': ['Next.js', 'GraphQL', 'Testing Libraries', 'Docker']
            },
            'Backend Developer': {
                'critical': ['Python', 'Java', 'Node.js', 'SQL', 'REST APIs'],
                'important': ['Django', 'Spring Boot', 'PostgreSQL', 'MongoDB', 'Git'],
                'nice_to_have': ['Docker', 'Kubernetes', 'Redis', 'Microservices']
            },
            'Full Stack Developer': {
                'critical': ['JavaScript', 'Python', 'React', 'Node.js', 'SQL'],
                'important': ['HTML', 'CSS', 'Git', 'REST APIs', 'MongoDB'],
                'nice_to_have': ['Docker', 'AWS', 'TypeScript', 'GraphQL']
            },
            'Data Scientist': {
                'critical': ['Python', 'SQL', 'Machine Learning', 'Statistics', 'Pandas'],
                'important': ['NumPy', 'Scikit-learn', 'Matplotlib', 'Jupyter', 'R'],
                'nice_to_have': ['TensorFlow', 'PyTorch', 'Apache Spark', 'Tableau']
            },
            'DevOps Engineer': {
                'critical': ['Docker', 'Kubernetes', 'AWS', 'Linux', 'Git'],
                'important': ['Terraform', 'Jenkins', 'Python', 'Bash', 'Ansible'],
                'nice_to_have': ['Prometheus', 'Grafana', 'Helm', 'Service Mesh']
            }
        }

    def analyze_skills(self, resume_text: str) -> Dict[str, Any]:
        """Analyze resume text to extract skills and experience"""
        
        prompt = f"""
        Analyze the following resume text and extract:
        1. All technical skills mentioned
        2. Programming languages and frameworks
        3. Years of experience for each skill (if mentioned)
        4. Overall experience level (entry/junior/mid/senior)
        5. Predicted job role based on skills
        6. Education background
        7. Certifications

        Resume text:
        {resume_text}

        Return the analysis in the following JSON format:
        {{
            "skills": [
                {{
                    "name": "skill_name",
                    "level": "beginner|intermediate|advanced",
                    "years": 0,
                    "confidence": 0.8,
                    "context": "where_mentioned"
                }}
            ],
            "predicted_role": "role_name",
            "experience_level": "entry|junior|mid|senior",
            "total_years_experience": 0,
            "education": ["degree_info"],
            "certifications": ["cert_info"]
        }}
        """

        try:
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert HR analyst specializing in resume analysis and skill assessment."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=2000
            )
            
            result = json.loads(response.choices[0].message.content)
            return result
            
        except Exception as e:
            # Fallback to rule-based analysis if OpenAI fails
            return self._fallback_skill_analysis(resume_text)

    def _fallback_skill_analysis(self, resume_text: str) -> Dict[str, Any]:
        """Fallback rule-based skill analysis"""
        
        # Common technical skills to look for
        technical_skills = [
            'Python', 'JavaScript', 'Java', 'C++', 'React', 'Angular', 'Vue.js',
            'Node.js', 'Django', 'Flask', 'Spring', 'HTML', 'CSS', 'SQL',
            'MongoDB', 'PostgreSQL', 'AWS', 'Docker', 'Kubernetes', 'Git',
            'Machine Learning', 'Data Science', 'TensorFlow', 'PyTorch'
        ]
        
        found_skills = []
        resume_lower = resume_text.lower()
        
        for skill in technical_skills:
            if skill.lower() in resume_lower:
                # Estimate experience level based on context
                level = self._estimate_skill_level(skill, resume_text)
                years = self._extract_years_experience(skill, resume_text)
                
                found_skills.append({
                    "name": skill,
                    "level": level,
                    "years": years,
                    "confidence": 0.7,
                    "context": "mentioned in resume"
                })
        
        # Predict role based on skills
        predicted_role = self._predict_role_from_skills([s["name"] for s in found_skills])
        
        return {
            "skills": found_skills,
            "predicted_role": predicted_role,
            "experience_level": "intermediate",
            "total_years_experience": 3,
            "education": [],
            "certifications": []
        }

    def _estimate_skill_level(self, skill: str, resume_text: str) -> str:
        """Estimate skill level based on context"""
        context_window = self._get_skill_context(skill, resume_text)
        
        if any(word in context_window.lower() for word in ['expert', 'senior', 'lead', 'architect']):
            return 'advanced'
        elif any(word in context_window.lower() for word in ['experienced', 'proficient', 'intermediate']):
            return 'intermediate'
        else:
            return 'beginner'

    def _extract_years_experience(self, skill: str, resume_text: str) -> int:
        """Extract years of experience for a skill"""
        context = self._get_skill_context(skill, resume_text)
        
        # Look for patterns like "3 years", "5+ years", etc.
        year_patterns = [
            r'(\d+)\+?\s*years?\s*(?:of\s*)?(?:experience\s*)?(?:with\s*)?(?:in\s*)?' + re.escape(skill.lower()),
            re.escape(skill.lower()) + r'.*?(\d+)\+?\s*years?',
            r'(\d+)\+?\s*years?.*?' + re.escape(skill.lower())
        ]
        
        for pattern in year_patterns:
            match = re.search(pattern, context.lower())
            if match:
                return int(match.group(1))
        
        return 1  # Default to 1 year if no specific mention

    def _get_skill_context(self, skill: str, resume_text: str, window_size: int = 100) -> str:
        """Get context around a skill mention"""
        skill_lower = skill.lower()
        resume_lower = resume_text.lower()
        
        index = resume_lower.find(skill_lower)
        if index == -1:
            return ""
        
        start = max(0, index - window_size)
        end = min(len(resume_text), index + len(skill) + window_size)
        
        return resume_text[start:end]

    def _predict_role_from_skills(self, skills: List[str]) -> str:
        """Predict job role based on skills"""
        skill_counts = {}
        
        for role, role_skills in self.skill_frameworks.items():
            count = 0
            for category in role_skills.values():
                for skill in category:
                    if skill in skills:
                        count += 1
            skill_counts[role] = count
        
        if not skill_counts:
            return "Software Developer"
        
        return max(skill_counts, key=skill_counts.get)

    def identify_skill_gaps(self, skill_analysis: Dict[str, Any], target_role: str = None) -> List[Dict[str, Any]]:
        """Identify skill gaps based on analysis and target role"""
        
        if not target_role:
            target_role = skill_analysis.get('predicted_role', 'Software Developer')
        
        current_skills = {skill['name'].lower(): skill for skill in skill_analysis['skills']}
        required_skills = self.skill_frameworks.get(target_role, self.skill_frameworks['Software Developer'])
        
        gaps = []
        
        for priority, skills in required_skills.items():
            for skill in skills:
                skill_lower = skill.lower()
                
                if skill_lower not in current_skills:
                    # Skill is completely missing
                    gaps.append({
                        'skill': skill,
                        'current_level': 'beginner',
                        'required_level': 'intermediate' if priority != 'critical' else 'advanced',
                        'priority': self._map_priority(priority),
                        'context': f'Required for {target_role}',
                        'gap_type': 'missing'
                    })
                else:
                    # Check if skill level is sufficient
                    current_skill = current_skills[skill_lower]
                    required_level = 'advanced' if priority == 'critical' else 'intermediate'
                    
                    level_hierarchy = {'beginner': 0, 'intermediate': 1, 'advanced': 2, 'expert': 3}
                    
                    current_level_score = level_hierarchy.get(current_skill['level'], 0)
                    required_level_score = level_hierarchy.get(required_level, 1)
                    
                    if current_level_score < required_level_score:
                        gaps.append({
                            'skill': skill,
                            'current_level': current_skill['level'],
                            'required_level': required_level,
                            'priority': self._map_priority(priority),
                            'context': f'Need to upgrade from {current_skill["level"]} to {required_level}',
                            'gap_type': 'upgrade'
                        })
        
        return gaps

    def _map_priority(self, framework_priority: str) -> str:
        """Map framework priority to database priority"""
        mapping = {
            'critical': 'critical',
            'important': 'important',
            'nice_to_have': 'nice_to_have'
        }
        return mapping.get(framework_priority, 'important')


class CourseRecommendationEngine:
    """AI-powered course recommendation service"""
    
    def __init__(self):
        self.openai_client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
        
    def find_courses_for_skill(self, skill_name: str, current_level: str, 
                             target_level: str, priority: str) -> List[Dict[str, Any]]:
        """Find relevant courses for a specific skill gap"""
        
        # Mock course data - In production, integrate with real APIs
        mock_courses = self._get_mock_courses_for_skill(skill_name, current_level, target_level)
        
        # Use AI to enhance recommendations
        enhanced_courses = self._enhance_recommendations_with_ai(
            skill_name, current_level, target_level, mock_courses
        )
        
        return enhanced_courses

    def _get_mock_courses_for_skill(self, skill_name: str, current_level: str, target_level: str) -> List[Dict[str, Any]]:
        """Get mock courses for demonstration - replace with real API integration"""
        
        course_templates = {
            'JavaScript': [
                {
                    'title': 'JavaScript: Understanding the Weird Parts',
                    'description': 'An advanced look at JavaScript, including how it works and how to avoid common pitfalls.',
                    'provider_id': 1,
                    'instructor': 'Anthony Alicea',
                    'url': 'https://www.udemy.com/course/understand-javascript/',
                    'thumbnail': 'https://img-c.udemycdn.com/course/240x135/364426_2991_6.jpg',
                    'duration': 11,
                    'level': 'intermediate',
                    'type': 'video',
                    'price': 89.99,
                    'is_free': False,
                    'rating': 4.6,
                    'students': 170000
                },
                {
                    'title': 'JavaScript Tutorial for Beginners',
                    'description': 'Learn JavaScript fundamentals from scratch',
                    'provider_id': 2,
                    'instructor': 'Programming with Mosh',
                    'url': 'https://www.youtube.com/watch?v=W6NZfCO5SIk',
                    'thumbnail': 'https://i.ytimg.com/vi/W6NZfCO5SIk/maxresdefault.jpg',
                    'duration': 6,
                    'level': 'beginner',
                    'type': 'video',
                    'price': 0,
                    'is_free': True,
                    'rating': 4.8,
                    'students': 2500000
                }
            ],
            'React': [
                {
                    'title': 'React - The Complete Guide',
                    'description': 'Dive in and learn React.js from scratch! Learn Reactjs, Hooks, Redux, React Routing, Animations, Next.js and way more!',
                    'provider_id': 1,
                    'instructor': 'Maximilian Schwarzmüller',
                    'url': 'https://www.udemy.com/course/react-the-complete-guide-incl-redux/',
                    'thumbnail': 'https://img-c.udemycdn.com/course/240x135/1362070_b9a1_2.jpg',
                    'duration': 48,
                    'level': 'intermediate',
                    'type': 'video',
                    'price': 94.99,
                    'is_free': False,
                    'rating': 4.6,
                    'students': 450000
                }
            ],
            'Python': [
                {
                    'title': '100 Days of Code: The Complete Python Pro Bootcamp',
                    'description': 'Master Python by building 100 projects in 100 days. Learn data science, automation, build websites, games and apps!',
                    'provider_id': 1,
                    'instructor': 'Dr. Angela Yu',
                    'url': 'https://www.udemy.com/course/100-days-of-code/',
                    'thumbnail': 'https://img-c.udemycdn.com/course/240x135/2776760_f176_10.jpg',
                    'duration': 60,
                    'level': 'beginner',
                    'type': 'video',
                    'price': 84.99,
                    'is_free': False,
                    'rating': 4.7,
                    'students': 680000
                }
            ],
            'Machine Learning': [
                {
                    'title': 'Machine Learning Course - CS229',
                    'description': 'Stanford CS229: Machine Learning Full Course taught by Andrew Ng',
                    'provider_id': 2,
                    'instructor': 'Andrew Ng',
                    'url': 'https://www.youtube.com/playlist?list=PLoROMvodv4rMiGQp3WXShtMGgzqpfVfbU',
                    'thumbnail': 'https://i.ytimg.com/vi/jGwO_UgTS7I/maxresdefault.jpg',
                    'duration': 25,
                    'level': 'advanced',
                    'type': 'video',
                    'price': 0,
                    'is_free': True,
                    'rating': 4.9,
                    'students': 1200000
                }
            ]
        }
        
        # Return courses for the skill or generic programming courses
        return course_templates.get(skill_name, course_templates.get('JavaScript', []))

    def _enhance_recommendations_with_ai(self, skill_name: str, current_level: str, 
                                       target_level: str, courses: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Use AI to enhance course recommendations with relevance scores"""
        
        try:
            prompt = f"""
            Rate the relevance of these courses for someone who wants to learn {skill_name} 
            from {current_level} level to {target_level} level.
            
            Courses: {json.dumps(courses, indent=2)}
            
            For each course, provide:
            1. Relevance score (0.0 to 1.0)
            2. Brief explanation of why it's suitable
            3. Learning order recommendation (1-5)
            
            Return as JSON array with enhanced course data.
            """
            
            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert educational content curator."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=1500
            )
            
            # Parse AI response and enhance courses
            enhanced = json.loads(response.choices[0].message.content)
            
            for i, course in enumerate(courses):
                if i < len(enhanced):
                    course['relevance_score'] = enhanced[i].get('relevance_score', 0.8)
                    course['ai_explanation'] = enhanced[i].get('explanation', '')
                    course['learning_order'] = enhanced[i].get('learning_order', i + 1)
                else:
                    course['relevance_score'] = 0.7
                    course['ai_explanation'] = f'Good course for learning {skill_name}'
                    course['learning_order'] = i + 1
            
            return sorted(courses, key=lambda x: x['relevance_score'], reverse=True)
            
        except Exception as e:
            # Fallback to default scoring
            for i, course in enumerate(courses):
                course['relevance_score'] = 0.8 - (i * 0.1)
                course['ai_explanation'] = f'Recommended course for {skill_name}'
                course['learning_order'] = i + 1
            
            return courses

    def create_learning_path(self, skill_gaps: List[Dict[str, Any]], 
                           target_role: str) -> Dict[str, Any]:
        """Create a structured learning path based on skill gaps"""
        
        # Group skills by priority
        critical_skills = [gap for gap in skill_gaps if gap['priority'] == 'critical']
        important_skills = [gap for gap in skill_gaps if gap['priority'] == 'important']
        nice_to_have_skills = [gap for gap in skill_gaps if gap['priority'] == 'nice_to_have']
        
        learning_path = {
            'name': f'{target_role} Learning Path',
            'description': f'Structured learning path to become a {target_role}',
            'estimated_weeks': 0,
            'phases': []
        }
        
        # Phase 1: Critical skills
        if critical_skills:
            phase1_courses = []
            for skill_gap in critical_skills:
                courses = self.find_courses_for_skill(
                    skill_gap['skill'], 
                    skill_gap['current_level'], 
                    skill_gap['required_level'],
                    skill_gap['priority']
                )
                if courses:
                    phase1_courses.append(courses[0])  # Best course for each skill
            
            learning_path['phases'].append({
                'name': 'Foundation Skills',
                'description': 'Critical skills needed for the role',
                'courses': phase1_courses,
                'estimated_weeks': len(phase1_courses) * 3
            })
        
        # Phase 2: Important skills
        if important_skills:
            phase2_courses = []
            for skill_gap in important_skills:
                courses = self.find_courses_for_skill(
                    skill_gap['skill'], 
                    skill_gap['current_level'], 
                    skill_gap['required_level'],
                    skill_gap['priority']
                )
                if courses:
                    phase2_courses.append(courses[0])
            
            learning_path['phases'].append({
                'name': 'Core Skills',
                'description': 'Important skills for professional growth',
                'courses': phase2_courses,
                'estimated_weeks': len(phase2_courses) * 2
            })
        
        # Calculate total estimated time
        learning_path['estimated_weeks'] = sum(phase['estimated_weeks'] for phase in learning_path['phases'])
        
        return learning_path