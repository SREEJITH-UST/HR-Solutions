from django.db import models
from django.contrib.auth.models import User
from django.core.validators import RegexValidator
import json

class UserProfile(models.Model):
    USER_TYPES = [
        ('candidate', 'Candidate'),
        ('manager', 'Manager'),
        ('admin', 'Admin'),
    ]
    
    COUNTRY_CODES = [
        ('+91', 'India (+91)'),
        ('+1', 'USA (+1)'),
        ('+44', 'UK (+44)'),
        ('+86', 'China (+86)'),
        ('+81', 'Japan (+81)'),
        ('+49', 'Germany (+49)'),
        ('+33', 'France (+33)'),
        ('+39', 'Italy (+39)'),
        ('+7', 'Russia (+7)'),
        ('+61', 'Australia (+61)'),
        ('+55', 'Brazil (+55)'),
        ('+52', 'Mexico (+52)'),
        ('+82', 'South Korea (+82)'),
        ('+65', 'Singapore (+65)'),
        ('+971', 'UAE (+971)'),
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default='candidate')
    country_code = models.CharField(max_length=5, choices=COUNTRY_CODES, default='+91')
    mobile_number = models.CharField(
        max_length=10,
        validators=[RegexValidator(
            regex=r'^\d{10}$',
            message='Mobile number must be exactly 10 digits'
        )]
    )
    resume = models.FileField(
        upload_to='resumes/',
        help_text='Upload your resume (PDF or Word format)',
        blank=False
    )
    profile_created_at = models.DateTimeField(auto_now_add=True)
    profile_updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user.username}'s Profile ({self.user_type})"

class CandidateProfile(models.Model):
    EXPERIENCE_LEVELS = [
        ('fresher', 'Fresher (0-1 years)'),
        ('junior', 'Junior (1-3 years)'),
        ('mid', 'Mid-level (3-5 years)'),
        ('senior', 'Senior (5-8 years)'),
        ('lead', 'Lead (8-12 years)'),
        ('principal', 'Principal (12+ years)'),
    ]
    
    user_profile = models.OneToOneField(UserProfile, on_delete=models.CASCADE)
    
    # AI-extracted information from resume
    total_experience_years = models.FloatField(default=0.0)
    total_experience_months = models.IntegerField(default=0)
    experience_level = models.CharField(max_length=20, choices=EXPERIENCE_LEVELS, default='fresher')
    
    # Skills and expertise
    primary_skills = models.JSONField(default=list, help_text='Primary technical skills')
    secondary_skills = models.JSONField(default=list, help_text='Secondary/supporting skills')
    soft_skills = models.JSONField(default=list, help_text='Communication, leadership, etc.')
    
    # Experience breakdown by domain
    domain_experience = models.JSONField(default=dict, help_text='Experience in different domains')
    
    # Education details
    education_details = models.JSONField(default=list, help_text='Education background')
    certifications = models.JSONField(default=list, help_text='Professional certifications')
    
    # Project details
    notable_projects = models.JSONField(default=list, help_text='Key projects and achievements')
    
    # Contact and location
    current_location = models.CharField(max_length=100, blank=True)
    preferred_locations = models.JSONField(default=list, help_text='Preferred work locations')
    
    # Career preferences
    current_role = models.CharField(max_length=100, blank=True)
    desired_roles = models.JSONField(default=list, help_text='Desired job roles')
    current_salary = models.CharField(max_length=50, blank=True)
    expected_salary = models.CharField(max_length=50, blank=True)
    
    # AI analysis results
    resume_summary = models.TextField(blank=True, help_text='AI-generated resume summary')
    strengths = models.JSONField(default=list, help_text='Identified strengths')
    areas_for_improvement = models.JSONField(default=list, help_text='Areas for development')
    resume_score = models.IntegerField(default=0, help_text='Resume quality score (0-100)')
    
    # Processing status
    resume_processed = models.BooleanField(default=False)
    processing_status = models.CharField(max_length=50, default='pending')
    processing_error = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.user_profile.user.username}'s Employee Profile"


class LearningCourse(models.Model):
    """Model for storing course recommendations"""
    COURSE_PROVIDERS = [
        ('udemy', 'Udemy'),
        ('coursera', 'Coursera'),
        ('linkedin', 'LinkedIn Learning'),
        ('pluralsight', 'Pluralsight'),
        ('internal', 'Internal Training'),
    ]
    
    SKILL_CATEGORIES = [
        ('frontend', 'Frontend Development'),
        ('backend', 'Backend Development'),
        ('fullstack', 'Full Stack Development'),
        ('mobile', 'Mobile Development'),
        ('devops', 'DevOps & Infrastructure'),
        ('data_science', 'Data Science & Analytics'),
        ('ai_ml', 'AI & Machine Learning'),
        ('cloud', 'Cloud Computing'),
        ('security', 'Cybersecurity'),
        ('project_management', 'Project Management'),
        ('soft_skills', 'Soft Skills & Leadership'),
    ]
    
    title = models.CharField(max_length=200)
    description = models.TextField()
    provider = models.CharField(max_length=20, choices=COURSE_PROVIDERS, default='udemy')
    course_url = models.URLField()
    skill_category = models.CharField(max_length=30, choices=SKILL_CATEGORIES)
    difficulty_level = models.CharField(max_length=20, choices=[
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
    ])
    duration_hours = models.IntegerField(default=0)
    rating = models.FloatField(default=0.0)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    skills_covered = models.JSONField(default=list, help_text='List of specific skills covered')
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.provider}"


class EmployeeDevelopmentPlan(models.Model):
    """Model for tracking employee development and course assignments"""
    ASSIGNMENT_STATUS = [
        ('recommended', 'AI Recommended'),
        ('manager_assigned', 'Manager Assigned'),
        ('self_enrolled', 'Self Enrolled'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('paused', 'Paused'),
        ('cancelled', 'Cancelled'),
    ]
    
    employee_profile = models.ForeignKey(CandidateProfile, on_delete=models.CASCADE, related_name='development_plans')
    assigned_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='assigned_courses')
    course = models.ForeignKey(LearningCourse, on_delete=models.CASCADE)
    
    # AI Analysis
    skill_gap_identified = models.CharField(max_length=100)
    current_skill_level = models.CharField(max_length=20, choices=[
        ('novice', 'Novice'),
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ])
    target_skill_level = models.CharField(max_length=20, choices=[
        ('novice', 'Novice'),
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ])
    
    # Assignment details
    assignment_reason = models.TextField(help_text='AI-generated reason for recommendation')
    priority_level = models.CharField(max_length=20, choices=[
        ('low', 'Low Priority'),
        ('medium', 'Medium Priority'),
        ('high', 'High Priority'),
        ('critical', 'Critical'),
    ], default='medium')
    
    # Progress tracking
    status = models.CharField(max_length=20, choices=ASSIGNMENT_STATUS, default='recommended')
    progress_percentage = models.IntegerField(default=0)
    estimated_completion_date = models.DateField(null=True, blank=True)
    actual_completion_date = models.DateField(null=True, blank=True)
    
    # Feedback
    employee_feedback = models.TextField(blank=True)
    manager_notes = models.TextField(blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        unique_together = ['employee_profile', 'course']
    
    def __str__(self):
        return f"{self.employee_profile.user_profile.user.username} - {self.course.title}"
    
    def get_total_experience_display(self):
        if self.total_experience_years >= 1:
            return f"{self.total_experience_years:.1f} years"
        else:
            return f"{self.total_experience_months} months"

class TalentProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    skills = models.TextField()  # JSON or comma-separated skills
    feedback = models.TextField(blank=True, null=True)  # AI-analyzed feedback

    def __str__(self):
        return f"{self.user.username}'s Profile"

class ProjectRequirement(models.Model):
    project_name = models.CharField(max_length=255)
    required_skills = models.TextField()

    def __str__(self):
        return self.project_name

class InterviewSummary(models.Model):
    candidate = models.ForeignKey(User, on_delete=models.CASCADE)
    summary = models.TextField()  # AI-generated
    video_assessment = models.FileField(upload_to='assessments/', null=True, blank=True)  # For monitored tests

    def __str__(self):
        return f"Summary for {self.candidate.username}"
    
