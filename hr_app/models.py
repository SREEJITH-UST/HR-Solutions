from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, MaxValueValidator

class Employee(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    employee_id = models.CharField(max_length=10, unique=True)
    department = models.CharField(max_length=100)
    position = models.CharField(max_length=100)
    skills = models.JSONField(default=list)  # List of skills with proficiency levels
    experience_years = models.FloatField(validators=[MinValueValidator(0)])
    availability_start = models.DateField()
    availability_end = models.DateField(null=True, blank=True)
    current_project = models.ForeignKey('Project', on_delete=models.SET_NULL, null=True, blank=True, related_name='current_team')
    skill_vector = models.JSONField(null=True, blank=True)  # Store skill embeddings

    def __str__(self):
        return f"{self.user.get_full_name()} ({self.employee_id})"

class Project(models.Model):
    STATUS_CHOICES = [
        ('PLANNING', 'Planning'),
        ('IN_PROGRESS', 'In Progress'),
        ('COMPLETED', 'Completed'),
        ('ON_HOLD', 'On Hold')
    ]

    title = models.CharField(max_length=200)
    description = models.TextField()
    required_skills = models.JSONField()  # List of required skills with minimum proficiency
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PLANNING')
    manager = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name='managed_projects')
    skill_vector = models.JSONField(null=True, blank=True)  # Store skill requirement embeddings
    team_size = models.IntegerField(validators=[MinValueValidator(1)])
    priority = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])

    def __str__(self):
        return self.title

class ResourceMatch(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE)
    match_score = models.FloatField()  # Cosine similarity score
    skills_match_percentage = models.FloatField()  # Percentage of required skills matched
    availability_match = models.BooleanField()  # Whether employee is available during project duration
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=[
        ('SUGGESTED', 'Suggested'),
        ('ACCEPTED', 'Accepted'),
        ('REJECTED', 'Rejected'),
        ('COMPLETED', 'Completed')
    ], default='SUGGESTED')

    class Meta:
        unique_together = ['project', 'employee']
        ordering = ['-match_score']

    def __str__(self):
        return f"{self.employee} - {self.project} ({self.match_score:.2f})"

class MatchFeedback(models.Model):
    resource_match = models.ForeignKey(ResourceMatch, on_delete=models.CASCADE)
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    feedback_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(Employee, on_delete=models.CASCADE)

    def __str__(self):
        return f"Feedback for {self.resource_match} by {self.created_by}"
