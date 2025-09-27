from django.contrib.auth.models import User
from hr_app.models import UserProfile

user = User.objects.get(username="your_username")
user.is_staff = True
user.is_superuser = True  # Optional: gives full admin rights
user.save()

profile = UserProfile.objects.get(user=user)
profile.user_type = "admin"
profile.save()