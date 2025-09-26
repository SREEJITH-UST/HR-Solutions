from django import forms
from django.contrib.auth.models import User
from .models import Project, Employee, ResourceMatch, MatchFeedback

class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

class SignupForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput)
    employee_id = forms.CharField(max_length=10)
    department = forms.CharField(max_length=100)
    position = forms.CharField(max_length=100)
    skills = forms.JSONField(required=False, widget=forms.Textarea(attrs={
        'placeholder': 'Enter skills as JSON array: [{"skill": "Python", "proficiency": 4}, ...]'
    }))
    experience_years = forms.FloatField(min_value=0)
    availability_start = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    availability_end = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}), required=False)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name']
        help_texts = {
            'username': None,
        }

class ProjectForm(forms.ModelForm):
    required_skills = forms.JSONField(widget=forms.Textarea(attrs={
        'placeholder': 'Enter required skills as JSON array: [{"skill": "Python", "min_proficiency": 3}, ...]'
    }))
    start_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))
    end_date = forms.DateField(widget=forms.DateInput(attrs={'type': 'date'}))

    class Meta:
        model = Project
        fields = ['title', 'description', 'required_skills', 'start_date', 
                 'end_date', 'team_size', 'priority']

class MatchFeedbackForm(forms.ModelForm):
    class Meta:
        model = MatchFeedback
        fields = ['rating', 'feedback_text']
        widgets = {
            'feedback_text': forms.Textarea(attrs={'rows': 4}),
        }
