from django import forms
from django.contrib.auth.models import User
from django.core.validators import RegexValidator, FileExtensionValidator
from django.core.exceptions import ValidationError
from .models import UserProfile, AdminProfile
import re

class LoginForm(forms.Form):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

class SignupForm(forms.Form):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter username',
            'id': 'id_username'
        }),
        help_text='Username must be unique'
    )
    
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter email address'
        }),
        validators=[RegexValidator(
            regex=r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$',
            message='Please enter a valid email address'
        )]
    )
    
    country_code = forms.ChoiceField(
        choices=UserProfile.COUNTRY_CODES,
        initial='+91',
        widget=forms.Select(attrs={
            'class': 'form-control country-code-select'
        })
    )
    
    mobile_number = forms.CharField(
        max_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter 10-digit mobile number',
            'pattern': '[0-9]{10}',
            'maxlength': '10'
        }),
        validators=[RegexValidator(
            regex=r'^\d{10}$',
            message='Mobile number must be exactly 10 digits'
        )]
    )
    
    resume = forms.FileField(
        required=True,  # Now required since all users are candidates
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.pdf,.doc,.docx'
        }),
        validators=[FileExtensionValidator(
            allowed_extensions=['pdf', 'doc', 'docx'],
            message='Only PDF and Word documents are allowed'
        )],
        help_text='Upload your resume (PDF or Word format, max 5MB)'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter password',
            'id': 'id_password'
        }),
        help_text='Password must be at least 8 characters with uppercase, lowercase, number and special character'
    )
    
    confirm_password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Confirm password'
        })
    )
    
    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise ValidationError('This username is already taken. Please choose a different one.')
        return username
    
    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise ValidationError('This email is already registered. Please use a different email.')
        return email
    
    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise ValidationError('Password must be at least 8 characters long.')
        
        if not re.search(r'[A-Z]', password):
            raise ValidationError('Password must contain at least one uppercase letter.')
        
        if not re.search(r'[a-z]', password):
            raise ValidationError('Password must contain at least one lowercase letter.')
        
        if not re.search(r'\d', password):
            raise ValidationError('Password must contain at least one number.')
        
        if not re.search(r'[!@#$%^&*()_+\-=\[\]{};:"\\|,.<>\?]', password):
            raise ValidationError('Password must contain at least one special character.')
        
        return password
    
    def clean_confirm_password(self):
        password = self.cleaned_data.get('password')
        confirm_password = self.cleaned_data.get('confirm_password')
        
        if password and confirm_password and password != confirm_password:
            raise ValidationError('Passwords do not match.')
        
        return confirm_password
    
    def clean_resume(self):
        resume = self.cleaned_data.get('resume')
        
        if resume and resume.size > 5 * 1024 * 1024:  # 5MB limit
            raise ValidationError('File size must be less than 5MB.')
        return resume

class AdminProfileForm(forms.ModelForm):
    """Form for editing admin profile information"""
    
    # Include User model fields
    first_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter last name'
        })
    )
    
    email = forms.EmailField(
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter primary email'
        })
    )
    
    # UserProfile fields
    mobile_number = forms.CharField(
        max_length=10,
        validators=[RegexValidator(
            regex=r'^\d{10}$',
            message='Mobile number must be exactly 10 digits'
        )],
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter mobile number'
        })
    )
    
    country_code = forms.ChoiceField(
        choices=UserProfile.COUNTRY_CODES,
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    class Meta:
        model = AdminProfile
        fields = [
            'profile_picture', 'job_title', 'department', 'location',
            'alternative_email', 'office_phone', 'linkedin_url', 
            'twitter_url', 'facebook_url', 'bio', 'years_experience'
        ]
        
        widgets = {
            'profile_picture': forms.FileInput(attrs={
                'class': 'form-control',
                'accept': 'image/*'
            }),
            'job_title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., HR Director, Chief People Officer'
            }),
            'department': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Human Resources, Administration'
            }),
            'location': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., New York, NY or Mumbai Office'
            }),
            'alternative_email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Alternative email address'
            }),
            'office_phone': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Office phone number'
            }),
            'linkedin_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://linkedin.com/in/yourprofile'
            }),
            'twitter_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://twitter.com/yourusername'
            }),
            'facebook_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://facebook.com/yourprofile'
            }),
            'bio': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Tell us about your professional background and expertise...'
            }),
            'years_experience': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0',
                'max': '50'
            })
        }
    
    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        if user:
            self.fields['first_name'].initial = user.first_name
            self.fields['last_name'].initial = user.last_name
            self.fields['email'].initial = user.email
            
            try:
                user_profile = UserProfile.objects.get(user=user)
                self.fields['mobile_number'].initial = user_profile.mobile_number
                self.fields['country_code'].initial = user_profile.country_code
            except UserProfile.DoesNotExist:
                pass
    
    def clean_profile_picture(self):
        picture = self.cleaned_data.get('profile_picture')
        if picture:
            if picture.size > 5 * 1024 * 1024:  # 5MB limit
                raise ValidationError('Image file too large. Please upload an image smaller than 5MB.')
        return picture
