
import requests
import sys
import os
import json
from datetime import datetime

class WyEBIYAPodcastTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        
    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        default_headers = {'Accept': 'application/json'}
        if headers:
            default_headers.update(headers)
            
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers)
            elif method == 'POST':
                response = requests.post(url, data=data, files=files, headers=default_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=default_headers)
                
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json() if response.text else {}
                except json.JSONDecodeError:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response.text}")
                return False, {}
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}
            
    def test_health_check(self):
        """Test the health check endpoint"""
        return self.run_test("Health Check", "GET", "api/health", 200)
        
    def test_get_categories(self):
        """Test getting all categories"""
        return self.run_test("Get Categories", "GET", "api/categories", 200)
        
    def test_get_audio_files(self):
        """Test getting all audio files"""
        return self.run_test("Get Audio Files", "GET", "api/audio-files", 200)
        
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*50)
        print(f"📊 Tests Summary: {self.tests_passed}/{self.tests_run} passed")
        print("="*50)
        
def main():
    # Get the backend URL from environment or use the provided URL
    backend_url = "https://69b0f385-191d-4d9c-8f85-af6b574a2e14.preview.emergentagent.com"
    
    print(f"Testing backend at: {backend_url}")
    
    # Initialize tester
    tester = WyEBIYAPodcastTester(backend_url)
    
    # Run basic API tests
    tester.test_health_check()
    tester.test_get_categories()
    tester.test_get_audio_files()
    
    # Print summary
    tester.print_summary()
    
    return 0 if tester.tests_passed == tester.tests_run else 1
    
if __name__ == "__main__":
    sys.exit(main())
