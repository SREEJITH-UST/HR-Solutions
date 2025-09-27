"""
Management command to clean up expired sessions and manage user sessions
"""

from django.core.management.base import BaseCommand
from django.contrib.sessions.models import Session
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
import json


class Command(BaseCommand):
    help = 'Manage user sessions - cleanup expired sessions and enforce single session per user'

    def add_arguments(self, parser):
        parser.add_argument(
            '--cleanup',
            action='store_true',
            help='Clean up expired sessions',
        )
        parser.add_argument(
            '--enforce-single',
            action='store_true',
            help='Enforce single session per user (logout all but most recent)',
        )
        parser.add_argument(
            '--list-active',
            action='store_true',
            help='List all active sessions',
        )
        parser.add_argument(
            '--user',
            type=str,
            help='Target specific user (username)',
        )

    def handle(self, *args, **options):
        if options['cleanup']:
            self.cleanup_expired_sessions()
        
        if options['enforce_single']:
            self.enforce_single_session(options.get('user'))
        
        if options['list_active']:
            self.list_active_sessions(options.get('user'))

    def cleanup_expired_sessions(self):
        """Remove expired sessions"""
        self.stdout.write(self.style.SUCCESS('Cleaning up expired sessions...'))
        
        expired_sessions = Session.objects.filter(expire_date__lt=timezone.now())
        count = expired_sessions.count()
        
        if count > 0:
            expired_sessions.delete()
            self.stdout.write(
                self.style.SUCCESS(f'Successfully cleaned up {count} expired sessions')
            )
        else:
            self.stdout.write('No expired sessions found')

    def enforce_single_session(self, username=None):
        """Enforce single session per user"""
        self.stdout.write(self.style.SUCCESS('Enforcing single session per user...'))
        
        # Get active sessions
        active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        
        # Group sessions by user
        user_sessions = {}
        sessions_to_delete = []
        
        for session in active_sessions:
            try:
                session_data = session.get_decoded()
                user_id = session_data.get('_auth_user_id')
                
                if user_id:
                    if username:
                        # Check if this is the target user
                        try:
                            user = User.objects.get(id=user_id)
                            if user.username != username:
                                continue
                        except User.DoesNotExist:
                            continue
                    
                    if user_id not in user_sessions:
                        user_sessions[user_id] = []
                    
                    user_sessions[user_id].append({
                        'session': session,
                        'last_activity': session_data.get('last_activity', session.expire_date.isoformat())
                    })
            except (KeyError, ValueError, TypeError):
                # Invalid session, mark for deletion
                sessions_to_delete.append(session)
        
        # Delete invalid sessions
        if sessions_to_delete:
            for session in sessions_to_delete:
                session.delete()
            self.stdout.write(f'Deleted {len(sessions_to_delete)} invalid sessions')
        
        # Keep only the most recent session for each user
        users_processed = 0
        sessions_deleted = 0
        
        for user_id, sessions in user_sessions.items():
            if len(sessions) > 1:
                # Sort by last activity (most recent first)
                sessions.sort(key=lambda x: x['last_activity'], reverse=True)
                
                # Delete all but the most recent session
                for session_info in sessions[1:]:
                    session_info['session'].delete()
                    sessions_deleted += 1
                
                users_processed += 1
        
        if users_processed > 0:
            self.stdout.write(
                self.style.SUCCESS(
                    f'Processed {users_processed} users, deleted {sessions_deleted} duplicate sessions'
                )
            )
        else:
            self.stdout.write('No duplicate sessions found')

    def list_active_sessions(self, username=None):
        """List active sessions"""
        self.stdout.write(self.style.SUCCESS('Active sessions:'))
        
        active_sessions = Session.objects.filter(expire_date__gte=timezone.now())
        
        if not active_sessions.exists():
            self.stdout.write('No active sessions found')
            return
        
        session_count = 0
        for session in active_sessions:
            try:
                session_data = session.get_decoded()
                user_id = session_data.get('_auth_user_id')
                
                if user_id:
                    try:
                        user = User.objects.get(id=user_id)
                        
                        if username and user.username != username:
                            continue
                        
                        last_activity = session_data.get('last_activity', 'Unknown')
                        
                        self.stdout.write(
                            f'User: {user.username} | Session: {session.session_key[:8]}... | '
                            f'Expires: {session.expire_date} | Last Activity: {last_activity}'
                        )
                        session_count += 1
                        
                    except User.DoesNotExist:
                        self.stdout.write(
                            f'Orphaned session: {session.session_key[:8]}... | '
                            f'User ID: {user_id} (user not found)'
                        )
                        session_count += 1
            except (KeyError, ValueError, TypeError):
                self.stdout.write(
                    f'Invalid session: {session.session_key[:8]}... | '
                    f'Expires: {session.expire_date}'
                )
                session_count += 1
        
        self.stdout.write(f'\nTotal active sessions: {session_count}')