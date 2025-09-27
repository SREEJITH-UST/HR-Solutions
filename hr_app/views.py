from django.views.decorators.csrf import csrf_exempt, csrf_protect
# --- Feedback Action Assessment APIs ---
import random
from django.contrib.auth.decorators import login_required

@login_required
def start_action_assessment(request, id):
    """API to start an assessment: returns AI-generated questions for the action."""
    from .models import FeedbackAction
    from .gemini_client import get_gemini_client
    try:
        action = FeedbackAction.objects.get(id=id, employee=request.user)
        # Generate 3 questions using Gemini (or fallback)
        prompt = f"Generate 3 interview-style questions to assess understanding and completion of the following action: {action.title}. Action details: {action.description}"
        client = get_gemini_client()
        response = client.generate_content(prompt)
        text = response.text.strip()
        print('Gemini raw response:', repr(text))  # Log the raw Gemini output for debugging
        # Extract questions by finding quoted strings within numbered sections
        import re
        questions = []
        
        # Split text into sections by number pattern
        sections = re.split(r'\n\s*[0-9]+\.\s*', text)
        
        for section in sections[1:]:  # Skip first empty section
            # Look for quoted question (text between quotes)
            quote_match = re.search(r'"([^"]+)"', section)
            if quote_match:
                question = quote_match.group(1).strip()
                # Clean up any remaining markdown
                question = re.sub(r'\*\*|\*', '', question)
                questions.append(question)
            else:
                # Fallback: take first sentence that ends with ?
                sentences = section.split('.')
                for sentence in sentences:
                    if '?' in sentence:
                        question = sentence.split('?')[0] + '?'
                        question = re.sub(r'\*\*|\*|"', '', question).strip()
                        if question:
                            questions.append(question)
                            break
        
        questions = questions[:3] if questions else [f"Describe how you completed the action '{action.title}'."]
        return JsonResponse({'success': True, 'questions': questions})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from django.db import models
from .forms import LoginForm, SignupForm
from .models import (
    UserProfile, CandidateProfile, LearningCourse, EmployeeDevelopmentPlan,
    SkillUpCourse, CourseAssignment, VideoAssessment, AttentionTrackingData, CourseProgress,
    ManagerFeedback, FeedbackAction
)
from .services import ResumeProcessingService
from .development_service import EmployeeDevelopmentService
import json
import threading
from django.views.decorators.csrf import csrf_protect, csrf_exempt
from .gemini_client import get_gemini_client
import re

# Create your views here.

def send_notification_email(request):
    send_mail(
        subject='Test Email',
        message='This is a test email from HR app.',
        from_email= 'test@example.com',
        recipient_list=['recipient@example.com'],
        fail_silently=False,
    )
    return HttpResponse("Email sent successfully!")

def check_username_availability(request):
    """AJAX view to check username availability"""
    if request.method == 'GET':
        username = request.GET.get('username', '')
        is_available = not User.objects.filter(username=username).exists()
        return JsonResponse({'available': is_available})
    return JsonResponse({'available': False})

def process_resume_async(user_profile_id):
    """Process resume in background"""
    try:
        user_profile = UserProfile.objects.get(id=user_profile_id)
        service = ResumeProcessingService()
        service.process_resume(user_profile)
    except Exception as e:
        print(f"Resume processing failed: {str(e)}")

def check_processing_status(request):
    """AJAX endpoint to check resume processing status"""
    if request.user.is_authenticated:
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            candidate_profile = CandidateProfile.objects.get(user_profile=user_profile)
            
            return JsonResponse({
                'status': candidate_profile.processing_status,
                'processed': candidate_profile.resume_processed,
                'error': candidate_profile.processing_error
            })
        except (UserProfile.DoesNotExist, CandidateProfile.DoesNotExist):
            return JsonResponse({
                'status': 'not_found',
                'processed': False,
                'error': 'Profile not found'
            })
    
    return JsonResponse({'status': 'unauthorized', 'processed': False})

def login_view(request):
    login_form = LoginForm()
    signup_form = SignupForm()
    login_error = signup_error = ''

    if request.method == 'POST':
        if 'login' in request.POST:
            login_form = LoginForm(request.POST)
            if login_form.is_valid():
                user = authenticate(
                    username=login_form.cleaned_data['username'],
                    password=login_form.cleaned_data['password']
                )
                if user:
                    login(request, user)
                    return redirect('dashboard')
                else:
                    login_error = "Invalid username or password."
        elif 'signup' in request.POST:
            signup_form = SignupForm(request.POST, request.FILES)
            if signup_form.is_valid():
                # Create user
                user = User.objects.create_user(
                    username=signup_form.cleaned_data['username'],
                    email=signup_form.cleaned_data['email'],
                    password=signup_form.cleaned_data['password'],
                    first_name=signup_form.cleaned_data['first_name'],
                    last_name=signup_form.cleaned_data['last_name']
                )
                
                # Create user profile
                user_profile = UserProfile.objects.create(
                    user=user,
                    country_code=signup_form.cleaned_data['country_code'],
                    mobile_number=signup_form.cleaned_data['mobile_number'],
                    resume=signup_form.cleaned_data['resume'],
                    user_type='candidate'  # Default to candidate
                )
                
                # Start resume processing in background
                thread = threading.Thread(
                    target=process_resume_async, 
                    args=(user_profile.id,)
                )
                thread.start()
                
                # Login the user
                login(request, user)
                return redirect('processing')
            else:
                signup_error = "Signup failed. Please check the details."

    return render(request, 'accounts/login.html', {
        'login_form': login_form,
        'signup_form': signup_form,
        'login_error': login_error,
        'signup_error': signup_error,
    })

def signup_view(request):
    signup_form = SignupForm()
    signup_error = ''
    if request.method == 'POST':
        signup_form = SignupForm(request.POST, request.FILES)
        if signup_form.is_valid():
            # Create user
            user = User.objects.create_user(
                username=signup_form.cleaned_data['username'],
                email=signup_form.cleaned_data['email'],
                password=signup_form.cleaned_data['password'],
                first_name=signup_form.cleaned_data['first_name'],
                last_name=signup_form.cleaned_data['last_name']
            )
            
            # Create user profile
            user_profile = UserProfile.objects.create(
                user=user,
                country_code=signup_form.cleaned_data['country_code'],
                mobile_number=signup_form.cleaned_data['mobile_number'],
                resume=signup_form.cleaned_data['resume'],
                user_type='candidate'  # Default to candidate
            )
            
            # Start resume processing in background
            thread = threading.Thread(
                target=process_resume_async, 
                args=(user_profile.id,)
            )
            thread.start()
            
            # Login the user
            login(request, user)
            return redirect('processing')
        else:
            signup_error = "Signup failed. Please check the details."
    return render(request, 'accounts/signup.html', {
        'signup_form': signup_form,
        'signup_error': signup_error,
    })

@login_required
def processing_view(request):
    """Show processing status page"""
    return render(request, 'accounts/processing.html', {
        'user': request.user
    })

@login_required
def dashboard_view(request):
    """Main dashboard that routes based on user type"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        
        if user_profile.user_type == 'admin':
            return redirect('admin_dashboard')
        elif user_profile.user_type == 'manager':
            return redirect('manager_dashboard')
        else:  # candidate
            return redirect('candidate_dashboard')
            
    except UserProfile.DoesNotExist:
        # Handle users without profile - redirect to signup to complete profile
        return redirect('signup')

@login_required
def candidate_dashboard(request):
    """Employee dashboard with development plans"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        candidate_profile = CandidateProfile.objects.get(user_profile=user_profile)
        
        # Calculate score degree for CSS (percentage to degrees)
        score_degrees = candidate_profile.resume_score * 3.6
        
        # Get development plans for this employee
        development_plans = EmployeeDevelopmentPlan.objects.filter(
            employee_profile=candidate_profile
        ).select_related('course').order_by('-created_at')
        
        context = {
            'user_profile': user_profile,
            'candidate_profile': candidate_profile,
            'resume_processed': candidate_profile.resume_processed,
            'score_degrees': score_degrees,
            'development_plans': development_plans,
        }
        
        return render(request, 'dashboard/candidate.html', context)
        
    except (UserProfile.DoesNotExist, CandidateProfile.DoesNotExist):
        return render(request, 'dashboard/candidate.html', {
            'user_profile': None,
            'candidate_profile': None,
            'resume_processed': False,
            'score_degrees': 0,
            'development_plans': [],
        })

@login_required
def manager_dashboard(request):
    """Manager dashboard"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    # Get all candidates for manager to review
    candidates = CandidateProfile.objects.filter(resume_processed=True).select_related('user_profile__user')
    
    # Get statistics
    total_candidates = CandidateProfile.objects.count()
    new_applications = CandidateProfile.objects.filter(
        created_at__gte=timezone.now() - timezone.timedelta(days=7)
    ).count()
    pending_reviews = CandidateProfile.objects.filter(resume_processed=False).count()
    
    context = {
        'user_profile': user_profile,
        'candidates': candidates,
        'total_candidates': total_candidates,
        'new_applications': new_applications,
        'pending_reviews': pending_reviews,
        'interviews_scheduled': 0,  # Placeholder for future feature
    }
    
    return render(request, 'dashboard/manager.html', context)@login_required
def admin_dashboard(request):
    """Admin dashboard"""
    user_profile = UserProfile.objects.get(user=request.user)
    
    # Get all user profiles for admin view
    all_users = UserProfile.objects.select_related('user').all()
    
    # Get statistics
    total_users = User.objects.count()
    total_candidates = CandidateProfile.objects.count()
    total_managers = UserProfile.objects.filter(user_type='manager').count()
    resumes_processed = CandidateProfile.objects.filter(resume_processed=True).count()
    
    context = {
        'user_profile': user_profile,
        'all_users': all_users,
        'total_users': total_users,
        'total_candidates': total_candidates,
        'total_managers': total_managers,
        'resumes_processed': resumes_processed,
    }
    
    return render(request, 'dashboard/admin.html', context)

def forgot_password_view(request):
    error = ''
    success = ''
    if request.method == 'POST':
        email = request.POST.get('email')
        if not email:
            error = 'Please enter your email address.'
        else:
            try:
                user = User.objects.get(email=email)
                # Here you would send a real reset link. For demo, just show a message.
                success = 'A password reset link has been sent to your email.'
            except User.DoesNotExist:
                error = 'No user found with that email address.'
    return render(request, 'accounts/forgot_password.html', {'error': error, 'success': success})

@login_required
def reprocess_resume(request):
    """Manually reprocess a user's resume for testing"""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
        if hasattr(user_profile, 'resume') and user_profile.resume:
            # Reprocess the resume
            processing_service = ResumeProcessingService()
            
            # Run processing in background thread
            def process_in_background():
                try:
                    processing_service.process_resume(user_profile)
                except Exception as e:
                    print(f"Background processing error: {str(e)}")
            
            processing_thread = threading.Thread(target=process_in_background)
            processing_thread.start()
            
            return JsonResponse({'status': 'success', 'message': 'Resume reprocessing started'})
        else:
            return JsonResponse({'status': 'error', 'message': 'No resume found'})
    except Exception as e:
        return JsonResponse({'status': 'error', 'message': str(e)})

@login_required
def upload_resume(request):
    """Handle new resume upload"""
    if request.method == 'POST':
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            
            if 'resume' not in request.FILES:
                return JsonResponse({'status': 'error', 'message': 'No file uploaded'})
            
            resume_file = request.FILES['resume']
            
            # Validate file type
            allowed_extensions = ['.pdf', '.docx', '.doc']
            file_extension = resume_file.name.lower().split('.')[-1]
            if f'.{file_extension}' not in allowed_extensions:
                return JsonResponse({'status': 'error', 'message': 'Invalid file type. Please upload PDF or DOCX files only.'})
            
            # Validate file size (10MB limit)
            if resume_file.size > 10 * 1024 * 1024:
                return JsonResponse({'status': 'error', 'message': 'File too large. Please upload files smaller than 10MB.'})
            
            # Delete old resume file if exists
            if user_profile.resume:
                try:
                    user_profile.resume.delete()
                except:
                    pass
            
            # Save new resume
            user_profile.resume = resume_file
            user_profile.save()
            
            # Reset candidate profile processing status
            try:
                candidate_profile = CandidateProfile.objects.get(user_profile=user_profile)
                candidate_profile.resume_processed = False
                candidate_profile.processing_status = 'pending'
                candidate_profile.processing_error = ''
                candidate_profile.save()
            except CandidateProfile.DoesNotExist:
                pass
            
            # Start processing in background
            processing_service = ResumeProcessingService()
            
            def process_in_background():
                try:
                    processing_service.process_resume(user_profile)
                except Exception as e:
                    print(f"Background processing error: {str(e)}")
            
            processing_thread = threading.Thread(target=process_in_background)
            processing_thread.start()
            
            return JsonResponse({
                'status': 'success', 
                'message': 'Resume uploaded successfully. Processing started.',
                'redirect_url': '/processing/'
            })
            
        except UserProfile.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User profile not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Upload failed: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def generate_development_plan(request):
    """Generate AI-powered development plan for employee"""
    if request.method == 'POST':
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            candidate_profile, created = CandidateProfile.objects.get_or_create(
                user_profile=user_profile
            )
            
            # Initialize development service
            dev_service = EmployeeDevelopmentService()
            
            # Generate plan synchronously for testing
            print(f"Starting plan generation for user: {request.user.username}")
            result = dev_service.create_development_plan(
                candidate_profile, 
                manager_user=request.user if user_profile.user_type == 'manager' else None
            )
            print(f"Development plan result: {result}")
            
            if result.get('success'):
                return JsonResponse({
                    'status': 'success',
                    'message': f'Successfully generated {result.get("created_plans", 0)} course recommendations! Refresh the page to see them.'
                })
            else:
                return JsonResponse({
                    'status': 'error', 
                    'message': f'Plan generation failed: {result.get("error", "Unknown error")}'
                })
            
        except UserProfile.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'User profile not found'})
        except Exception as e:
            print(f"Exception in generate_development_plan: {str(e)}")
            import traceback
            traceback.print_exc()
            return JsonResponse({'status': 'error', 'message': f'Plan generation failed: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def enroll_course(request, plan_id):
    """Enroll employee in a recommended course"""
    if request.method == 'POST':
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            candidate_profile = CandidateProfile.objects.get(user_profile=user_profile)
            
            # Get the development plan
            plan = EmployeeDevelopmentPlan.objects.get(
                id=plan_id, 
                employee_profile=candidate_profile
            )
            
            # Update status to enrolled/in_progress
            plan.status = 'in_progress'
            plan.save()
            
            return JsonResponse({
                'status': 'success',
                'message': f'Successfully enrolled in {plan.course.title}',
                'course_url': plan.course.course_url,
                'redirect': True
            })
            
        except (UserProfile.DoesNotExist, CandidateProfile.DoesNotExist, EmployeeDevelopmentPlan.DoesNotExist):
            return JsonResponse({'status': 'error', 'message': 'Plan not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Enrollment failed: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def update_course_progress(request, plan_id):
    """Update course progress"""
    if request.method == 'POST':
        try:
            user_profile = UserProfile.objects.get(user=request.user)
            candidate_profile = CandidateProfile.objects.get(user_profile=user_profile)
            
            plan = EmployeeDevelopmentPlan.objects.get(
                id=plan_id, 
                employee_profile=candidate_profile
            )
            
            progress = int(request.POST.get('progress', 0))
            plan.progress_percentage = min(progress, 100)
            
            if progress >= 100:
                plan.status = 'completed'
                plan.actual_completion_date = timezone.now().date()
            
            plan.save()
            
            return JsonResponse({
                'status': 'success',
                'message': 'Progress updated successfully'
            })
            
        except (UserProfile.DoesNotExist, CandidateProfile.DoesNotExist, EmployeeDevelopmentPlan.DoesNotExist):
            return JsonResponse({'status': 'error', 'message': 'Plan not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': f'Update failed: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

def home(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    return redirect('login')

@csrf_protect
def custom_logout(request):
    """Logs out user and shows feedback form before login page."""
    if request.method == 'POST':
        feedback = request.POST.get('feedback', '').strip()
        # Optionally, save feedback to database or email it to admin here
        return render(request, 'accounts/logout_feedback.html', {'feedback_submitted': True})
    else:
        logout(request)
        return render(request, 'accounts/logout_feedback.html', {'feedback_submitted': False})

@login_required
def professional_development_view(request):
    user_profile = UserProfile.objects.get(user=request.user)
    candidate_profile = CandidateProfile.objects.get(user_profile=user_profile)
    context = {
        'user_profile': user_profile,
        'candidate_profile': candidate_profile,
    }
    return render(request, 'dashboard/professional_development.html', context)

@login_required
def feedback_view(request):
    """Display manager feedback and AI-powered recommendations"""
    from .models import ManagerFeedback, FeedbackAction, FeedbackCourseRecommendation, CandidateProfile
    from collections import Counter
    from django.db.models import Avg
    from .development_service import EmployeeDevelopmentService
    from django.db import transaction

    # Get all feedback for the current user
    feedbacks = ManagerFeedback.objects.filter(employee=request.user)

    if feedbacks.exists():
        # Calculate average rating
        average_rating = feedbacks.aggregate(Avg('rating'))['rating__avg'] or 0

        # Get common areas of concern
        all_areas = []
        for feedback in feedbacks:
            if feedback.areas_of_concern:
                all_areas.extend(feedback.areas_of_concern)
        common_areas = dict(Counter(all_areas).most_common(5))

        # Get recommended actions
        recommended_actions = list(FeedbackAction.objects.filter(employee=request.user).order_by('priority', '-created_at'))

        # Get course recommendations
        recommended_courses = list(FeedbackCourseRecommendation.objects.filter(employee=request.user).select_related('course'))

        # If no actions or courses exist, use Gemini to generate them
        if not recommended_actions or not recommended_courses:
            try:
                # Get candidate profile for AI context
                candidate_profile = CandidateProfile.objects.get(user_profile__user=request.user)
                dev_service = EmployeeDevelopmentService()

                # Use areas of concern and feedback messages as input for AI
                feedback_text = '\n'.join([f.message for f in feedbacks])
                areas = list(set(all_areas))
                # For skill gap analysis, add areas as "areas_for_improvement"
                candidate_profile.areas_for_improvement = areas
                candidate_profile.save(update_fields=["areas_for_improvement"])

                # Analyze skill gaps
                skill_gap_result = dev_service.analyze_skill_gaps(candidate_profile)
                skill_gaps = skill_gap_result.get("skill_gaps", [])

                # Generate actions from skill gaps if none exist
                if not recommended_actions and skill_gaps:
                    with transaction.atomic():
                        for gap in skill_gaps:
                            FeedbackAction.objects.create(
                                feedback=feedbacks.first(),  # Link to latest feedback
                                employee=request.user,
                                title=f"Improve {gap['skill_name']}",
                                description=gap.get('reason', 'Focus on this area for improvement.'),
                                priority=gap.get('priority', 'medium'),
                                estimated_time_hours=8
                            )
                    recommended_actions = list(FeedbackAction.objects.filter(employee=request.user).order_by('priority', '-created_at'))

                # Generate course recommendations from skill gaps if none exist
                if not recommended_courses and skill_gaps:
                    course_recs = dev_service.recommend_courses(skill_gaps, candidate_profile)
                    with transaction.atomic():
                        for course in course_recs:
                            # Try to find or create a LearningCourse
                            from .models import LearningCourse
                            lc, _ = LearningCourse.objects.get_or_create(
                                title=course['title'],
                                defaults={
                                    'description': course.get('description', ''),
                                    'provider': course.get('provider', 'udemy'),
                                    'course_url': course.get('course_url', ''),
                                    'skill_category': course.get('skill_category', 'soft_skills'),
                                    'difficulty_level': course.get('difficulty_level', 'beginner'),
                                    'duration_hours': int(course.get('estimated_duration_hours', 8)),
                                    'rating': float(course.get('estimated_rating', 4.0)),
                                    'price': float(course.get('estimated_price', 0)),
                                    'skills_covered': course.get('skills_covered', []),
                                }
                            )
                            FeedbackCourseRecommendation.objects.get_or_create(
                                feedback=feedbacks.first(),
                                employee=request.user,
                                course=lc,
                                feedback_area_addressed=course.get('target_skill_gap', 'General')
                            )
                    recommended_courses = list(FeedbackCourseRecommendation.objects.filter(employee=request.user).select_related('course'))
            except Exception as e:
                print("[AI FEEDBACK RECOMMENDATION ERROR]", str(e))

        context = {
            'feedbacks': feedbacks,
            'average_rating': average_rating,
            'common_areas': common_areas,
            'recommended_actions': recommended_actions,
            'recommended_courses': recommended_courses,
        }
    else:
        context = {
            'feedbacks': None,
            'average_rating': 0,
            'common_areas': {},
            'recommended_actions': [],
            'recommended_courses': [],
        }

    return render(request, 'dashboard/feedback.html', context)

@login_required
def mark_action_complete(request, action_id):
    """Mark a feedback action as completed"""
    if request.method == 'POST':
        try:
            from .models import FeedbackAction
            action = FeedbackAction.objects.get(id=action_id, employee=request.user)
            action.is_completed = True
            action.completed_at = timezone.now()
            action.save()
            
            return JsonResponse({'status': 'success', 'message': 'Action marked as completed'})
        except FeedbackAction.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Action not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

@login_required
def enroll_feedback_course(request, course_id):
    """Enroll in a course recommended based on feedback"""
    if request.method == 'POST':
        try:
            from .models import FeedbackCourseRecommendation
            course_rec = FeedbackCourseRecommendation.objects.get(
                id=course_id, 
                employee=request.user
            )
            course_rec.is_enrolled = True
            course_rec.enrolled_at = timezone.now()
            course_rec.save()
            
            return JsonResponse({'status': 'success', 'message': 'Successfully enrolled in course'})
        except FeedbackCourseRecommendation.DoesNotExist:
            return JsonResponse({'status': 'error', 'message': 'Course recommendation not found'})
        except Exception as e:
            return JsonResponse({'status': 'error', 'message': str(e)})

# ================== SKILL-UP MODULE VIEWS ==================

@login_required
def skillup_dashboard(request):
    """Skill-Up Module dashboard view"""
    try:
        # Get user profile and candidate profile
        from .models import UserProfile, CandidateProfile, EmployeeDevelopmentPlan
        from django.db import models
        
        user_profile = UserProfile.objects.get(user=request.user)
        candidate_profile = CandidateProfile.objects.get(user_profile=user_profile)
        
        # Get development plans (course assignments) for this employee
        assignments = EmployeeDevelopmentPlan.objects.filter(
            employee_profile=candidate_profile
        ).select_related('course', 'assigned_by').order_by('-created_at')
        
        # Calculate statistics
        total_assignments = assignments.count()
        completed_count = assignments.filter(status='completed').count()
        in_progress_count = assignments.filter(status='in_progress').count()
        
        # Calculate average score (using progress_percentage as score)
        if total_assignments > 0:
            avg_score = assignments.aggregate(avg_score=models.Avg('progress_percentage'))['avg_score'] or 0
        else:
            avg_score = 0
        
        context = {
            'assignments': assignments,
            'total_assignments': total_assignments,
            'completed_count': completed_count,
            'in_progress_count': in_progress_count,
            'avg_score': avg_score,
        }
        return render(request, 'skillup/dashboard.html', context)
        
    except (UserProfile.DoesNotExist, CandidateProfile.DoesNotExist):
        # If user doesn't have profiles, show empty dashboard
        return render(request, 'skillup/dashboard.html', {
            'assignments': [],
            'total_assignments': 0,
            'completed_count': 0,
            'in_progress_count': 0,
            'avg_score': 0,
        })
    except Exception as e:
        print(f"Skill-Up dashboard error: {str(e)}")
        return render(request, 'skillup/dashboard.html', {
            'assignments': [],
            'total_assignments': 0,
            'completed_count': 0,
            'in_progress_count': 0,
            'avg_score': 0,
        })

@login_required
def start_video_assessment(request, assignment_id):
    """Start video assessment for a course assignment"""
    try:
        assignment = CourseAssignment.objects.get(
            id=assignment_id,
            employee=request.user
        )
        
        if not assignment.course.has_video_assessment:
            return JsonResponse({'success': False, 'message': 'This course does not have video assessment'})
        
        # Create or get existing video assessment
        video_assessment, created = VideoAssessment.objects.get_or_create(
            assignment=assignment,
            defaults={
                'status': 'scheduled',
                'started_at': timezone.now()
            }
        )
        
        if request.method == 'GET':
            # Return assessment page
            context = {
                'assignment': assignment,
                'assessment': video_assessment
            }
            return render(request, 'skillup/video_assessment.html', context)
            
        elif request.method == 'POST':
            # Start the assessment
            video_assessment.status = 'in_progress'
            video_assessment.started_at = timezone.now()
            video_assessment.save()
            
            # Update assignment status
            assignment.status = 'in_progress'
            assignment.save()
            
            return JsonResponse({
                'success': True,
                'assessment_id': video_assessment.id,
                'message': 'Assessment started successfully'
            })
            
    except CourseAssignment.DoesNotExist:
        return JsonResponse({'success': False, 'message': 'Assignment not found'})
    except Exception as e:
        print(f"Video assessment start error: {str(e)}")
        return JsonResponse({'success': False, 'message': 'Failed to start assessment'})

@csrf_protect
def analyze_video_frame(request):
    """API endpoint to analyze video frames during assessment"""
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            assessment_id = data.get('assessment_id')
            frame_data = data.get('frame_data')  # Base64 encoded image
            timestamp = data.get('timestamp')
            
            # Get the video assessment
            assessment = VideoAssessment.objects.get(id=assessment_id)
            
            # Simple AI analysis simulation
            # In production, this would use real AI models
            import random
            
            analysis_result = {
                'attention_score': random.uniform(0.7, 1.0),
                'engagement_level': random.choice(['high', 'medium', 'low']),
                'facial_expression': random.choice(['focused', 'confused', 'distracted', 'engaged']),
                'looking_at_screen': random.choice([True, False]),
                'confidence': random.uniform(0.8, 0.95)
            }
            
            # Save attention tracking data
            AttentionTrackingData.objects.create(
                video_assessment=assessment,
                timestamp=timestamp,
                attention_score=analysis_result['attention_score'],
                engagement_level=analysis_result['engagement_level'],
                facial_expression=analysis_result['facial_expression'],
                looking_at_screen=analysis_result['looking_at_screen'],
                raw_data=json.dumps(analysis_result)
            )
            
            return JsonResponse({
                'success': True,
                'analysis': analysis_result
            })
            
        except Exception as e:
            print(f"Frame analysis error: {str(e)}")
            return JsonResponse({
                'success': False,
                'message': 'Analysis failed'
            })
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def complete_video_assessment(request, assessment_id):
    """Complete video assessment and calculate scores"""
    if request.method == 'POST':
        try:
            assessment = VideoAssessment.objects.get(
                id=assessment_id,
                assignment__employee=request.user
            )
            
            # Calculate scores based on attention tracking data
            tracking_data = AttentionTrackingData.objects.filter(
                video_assessment=assessment
            )
            
            if tracking_data.exists():
                # Calculate average attention score
                avg_attention = tracking_data.aggregate(
                    avg_score=models.Avg('attention_score')
                )['avg_score'] or 0
                
                # Calculate engagement metrics
                high_engagement_count = tracking_data.filter(engagement_level='high').count()
                total_data_points = tracking_data.count()
                engagement_ratio = high_engagement_count / max(total_data_points, 1)
                
                # Calculate looking at screen percentage
                looking_count = tracking_data.filter(looking_at_screen=True).count()
                looking_ratio = looking_count / max(total_data_points, 1)
                
                # Final score calculation (weighted average)
                final_score = (
                    avg_attention * 0.4 +
                    engagement_ratio * 0.3 +
                    looking_ratio * 0.3
                ) * 100
            else:
                final_score = 50.0  # Default score if no tracking data
            
            # Update assessment
            assessment.status = 'completed'
            assessment.completed_at = timezone.now()
            assessment.final_score = final_score
            assessment.save()
            
            # Update assignment
            assignment = assessment.assignment
            assignment.status = 'completed'
            assignment.score = final_score
            assignment.completed_at = timezone.now()
            assignment.save()
            
            # Create or update course progress
            CourseProgress.objects.update_or_create(
                employee=request.user,
                course=assignment.course,
                defaults={
                    'progress_percentage': 100,
                    'completion_status': 'completed',
                    'last_accessed': timezone.now(),
                    'final_score': final_score
                }
            )
            
            return JsonResponse({
                'success': True,
                'final_score': final_score,
                'message': 'Assessment completed successfully!'
            })
            
        except VideoAssessment.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Assessment not found'})
        except Exception as e:
            print(f"Assessment completion error: {str(e)}")
            return JsonResponse({'success': False, 'message': 'Failed to complete assessment'})
    
    return JsonResponse({'success': False, 'message': 'Invalid request method'})

@login_required
def admin_skillup_dashboard(request):
    """Admin dashboard for Skill-Up Module"""
    if not request.user.is_staff:
        return redirect('skillup_dashboard')
    
    try:
        # Get all assignments with related data
        assignments = CourseAssignment.objects.select_related(
            'employee', 'course', 'assigned_by', 'video_assessment'
        ).order_by('-assigned_at')
        
        # Calculate overview statistics
        total_candidates = User.objects.filter(is_staff=False).count()
        active_assignments = assignments.filter(status__in=['assigned', 'in_progress']).count()
        in_progress_assessments = VideoAssessment.objects.filter(status='in_progress').count()
        completed_today = assignments.filter(
            completed_at__date=timezone.now().date()
        ).count()
        
        # Calculate average completion rate
        completed_assignments = assignments.filter(status='completed')
        if assignments.exists():
            avg_completion_rate = (completed_assignments.count() / assignments.count()) * 100
        else:
            avg_completion_rate = 0
        
        # Get available courses for assignment
        available_courses = SkillUpCourse.objects.filter(is_active=True)
        
        context = {
            'assignments': assignments,
            'total_candidates': total_candidates,
            'active_assignments': active_assignments,
            'in_progress_assessments': in_progress_assessments,
            'completed_today': completed_today,
            'avg_completion_rate': avg_completion_rate,
            'available_courses': available_courses
        }
        
        return render(request, 'skillup/admin_dashboard.html', context)
        
    except Exception as e:
        print(f"Admin dashboard error: {str(e)}")
        return render(request, 'skillup/admin_dashboard.html', {
            'assignments': [],
            'total_candidates': 0,
            'active_assignments': 0,
            'in_progress_assessments': 0,
            'completed_today': 0,
            'avg_completion_rate': 0,
            'available_courses': []
        })

@csrf_protect  
def assign_course_api(request):
    """API endpoint for assigning courses to candidates"""
    if request.method == 'POST' and request.user.is_staff:
        try:
            data = json.loads(request.body)
            candidate_id = data.get('candidate_id')
            course_id = data.get('course_id')
            
            candidate = User.objects.get(id=candidate_id, is_staff=False)
            course = SkillUpCourse.objects.get(id=course_id, is_active=True)
            
            # Check if assignment already exists
            existing_assignment = CourseAssignment.objects.filter(
                employee=candidate,
                course=course
            ).first()
            
            if existing_assignment:
                return JsonResponse({
                    'success': False, 
                    'message': 'Course already assigned to this candidate'
                })
            
            # Create new assignment
            assignment = CourseAssignment.objects.create(
                employee=candidate,
                course=course,
                assigned_by=request.user,
                status='assigned'
            )
            
            return JsonResponse({
                'success': True,
                'message': f'Course "{course.title}" successfully assigned to {candidate.get_full_name()}'
            })
            
        except User.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Candidate not found'})
        except SkillUpCourse.DoesNotExist:
            return JsonResponse({'success': False, 'message': 'Course not found'})
        except Exception as e:
            print(f"Course assignment error: {str(e)}")
            return JsonResponse({'success': False, 'message': 'Assignment failed'})
    
    return JsonResponse({'success': False, 'message': 'Unauthorized or invalid request'})

@login_required
def view_assignment_progress(request, assignment_id):
    """View detailed progress of a specific assignment"""
    try:
        assignment = CourseAssignment.objects.select_related(
            'employee', 'course', 'video_assessment'
        ).get(id=assignment_id)
        
        # Check permissions
        if not (request.user.is_staff or assignment.employee == request.user):
            return redirect('skillup_dashboard')
        
        # Get course progress
        course_progress = CourseProgress.objects.filter(
            employee=assignment.employee,
            course=assignment.course
        ).first()
        
        # Get attention tracking data if video assessment exists
        attention_data = []
        if assignment.video_assessment:
            attention_data = AttentionTrackingData.objects.filter(
                video_assessment=assignment.video_assessment
            ).order_by('timestamp')
        
        context = {
            'assignment': assignment,
            'course_progress': course_progress,
            'attention_data': attention_data
        }
        
        return render(request, 'skillup/assignment_progress.html', context)
        
    except CourseAssignment.DoesNotExist:
        return redirect('skillup_dashboard')
    except Exception as e:
        print(f"Progress view error: {str(e)}")
        return redirect('skillup_dashboard')

@login_required
def view_assessment_details(request, assessment_id):
    """View detailed video assessment results"""
    try:
        assessment = VideoAssessment.objects.select_related(
            'assignment__employee', 'assignment__course'
        ).get(id=assessment_id)
        
        # Check permissions
        if not (request.user.is_staff or assessment.assignment.employee == request.user):
            return redirect('skillup_dashboard')
        
        # Get attention tracking data
        tracking_data = AttentionTrackingData.objects.filter(
            video_assessment=assessment
        ).order_by('timestamp')
        
        # Calculate analytics
        analytics = {}
        if tracking_data.exists():
            analytics = {
                'total_duration': (assessment.completed_at - assessment.started_at).total_seconds() if assessment.completed_at else 0,
                'avg_attention': tracking_data.aggregate(avg=models.Avg('attention_score'))['avg'] or 0,
                'engagement_breakdown': {
                    'high': tracking_data.filter(engagement_level='high').count(),
                    'medium': tracking_data.filter(engagement_level='medium').count(),
                    'low': tracking_data.filter(engagement_level='low').count()
                },
                'screen_focus_percentage': (
                    tracking_data.filter(looking_at_screen=True).count() / 
                    max(tracking_data.count(), 1)
                ) * 100
            }
        
        context = {
            'assessment': assessment,
            'tracking_data': tracking_data,
            'analytics': analytics
        }
        
        return render(request, 'skillup/assessment_details.html', context)
        
    except VideoAssessment.DoesNotExist:
        return redirect('skillup_dashboard')
    except Exception as e:
        print(f"Assessment details error: {str(e)}")
        return redirect('skillup_dashboard')
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})

# Admin Dashboard Views
@login_required
def admin_dashboard(request):
    """Admin dashboard showing all employees"""
    from django.core.paginator import Paginator
    
    # Check if user is admin
    if not request.user.is_staff and not (hasattr(request.user, 'userprofile') and request.user.userprofile.user_type == 'admin'):
        return redirect('candidate_dashboard')
    
    # Get all employees
    employees = User.objects.select_related('userprofile').prefetch_related(
        'userprofile__candidateprofile'
    ).order_by('-date_joined')
    
    # Filter by search query if provided
    search_query = request.GET.get('search', '')
    if search_query:
        employees = employees.filter(
            models.Q(first_name__icontains=search_query) |
            models.Q(last_name__icontains=search_query) |
            models.Q(email__icontains=search_query)
        )
    
    # Filter by status if provided
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        employees = employees.filter(is_active=True)
    elif status_filter == 'inactive':
        employees = employees.filter(is_active=False)
    elif status_filter == 'processing':
        # Only filter for users who have candidate profiles that are being processed
        employees = employees.filter(
            userprofile__candidateprofile__isnull=False,
            userprofile__candidateprofile__resume_processed=False
        )
    
    # Filter by role if provided
    role_filter = request.GET.get('role', '')
    if role_filter:
        employees = employees.filter(userprofile__user_type=role_filter)
    
    # Pagination
    paginator = Paginator(employees, 20)  # Show 20 employees per page
    page_number = request.GET.get('page')
    employees_page = paginator.get_page(page_number)
    
    # Statistics
    total_employees = User.objects.count()
    active_employees = User.objects.filter(is_active=True).count()
    completed_profiles = CandidateProfile.objects.filter(resume_processed=True).count()
    pending_processing = CandidateProfile.objects.filter(resume_processed=False).count()
    
    context = {
        'employees': employees_page,
        'all_users': [user.userprofile for user in employees_page if hasattr(user, 'userprofile')],
        'total_employees': total_employees,
        'active_employees': active_employees,
        'completed_profiles': completed_profiles,
        'pending_processing': pending_processing,
        'search_query': search_query,
        'status_filter': status_filter,
        'role_filter': role_filter,
        # Add some debug info
        'total_candidates': UserProfile.objects.filter(user_type='candidate').count(),
        'total_managers': UserProfile.objects.filter(user_type='manager').count(),
        'total_admins': UserProfile.objects.filter(user_type='admin').count(),
    }
    
    return render(request, 'dashboard/admin.html', context)

@login_required
def admin_employee_detail(request, employee_id):
    """Admin view for detailed employee information"""
    # Check if user is admin
    if not request.user.is_staff and not (hasattr(request.user, 'userprofile') and request.user.userprofile.user_type == 'admin'):
        return redirect('candidate_dashboard')
    
    try:
        employee = User.objects.select_related('userprofile').get(id=employee_id)
        
        # Get candidate profile if exists
        candidate_profile = None
        try:
            candidate_profile = employee.userprofile.candidateprofile
        except:
            pass
        
        # Get development plans
        development_plans = []
        if candidate_profile:
            development_plans = EmployeeDevelopmentPlan.objects.filter(
                employee_profile=candidate_profile
            ).select_related('course').order_by('-created_at')[:5]
        
        # Get course assignments
        course_assignments = []
        try:
            course_assignments = CourseAssignment.objects.filter(
                user=employee
            ).select_related('course').order_by('-assigned_at')[:5]
        except:
            pass
        
        # Get feedback history for this employee
        feedback_history = ManagerFeedback.objects.filter(
            employee=employee
        ).select_related('manager').order_by('-created_at')
        
        context = {
            'employee': employee,
            'candidate_profile': candidate_profile,
            'development_plans': development_plans,
            'course_assignments': course_assignments,
            'feedback_history': feedback_history,
        }
        
        return render(request, 'employee_detail.html', context)
        
    except User.DoesNotExist:
        return redirect('hr_admin_dashboard')
    except Exception as e:
        print(f"Employee detail error: {str(e)}")
        return redirect('hr_admin_dashboard')

@login_required
def admin_employee_feedback(request, employee_id):
    """Admin feedback page for a specific employee"""
    print('DEBUG: Entered admin_employee_feedback')
    print('DEBUG: user:', request.user.username, '| is_staff:', request.user.is_staff)
    user_type = None
    if hasattr(request.user, 'userprofile'):
        user_type = getattr(request.user.userprofile, 'user_type', None)
    print('DEBUG: user_type:', user_type)
    # Check if user is admin
    if not (request.user.is_staff or (user_type == 'admin')):
        print('DEBUG: Permission denied, redirecting to candidate_dashboard')
        return redirect('candidate_dashboard')
    
    try:
        employee = User.objects.select_related('userprofile').get(id=employee_id)
        
        # Get candidate profile if exists
        candidate_profile = None
        try:
            candidate_profile = employee.userprofile.candidateprofile
        except:
            pass
        
        # Get feedback history for this employee
        feedback_history = ManagerFeedback.objects.filter(
            employee=employee
        ).select_related('manager').order_by('-created_at')
        
        context = {
            'employee': employee,
            'candidate_profile': candidate_profile,
            'feedback_history': feedback_history,
        }
        
        return render(request, 'admin/employee_feedback.html', context)
        
    except User.DoesNotExist:
        return redirect('admin_dashboard')
    except Exception as e:
        print(f"Employee feedback page error: {str(e)}")
        return redirect('admin_dashboard')

@csrf_protect
def admin_submit_feedback(request, employee_id):
    """Submit feedback for an employee"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    
    # Check if user is admin
    if not request.user.is_staff and not (hasattr(request.user, 'userprofile') and request.user.userprofile.user_type == 'admin'):
        return JsonResponse({'success': False, 'error': 'Access denied'})
    
    try:
        employee = User.objects.get(id=employee_id)
        
        # Get form data
        subject = request.POST.get('subject', '').strip()
        message = request.POST.get('message', '').strip()
        rating = int(request.POST.get('rating', 3))
        areas_of_concern_text = request.POST.get('areas_of_concern', '').strip()
        
        # Validate required fields
        if not subject or not message:
            return JsonResponse({'success': False, 'error': 'Subject and message are required'})
        
        # Process areas of concern
        areas_of_concern = []
        if areas_of_concern_text:
            areas_of_concern = [area.strip() for area in areas_of_concern_text.split(',') if area.strip()]
        
        # Create feedback
        feedback = ManagerFeedback.objects.create(
            employee=employee,
            manager=request.user,
            subject=subject,
            message=message,
            rating=rating,
            areas_of_concern=areas_of_concern
        )
        
        return JsonResponse({
            'success': True, 
            'message': 'Feedback submitted successfully',
            'feedback_id': feedback.id
        })
        
    except User.DoesNotExist:
        return JsonResponse({'success': False, 'error': 'Employee not found'})
    except ValueError as e:
        return JsonResponse({'success': False, 'error': f'Invalid data: {str(e)}'})
    except Exception as e:
        print(f"Feedback submission error: {str(e)}")
        return JsonResponse({'success': False, 'error': 'An error occurred while submitting feedback'})

@csrf_exempt
def ai_feedback_suggestion(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Only POST method allowed'})
    try:
        prompt = request.POST.get('prompt', '').strip()
        if not prompt:
            prompt = 'Suggest a constructive feedback message for an employee.'
        client = get_gemini_client()
        response = client.generate_content(prompt)
        suggestion = response.text if hasattr(response, 'text') else str(response)
        print('AI RAW SUGGESTION:', suggestion)
        # Extract only the first option or sentence if multiple are present
        # Prefer lines starting with Option 1, otherwise first non-empty line
        option_match = re.search(r'Option 1.*?:\s*(["\“\']?)(.+?)\1\s*(?:\n|$)', suggestion, re.IGNORECASE)
        if option_match:
            suggestion = option_match.group(2).strip()
        else:
            # Fallback: first non-empty line that is not a heading
            lines = [l.strip() for l in suggestion.splitlines() if l.strip() and not l.lower().startswith(('here', 'option', 'focus', 'improved', 'list', 'clarity', 'specificity', 'professionalism'))]
            if lines:
                suggestion = lines[0]
        # Try to extract after 'Areas of Concern:' or 'Areas for Development:' or 'Message:'
        match = re.search(r'(Areas of Concern|Areas for Development|Message)[:\s\*]*([\s\S]+)', suggestion, re.IGNORECASE)
        if match:
            suggestion = match.group(2).strip()
        # Remove any line starting with 'Subject:'
        suggestion = re.sub(r'^Subject:.*$', '', suggestion, flags=re.MULTILINE).strip()
        # Remove any leading markdown or asterisks from the suggestion
        suggestion = re.sub(r'^[\*\s]+', '', suggestion)
        # Fallback: if suggestion is empty, use first non-empty, non-heading, non-Subject line
        if not suggestion:
            lines = [l.strip() for l in suggestion.splitlines() if l.strip() and not l.lower().startswith(('here', 'option', 'focus', 'improved', 'list', 'clarity', 'specificity', 'professionalism', 'subject'))]
            if lines:
                suggestion = lines[0]
        # Extract bullet points after "Areas of Concern:" (with or without **)
        areas_match = re.search(r'(?:\*\*)?Areas of Concern(?:\*\*)?:\s*([\s\S]*)', suggestion, re.IGNORECASE)
        if areas_match:
            areas_text = areas_match.group(1).strip()
            # Extract all bullet points and join them with newlines
            bullets = re.findall(r'^\s*\*\s*(.+)', areas_text, re.MULTILINE)
            if bullets:
                suggestion = '\n'.join(bullets)
            elif areas_text and not areas_text.startswith('*'):
                suggestion = areas_text
        else:
            # Extract text after "**Improved:**" if present
            improved_match = re.search(r'\*\*Improved:\*\*\s*(.+)', suggestion, re.IGNORECASE)
            if improved_match:
                suggestion = improved_match.group(1).strip()
            else:
                # Extract first bullet point from anywhere
                bullet_match = re.search(r'^\s*\*\s*(.+)', suggestion, re.MULTILINE)
                if bullet_match:
                    suggestion = bullet_match.group(1).strip()
                else:
                    # Remove any markdown formatting and get first meaningful line
                    lines = [l.strip() for l in suggestion.splitlines() if l.strip() and not l.startswith(('**', 'Here', 'Option', 'Original', 'Subject'))]
                    if lines:
                        suggestion = lines[0]
        
        # Final extraction for Areas of Concern format
        final_areas_match = re.search(r'Areas of Concern\s*:\s*([\s\S]*)', suggestion, re.IGNORECASE)
        if final_areas_match:
            areas_text = final_areas_match.group(1).strip()
            bullets = re.findall(r'^\s*\*\s*(.+)', areas_text, re.MULTILINE)
            if bullets:
                suggestion = '\n'.join([b.strip() for b in bullets])
        
        # Clean up any remaining markdown
        suggestion = re.sub(r'\*\*', '', suggestion).strip()
        return JsonResponse({'success': True, 'suggestion': suggestion})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

from django.http import JsonResponse  # ensure JsonResponse is imported

@csrf_exempt
@login_required
def submit_action_assessment(request, id):
    """Endpoint to handle submission of action assessments."""
    import json
    from .models import FeedbackAction
    
    try:
        if request.method == 'POST':
            action = FeedbackAction.objects.get(id=id, employee=request.user)
            
            # Get form data
            video_file = request.FILES.get('video')
            transcript = request.POST.get('transcript', '')
            questions = json.loads(request.POST.get('questions', '[]'))
            answers = json.loads(request.POST.get('answers', '[]'))
            cheating_data = json.loads(request.POST.get('cheating_data', '{}'))
            
            # Analyze cheating indicators
            cheating_detected = False
            cheating_details = []
            
            if cheating_data.get('tabSwitches', 0) > 0:
                cheating_detected = True
                cheating_details.append(f"Tab switched {cheating_data['tabSwitches']} times")
                
            if cheating_data.get('windowBlur', 0) > 2:
                cheating_detected = True
                cheating_details.append(f"Window lost focus {cheating_data['windowBlur']} times")
                
            if len(cheating_data.get('suspicious_activity', [])) > 3:
                cheating_detected = True
                cheating_details.append(f"{len(cheating_data['suspicious_activity'])} suspicious activities detected")
            
            # Generate AI feedback using Gemini
            from .gemini_client import get_gemini_client
            
            prompt = f"""
            Analyze this employee assessment for action completion: "{action.title}"
            
            Questions asked: {questions}
            Answers provided: {answers}
            Transcript: {transcript}
            
            Please provide:
            1. A score from 1-10 on action completion
            2. Brief feedback on the quality of responses
            3. Whether the action appears to be genuinely completed
            
            Respond in JSON format: {{"score": X, "feedback": "...", "completed": true/false}}
            """
            
            try:
                client = get_gemini_client()
                response = client.generate_content(prompt)
                ai_result = json.loads(response.text.strip())
                ai_score = ai_result.get('score', 5)
                ai_feedback = ai_result.get('feedback', 'Assessment completed.')
                action_completed = ai_result.get('completed', False)
            except:
                ai_score = 7  # Default score if AI analysis fails
                ai_feedback = 'Assessment completed successfully.'
                action_completed = True
            
            # Apply cheating penalty
            if cheating_detected:
                ai_score = max(1, ai_score - 3)  # Reduce score by 3 points for cheating
                ai_feedback += " Note: Assessment integrity concerns detected."
            
            # Mark action as complete if score is good and no major cheating
            if ai_score >= 6 and not (cheating_data.get('tabSwitches', 0) > 2):
                action.is_completed = True
                action.save()
                marked_complete = True
            else:
                marked_complete = False
            
            return JsonResponse({
                'success': True,
                'ai_score': ai_score,
                'ai_feedback': ai_feedback,
                'cheating_detected': cheating_detected,
                'cheating_details': '; '.join(cheating_details),
                'marked_complete': marked_complete
            })
        
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@login_required 
def start_course_assessment(request, assignment_id):
    """Start video assessment for course completion"""
    try:
        from .models import EmployeeDevelopmentPlan
        
        assignment = EmployeeDevelopmentPlan.objects.get(
            id=assignment_id,
            employee_profile__user_profile__user=request.user
        )
        
        course = assignment.course
        
        # Generate course-specific questions using Gemini
        from .gemini_client import get_gemini_client
        
        prompt = f"""
        Generate 3 detailed interview questions to assess if the user has completed and understood the course: "{course.title}"
        
        Course Description: {course.description}
        Course Skills: {getattr(course, 'skills_covered', 'General skills')}
        
        The questions should:
        1. Test practical understanding of course concepts
        2. Ask for specific examples or applications
        3. Verify genuine learning vs superficial completion
        
        Format each question clearly and make them specific to this course content.
        """
        
        try:
            client = get_gemini_client()
            response = client.generate_content(prompt)
            text = response.text.strip()
            
            print(f'Course Assessment - Gemini raw response: {repr(text)}')
            
            # Extract questions using the same logic as before
            import re
            questions = []
            
            # Split text into sections by number pattern
            sections = re.split(r'\n\s*[0-9]+\.\s*', text)
            
            for section in sections[1:]:  # Skip first empty section
                # Look for quoted question (text between quotes)
                quote_match = re.search(r'"([^"]+)"', section)
                if quote_match:
                    question = quote_match.group(1).strip()
                    # Clean up any remaining markdown
                    question = re.sub(r'\*\*|\*', '', question)
                    questions.append(question)
                else:
                    # Fallback: take first sentence that ends with ?
                    sentences = section.split('.')
                    for sentence in sentences:
                        if '?' in sentence:
                            question = sentence.split('?')[0] + '?'
                            question = re.sub(r'\*\*|\*|"', '', question).strip()
                            if question:
                                questions.append(question)
                                break
            
            questions = questions[:3] if questions else [
                f"How have you applied the key concepts from '{course.title}' in practical scenarios?",
                f"What specific skills from this course will you use in your current role?", 
                f"Describe a project or task where you could implement what you learned from '{course.title}'."
            ]
            
            return JsonResponse({'success': True, 'questions': questions})
            
        except Exception as e:
            # Fallback questions if AI fails
            questions = [
                f"How have you applied the key concepts from '{course.title}' in practical scenarios?",
                f"What specific skills from this course will you use in your current role?",
                f"Describe a project or task where you could implement what you learned from '{course.title}'."
            ]
            return JsonResponse({'success': True, 'questions': questions})
            
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})

@csrf_exempt
@login_required
def submit_course_assessment(request, assignment_id):
    """Submit course video assessment and mark completion"""
    import json
    from .models import EmployeeDevelopmentPlan
    
    try:
        if request.method == 'POST':
            assignment = EmployeeDevelopmentPlan.objects.get(
                id=assignment_id,
                employee_profile__user_profile__user=request.user
            )
            
            course = assignment.course
            
            # Get form data
            video_file = request.FILES.get('video')
            transcript = request.POST.get('transcript', '')
            questions = json.loads(request.POST.get('questions', '[]'))
            answers = json.loads(request.POST.get('answers', '[]'))
            cheating_data = json.loads(request.POST.get('cheating_data', '{}'))
            
            # Analyze cheating indicators
            cheating_detected = False
            cheating_details = []
            
            if cheating_data.get('tabSwitches', 0) > 0:
                cheating_detected = True
                cheating_details.append(f"Tab switched {cheating_data['tabSwitches']} times")
                
            if cheating_data.get('windowBlur', 0) > 2:
                cheating_detected = True
                cheating_details.append(f"Window lost focus {cheating_data['windowBlur']} times")
                
            if len(cheating_data.get('suspicious_activity', [])) > 3:
                cheating_detected = True
                cheating_details.append(f"{len(cheating_data['suspicious_activity'])} suspicious activities detected")
            
            # Generate AI feedback using Gemini
            from .gemini_client import get_gemini_client
            
            prompt = f"""
            Analyze this course completion assessment for: "{course.title}"
            
            Course Description: {course.description}
            Questions asked: {questions}
            Answers provided: {answers}
            Transcript: {transcript}
            
            Please evaluate:
            1. Understanding of course concepts (1-10)
            2. Practical application knowledge (1-10) 
            3. Genuine completion vs superficial (1-10)
            4. Overall course mastery (1-10)
            
            Respond in JSON format: {{"understanding": X, "application": X, "completion": X, "overall": X, "feedback": "...", "course_completed": true/false}}
            """
            
            try:
                client = get_gemini_client()
                response = client.generate_content(prompt)
                ai_result = json.loads(response.text.strip())
                
                understanding = ai_result.get('understanding', 7)
                application = ai_result.get('application', 7) 
                completion = ai_result.get('completion', 7)
                overall_score = ai_result.get('overall', 7)
                ai_feedback = ai_result.get('feedback', 'Course assessment completed.')
                course_completed = ai_result.get('course_completed', True)
                
            except:
                understanding = application = completion = overall_score = 7
                ai_feedback = 'Course assessment completed successfully.'
                course_completed = True
            
            # Apply cheating penalty
            if cheating_detected:
                overall_score = max(1, overall_score - 3)
                ai_feedback += " Note: Assessment integrity concerns detected."
            
            # Mark course as complete if score is good and no major cheating
            if overall_score >= 6 and not (cheating_data.get('tabSwitches', 0) > 2):
                assignment.status = 'completed'
                assignment.progress_percentage = 100
                assignment.save()
                marked_complete = True
            else:
                marked_complete = False
            
            return JsonResponse({
                'success': True,
                'ai_score': overall_score,
                'understanding': understanding,
                'application': application, 
                'completion': completion,
                'ai_feedback': ai_feedback,
                'cheating_detected': cheating_detected,
                'cheating_details': '; '.join(cheating_details),
                'marked_complete': marked_complete,
                'course_title': course.title
            })
        
        return JsonResponse({'success': False, 'error': 'Invalid request method'})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
