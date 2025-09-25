"""
URL configuration for hr_solution project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.shortcuts import render
from hr_app.views import (
    send_notification_email, login_view, signup_view, forgot_password_view, 
    check_username_availability, dashboard_view, check_processing_status,
    candidate_dashboard, manager_dashboard, admin_dashboard, reprocess_resume, upload_resume,
    generate_development_plan, enroll_course, update_course_progress, custom_logout
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('test-email/', send_notification_email, name='test_email'),
    path('', login_view, name='home'),
    path('signup/', signup_view, name='signup'),
    path('forgot-password/', forgot_password_view, name='forgot_password'),
    path('check-username/', check_username_availability, name='check_username'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('candidate-dashboard/', candidate_dashboard, name='candidate_dashboard'),
    path('manager-dashboard/', manager_dashboard, name='manager_dashboard'),
    path('admin-dashboard/', admin_dashboard, name='admin_dashboard'),
    path('check-processing-status/', check_processing_status, name='check_processing_status'),
    path('reprocess-resume/', reprocess_resume, name='reprocess_resume'),
    path('upload-resume/', upload_resume, name='upload_resume'),
    path('processing/', lambda request: render(request, 'processing.html'), name='processing'),
    # Employee Development URLs
    path('generate-development-plan/', generate_development_plan, name='generate_development_plan'),
    path('enroll-course/<int:plan_id>/', enroll_course, name='enroll_course'),
    path('update-course-progress/<int:plan_id>/', update_course_progress, name='update_course_progress'),
    path('logout/', custom_logout, name='logout'),
    path('login/', login_view, name='login'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0] if settings.STATICFILES_DIRS else '')
