from django.db import models
from django.contrib.auth.models import User
from django.core.validators import FileExtensionValidator
import uuid

class EmployeeProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    department = models.CharField(max_length=100, blank=True)
    job_title = models.CharField(max_length=100, blank=True)
    experience_years = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - {self.job_title}"

class ResumeUpload(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resume_file = models.FileField(
        upload_to='resumes/',
        validators=[FileExtensionValidator(allowed_extensions=['pdf', 'doc', 'docx'])]
    )
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    processed = models.BooleanField(default=False)
    extracted_text = models.TextField(blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.original_filename}"

class SkillCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Skill Categories"

    def __str__(self):
        return self.name

class Skill(models.Model):
    name = models.CharField(max_length=100, unique=True)
    category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE)
    is_technical = models.BooleanField(default=True)
    
    def __str__(self):
        return self.name

class SkillAnalysis(models.Model):
    SKILL_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('expert', 'Expert'),
    ]
    
    resume_upload = models.ForeignKey(ResumeUpload, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    current_level = models.CharField(max_length=20, choices=SKILL_LEVELS)
    years_experience = models.IntegerField(default=0)
    confidence_score = models.FloatField(default=0.0)  # AI confidence in skill detection
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['resume_upload', 'skill']

    def __str__(self):
        return f"{self.skill.name} - {self.current_level}"

class SkillGap(models.Model):
    PRIORITY_LEVELS = [
        ('critical', 'Critical'),
        ('important', 'Important'),
        ('nice_to_have', 'Nice to Have'),
    ]
    
    resume_upload = models.ForeignKey(ResumeUpload, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    required_level = models.CharField(max_length=20, choices=SkillAnalysis.SKILL_LEVELS)
    current_level = models.CharField(max_length=20, choices=SkillAnalysis.SKILL_LEVELS, default='beginner')
    priority = models.CharField(max_length=20, choices=PRIORITY_LEVELS)
    job_role_context = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ['resume_upload', 'skill']

    def __str__(self):
        return f"{self.skill.name} Gap - {self.priority}"

class CourseProvider(models.Model):
    name = models.CharField(max_length=100, unique=True)
    website_url = models.URLField()
    api_endpoint = models.URLField(blank=True)
    is_free = models.BooleanField(default=False)
    logo_url = models.URLField(blank=True)
    
    def __str__(self):
        return self.name

class Course(models.Model):
    DIFFICULTY_LEVELS = [
        ('beginner', 'Beginner'),
        ('intermediate', 'Intermediate'),
        ('advanced', 'Advanced'),
        ('all_levels', 'All Levels'),
    ]
    
    COURSE_TYPES = [
        ('video', 'Video Course'),
        ('interactive', 'Interactive'),
        ('project_based', 'Project Based'),
        ('text', 'Text/Article'),
        ('mixed', 'Mixed Format'),
    ]
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    provider = models.ForeignKey(CourseProvider, on_delete=models.CASCADE)
    instructor_name = models.CharField(max_length=100, blank=True)
    course_url = models.URLField()
    thumbnail_url = models.URLField(blank=True)
    duration_hours = models.IntegerField(default=0)
    difficulty_level = models.CharField(max_length=20, choices=DIFFICULTY_LEVELS)
    course_type = models.CharField(max_length=20, choices=COURSE_TYPES)
    price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    is_free = models.BooleanField(default=False)
    rating = models.FloatField(default=0.0)
    total_students = models.IntegerField(default=0)
    skills = models.ManyToManyField(Skill)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.title} - {self.provider.name}"

class CourseRecommendation(models.Model):
    resume_upload = models.ForeignKey(ResumeUpload, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    skill_gap = models.ForeignKey(SkillGap, on_delete=models.CASCADE)
    relevance_score = models.FloatField(default=0.0)
    recommended_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['recommended_order', '-relevance_score']

    def __str__(self):
        return f"{self.course.title} for {self.skill_gap.skill.name}"

class UserCourseInteraction(models.Model):
    STATUS_CHOICES = [
        ('interested', 'Interested'),
        ('in_progress', 'In Progress'),
        ('completed', 'Completed'),
        ('bookmarked', 'Bookmarked'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    progress_percentage = models.IntegerField(default=0)
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ['user', 'course']

    def __str__(self):
        return f"{self.user.username} - {self.course.title} ({self.status})"

class LearningPath(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    resume_upload = models.ForeignKey(ResumeUpload, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    target_role = models.CharField(max_length=100, blank=True)
    estimated_completion_weeks = models.IntegerField(default=0)
    courses = models.ManyToManyField(Course, through='LearningPathCourse')
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.name} - {self.user.username}"

class LearningPathCourse(models.Model):
    learning_path = models.ForeignKey(LearningPath, on_delete=models.CASCADE)
    course = models.ForeignKey(Course, on_delete=models.CASCADE)
    order = models.IntegerField(default=0)
    is_prerequisite = models.BooleanField(default=False)
    estimated_weeks = models.IntegerField(default=1)

    class Meta:
        ordering = ['order']
        unique_together = ['learning_path', 'course']