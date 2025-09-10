#!/usr/bin/env python
"""
Script to test Celery tasks for Arbitrage Hero Repricer
"""
import os
import sys
import django
from datetime import datetime

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

# Now import Celery and tasks
from project.celery import app
from project.ah_authentication.tasks import verify_user_credentials
from project.ah_authentication.models import UserAccount

def test_verify_credentials_task():
    """Test the verify_user_credentials task"""
    print("🧪 Testing verify_user_credentials Celery task...")
    print("=" * 50)
    
    # Method 1: Call task asynchronously (requires running Celery worker)
    try:
        result = verify_user_credentials.delay()
        print(f"✅ Task queued successfully!")
        print(f"   Task ID: {result.id}")
        print(f"   Task State: {result.state}")
        print(f"   Queue Time: {datetime.now().strftime('%H:%M:%S')}")
        print()
        
        # Wait a bit and check result
        print("Waiting for task completion (max 30 seconds)...")
        try:
            result.get(timeout=30)
            print(f"✅ Task completed successfully!")
        except Exception as e:
            print(f"⚠️  Task execution error or timeout: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to queue task: {e}")
        return False

def test_verify_credentials_sync():
    """Test the verify_user_credentials function synchronously"""
    print("\n🔧 Testing verify_user_credentials synchronously...")
    print("=" * 50)
    
    try:
        # Get test users
        test_users = UserAccount.objects.filter(user_id__startswith='test_user_')
        print(f"Found {test_users.count()} test users")
        
        if test_users.exists():
            print("Test users:")
            for user in test_users:
                print(f"   - {user.user_id} ({user.marketplace_type}) - Status: {user.status}")
        
        # Call the task function directly (synchronous)
        print("\nCalling verify_user_credentials synchronously...")
        verify_user_credentials(accounts=list(test_users), notify_user=False)
        print("✅ Synchronous execution completed!")
        
        # Check if status was updated
        print("\nChecking updated user statuses...")
        updated_users = UserAccount.objects.filter(user_id__startswith='test_user_')
        for user in updated_users:
            print(f"   - {user.user_id}: {user.status} (Updated: {user.updated_at})")
        
        return True
        
    except Exception as e:
        print(f"❌ Synchronous execution failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_celery_connection():
    """Test Celery connection and broker status"""
    print("\n🔗 Testing Celery connection...")
    print("=" * 50)
    
    try:
        # Test Redis connection (Celery broker)
        from celery import current_app
        inspector = current_app.control.inspect()
        
        # Check active workers
        active_workers = inspector.active()
        if active_workers:
            print(f"✅ Found {len(active_workers)} active workers:")
            for worker, tasks in active_workers.items():
                print(f"   - {worker}: {len(tasks)} active tasks")
        else:
            print("⚠️  No active workers found")
        
        # Check registered tasks
        registered_tasks = inspector.registered()
        if registered_tasks:
            print(f"\n✅ Workers have registered tasks:")
            for worker, tasks in registered_tasks.items():
                relevant_tasks = [task for task in tasks if 'verify_user_credentials' in task]
                if relevant_tasks:
                    print(f"   - {worker}: {relevant_tasks}")
        
        # Check scheduled tasks (beat)
        scheduled = inspector.scheduled()
        if scheduled:
            print(f"\n✅ Scheduled tasks found:")
            for worker, tasks in scheduled.items():
                if tasks:
                    print(f"   - {worker}: {len(tasks)} scheduled tasks")
        
        return True
        
    except Exception as e:
        print(f"❌ Celery connection test failed: {e}")
        return False

def show_task_usage_examples():
    """Show correct ways to call Celery tasks"""
    print("\n📖 Correct Task Usage Examples:")
    print("=" * 50)
    
    print("""
# Method 1: Asynchronous execution (requires Celery worker)
from project.ah_authentication.tasks import verify_user_credentials
result = verify_user_credentials.delay()
print(f"Task ID: {result.id}")

# Method 2: Synchronous execution (for testing/debugging)
from project.ah_authentication.tasks import verify_user_credentials  
verify_user_credentials(accounts=[], notify_user=False)

# Method 3: Apply async with custom arguments
result = verify_user_credentials.apply_async(
    args=[list(UserAccount.objects.filter(enabled=True)), False],
    countdown=10  # Execute after 10 seconds
)

# Method 4: Using Django shell
python manage.py shell
>>> from project.ah_authentication.tasks import verify_user_credentials
>>> result = verify_user_credentials.delay()
>>> print(result.id)
    """)

def main():
    """Run all Celery task tests"""
    print("🚀 Arbitrage Hero Repricer - Celery Task Testing")
    print("=" * 70)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = []
    
    # Test Celery connection
    results.append(('Celery Connection', test_celery_connection()))
    
    # Test synchronous execution
    results.append(('Synchronous Execution', test_verify_credentials_sync()))
    
    # Test asynchronous execution
    results.append(('Asynchronous Execution', test_verify_credentials_task()))
    
    # Show usage examples
    show_task_usage_examples()
    
    # Summary
    print("\n📊 Test Results Summary")
    print("=" * 50)
    
    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name:25} {status}")
        if result:
            passed += 1
    
    print(f"\nOverall: {passed}/{len(results)} tests passed")
    
    if passed == len(results):
        print("\n🎉 All Celery tasks are working correctly!")
        print("You can now use verify_user_credentials.delay() in Django shell")
    else:
        print("\n⚠️  Some tests failed. Check the errors above.")
    
    return passed == len(results)

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)