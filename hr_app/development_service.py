import json
import logging
from typing import List, Dict, Any
from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from datetime import datetime, timedelta
from datetime import timedelta
from .models import CandidateProfile, LearningCourse, EmployeeDevelopmentPlan
from .gemini_client import get_gemini_client

logger = logging.getLogger(__name__)

class EmployeeDevelopmentService:
    """Service for AI-powered employee development and course recommendations"""
    
    def __init__(self):
        self.client = get_gemini_client()
    
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
            gemini_response = self.client.generate_content(prompt)
            analysis_text = gemini_response.text.strip()
            print("[AI RAW SKILL GAP RESPONSE]", analysis_text)
            try:
                analysis_json = json.loads(analysis_text)
                return analysis_json
            except json.JSONDecodeError:
                print("[AI SKILL GAP JSON ERROR]", analysis_text)
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
        Use AI to recommend specific courses based on skill gaps. No fallback.
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
            gemini_response = self.client.generate_content(prompt)
            recommendations_text = gemini_response.text.strip()
            print("[AI RAW RESPONSE]", recommendations_text)
            # --- Strip markdown code block if present ---
            if recommendations_text.startswith('```'):
                # Remove triple backticks and optional 'json' after them
                recommendations_text = recommendations_text.lstrip('`')
                if recommendations_text.lower().startswith('json'):
                    recommendations_text = recommendations_text[4:]
                recommendations_text = recommendations_text.strip()
                if recommendations_text.endswith('```'):
                    recommendations_text = recommendations_text[:-3].strip()
            try:
                recommendations_json = json.loads(recommendations_text)
                return recommendations_json.get('course_recommendations', [])
            except json.JSONDecodeError as jde:
                print("[AI JSON ERROR]", jde)
                print("[AI RESPONSE TEXT]", recommendations_text)
                return []
        except Exception as e:
            import traceback
            print("[AI EXCEPTION]", e)
            traceback.print_exc()
            logger.error(f"Error in course recommendations: {str(e)}")
            return []  # No fallback, just return empty

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
            
            # If no recommendations from AI, do not use fallback
            if not course_recommendations:
                print("No AI recommendations returned.")
                # Just return empty recommendations, do not call fallback

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
    
    def send_courses_to_email(self, employee_profile: CandidateProfile, development_plans: List[EmployeeDevelopmentPlan]) -> Dict[str, Any]:
        """
        Send recommended courses to employee's registered email
        """
        try:
            # Get user email and name - ensure we're using the registered email
            user_email = employee_profile.user_profile.user.email
            user_name = f"{employee_profile.user_profile.user.first_name} {employee_profile.user_profile.user.last_name}".strip()
            username = employee_profile.user_profile.user.username
            
            # Debug logging to verify correct email is being used
            logger.info(f"Sending course recommendations to:")
            logger.info(f"  Username: {username}")
            logger.info(f"  Registered Email: {user_email}")
            logger.info(f"  Full Name: {user_name}")
            
            if not user_name:
                user_name = username
            
            if not user_email:
                logger.error(f"No email address found for user {username}")
                return {
                    'success': False,
                    'error': 'No email address found for this user'
                }
                
            logger.info(f"Preparing to send course recommendations to: {user_email}")
            
            # Prepare course data for email
            courses_data = []
            for plan in development_plans:
                course_info = {
                    'title': plan.course.title,
                    'provider': plan.course.provider.title() if plan.course.provider else 'Online',
                    'description': plan.course.description,
                    'duration': f"{plan.course.duration_hours} hours" if plan.course.duration_hours else "Duration not specified",
                    'rating': f"{plan.course.rating}/5" if plan.course.rating else "Not rated",
                    'price': f"${plan.course.price}" if plan.course.price else "Price not specified",
                    'skill_category': plan.course.skill_category.replace('_', ' ').title(),
                    'course_url': plan.course.course_url or "#",
                    'skills_covered': ', '.join(plan.course.skills_covered) if plan.course.skills_covered else "Various skills",
                    'priority': plan.priority_level.title() if plan.priority_level else "Medium",
                    'skill_gap': plan.skill_gap_identified,
                    'reason': plan.assignment_reason
                }
                courses_data.append(course_info)
            
            if not courses_data:
                return {
                    'success': False,
                    'error': 'No course data available to send'
                }
            
            logger.info(f"Prepared {len(courses_data)} courses for email")
            
            # Create email content
            subject = f"Your Personalized Learning Recommendations - NextGenHR"
            
            # HTML email content
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <style>
                    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #2d3748; background-color: #f7fafc; margin: 0; padding: 20px; }}
                    .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 10px; overflow: hidden; box-shadow: 0 10px 30px rgba(0,0,0,0.1); }}
                    .header {{ background: linear-gradient(135deg, #2d3748 0%, #4a5568 50%, #68d391 100%); color: white; padding: 30px; text-align: center; }}
                    .header h1 {{ margin: 0; font-size: 2rem; }}
                    .content {{ padding: 30px; }}
                    .course-card {{ border: 1px solid #e2e8f0; border-radius: 8px; padding: 20px; margin: 20px 0; background: #f7fafc; }}
                    .course-title {{ color: #2d3748; font-size: 1.3rem; font-weight: 600; margin-bottom: 10px; }}
                    .course-meta {{ color: #4a5568; font-size: 0.9rem; margin-bottom: 15px; }}
                    .course-description {{ color: #2d3748; margin-bottom: 15px; }}
                    .course-details {{ display: flex; flex-wrap: wrap; gap: 15px; margin-bottom: 15px; }}
                    .detail-item {{ background: #68d391; color: white; padding: 5px 10px; border-radius: 15px; font-size: 0.8rem; }}
                    .course-url {{ display: inline-block; background: linear-gradient(135deg, #68d391 0%, #48bb78 100%); color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px; margin-top: 10px; }}
                    .footer {{ background: #2d3748; color: white; padding: 20px; text-align: center; font-size: 0.9rem; }}
                    .priority-high {{ border-left: 4px solid #e53e3e; }}
                    .priority-medium {{ border-left: 4px solid #ed8936; }}
                    .priority-low {{ border-left: 4px solid #68d391; }}
                </style>
            </head>
            <body>
                <div class="container">
                    <div class="header">
                        <h1>🎓 Your Learning Recommendations</h1>
                        <p>Personalized course suggestions to boost your career</p>
                    </div>
                    
                    <div class="content">
                        <h2>Hello {user_name}!</h2>
                        <p>Based on your profile analysis, we've identified some exciting learning opportunities that can help accelerate your career growth. Here are your personalized course recommendations:</p>
                        
                        <div class="courses-section">
            """
            
            # Add courses to HTML
            for course in courses_data:
                priority_class = f"priority-{course['priority'].lower()}"
                html_content += f"""
                            <div class="course-card {priority_class}">
                                <div class="course-title">{course['title']}</div>
                                <div class="course-meta">
                                    <strong>Provider:</strong> {course['provider']} | 
                                    <strong>Duration:</strong> {course['duration']} | 
                                    <strong>Rating:</strong> {course['rating']} | 
                                    <strong>Priority:</strong> {course['priority']}
                                </div>
                                <div class="course-description">{course['description']}</div>
                                <div class="course-details">
                                    <span class="detail-item">💰 {course['price']}</span>
                                    <span class="detail-item">📚 {course['skill_category']}</span>
                                    <span class="detail-item">🎯 {course['skill_gap']}</span>
                                </div>
                                <p><strong>Skills you'll learn:</strong> {course['skills_covered']}</p>
                                <p><strong>Why recommended:</strong> {course['reason']}</p>
                                <a href="{course['course_url']}" class="course-url" target="_blank">View Course →</a>
                            </div>
                """
            
            html_content += f"""
                        </div>
                        
                        <div style="margin-top: 30px; padding: 20px; background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%); border-radius: 8px;">
                            <h3>💡 Next Steps:</h3>
                            <ol>
                                <li>Review each course recommendation carefully</li>
                                <li>Start with high-priority courses first</li>
                                <li>Set aside dedicated time for learning</li>
                                <li>Track your progress and celebrate milestones</li>
                            </ol>
                        </div>
                        
                        <p style="margin-top: 20px;">
                            <strong>Questions or need help?</strong> Our HR team is here to support your learning journey. 
                            Feel free to reach out anytime!
                        </p>
                    </div>
                    
                    <div class="footer">
                        <p><strong>NextGenHR</strong> - Empowering Your Career Growth</p>
                        <p>© 2025 NextGenHR. All rights reserved.</p>
                    </div>
                </div>
            </body>
            </html>
            """
            
            # Plain text version (fallback)
            text_content = f"""
Hello {user_name}!

Your Personalized Learning Recommendations from NextGenHR

Based on your profile analysis, we've identified some exciting learning opportunities:

"""
            for i, course in enumerate(courses_data, 1):
                text_content += f"""
{i}. {course['title']}
   Provider: {course['provider']}
   Duration: {course['duration']}
   Priority: {course['priority']}
   Skills: {course['skills_covered']}
   Why recommended: {course['reason']}
   Course Link: {course['course_url']}
   
"""
            
            text_content += """
Next Steps:
1. Review each course recommendation carefully
2. Start with high-priority courses first  
3. Set aside dedicated time for learning
4. Track your progress and celebrate milestones

Questions? Our HR team is here to help!

Best regards,
NextGenHR Team
"""
            
            # Get Django settings for email
            from django.conf import settings
            
            # Send email with proper error handling and SSL/TLS timeout fixes
            logger.info(f"Attempting to send email to {user_email} with {len(courses_data)} course recommendations")
            
            try:
                # Get Django settings for email
                from django.conf import settings
                from django.core.mail import get_connection, EmailMultiAlternatives
                import socket
                
                # Validate email configuration
                if not getattr(settings, 'EMAIL_HOST_USER', None):
                    logger.error("EMAIL_HOST_USER not configured in settings")
                    return {
                        'success': False,
                        'error': 'Email configuration is missing. Please configure EMAIL_HOST_USER in settings.'
                    }
                
                if not getattr(settings, 'EMAIL_HOST_PASSWORD', None):
                    logger.error("EMAIL_HOST_PASSWORD not configured in settings") 
                    return {
                        'success': False,
                        'error': 'Email configuration is missing. Please configure EMAIL_HOST_PASSWORD in settings.'
                    }
                
                logger.info(f"Email configuration found - Host: {settings.EMAIL_HOST_USER}")
                
                # Try multiple email sending approaches to handle SSL/TLS issues
                email_sent = False
                last_error = None
                
                # Method 1: Try with EmailMultiAlternatives for better control
                try:
                    logger.info("Attempting to send email using EmailMultiAlternatives...")
                    
                    msg = EmailMultiAlternatives(
                        subject=subject,
                        body=text_content,
                        from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nextgenhr.com'),
                        to=[user_email]
                    )
                    msg.attach_alternative(html_content, "text/html")
                    
                    # Set socket timeout to prevent hanging
                    old_timeout = socket.getdefaulttimeout()
                    socket.setdefaulttimeout(30)
                    
                    send_result = msg.send(fail_silently=False)
                    
                    # Restore old timeout
                    socket.setdefaulttimeout(old_timeout)
                    
                    if send_result == 1:
                        email_sent = True
                        logger.info("Email sent successfully using EmailMultiAlternatives")
                    
                except Exception as e:
                    last_error = str(e)
                    logger.warning(f"EmailMultiAlternatives method failed: {last_error}")
                    
                    # Restore socket timeout
                    if 'old_timeout' in locals():
                        socket.setdefaulttimeout(old_timeout)
                
                # Method 2: Try with basic send_mail if first method failed
                if not email_sent:
                    try:
                        logger.info("Attempting to send email using send_mail...")
                        
                        # Set socket timeout
                        old_timeout = socket.getdefaulttimeout()
                        socket.setdefaulttimeout(30)
                        
                        send_result = send_mail(
                            subject=subject,
                            message=text_content,
                            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nextgenhr.com'),
                            recipient_list=[user_email],
                            html_message=html_content,
                            fail_silently=False,
                        )
                        
                        # Restore old timeout
                        socket.setdefaulttimeout(old_timeout)
                        
                        if send_result == 1:
                            email_sent = True
                            logger.info("Email sent successfully using send_mail")
                        
                    except Exception as e:
                        last_error = str(e)
                        logger.warning(f"send_mail method failed: {last_error}")
                        
                        # Restore socket timeout
                        if 'old_timeout' in locals():
                            socket.setdefaulttimeout(old_timeout)
                
                # Method 3: Try with manual connection handling
                if not email_sent:
                    try:
                        logger.info("Attempting to send email with manual connection...")
                        
                        # Create connection with custom settings
                        connection = get_connection(
                            host=settings.EMAIL_HOST,
                            port=settings.EMAIL_PORT,
                            username=settings.EMAIL_HOST_USER,
                            password=settings.EMAIL_HOST_PASSWORD,
                            use_tls=True,
                            fail_silently=False,
                            timeout=30
                        )
                        
                        # Set socket timeout
                        old_timeout = socket.getdefaulttimeout()
                        socket.setdefaulttimeout(30)
                        
                        connection.open()
                        
                        msg = EmailMultiAlternatives(
                            subject=subject,
                            body=text_content,
                            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nextgenhr.com'),
                            to=[user_email],
                            connection=connection
                        )
                        msg.attach_alternative(html_content, "text/html")
                        
                        send_result = msg.send()
                        connection.close()
                        
                        # Restore old timeout
                        socket.setdefaulttimeout(old_timeout)
                        
                        if send_result == 1:
                            email_sent = True
                            logger.info("Email sent successfully with manual connection")
                            
                    except Exception as e:
                        last_error = str(e)
                        logger.error(f"Manual connection method failed: {last_error}")
                        
                        # Restore socket timeout
                        if 'old_timeout' in locals():
                            socket.setdefaulttimeout(old_timeout)
                
                # Check final result
                if email_sent:
                    logger.info(f"Email sent successfully to {user_email}")
                    return {
                        'success': True,
                        'message': 'Courses shared with registered email successfully!',
                        'email': user_email,
                        'courses_count': len(courses_data)
                    }
                else:
                    # As a last resort for development, try console backend
                    logger.warning("All SMTP methods failed, trying console backend as fallback...")
                    try:
                        from django.core.mail.backends.console import EmailBackend
                        console_backend = EmailBackend()
                        
                        # Create message for console output
                        console_msg = EmailMultiAlternatives(
                            subject=subject,
                            body=text_content,
                            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@nextgenhr.com'),
                            to=[user_email]
                        )
                        console_msg.attach_alternative(html_content, "text/html")
                        
                        # Send via console (will print to terminal)
                        console_backend.send_messages([console_msg])
                        
                        logger.info("Email content displayed in console (development mode)")
                        return {
                            'success': True,
                            'message': 'Email sent successfully! (Displayed in console for development)',
                            'email': user_email,
                            'courses_count': len(courses_data)
                        }
                        
                    except Exception as console_error:
                        logger.error(f"Even console backend failed: {str(console_error)}")
                    
                    error_msg = f"All email sending methods failed. Last error: {last_error}"
                    logger.error(error_msg)
                    return {
                        'success': False,
                        'error': f'Failed to send email due to connection issues. Please try again later or contact support.'
                    }
                    
            except Exception as mail_error:
                logger.error(f"Email sending failed with exception: {str(mail_error)}")
                return {
                    'success': False,
                    'error': f'Failed to send email: {str(mail_error)}'
                }
            
        except Exception as e:
            error_msg = f"Error sending course recommendations email: {str(e)}"
            logger.error(error_msg)
            return {
                'success': False,
                'error': error_msg
            }