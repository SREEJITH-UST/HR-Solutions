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
    SkillUpCourse, CourseAssignment, VideoAssessment, AttentionTrackingData, CourseProgress
)
from .services import ResumeProcessingService
from .development_service import EmployeeDevelopmentService
import json
import threading
from django.views.decorators.csrf import csrf_protect

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
    """Display manager feedback and recommendations"""
    from .models import ManagerFeedback, FeedbackAction, FeedbackCourseRecommendation
    from collections import Counter
    from django.db.models import Avg
    
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
        recommended_actions = FeedbackAction.objects.filter(employee=request.user).order_by('priority', '-created_at')
        
        # Get course recommendations
        recommended_courses = FeedbackCourseRecommendation.objects.filter(employee=request.user).select_related('course')
        
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
        # Get user's course assignments
        assignments = CourseAssignment.objects.filter(
            employee=request.user
        ).select_related('course', 'assigned_by', 'video_assessment').order_by('-assigned_at')
        
        # Calculate statistics
        stats = {
            'total_courses': assignments.count(),
            'completed_courses': assignments.filter(status='completed').count(),
            'in_progress_courses': assignments.filter(status='in_progress').count(),
            'pending_assessments': assignments.filter(
                course__has_video_assessment=True,
                video_assessment__isnull=True
            ).count()
        }
        
        # Calculate completion rate
        if stats['total_courses'] > 0:
            stats['completion_rate'] = (stats['completed_courses'] / stats['total_courses']) * 100
        else:
            stats['completion_rate'] = 0
        
        # Get available courses for enrollment
        assigned_course_ids = assignments.values_list('course_id', flat=True)
        available_courses = SkillUpCourse.objects.exclude(
            id__in=assigned_course_ids
        ).filter(is_active=True)
        
        context = {
            'assignments': assignments,
            'stats': stats,
            'available_courses': available_courses
        }
        return render(request, 'skillup/dashboard.html', context)
        
    except Exception as e:
        print(f"Skill-Up dashboard error: {str(e)}")
        return render(request, 'skillup/dashboard.html', {
            'assignments': [],
            'stats': {'total_courses': 0, 'completed_courses': 0, 'in_progress_courses': 0, 'pending_assessments': 0, 'completion_rate': 0},
            'available_courses': []
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
