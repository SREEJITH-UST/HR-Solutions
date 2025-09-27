"""
Session management middleware for HR Solutions
Handles single-session-per-user enforcement and session timeout management
"""

from django.contrib.auth import logout
from django.contrib.sessions.models import Session
from django.utils import timezone
from django.shortcuts import redirect
from django.urls import reverse
import json
from datetime import datetime, timedelta


class SessionManagementMiddleware:
    """Middleware to handle session management and security"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Process the request before the view
        self.process_request(request)
        
        response = self.get_response(request)
        
        # Process the response after the view
        return self.process_response(request, response)
    
    def process_request(self, request):
        """Process incoming request for session validation"""
        
        # Skip processing for certain URLs
        exempt_urls = [
            reverse('login'),
            '/admin/',
            '/static/',
            '/media/'
        ]
        
        if any(request.path.startswith(url) for url in exempt_urls):
            return None
        
        # Check if user is authenticated
        if request.user.is_authenticated:
            # Update last activity timestamp
            request.session['last_activity'] = timezone.now().isoformat()
            
            # Check for session timeout (1 hour default)
            last_activity = request.session.get('last_activity')
            if last_activity:
                try:
                    last_activity_time = datetime.fromisoformat(last_activity.replace('Z', '+00:00'))
                    if timezone.now() - last_activity_time > timedelta(hours=1):
                        logout(request)
                        return redirect('login')
                except (ValueError, TypeError):
                    # Invalid timestamp, logout for security
                    logout(request)
                    return redirect('login')
            
            # Validate that this is the only active session for the user
            current_session_key = request.session.session_key
            if current_session_key:
                user_sessions = Session.objects.filter(
                    expire_date__gte=timezone.now()
                ).exclude(session_key=current_session_key)
                
                # Check if any other sessions belong to the same user
                for session in user_sessions:
                    try:
                        session_data = session.get_decoded()
                        session_user_id = session_data.get('_auth_user_id')
                        if session_user_id == str(request.user.id):
                            # Another session exists for this user, logout current session
                            logout(request)
                            return redirect('login')
                    except (KeyError, ValueError, TypeError):
                        # Invalid session data, delete it
                        session.delete()
        
        return None
    
    def process_response(self, request, response):
        """Process outgoing response"""
        
        # Add security headers for authenticated users
        if request.user.is_authenticated:
            response['X-Frame-Options'] = 'DENY'
            response['X-Content-Type-Options'] = 'nosniff'
            response['X-XSS-Protection'] = '1; mode=block'
            
            # Prevent caching of sensitive pages
            if request.path != '/login/':
                response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
                response['Pragma'] = 'no-cache'
                response['Expires'] = '0'
        
        return response


class SessionCleanupMiddleware:
    """Middleware to clean up expired sessions"""
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # Clean expired sessions periodically (every 100 requests)
        import random
        if random.randint(1, 100) == 1:  # 1% chance
            self.cleanup_expired_sessions()
        
        response = self.get_response(request)
        return response
    
    def cleanup_expired_sessions(self):
        """Remove expired sessions from database"""
        try:
            expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
            expired_count = expired_sessions.count()
            if expired_count > 0:
                expired_sessions.delete()
                print(f"Cleaned up {expired_count} expired sessions")
        except Exception as e:
            print(f"Error cleaning expired sessions: {e}")