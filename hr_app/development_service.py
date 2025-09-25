import openai
import json
import logging
import requests
from typing import List, Dict, Any
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from .models import CandidateProfile, LearningCourse, EmployeeDevelopmentPlan

logger = logging.getLogger(__name__)

class EmployeeDevelopmentService:
    """Service for AI-powered employee development and course recommendations"""
    
    def __init__(self):
        self.client = openai.OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def analyze_skill_gaps(self, employee_profile: CandidateProfile) -> Dict[str, Any]:
        """
        Analyze employee's current skills vs role requirements to identify gaps
        """
        try:
            # Prepare employee data for AI analysis
            employee_data = {
                "current_role": employee_profile.current_role or "Not specified",
                "experience_level": employee_profile.experience_level or "entry",
                "primary_skills": employee_profile.primary_skills or [],
                "secondary_skills": employee_profile.secondary_skills or [],
                "domain_experience": employee_profile.domain_experience or [],
                "strengths": employee_profile.strengths or [],
                "areas_for_improvement": employee_profile.areas_for_improvement or []
            }
            
            # AI prompt for skill gap analysis
            prompt = f"""
            Analyze the following employee profile and identify skill gaps for career growth:
            
            Employee Details:
            - Current Role: {employee_data['current_role']}
            - Experience Level: {employee_data['experience_level']}
            - Primary Skills: {', '.join(employee_data['primary_skills']) if employee_data['primary_skills'] else 'None listed'}
            - Secondary Skills: {', '.join(employee_data['secondary_skills']) if employee_data['secondary_skills'] else 'None listed'}
            - Domain Experience: {', '.join(employee_data['domain_experience']) if employee_data['domain_experience'] else 'None listed'}
            - Strengths: {', '.join(employee_data['strengths']) if employee_data['strengths'] else 'None listed'}
            - Areas for Improvement: {', '.join(employee_data['areas_for_improvement']) if employee_data['areas_for_improvement'] else 'None listed'}
            
            Based on current industry trends and role requirements, provide:
            1. Top 5 skill gaps that need immediate attention
            2. Recommended skill categories for each gap
            3. Priority level (critical, high, medium, low) for each gap
            4. Estimated current skill level vs target skill level
            5. Specific learning outcomes needed
            
            Return as JSON format:
            {{
                "skill_gaps": [
                    {{
                        "skill_name": "skill name",
                        "category": "category (frontend/backend/etc)",
                        "priority": "critical/high/medium/low",
                        "current_level": "novice/beginner/intermediate/advanced/expert",
                        "target_level": "novice/beginner/intermediate/advanced/expert",
                        "learning_outcomes": ["outcome1", "outcome2"],
                        "reason": "detailed explanation"
                    }}
                ],
                "overall_development_focus": "main area to focus on",
                "career_progression_path": "suggested next steps"
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert HR development consultant specializing in technical career growth and skill gap analysis."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=1500
            )
            
            analysis_text = response.choices[0].message.content.strip()
            
            # Parse JSON response
            try:
                analysis_json = json.loads(analysis_text)
                return analysis_json
            except json.JSONDecodeError:
                # Fallback parsing if JSON is malformed
                return self._fallback_skill_gap_analysis(employee_profile)
                
        except Exception as e:
            logger.error(f"Error in skill gap analysis: {str(e)}")
            return self._fallback_skill_gap_analysis(employee_profile)
    
    def _fallback_skill_gap_analysis(self, employee_profile: CandidateProfile) -> Dict[str, Any]:
        """Fallback skill gap analysis without AI"""
        current_skills = set(employee_profile.primary_skills or [])
        areas_for_improvement = employee_profile.areas_for_improvement or []
        
        # Common skill gaps based on role
        role_skill_requirements = {
            "frontend": ["React", "Vue.js", "TypeScript", "CSS3", "JavaScript ES6+"],
            "backend": ["Python", "Node.js", "SQL", "API Design", "Database Optimization"],
            "fullstack": ["React", "Node.js", "Python", "SQL", "DevOps", "Cloud Computing"],
            "mobile": ["React Native", "Flutter", "iOS Development", "Android Development"],
            "data": ["Python", "SQL", "Machine Learning", "Data Visualization", "Statistics"],
        }
        
        # Identify potential gaps
        skill_gaps = []
        for area in areas_for_improvement[:3]:  # Top 3 areas
            skill_gaps.append({
                "skill_name": area,
                "category": "technical",
                "priority": "high",
                "current_level": "beginner",
                "target_level": "intermediate",
                "learning_outcomes": [f"Master {area} fundamentals", f"Apply {area} in projects"],
                "reason": f"Identified as improvement area in profile analysis"
            })
        
        return {
            "skill_gaps": skill_gaps,
            "overall_development_focus": "Technical Skills Enhancement",
            "career_progression_path": "Focus on core technical competencies"
        }
    
    def recommend_courses(self, skill_gaps: List[Dict], employee_profile: CandidateProfile) -> List[Dict[str, Any]]:
        """
        Use AI to recommend specific courses based on skill gaps
        """
        try:
            skill_gap_summary = []
            for gap in skill_gaps:
                skill_gap_summary.append(f"- {gap['skill_name']} ({gap['priority']} priority)")
            
            prompt = f"""
            Based on the following skill gaps for an employee, recommend specific online courses:
            
            Employee Role: {employee_profile.current_role or 'Software Developer'}
            Experience Level: {employee_profile.experience_level or 'intermediate'}
            
            Skill Gaps Identified:
            {chr(10).join(skill_gap_summary)}
            
            Recommend 3-5 specific courses for each skill gap. Focus on:
            1. Udemy courses (preferred)
            2. Practical, hands-on learning
            3. Industry-recognized instructors
            4. Courses that build from current level to target level
            
            Return as JSON:
            {{
                "course_recommendations": [
                    {{
                        "title": "Complete Course Title",
                        "provider": "udemy",
                        "skill_category": "category",
                        "difficulty_level": "beginner/intermediate/advanced",
                        "description": "course description",
                        "skills_covered": ["skill1", "skill2"],
                        "estimated_duration_hours": 20,
                        "target_skill_gap": "matching skill gap name",
                        "course_url": "https://www.udemy.com/course/...",
                        "estimated_rating": 4.5,
                        "estimated_price": 49.99,
                        "learning_outcomes": ["outcome1", "outcome2"],
                        "why_recommended": "explanation"
                    }}
                ]
            }}
            """
            
            response = self.client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": "You are an expert learning and development specialist with deep knowledge of online courses and technical training programs."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=2000
            )
            
            recommendations_text = response.choices[0].message.content.strip()
            
            try:
                recommendations_json = json.loads(recommendations_text)
                return recommendations_json.get('course_recommendations', [])
            except json.JSONDecodeError:
                return self._fallback_course_recommendations(skill_gaps)
                
        except Exception as e:
            logger.error(f"Error in course recommendations: {str(e)}")
            return self._fallback_course_recommendations(skill_gaps)
    
    def _fallback_course_recommendations(self, skill_gaps: List[Dict]) -> List[Dict[str, Any]]:
        """Fallback course recommendations"""
        recommendations = []
        
        # Enhanced course templates with more options
        course_templates = {
            "React": {
                "title": "React - The Complete Guide (incl Hooks, React Router, Redux)",
                "provider": "udemy",
                "skill_category": "frontend",
                "difficulty_level": "intermediate",
                "description": "Master React.js fundamentals and advanced concepts",
                "skills_covered": ["React", "Hooks", "Redux", "React Router"],
                "estimated_duration_hours": 48,
                "course_url": "https://www.udemy.com/course/react-the-complete-guide/",
                "estimated_rating": 4.6,
                "estimated_price": 84.99
            },
            "Python": {
                "title": "Complete Python Bootcamp From Zero to Hero in Python 3",
                "provider": "udemy",
                "skill_category": "backend",
                "difficulty_level": "beginner",
                "description": "Learn Python programming from scratch",
                "skills_covered": ["Python", "OOP", "File Handling", "Web Development"],
                "estimated_duration_hours": 22,
                "course_url": "https://www.udemy.com/course/complete-python-bootcamp/",
                "estimated_rating": 4.6,
                "estimated_price": 84.99
            },
            "JavaScript": {
                "title": "The Complete JavaScript Course 2024: From Zero to Expert!",
                "provider": "udemy",
                "skill_category": "frontend",
                "difficulty_level": "intermediate",
                "description": "Modern JavaScript from the beginning! Learn JavaScript ES6+",
                "skills_covered": ["JavaScript", "ES6+", "DOM Manipulation", "Async Programming"],
                "estimated_duration_hours": 69,
                "course_url": "https://www.udemy.com/course/the-complete-javascript-course/",
                "estimated_rating": 4.7,
                "estimated_price": 89.99
            },
            "Communication": {
                "title": "Complete Communication Skills Master Class for Life",
                "provider": "udemy", 
                "skill_category": "soft_skills",
                "difficulty_level": "beginner",
                "description": "Public Speaking, Presentation & Leadership Communication Skills",
                "skills_covered": ["Public Speaking", "Presentation Skills", "Leadership", "Interpersonal Skills"],
                "estimated_duration_hours": 8,
                "course_url": "https://www.udemy.com/course/complete-communication-skills-master-class-for-life/",
                "estimated_rating": 4.5,
                "estimated_price": 49.99
            }
        }
        
        # Default courses if no specific skill gaps match
        default_courses = [
            {
                "title": "Full Stack Web Development Bootcamp",
                "provider": "udemy",
                "skill_category": "fullstack",
                "difficulty_level": "intermediate",
                "description": "Complete guide to full stack web development",
                "skills_covered": ["HTML", "CSS", "JavaScript", "React", "Node.js"],
                "estimated_duration_hours": 52,
                "course_url": "https://www.udemy.com/course/the-web-developer-bootcamp/",
                "estimated_rating": 4.7,
                "estimated_price": 94.99,
                "target_skill_gap": "Full Stack Development",
                "learning_outcomes": ["Build complete web applications", "Master modern web technologies"],
                "why_recommended": "Comprehensive skill development for career growth"
            },
            {
                "title": "Communication Skills for Professionals",
                "provider": "udemy",
                "skill_category": "soft_skills", 
                "difficulty_level": "beginner",
                "description": "Essential communication skills for workplace success",
                "skills_covered": ["Communication", "Presentation", "Team Collaboration"],
                "estimated_duration_hours": 6,
                "course_url": "https://www.udemy.com/course/communication-skills-complete-course/",
                "estimated_rating": 4.4,
                "estimated_price": 39.99,
                "target_skill_gap": "Communication Skills",
                "learning_outcomes": ["Improve workplace communication", "Build confidence in presentations"],
                "why_recommended": "Essential for career advancement and team collaboration"
            }
        ]
        
        # Try to match skill gaps with templates
        for gap in skill_gaps[:3]:  # Top 3 gaps
            skill_name = gap.get('skill_name', '')
            # Look for partial matches in skill name
            for template_key, template_course in course_templates.items():
                if template_key.lower() in skill_name.lower() or skill_name.lower() in template_key.lower():
                    course = template_course.copy()
                    course.update({
                        "target_skill_gap": skill_name,
                        "learning_outcomes": [f"Master {skill_name} fundamentals", f"Build projects with {skill_name}"],
                        "why_recommended": f"Addresses {skill_name} skill gap identified in analysis"
                    })
                    recommendations.append(course)
                    break
        
        # If no matches found or not enough recommendations, add default courses
        if len(recommendations) < 2:
            recommendations.extend(default_courses)
        
        # Ensure we have at least 2 recommendations
        return recommendations[:3]  # Return top 3
    
    def create_development_plan(self, employee_profile: CandidateProfile, manager_user=None) -> Dict[str, Any]:
        """
        Create a comprehensive development plan for an employee
        """
        try:
            # Step 1: Analyze skill gaps
            print(f"Step 1: Analyzing skill gaps for {employee_profile.user_profile.user.username}")
            skill_analysis = self.analyze_skill_gaps(employee_profile)
            skill_gaps = skill_analysis.get('skill_gaps', [])
            print(f"Found {len(skill_gaps)} skill gaps: {[gap.get('skill_name') for gap in skill_gaps]}")
            
            # Step 2: Get course recommendations
            print(f"Step 2: Getting course recommendations")
            course_recommendations = self.recommend_courses(skill_gaps, employee_profile)
            print(f"Found {len(course_recommendations)} course recommendations")
            
            # If no recommendations from AI, use fallback
            if not course_recommendations:
                print("No AI recommendations, using fallback...")
                course_recommendations = self._fallback_course_recommendations(skill_gaps)
                print(f"Fallback generated {len(course_recommendations)} recommendations")
            
            # Step 3: Create or update courses in database
            created_plans = []
            
            for course_rec in course_recommendations:
                print(f"Processing course: {course_rec.get('title', 'Unknown')}")
                
                # Create or get course
                try:
                    course, course_created = LearningCourse.objects.get_or_create(
                        title=course_rec.get('title', 'Unknown Course'),
                        provider=course_rec.get('provider', 'udemy'),
                        defaults={
                            'description': course_rec.get('description', ''),
                            'course_url': course_rec.get('course_url', ''),
                            'skill_category': course_rec.get('skill_category', 'technical'),
                            'difficulty_level': course_rec.get('difficulty_level', 'intermediate'),
                            'duration_hours': course_rec.get('estimated_duration_hours', 0),
                            'rating': course_rec.get('estimated_rating', 0.0),
                            'price': course_rec.get('estimated_price', 0.00),
                            'skills_covered': course_rec.get('skills_covered', [])
                        }
                    )
                    print(f"Course {'created' if course_created else 'found'}: {course.title}")
                except Exception as e:
                    print(f"Error creating course: {e}")
                    continue
                
                # Find matching skill gap
                target_gap = next((gap for gap in skill_gaps if gap['skill_name'].lower() in course_rec.get('target_skill_gap', '').lower()), {})
                
                # Create development plan
                try:
                    plan, plan_created = EmployeeDevelopmentPlan.objects.get_or_create(
                        employee_profile=employee_profile,
                        course=course,
                        defaults={
                            'assigned_by': manager_user,
                            'skill_gap_identified': course_rec.get('target_skill_gap', 'General Development'),
                            'current_skill_level': target_gap.get('current_level', 'beginner'),
                            'target_skill_level': target_gap.get('target_level', 'intermediate'),
                            'assignment_reason': course_rec.get('why_recommended', 'AI recommended for skill development'),
                            'priority_level': target_gap.get('priority', 'medium'),
                            'status': 'recommended',
                            'estimated_completion_date': timezone.now().date() + timedelta(days=course.duration_hours * 2)  # 2 days per hour estimate
                        }
                    )
                    
                    if plan_created:
                        created_plans.append(plan)
                        print(f"Development plan created for: {course.title}")
                    else:
                        print(f"Development plan already exists for: {course.title}")
                        
                except Exception as e:
                    print(f"Error creating development plan: {e}")
                    continue
            
            return {
                'success': True,
                'skill_analysis': skill_analysis,
                'created_plans': len(created_plans),
                'total_recommendations': len(course_recommendations),
                'development_focus': skill_analysis.get('overall_development_focus', 'Technical Skills'),
                'career_path': skill_analysis.get('career_progression_path', 'Skill Enhancement')
            }
            
        except Exception as e:
            logger.error(f"Error creating development plan: {str(e)}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_udemy_courses(self, search_query: str) -> List[Dict]:
        """
        Fetch real courses from Udemy API (if configured)
        """
        # Note: This would require Udemy API credentials
        # For now, return mock data based on search
        
        mock_courses = {
            "react": [
                {
                    "title": "React - The Complete Guide (incl Hooks, React Router, Redux)",
                    "url": "https://www.udemy.com/course/react-the-complete-guide/",
                    "price": 84.99,
                    "rating": 4.6,
                    "duration": "48.5 hours"
                }
            ],
            "python": [
                {
                    "title": "Complete Python Bootcamp From Zero to Hero in Python 3",
                    "url": "https://www.udemy.com/course/complete-python-bootcamp/",
                    "price": 84.99,
                    "rating": 4.6,
                    "duration": "22 hours"
                }
            ]
        }
        
        return mock_courses.get(search_query.lower(), [])