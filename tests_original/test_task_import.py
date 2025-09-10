#!/usr/bin/env python
"""
Test script to demonstrate correct task import and usage
"""
import os
import sys
import django

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

print("Testing task import and execution methods...")
print("=" * 60)

# Method 1: Import via Celery app
print("\n1. Import via Celery app:")
try:
    from project.celery import app
    verify_task = app.tasks['project.ah_authentication.tasks.verify_user_credentials']
    result = verify_task.delay()
    print(f"✅ SUCCESS: Task queued with ID: {result.id}")
except Exception as e:
    print(f"❌ FAILED: {e}")

# Method 2: Direct import (this might not work due to decoration)
print("\n2. Direct import:")
try:
    from project.ah_authentication.tasks import verify_user_credentials
    print(f"Task type: {type(verify_user_credentials)}")
    print(f"Has delay method: {hasattr(verify_user_credentials, 'delay')}")
    if hasattr(verify_user_credentials, 'delay'):
        result = verify_user_credentials.delay()
        print(f"✅ SUCCESS: Task queued with ID: {result.id}")
    else:
        print("❌ Task does not have delay method")
except Exception as e:
    print(f"❌ FAILED: {e}")

# Method 3: Import after setting up app properly
print("\n3. Import after app setup:")
try:
    # Ensure app is imported first
    from project.celery import app
    # Force task discovery
    app.autodiscover_tasks()
    
    # Now import the task
    from project.ah_authentication.tasks import verify_user_credentials
    print(f"Task type after autodiscover: {type(verify_user_credentials)}")
    print(f"Has delay method: {hasattr(verify_user_credentials, 'delay')}")
    
    if hasattr(verify_user_credentials, 'delay'):
        result = verify_user_credentials.delay()
        print(f"✅ SUCCESS: Task queued with ID: {result.id}")
    else:
        # Try calling directly for testing
        verify_user_credentials(accounts=[], notify_user=False)
        print("✅ SUCCESS: Task executed synchronously")
        
except Exception as e:
    print(f"❌ FAILED: {e}")

# Method 4: Using send_task (always works)
print("\n4. Using send_task:")
try:
    from project.celery import app
    result = app.send_task('project.ah_authentication.tasks.verify_user_credentials')
    print(f"✅ SUCCESS: Task sent with ID: {result.id}")
except Exception as e:
    print(f"❌ FAILED: {e}")

print("\n" + "=" * 60)
print("RECOMMENDED APPROACHES FOR DJANGO SHELL:")
print("""
# Option A: Use send_task (always works)
from project.celery import app
result = app.send_task('project.ah_authentication.tasks.verify_user_credentials')
print(f"Task ID: {result.id}")

# Option B: Import app first, then task
from project.celery import app
app.autodiscover_tasks()  # Force discovery
from project.ah_authentication.tasks import verify_user_credentials
result = verify_user_credentials.delay()

# Option C: Synchronous execution for testing
from project.ah_authentication.tasks import verify_user_credentials
verify_user_credentials(accounts=[], notify_user=False)
""")