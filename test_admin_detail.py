#!/usr/bin/env python
"""
Test script for admin dashboard employee detail functionality
"""
import os
import sys
import django
from django.conf import settings

# Add the project directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'hr_solution.settings')
django.setup()

from django.contrib.auth.models import User
from hr_app.models import UserProfile, CandidateProfile

def test_admin_dashboard_functionality():
    """Test the admin dashboard employee detail functionality"""
    print("🔍 Testing Admin Dashboard Employee Detail Functionality...")
    print("=" * 60)
    
    # Test 1: Check if we have users in the system
    print("\n📊 1. Checking Users in System:")
    users = User.objects.all()
    print(f"   Total users: {users.count()}")
    
    for user in users[:5]:  # Show first 5 users
        print(f"   - {user.username} ({user.email}) - {user.get_full_name()}")
        
        # Check if user has profile
        try:
            profile = user.userprofile
            print(f"     Profile: {profile.user_type}")
            
            # Check if candidate profile exists
            try:
                candidate = profile.candidateprofile
                print(f"     Candidate Profile: ✅ (Resume processed: {candidate.resume_processed})")
            except:
                print(f"     Candidate Profile: ❌")
        except:
            print(f"     Profile: ❌ No profile")
    
    # Test 2: Check URL patterns
    print(f"\n🔗 2. URL Pattern Check:")
    from django.urls import reverse
    
    if users.exists():
        test_user = users.first()
        try:
            url = reverse('admin_employee_detail', kwargs={'employee_id': test_user.id})
            print(f"   ✅ URL pattern works: {url}")
        except Exception as e:
            print(f"   ❌ URL pattern error: {str(e)}")
    
    # Test 3: Check template existence
    print(f"\n📝 3. Template Check:")
    import os
    template_path = "hr_app/templates/admin/employee_detail.html"
    if os.path.exists(template_path):
        print(f"   ✅ Template exists: {template_path}")
        
        # Check file size
        size = os.path.getsize(template_path)
        print(f"   Template size: {size} bytes")
    else:
        print(f"   ❌ Template missing: {template_path}")
    
    # Test 4: Check view function
    print(f"\n🔧 4. View Function Check:")
    try:
        from hr_app.views import admin_employee_detail
        print(f"   ✅ View function imported successfully")
    except ImportError as e:
        print(f"   ❌ View function import error: {str(e)}")
    
    # Test 5: Check admin dashboard template
    print(f"\n📱 5. Admin Dashboard Template Check:")
    dashboard_template = "hr_app/templates/admin/dashboard.html"
    if os.path.exists(dashboard_template):
        print(f"   ✅ Dashboard template exists")
        
        # Check if it contains the correct URL reference
        with open(dashboard_template, 'r', encoding='utf-8') as f:
            content = f.read()
            if 'admin_employee_detail' in content:
                print(f"   ✅ Contains 'admin_employee_detail' URL reference")
            else:
                print(f"   ❌ Missing 'admin_employee_detail' URL reference")
    else:
        print(f"   ❌ Dashboard template missing")
    
    print(f"\n✨ Testing Complete!")
    print("=" * 60)
    print("🎯 Summary:")
    print("   1. Created missing employee_detail.html template")
    print("   2. Enhanced admin_employee_detail view with better error handling")
    print("   3. Added Django messages support")
    print("   4. Fixed URL pattern integration")
    print("\n📖 Next Steps:")
    print("   1. Start Django server: python manage.py runserver")
    print("   2. Login as admin user")
    print("   3. Go to Admin Dashboard")
    print("   4. Click 'View Details' on any employee")
    print("   5. Should now display detailed employee information!")

if __name__ == "__main__":
    test_admin_dashboard_functionality()
