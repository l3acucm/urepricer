#!/usr/bin/env python3
"""
End-to-end test runner with LocalStack and Redis setup.

This script:
1. Checks if LocalStack and Redis are running
2. Sets up test environment
3. Runs end-to-end tests
4. Provides clear feedback on test results
"""
import os
import sys
import subprocess
import time
import requests
import redis
import json
from pathlib import Path


def check_localstack():
    """Check if LocalStack is running and accessible."""
    try:
        response = requests.get("http://localhost:4566/health", timeout=5)
        if response.status_code == 200:
            health = response.json()
            if health.get("services", {}).get("sqs") == "available":
                print("✅ LocalStack SQS service is available")
                return True
            else:
                print("❌ LocalStack SQS service is not available")
                return False
    except Exception as e:
        print(f"❌ LocalStack is not accessible: {e}")
        return False


def check_redis():
    """Check if Redis is running and accessible."""
    try:
        client = redis.Redis(host='localhost', port=6380, decode_responses=True)
        client.ping()
        print("✅ Redis test instance is available")
        return True
    except Exception as e:
        print(f"❌ Redis test instance is not accessible: {e}")
        return False


def setup_localstack_queues():
    """Setup SQS queues in LocalStack if they don't exist."""
    try:
        import boto3
        
        sqs = boto3.client(
            'sqs',
            endpoint_url='http://localhost:4566',
            region_name='us-east-1',
            aws_access_key_id='test',
            aws_secret_access_key='test'
        )
        
        # Check if queue already exists
        try:
            response = sqs.list_queues(QueueNamePrefix='ah-repricer')
            existing_queues = response.get('QueueUrls', [])
            if any('ah-repricer-any-offer-changed' in url for url in existing_queues):
                print("✅ SQS queues already exist")
                return True
        except Exception:
            pass
        
        # Create the queue
        queue_response = sqs.create_queue(
            QueueName='ah-repricer-any-offer-changed',
            Attributes={
                'MessageRetentionPeriod': '1209600',
                'VisibilityTimeoutSeconds': '300',
                'ReceiveMessageWaitTimeSeconds': '20'
            }
        )
        
        print(f"✅ Created SQS queue: {queue_response['QueueUrl']}")
        return True
        
    except Exception as e:
        print(f"❌ Failed to setup LocalStack queues: {e}")
        return False


def run_unit_tests():
    """Run the existing unit tests to ensure they still pass."""
    print("\n🧪 Running existing unit tests...")
    
    result = subprocess.run([
        sys.executable, "-m", "pytest", 
        "tests/test_strategies.py",
        "-v", "--tb=short", 
        "--disable-warnings"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ All unit tests passed!")
        # Extract test count from output
        lines = result.stdout.split('\n')
        for line in lines:
            if 'passed' in line and ('warning' in line or 'failed' in line or 'error' in line):
                print(f"   {line}")
                break
        return True
    else:
        print("❌ Unit tests failed!")
        print("STDOUT:", result.stdout[-1000:])  # Last 1000 chars
        print("STDERR:", result.stderr[-1000:])  # Last 1000 chars  
        return False


def run_e2e_tests():
    """Run the end-to-end integration tests."""
    print("\n🚀 Running end-to-end integration tests...")
    
    # Set environment variables for testing
    env = os.environ.copy()
    env.update({
        'TESTING': 'true',
        'AWS_ENDPOINT_URL': 'http://localhost:4566',
        'REDIS_URL': 'redis://localhost:6380',
        'PYTEST_DISABLE_PLUGIN_AUTOLOAD': '1'
    })
    
    result = subprocess.run([
        sys.executable, "-m", "pytest",
        "tests/test_e2e_sqs_repricing.py",
        "tests/test_e2e_fastapi_repricing.py", 
        "tests/test_e2e_redis_integration.py",
        "-v", "--tb=short",
        "--disable-warnings",
        "-m", "integration",
        "--confcutdir=tests"
    ], env=env, capture_output=True, text=True)
    
    if result.returncode == 0:
        print("✅ All end-to-end tests passed!")
        # Extract test summary
        lines = result.stdout.split('\n')
        for line in lines:
            if 'passed' in line and ('warning' in line or 'failed' in line or 'error' in line):
                print(f"   {line}")
                break
        return True
    else:
        print("❌ End-to-end tests failed!")
        print("\nSTDOUT:")
        print(result.stdout[-2000:])  # Last 2000 chars
        print("\nSTDERR:")
        print(result.stderr[-2000:])  # Last 2000 chars
        return False


def main():
    """Main test runner function."""
    print("🏗️  Arbitrage Hero E2E Test Runner")
    print("="*50)
    
    # Check if we're in the right directory
    if not Path("pyproject.toml").exists():
        print("❌ Please run this script from the project root directory")
        return 1
    
    print("\n📋 Pre-flight checks...")
    
    # Check dependencies
    all_good = True
    
    if not check_localstack():
        print("💡 To start LocalStack: docker-compose -f docker-compose.localstack.yml up localstack")
        all_good = False
    
    if not check_redis():
        print("💡 To start Redis: docker-compose -f docker-compose.localstack.yml up redis")
        all_good = False
    
    if not all_good:
        print("\n❌ Prerequisites not met. Please start the required services.")
        return 1
    
    # Setup LocalStack queues
    if not setup_localstack_queues():
        print("\n❌ Failed to setup LocalStack resources")
        return 1
    
    print("\n✅ All prerequisites met!")
    
    # Run unit tests first to ensure they still work
    if not run_unit_tests():
        print("\n❌ Unit tests failed - aborting E2E tests")
        return 1
    
    # Run end-to-end tests
    if not run_e2e_tests():
        print("\n❌ End-to-end tests failed")
        return 1
    
    print("\n🎉 All tests passed successfully!")
    print("\n📊 Test Summary:")
    print("   ✅ Unit tests (pricing strategies)")
    print("   ✅ E2E SQS repricing tests")
    print("   ✅ E2E FastAPI webhook tests")
    print("   ✅ E2E Redis integration tests")
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)