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
from hr_app.views import (
    send_notification_email, login_view, signup_view, forgot_password_view,
    dashboard_view, create_project_view, submit_feedback_view, view_project_view,
    submit_recommendations_view
)

urlpatterns = [
    path('admin/', admin.site.urls),
    path('test-email/', send_notification_email, name='test_email'),
    path('', login_view, name='home'),
    path('signup/', signup_view, name='signup'),
    path('forgot-password/', forgot_password_view, name='forgot_password'),
    path('dashboard/', dashboard_view, name='dashboard'),
    path('project/create/', create_project_view, name='create_project'),
    path('project/view/<int:project_id>/', view_project_view, name='view_project'),
    path('feedback/submit/<int:project_id>/', submit_feedback_view, name='submit_feedback'),
    path('feedback/recommendations/', submit_recommendations_view, name='recommendations'),
]
