from django.contrib import admin
from .models import UserProfile, CandidateProfile, LearningCourse, EmployeeDevelopmentPlan

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'user_type', 'mobile_number', 'profile_created_at']
    list_filter = ['user_type', 'profile_created_at']
    search_fields = ['user__username', 'user__email', 'mobile_number']
    readonly_fields = ['profile_created_at']

@admin.register(CandidateProfile)
class CandidateProfileAdmin(admin.ModelAdmin):
    list_display = ['user_profile', 'resume_score', 'resume_processed', 'processing_status', 'created_at']
    list_filter = ['resume_processed', 'processing_status', 'created_at']
    search_fields = ['user_profile__user__username', 'user_profile__user__email']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Basic Info', {
            'fields': ('user_profile', 'resume_file', 'resume_processed')
        }),
        ('Resume Analysis', {
            'fields': ('resume_score', 'resume_summary', 'primary_skills', 'secondary_skills', 'domain_experience')
        }),
        ('Education & Certifications', {
            'fields': ('education_details', 'certifications')
        }),
        ('AI Analysis', {
            'fields': ('strengths', 'areas_for_improvement')
        }),
        ('Processing Status', {
            'fields': ('processing_status', 'processing_error')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(LearningCourse)
class LearningCourseAdmin(admin.ModelAdmin):
    list_display = ['title', 'provider', 'skill_category', 'difficulty_level', 'rating', 'price', 'created_at']
    list_filter = ['provider', 'skill_category', 'difficulty_level', 'created_at']
    search_fields = ['title', 'description', 'skills_covered']
    readonly_fields = ['created_at', 'updated_at']

@admin.register(EmployeeDevelopmentPlan)
class EmployeeDevelopmentPlanAdmin(admin.ModelAdmin):
    list_display = ['employee_profile', 'course', 'status', 'priority_level', 'progress_percentage', 'created_at']
    list_filter = ['status', 'priority_level', 'current_skill_level', 'target_skill_level', 'created_at']
    search_fields = ['employee_profile__user_profile__user__username', 'course__title', 'skill_gap_identified']
    readonly_fields = ['created_at', 'updated_at']