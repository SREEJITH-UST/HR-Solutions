from django.core.management.base import BaseCommand
from django.core.mail import send_mail
from django.conf import settings
import socket

class Command(BaseCommand):
    help = 'Test email configuration and connectivity'

    def add_arguments(self, parser):
        parser.add_argument(
            '--email',
            type=str,
            help='Email address to send test email to',
            default='test@example.com'
        )

    def handle(self, *args, **options):
        test_email = options['email']
        
        self.stdout.write('Testing email configuration...')
        
        # Check configuration
        if not settings.EMAIL_HOST_USER:
            self.stdout.write(
                self.style.ERROR('EMAIL_HOST_USER is not configured')
            )
            return
            
        if not settings.EMAIL_HOST_PASSWORD:
            self.stdout.write(
                self.style.ERROR('EMAIL_HOST_PASSWORD is not configured')
            )
            return
            
        self.stdout.write(f'Email Host: {settings.EMAIL_HOST}')
        self.stdout.write(f'Email Port: {settings.EMAIL_PORT}')
        self.stdout.write(f'Email User: {settings.EMAIL_HOST_USER}')
        self.stdout.write(f'Use TLS: {settings.EMAIL_USE_TLS}')
        
        # Test connection
        try:
            self.stdout.write('Testing email server connection...')
            
            # Set socket timeout
            old_timeout = socket.getdefaulttimeout()
            socket.setdefaulttimeout(30)
            
            result = send_mail(
                subject='Test Email from NextGenHR',
                message='This is a test email to verify email configuration.',
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[test_email],
                fail_silently=False,
            )
            
            # Restore timeout
            socket.setdefaulttimeout(old_timeout)
            
            if result == 1:
                self.stdout.write(
                    self.style.SUCCESS(f'Email sent successfully to {test_email}!')
                )
            else:
                self.stdout.write(
                    self.style.ERROR(f'Email sending failed. Result: {result}')
                )
                
        except Exception as e:
            # Restore timeout
            if 'old_timeout' in locals():
                socket.setdefaulttimeout(old_timeout)
                
            self.stdout.write(
                self.style.ERROR(f'Email sending failed with error: {str(e)}')
            )
            
            # Provide troubleshooting suggestions
            if 'timeout' in str(e).lower() or 'handshake' in str(e).lower():
                self.stdout.write('\nTroubleshooting suggestions for timeout/SSL errors:')
                self.stdout.write('1. Check your internet connection')
                self.stdout.write('2. Verify Gmail App Password is correct')
                self.stdout.write('3. Try using port 465 with SSL instead of 587 with TLS')
                self.stdout.write('4. Check if your firewall is blocking the connection')
                self.stdout.write('5. Try running this from a different network')
