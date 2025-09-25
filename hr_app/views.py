from django.shortcuts import render, redirect
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.utils import timezone
from .forms import LoginForm, SignupForm
from .models import UserProfile, CandidateProfile, LearningCourse, EmployeeDevelopmentPlan
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
