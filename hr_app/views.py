from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.contrib import messages
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
import logging
from django.views.decorators.csrf import csrf_protect

logger = logging.getLogger(__name__)

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
            try:
                login_form = LoginForm(request.POST)
                if login_form.is_valid():
                    username = login_form.cleaned_data['username']
                    password = login_form.cleaned_data['password']
                    
                    user = authenticate(username=username, password=password)
                    if user:
                        login(request, user)
                        return redirect('dashboard')
                    else:
                        login_error = "Invalid username or password."
                else:
                    # Form validation errors
                    form_errors = []
                    for field, errors in login_form.errors.items():
                        for error in errors:
                            form_errors.append(f"{field}: {error}")
                    login_error = "Form validation failed: " + "; ".join(form_errors)
            except Exception as e:
                logger.error(f"Login error: {str(e)}", exc_info=True)
                login_error = "An error occurred during login. Please try again."
        elif 'signup' in request.POST:
            signup_form = SignupForm(request.POST, request.FILES)
            if signup_form.is_valid():
                try:
                    # Create user
                    user = User.objects.create_user(
                        username=signup_form.cleaned_data['username'],
                        email=signup_form.cleaned_data['email'],
                        password=signup_form.cleaned_data['password'],
                        first_name=signup_form.cleaned_data['first_name'],
                        last_name=signup_form.cleaned_data['last_name']
                    )
                    
                    # Create user profile - all users are now candidates
                    user_profile_data = {
                        'user': user,
                        'country_code': signup_form.cleaned_data['country_code'],
                        'mobile_number': signup_form.cleaned_data['mobile_number'],
                        'user_type': 'candidate',
                        'resume': signup_form.cleaned_data['resume']
                    }
                    
                    user_profile = UserProfile.objects.create(**user_profile_data)
                    
                    # Start resume processing in background
                    thread = threading.Thread(
                        target=process_resume_async, 
                        args=(user_profile.id,)
                    )
                    thread.start()
                    
                    # Login the user
                    login(request, user)
                    
                    # All users go to processing page
                    return redirect('processing')
                
                except Exception as e:
                    # If user creation failed, delete the user if it was created
                    if 'user' in locals():
                        try:
                            user.delete()
                        except Exception as delete_error:
                            logger.error(f"Failed to delete user after signup error: {delete_error}")
                    
                    # Log detailed exception information
                    logger.error(f"Signup error: {str(e)}", exc_info=True)
                    signup_error = f"Signup failed: {str(e)}"
            else:
                # Form validation errors
                form_errors = []
                for field, errors in signup_form.errors.items():
                    for error in errors:
                        form_errors.append(f"{field}: {error}")
                signup_error = "Form validation failed: " + "; ".join(form_errors)
                logger.error(f"Signup form errors: {signup_form.errors}")

    return render(request, 'accounts/login.html', {
        'login_form': login_form,
        'signup_form': signup_form,
        'login_error': login_error,
        'signup_error': signup_error,
    })

def signup_view(request):
    signup_form = SignupForm()
    signup_error = ''
    signup_success = False
    
    if request.method == 'POST':
        logger.info("Processing POST request for signup")
        signup_form = SignupForm(request.POST, request.FILES)
        if signup_form.is_valid():
            logger.info(f"Signup form is valid for user: {signup_form.cleaned_data.get('username')}")
            try:
                # Create user
                user = User.objects.create_user(
                    username=signup_form.cleaned_data['username'],
                    email=signup_form.cleaned_data['email'],
                    password=signup_form.cleaned_data['password'],
                    first_name=signup_form.cleaned_data['first_name'],
                    last_name=signup_form.cleaned_data['last_name']
                )
                
                # Create user profile - initially set to pending until role selection
                user_profile_data = {
                    'user': user,
                    'country_code': signup_form.cleaned_data['country_code'],
                    'mobile_number': signup_form.cleaned_data['mobile_number'],
                    'user_type': 'pending',  # Set to pending until role selection
                    'resume': signup_form.cleaned_data['resume']
                }
                
                try:
                    user_profile = UserProfile.objects.create(**user_profile_data)
                    logger.info(f"UserProfile created successfully for user {user.username}")
                except Exception as profile_error:
                    logger.error(f"Error creating UserProfile: {str(profile_error)}")
                    # If 'pending' is not available in DB, fall back to 'candidate'
                    user_profile_data['user_type'] = 'candidate'
                    user_profile = UserProfile.objects.create(**user_profile_data)
                    logger.info(f"Fallback: UserProfile created with candidate type for user {user.username}")
                
                # Don't start resume processing yet - wait for role selection
                
                # Set success flag
                signup_success = True
                
                # Login the user
                login(request, user)
            
            except Exception as e:
                # If user creation failed, delete the user if it was created
                if 'user' in locals():
                    try:
                        user.delete()
                        logger.info(f"Cleaned up user {user.username} after signup error")
                    except Exception as delete_error:
                        logger.error(f"Failed to delete user after signup error: {str(delete_error)}")
                
                # Log detailed error information
                logger.error(f"Signup error details: {str(e)}", exc_info=True)
                
                # Provide user-friendly error message
                if "UNIQUE constraint failed" in str(e):
                    if "username" in str(e):
                        signup_error = "Username already exists. Please choose a different username."
                    elif "email" in str(e):
                        signup_error = "Email already registered. Please use a different email or try logging in."
                    else:
                        signup_error = "An account with this information already exists."
                elif "user_type" in str(e).lower() or "constraint" in str(e).lower():
                    signup_error = "There was a configuration issue. Please try again or contact support."
                else:
                    signup_error = f"Signup failed: {str(e)}"
            
            if signup_success:
                # Return success response for AJAX or redirect for regular form submission
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({
                        'status': 'success',
                        'message': 'Account created successfully! Please select your role...',
                        'redirect_url': '/role-selection/'
                    })
                else:
                    # Redirect to role selection page
                    return redirect('role_selection')
        else:
            # Form validation errors
            form_errors = []
            for field, errors in signup_form.errors.items():
                for error in errors:
                    form_errors.append(f"{field}: {error}")
            
            logger.error(f"Signup form validation errors: {signup_form.errors}")
            signup_error = "Please correct the following errors: " + "; ".join(form_errors)
            
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        if signup_success:
            return JsonResponse({
                'status': 'success',
                'message': 'Account created successfully! Please select your role...',
                'redirect_url': '/role-selection/'
            })
        else:
            return JsonResponse({
                'status': 'error',
                'message': signup_error or 'Signup failed. Please try again.'
            })
            
    return render(request, 'accounts/signup.html', {
        'signup_form': signup_form,
        'signup_error': signup_error,
        'signup_success': signup_success,
    })

@login_required
def role_selection_view(request):
    """Role selection page after signup"""
    error_message = ''
    
    if request.method == 'POST':
        selected_role = request.POST.get('role')
        
        if selected_role in ['candidate', 'admin']:
            try:
                # Update user profile with selected role
                user_profile = UserProfile.objects.get(user=request.user)
                user_profile.user_type = selected_role
                user_profile.save()
                
                # If candidate role, start resume processing
                if selected_role == 'candidate':
                    # Start resume processing in background
                    import threading
                    
                    thread = threading.Thread(
                        target=process_resume_async, 
                        args=(user_profile.id,)
                    )
                    thread.start()
                    
                    # Redirect to processing page for candidates
                    return redirect('processing')
                else:
                    # Redirect to admin dashboard for admins
                    return redirect('admin_dashboard')
                    
            except UserProfile.DoesNotExist:
                error_message = "User profile not found. Please contact support."
            except Exception as e:
                error_message = f"An error occurred: {str(e)}"
        else:
            error_message = "Please select a valid role."
    
    return render(request, 'accounts/role_selection.html', {
        'user': request.user,
        'error_message': error_message,
    })

@login_required
def processing_view(request):
    """Show processing status page"""
    return render(request, 'accounts/processing.html', {
        'user': request.user
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
    
    return render(request, 'dashboard/manager.html', context)

@login_required
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
    """Professional HR home page"""
    return render(request, 'home/index.html')

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

def about_view(request):
    """About Us page"""
    return render(request, 'home/about.html')

def blog_view(request):
    """Enhanced blog page with real-time HR blogs from multiple online sources"""
    try:
        import requests
        import feedparser
        from datetime import datetime
        import re
        from urllib.parse import urljoin
    except ImportError as e:
        logger.error(f"Required packages not installed: {str(e)}")
        # Fallback to default blogs if packages not available
        blogs = [
            {
                'title': 'The Future of Remote Work in HR',
                'description': 'Explore how remote work is reshaping human resources practices and what it means for the future of work.',
                'url': 'https://www.shrm.org/topics/pages/remote-work.aspx',
                'published': 'December 15, 2024',
                'source': 'SHRM',
                'category': 'Future of Work'
            },
            {
                'title': 'AI and Machine Learning in Recruitment',
                'description': 'Discover how artificial intelligence is revolutionizing the recruitment process and improving candidate experiences.',
                'url': 'https://www.hrdive.com/news/ai-recruitment/',
                'published': 'December 10, 2024',
                'source': 'HR Dive',
                'category': 'Technology'
            },
            {
                'title': 'Employee Engagement Strategies for 2025',
                'description': 'Learn about the latest strategies to boost employee engagement and retention in the modern workplace.',
                'url': 'https://blog.namely.com/employee-engagement',
                'published': 'December 5, 2024',
                'source': 'Namely',
                'category': 'Employee Engagement'
            }
        ]
        return render(request, 'home/blog.html', {'blogs': blogs})
    
    blogs = []
    
    try:
        # Enhanced list of HR-related sources with better coverage
        hr_sources = [
            {
                'name': 'SHRM',
                'feeds': [
                    'https://feeds.feedburner.com/hrblog',
                    'https://www.shrm.org/resourcesandtools/hr-topics/pages/rss.aspx'
                ],
                'direct_urls': [
                    'https://www.shrm.org/topics/news/',
                    'https://www.shrm.org/resourcesandtools/hr-topics/talent-acquisition/'
                ]
            },
            {
                'name': 'HR Dive',
                'feeds': ['https://www.hrdive.com/feeds/'],
                'direct_urls': ['https://www.hrdive.com/news/']
            },
            {
                'name': 'Workday Blog',
                'feeds': ['https://blog.workday.com/en-us/feed'],
                'direct_urls': ['https://blog.workday.com/en-us/']
            },
            {
                'name': 'HR Morning',
                'feeds': ['https://hrmorning.com/feed/'],
                'direct_urls': ['https://hrmorning.com/']
            },
            {
                'name': 'BambooHR Blog',
                'feeds': ['https://www.bamboohr.com/blog/feed/'],
                'direct_urls': ['https://www.bamboohr.com/blog/']
            },
            {
                'name': 'HR Technologist',
                'feeds': ['https://www.hrtechnologist.com/feed/'],
                'direct_urls': ['https://www.hrtechnologist.com/']
            }
        ]
        
        # Set request timeout and headers
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        
        for source in hr_sources:
            # Try RSS feeds first
            for feed_url in source.get('feeds', []):
                try:
                    logger.info(f"Fetching RSS feed: {feed_url}")
                    
                    # Custom headers for feedparser
                    feed = feedparser.parse(feed_url)
                    
                    if hasattr(feed, 'entries') and feed.entries:
                        logger.info(f"Found {len(feed.entries)} entries from {source['name']}")
                        
                        for entry in feed.entries[:3]:  # Get top 3 from each feed
                            # Clean up the description/summary
                            description = getattr(entry, 'summary', getattr(entry, 'description', ''))
                            if description:
                                # Remove HTML tags and clean up
                                description = re.sub(r'<[^>]+>', '', description)
                                description = re.sub(r'\s+', ' ', description).strip()
                                # Limit length
                                description = description[:320] + '...' if len(description) > 320 else description
                            
                            # Parse published date
                            try:
                                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                                    pub_date = datetime(*entry.published_parsed[:6])
                                elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                                    pub_date = datetime(*entry.updated_parsed[:6])
                                else:
                                    pub_date = datetime.now()
                            except:
                                pub_date = datetime.now()
                            
                            # Determine category from title or tags
                            title = getattr(entry, 'title', 'HR Industry News')
                            category = determine_category(title, description)
                            
                            blogs.append({
                                'title': title,
                                'description': description or 'Stay updated with the latest HR trends and insights.',
                                'url': getattr(entry, 'link', '#'),
                                'published': pub_date.strftime('%B %d, %Y'),
                                'source': source['name'],
                                'category': category,
                                'is_recent': (datetime.now() - pub_date).days <= 30
                            })
                            
                        if len(blogs) >= 12:  # Limit to 12 total blogs for good layout
                            break
                            
                except Exception as e:
                    logger.error(f"Error fetching RSS from {feed_url}: {str(e)}")
                    continue
                    
            if len(blogs) >= 12:
                break
    
    except Exception as e:
        logger.error(f"Error in blog fetching: {str(e)}")
    
    # If still no blogs, provide comprehensive fallback content with current HR trends
    if not blogs:
        logger.info("Using fallback blog content")
        blogs = [
            {
                'title': 'The Future of Remote Work in HR',
                'description': 'Explore how remote work is reshaping human resources practices and what it means for the future of work. Learn about hybrid models, digital transformation, and employee engagement strategies.',
                'url': 'https://www.shrm.org/topics/pages/remote-work.aspx',
                'published': 'December 15, 2024',
                'source': 'SHRM',
                'category': 'Future of Work',
                'is_recent': True
            },
            {
                'title': 'AI and Machine Learning in Recruitment',
                'description': 'Discover how artificial intelligence is revolutionizing the recruitment process and improving candidate experiences. From resume screening to predictive analytics and bias reduction.',
                'url': 'https://www.hrdive.com/news/ai-recruitment/',
                'published': 'December 10, 2024',
                'source': 'HR Dive',
                'category': 'Technology',
                'is_recent': True
            },
            {
                'title': 'Employee Engagement Strategies for 2025',
                'description': 'Learn about the latest strategies to boost employee engagement and retention in the modern workplace. Focus on well-being, career development, recognition programs, and creating purpose-driven work.',
                'url': 'https://blog.namely.com/employee-engagement',
                'published': 'December 5, 2024',
                'source': 'Namely',
                'category': 'Employee Engagement',
                'is_recent': True
            },
            {
                'title': 'Digital Transformation in HR: Beyond the Basics',
                'description': 'Understanding how digital tools and technologies are transforming human resources departments across industries. Explore cloud-based solutions, automation trends, and the impact of HR analytics.',
                'url': 'https://www.hrtechnologist.com/articles/digital-transformation/',
                'published': 'November 28, 2024',
                'source': 'HR Technologist',
                'category': 'Digital Transformation',
                'is_recent': True
            },
            {
                'title': 'Building Inclusive Workplaces: DEI Strategies That Work',
                'description': 'Best practices for building inclusive workplaces and implementing effective diversity, equity, and inclusion strategies. Learn about measuring impact and creating lasting organizational change.',
                'url': 'https://www.shrm.org/topics/diversity-inclusion/',
                'published': 'November 25, 2024',
                'source': 'SHRM',
                'category': 'Diversity & Inclusion',
                'is_recent': True
            },
            {
                'title': 'Employee Mental Health: A Strategic HR Priority',
                'description': 'How organizations are prioritizing mental health support and creating psychologically safe work environments. Discover practical resources, implementation strategies, and ROI metrics.',
                'url': 'https://www.hrdive.com/topic/employee-wellness/',
                'published': 'November 20, 2024',
                'source': 'HR Dive',
                'category': 'Wellness',
                'is_recent': True
            },
            {
                'title': 'Skills-Based Hiring: The New Recruitment Paradigm',
                'description': 'Move beyond traditional degree requirements to skills-based hiring practices. Learn how to assess competencies, reduce bias, and find the right talent for evolving job roles.',
                'url': 'https://www.workday.com/en-us/resources/skills-based-hiring.html',
                'published': 'November 15, 2024',
                'source': 'Workday',
                'category': 'Talent Acquisition',
                'is_recent': True
            },
            {
                'title': 'Hybrid Work Models: Optimizing for Performance',
                'description': 'Strategies for implementing successful hybrid work models that balance flexibility with collaboration. Cover policy development, technology requirements, and performance management.',
                'url': 'https://www.bamboohr.com/blog/hybrid-work-best-practices',
                'published': 'November 10, 2024',
                'source': 'BambooHR',
                'category': 'Hybrid Work',
                'is_recent': True
            },
            {
                'title': 'HR Analytics: Data-Driven Decision Making',
                'description': 'Harness the power of HR analytics to make informed decisions about talent management, performance optimization, and strategic workforce planning. Tools and methodologies covered.',
                'url': 'https://hrmorning.com/news/hr-analytics-trends/',
                'published': 'November 5, 2024',
                'source': 'HR Morning',
                'category': 'Analytics',
                'is_recent': True
            },
            {
                'title': 'Generation Z in the Workplace: Management Strategies',
                'description': 'Understanding and managing Generation Z employees effectively. Learn about their values, communication preferences, career expectations, and how to create engaging work experiences.',
                'url': 'https://blog.workday.com/en-us/2024/generation-z-workplace-management.html',
                'published': 'October 30, 2024',
                'source': 'Workday',
                'category': 'Generational Workforce',
                'is_recent': True
            },
            {
                'title': 'Compensation Trends 2025: Staying Competitive',
                'description': 'Latest compensation and benefits trends for 2025. Explore pay equity initiatives, flexible benefits packages, and innovative reward systems that attract and retain top talent.',
                'url': 'https://www.shrm.org/resourcesandtools/hr-topics/compensation/',
                'published': 'October 25, 2024',
                'source': 'SHRM',
                'category': 'Compensation',
                'is_recent': True
            },
            {
                'title': 'Upskilling and Reskilling: Future-Proofing Your Workforce',
                'description': 'Develop comprehensive upskilling and reskilling programs to prepare your workforce for the future. Learn about identifying skill gaps, creating learning pathways, and measuring success.',
                'url': 'https://www.hrtechnologist.com/articles/learning-development/upskilling-reskilling-strategies/',
                'published': 'October 20, 2024',
                'source': 'HR Technologist',
                'category': 'Learning & Development',
                'is_recent': True
            }
        ]
    
    # Sort blogs by recency and mix sources for variety
    blogs = sorted(blogs, key=lambda x: (x.get('is_recent', False), x['published']), reverse=True)
    
    # Limit to 12 blogs for optimal layout
    blogs = blogs[:12]
    
    logger.info(f"Serving {len(blogs)} blog articles")
    return render(request, 'home/blog.html', {'blogs': blogs})


def determine_category(title, description):
    """Determine blog category based on title and description content"""
    content = f"{title} {description}".lower()
    
    categories = {
        'AI & Technology': ['ai', 'artificial intelligence', 'machine learning', 'automation', 'technology', 'digital', 'tech'],
        'Remote Work': ['remote', 'hybrid', 'telecommuting', 'work from home', 'distributed'],
        'Employee Engagement': ['engagement', 'retention', 'satisfaction', 'motivation', 'culture'],
        'Diversity & Inclusion': ['diversity', 'inclusion', 'equity', 'dei', 'bias', 'inclusive'],
        'Talent Acquisition': ['recruitment', 'hiring', 'talent acquisition', 'recruiting', 'candidate'],
        'Learning & Development': ['training', 'learning', 'development', 'upskill', 'reskill', 'education'],
        'Wellness': ['mental health', 'wellness', 'wellbeing', 'burnout', 'stress', 'health'],
        'Compensation': ['compensation', 'salary', 'benefits', 'pay', 'rewards', 'payroll'],
        'Performance Management': ['performance', 'appraisal', 'feedback', 'evaluation', 'goals'],
        'Leadership': ['leadership', 'management', 'managers', 'executives', 'leadership development']
    }
    
    for category, keywords in categories.items():
        if any(keyword in content for keyword in keywords):
            return category
    
    return 'HR News'

def contact_view(request):
    """Contact page"""
    return render(request, 'home/contact.html')

@login_required
def send_courses_email(request):
    """Send recommended courses to employee's email"""
    if request.method == 'POST':
        try:
            # Get user profile and candidate profile
            user_profile = UserProfile.objects.get(user=request.user)
            candidate_profile = CandidateProfile.objects.get(user_profile=user_profile)
            
            # Debug logging to verify user details
            logger.info(f"Course email request from user:")
            logger.info(f"  Username: {request.user.username}")
            logger.info(f"  User Email: {request.user.email}")
            logger.info(f"  User ID: {request.user.id}")
            logger.info(f"  Profile ID: {user_profile.id}")
            logger.info(f"  Candidate Profile ID: {candidate_profile.id}")
            
            logger.info(f"Processing email request for user: {request.user.username} ({request.user.email})")
            
            # Get employee's development plans
            development_plans = EmployeeDevelopmentPlan.objects.filter(
                employee_profile=candidate_profile,
                status__in=['recommended', 'in_progress', 'not_started']
            ).select_related('course').order_by('-created_at')
            
            logger.info(f"Found {development_plans.count()} development plans for user")
            
            if not development_plans.exists():
                logger.warning(f"No development plans found for user: {request.user.username}")
                return JsonResponse({
                    'status': 'error',
                    'message': 'No course recommendations found. Please generate development plan first.'
                })
            
            # Initialize development service
            dev_service = EmployeeDevelopmentService()
            
            # Send email
            logger.info("Attempting to send course recommendations via email...")
            result = dev_service.send_courses_to_email(candidate_profile, list(development_plans))
            
            logger.info(f"Email service result: {result}")
            
            if result.get('success'):
                logger.info(f"Email sent successfully to: {result.get('email')}")
                return JsonResponse({
                    'status': 'success',
                    'message': result['message'],
                    'email': result['email'],
                    'courses_count': result['courses_count']
                })
            else:
                logger.error(f"Email sending failed: {result.get('error')}")
                return JsonResponse({
                    'status': 'error',
                    'message': f"Failed to send email: {result.get('error', 'Unknown error occurred')}"
                })
            
        except (UserProfile.DoesNotExist, CandidateProfile.DoesNotExist) as e:
            logger.error(f"Profile not found for user {request.user.username}: {str(e)}")
            return JsonResponse({'status': 'error', 'message': 'Profile not found. Please complete your profile setup.'})
        except Exception as e:
            logger.error(f"Unexpected error in send_courses_email: {str(e)}", exc_info=True)
            return JsonResponse({'status': 'error', 'message': f'Email sending failed: {str(e)}'})
    
    return JsonResponse({'status': 'error', 'message': 'Invalid request method'})
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

# Admin Dashboard Views
@login_required
def admin_dashboard(request):
    """Admin dashboard showing all employees"""
    from django.core.paginator import Paginator
    
    # Check if user is admin
    if not request.user.is_staff and not (hasattr(request.user, 'userprofile') and request.user.userprofile.role == 'admin'):
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
        employees = employees.filter(is_active=True, userprofile__candidateprofile__resume_processed=True)
    elif status_filter == 'inactive':
        employees = employees.filter(is_active=False)
    elif status_filter == 'processing':
        employees = employees.filter(userprofile__candidateprofile__resume_processed=False)
    
    # Filter by role if provided
    role_filter = request.GET.get('role', '')
    if role_filter:
        employees = employees.filter(userprofile__role=role_filter)
    
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
        'total_employees': total_employees,
        'active_employees': active_employees,
        'completed_profiles': completed_profiles,
        'pending_processing': pending_processing,
        'search_query': search_query,
        'status_filter': status_filter,
        'role_filter': role_filter,
    }
    
    return render(request, 'admin/dashboard.html', context)

@login_required
def admin_employee_detail(request, employee_id):
    """Admin view for detailed employee information"""
    # Check if user is admin
    if not request.user.is_staff and not (hasattr(request.user, 'userprofile') and request.user.userprofile.user_type == 'admin'):
        messages.error(request, "Access denied. Admin privileges required.")
        return redirect('candidate_dashboard')
    
    try:
        employee = User.objects.select_related('userprofile').get(id=employee_id)
        
        # Get candidate profile if exists
        candidate_profile = None
        try:
            if hasattr(employee, 'userprofile') and hasattr(employee.userprofile, 'candidateprofile'):
                candidate_profile = employee.userprofile.candidateprofile
        except AttributeError:
            candidate_profile = None
        
        # Get development plans
        development_plans = []
        if candidate_profile:
            try:
                development_plans = EmployeeDevelopmentPlan.objects.filter(
                    employee_profile=candidate_profile
                ).select_related('course').order_by('-created_at')[:5]
            except Exception as e:
                logger.error(f"Error fetching development plans: {str(e)}")
        
        # Get course assignments
        course_assignments = []
        try:
            course_assignments = CourseAssignment.objects.filter(
                user=employee
            ).select_related('course').order_by('-assigned_at')[:5]
        except Exception as e:
            logger.error(f"Error fetching course assignments: {str(e)}")
        
        # Get feedback history for this employee
        feedback_history = []
        try:
            feedback_history = ManagerFeedback.objects.filter(
                employee=employee
            ).select_related('manager').order_by('-created_at')
        except Exception as e:
            logger.error(f"Error fetching feedback history: {str(e)}")
        
        context = {
            'employee': employee,
            'candidate_profile': candidate_profile,
            'development_plans': development_plans,
            'course_assignments': course_assignments,
            'feedback_history': feedback_history,
        }
        
        return render(request, 'admin/employee_detail.html', context)
        
    except User.DoesNotExist:
        messages.error(request, f"Employee with ID {employee_id} not found.")
        return redirect('admin_dashboard')
    except Exception as e:
        logger.error(f"Employee detail error: {str(e)}")
        messages.error(request, "An error occurred while loading employee details.")
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
