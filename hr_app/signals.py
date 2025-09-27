from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import CandidateProfile
from .development_service import EmployeeDevelopmentService

@receiver(post_save, sender=CandidateProfile)
def auto_generate_development_plan(sender, instance, created, **kwargs):
    # Only run if profile is newly created and has all required details
    required_fields = [
        instance.current_role,
        instance.experience_level,
        instance.primary_skills,
        instance.domain_experience,
        instance.strengths,
        instance.areas_for_improvement
    ]
    if created and all(required_fields):
        print(f"Auto-generating development plan for {instance.user_profile.user.username}")
        dev_service = EmployeeDevelopmentService()
        result = dev_service.create_development_plan(instance)
        print(f"Development plan result: {result}")