from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from hr_app.views import (
    # Your existing views
    send_notification_email, login_view, signup_view, forgot_password_view,
    # NEW: Professional development views
    professional_development, upload_resume, analyze_resume, 
    generate_recommendations, get_analysis_results, update_course_status
)

urlpatterns = [
    # KEEP: Your existing URLs
    path('admin/', admin.site.urls),
    path('test-email/', send_notification_email, name='test_email'),
    path('', login_view, name='login'),
    path('signup/', signup_view, name='signup'),
    path('forgot-password/', forgot_password_view, name='forgot_password'),
    
    # NEW: Professional Development URLs
    path('professional-development/', professional_development, name='professional_development'),
    path('professional-development/upload-resume/', upload_resume, name='upload_resume'),
    path('professional-development/analyze-resume/', analyze_resume, name='analyze_resume'),
    path('professional-development/generate-recommendations/', generate_recommendations, name='generate_recommendations'),
    path('professional-development/analysis/<uuid:upload_id>/', get_analysis_results, name='analysis_results'),
    path('professional-development/update-course-status/', update_course_status, name='update_course_status'),
]

# NEW: Serve media files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)