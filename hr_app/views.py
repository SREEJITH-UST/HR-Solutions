from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from .forms import LoginForm, SignupForm, ProjectForm, MatchFeedbackForm
from .models import Employee, Project, ResourceMatch, MatchFeedback
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import json
from sentence_transformers import SentenceTransformer
import os
import ssl

# Create unverified SSL context to handle certificate issues
ssl._create_default_https_context = ssl._create_unverified_context

# Lazy loading of the model
_model = None

def get_model():
    global _model
    if _model is None:
        try:
            _model = SentenceTransformer('all-MiniLM-L6-v2')
        except Exception as e:
            print(f"Warning: Could not load sentence transformer model: {e}")
            # Return a simple fallback that just returns a list of zeros
            class FallbackModel:
                def encode(self, texts, **kwargs):
                    return [[0.0] * 384]  # MiniLM-L6 has 384 dimensions
            _model = FallbackModel()
    return _model

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
            signup_form = SignupForm(request.POST)
            if signup_form.is_valid():
                user = signup_form.save(commit=False)
                user.set_password(signup_form.cleaned_data['password'])
                user.save()
                return redirect('home')
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
        signup_form = SignupForm(request.POST)
        if signup_form.is_valid():
            try:
                # Create and save the User instance
                user = signup_form.save(commit=False)
                user.set_password(signup_form.cleaned_data['password'])
                user.save()

                # Create and save the Employee instance
                employee = Employee.objects.create(
                    user=user,
                    employee_id=signup_form.cleaned_data['employee_id'],
                    department=signup_form.cleaned_data['department'],
                    position=signup_form.cleaned_data['position'],
                    skills=signup_form.cleaned_data.get('skills', []),
                    experience_years=signup_form.cleaned_data['experience_years'],
                    availability_start=signup_form.cleaned_data['availability_start'],
                    availability_end=signup_form.cleaned_data.get('availability_end')
                )

                # If skills are provided, generate and save skill vector
                if employee.skills:
                    employee.skill_vector = generate_skill_embedding(employee.skills)
                    employee.save()

                return redirect('home')
            except Exception as e:
                signup_error = f"Signup failed. Error: {str(e)}"
                # If user was created but employee creation failed, delete the user
                if 'user' in locals():
                    user.delete()
        else:
            signup_error = "Signup failed. Please check the details."
            
    return render(request, 'accounts/signup.html', {
        'signup_form': signup_form,
        'signup_error': signup_error,
    })

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

def home(request):
    return HttpResponse("Welcome to the HR Solutions Home Page!")

def generate_skill_embedding(skills_data):
    """Generate embeddings for skills data"""
    # Convert skills data to text representation
    skills_text = " ".join([f"{item['skill']} {item.get('proficiency', '')} {item.get('min_proficiency', '')}"
                           for item in skills_data])
    # Generate embedding
    model = get_model()
    return model.encode([skills_text])[0].tolist()

@login_required
def dashboard_view(request):
    if not hasattr(request.user, 'employee'):
        return redirect('home')
    
    context = {
        'managed_projects': Project.objects.filter(manager=request.user.employee),
        'current_project': request.user.employee.current_project,
        'pending_matches': ResourceMatch.objects.filter(
            employee=request.user.employee,
            status='SUGGESTED'
        )
    }
    
    return render(request, 'dashboard.html', context)

@login_required
def create_project_view(request):
    if request.method == 'POST':
        form = ProjectForm(request.POST)
        if form.is_valid():
            project = form.save(commit=False)
            project.manager = request.user.employee
            project.status = 'PLANNING'
            
            # Generate and store skill embeddings
            project.skill_vector = generate_skill_embedding(project.required_skills)
            project.save()
            
            # Find matching resources
            find_matching_resources(project)
            
            return redirect('view_project', project_id=project.id)
    else:
        form = ProjectForm()
    
    return render(request, 'resource_mapping/create_project.html', {'form': form})

def find_matching_resources(project):
    """Find matching resources for a project based on skills and availability"""
    # Get all employees
    employees = Employee.objects.exclude(
        Q(current_project__isnull=False) |
        Q(availability_end__lt=project.start_date) |
        Q(availability_start__gt=project.end_date)
    )

    # Calculate matches for each employee
    for employee in employees:
        # Calculate skill match percentage
        required_skills = {skill['skill']: skill['min_proficiency'] 
                         for skill in project.required_skills}
        employee_skills = {skill['skill']: skill['proficiency'] 
                         for skill in employee.skills}
        
        matched_skills = 0
        for skill, min_prof in required_skills.items():
            if skill in employee_skills and employee_skills[skill] >= min_prof:
                matched_skills += 1
        
        skills_match_percentage = (matched_skills / len(required_skills)) * 100 if required_skills else 0
        
        # Calculate cosine similarity if skill vectors exist
        if project.skill_vector and employee.skill_vector:
            match_score = float(cosine_similarity(
                [project.skill_vector], 
                [employee.skill_vector]
            )[0][0])
        else:
            match_score = skills_match_percentage / 100

        # Create or update resource match
        ResourceMatch.objects.update_or_create(
            project=project,
            employee=employee,
            defaults={
                'match_score': match_score,
                'skills_match_percentage': skills_match_percentage,
                'availability_match': True
            }
        )

@login_required
def view_project_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    matches = ResourceMatch.objects.filter(project=project).order_by('-match_score')
    
    return render(request, 'resource_mapping/view_project.html', {
        'project': project,
        'matches': matches
    })

@login_required
def update_match_status(request, match_id):
    if request.method == 'POST':
        match = get_object_or_404(ResourceMatch, id=match_id)
        new_status = request.POST.get('status')
        
        if new_status in ['ACCEPTED', 'REJECTED', 'COMPLETED']:
            match.status = new_status
            if new_status == 'ACCEPTED':
                # Update employee's current project
                match.employee.current_project = match.project
                match.employee.save()
            match.save()
            
            return JsonResponse({'status': 'success'})
    
    return JsonResponse({'error': 'Invalid request'}, status=400)

@login_required
def submit_feedback_view(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    if request.method == 'POST':
        form = MatchFeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.project = project
            feedback.created_by = request.user.employee
            feedback.save()
            return redirect('view_project', project_id=project.id)
    else:
        form = MatchFeedbackForm()
    
    return render(request, 'feedback/submit.html', {
        'form': form,
        'project': project
    })

@login_required
def submit_recommendations_view(request):
    # Get all feedback for analysis
    feedbacks = MatchFeedback.objects.all().order_by('-created_at')
    
    # In a real application, you would use AI/ML here to generate recommendations
    recommendations = [
        "Based on recent project feedback, consider emphasizing technical skills assessment",
        "Communication skills are frequently mentioned in feedback - consider adding specific evaluation",
        "Project success rate increases with longer skill-matching periods"
    ]
    
    return render(request, 'feedback/recommendations.html', {
        'feedbacks': feedbacks,
        'recommendations': recommendations
    })

@login_required
def submit_match_feedback(request, match_id):
    match = get_object_or_404(ResourceMatch, id=match_id)
    
    if request.method == 'POST':
        form = MatchFeedbackForm(request.POST)
        if form.is_valid():
            feedback = form.save(commit=False)
            feedback.resource_match = match
            feedback.created_by = request.user.employee
            feedback.save()
            
            return redirect('view_project', project_id=match.project.id)
    else:
        form = MatchFeedbackForm()
    
    return render(request, 'resource_mapping/submit_feedback.html', {
        'form': form,
        'match': match
    })


