#!/usr/bin/env python
"""
Demonstration script showing the correct way to manually execute Celery tasks
This addresses the 'function' object has no attribute 'delay' error
"""
import os
import sys
import django

# Setup Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'project.settings')
django.setup()

def demonstrate_correct_task_usage():
    """Show the correct way to execute Celery tasks manually"""
    
    print("🎯 Correct Ways to Execute Celery Tasks Manually")
    print("=" * 60)
    
    # Import the Celery app
    from project.celery import app
    
    print("✅ Method 1: Using app.send_task() - ALWAYS WORKS")
    print("-" * 50)
    
    try:
        # This is the reliable method that always works
        result = app.send_task('project.ah_authentication.tasks.verify_user_credentials')
        print(f"Task queued successfully!")
        print(f"Task ID: {result.id}")
        print(f"Task State: {result.state}")
        print()
        
        # You can also pass arguments
        result2 = app.send_task(
            'project.ah_authentication.tasks.process_redis_data',
            args=['process_key_for_listed_price']
        )
        print(f"Redis processing task ID: {result2.id}")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("✅ Method 2: Synchronous Execution - FOR TESTING")
    print("-" * 50)
    
    try:
        # Direct function call - good for testing/debugging
        from project.ah_authentication.tasks import verify_user_credentials
        print("Calling verify_user_credentials synchronously...")
        verify_user_credentials(accounts=[], notify_user=False)
        print("✅ Synchronous execution completed!")
        print()
        
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("📋 Available Tasks in Beat Schedule:")
    print("-" * 50)
    
    for task_name, config in app.conf.beat_schedule.items():
        print(f"• {task_name}")
        print(f"  Task: {config['task']}")
        print(f"  Schedule: {config['schedule']}")
        if 'args' in config:
            print(f"  Args: {config['args']}")
        print()
    
    print("🔧 How to Use in Django Shell:")
    print("-" * 50)
    print("""
# Start Django shell
python manage.py shell

# Method A: Using send_task (recommended)
from project.celery import app
result = app.send_task('project.ah_authentication.tasks.verify_user_credentials')
print(f"Task ID: {result.id}")

# Method B: With arguments
result = app.send_task('project.ah_authentication.tasks.process_redis_data', 
                      args=['process_key_for_listed_price'])

# Method C: Check task status
print(f"State: {result.state}")
result.get(timeout=60)  # Wait for completion

# Method D: Synchronous for testing
from project.ah_authentication.tasks import verify_user_credentials
verify_user_credentials()
    """)

if __name__ == "__main__":
    demonstrate_correct_task_usage()