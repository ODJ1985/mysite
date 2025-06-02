import os
import sys
import json
import time
import tempfile
import wave
import numpy as np
import requests
from datetime import datetime

class FileSizeLimitModifier:
    def __init__(self, base_url="https://1e3d862d-5dd1-4551-a519-06c14af7772e.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.category_id = None
        self.category_name = None
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "tests": [],
            "summary": {}
        }
        
    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, form_data=None, timeout=30):
        """Run a single API test with configurable timeout"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        test_result = {
            "name": name,
            "method": method,
            "endpoint": endpoint,
            "expected_status": expected_status,
            "actual_status": None,
            "success": False,
            "response": None,
            "error": None,
            "response_time_ms": None,
            "timeout": timeout
        }
        
        try:
            start_time = time.time()
            
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=timeout)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, data=form_data, timeout=timeout)
                else:
                    response = requests.post(url, json=data, headers=headers, timeout=timeout)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=timeout)
                
            end_time = time.time()
            response_time_ms = (end_time - start_time) * 1000
            test_result["response_time_ms"] = round(response_time_ms, 2)
            test_result["actual_status"] = response.status_code

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                print(f"Response time: {response_time_ms:.2f}ms")
                test_result["success"] = True
                try:
                    response_data = response.json()
                    test_result["response"] = response_data
                    return success, response_data
                except:
                    test_result["response"] = response.text
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response time: {response_time_ms:.2f}ms")
                try:
                    response_data = response.json()
                    error_detail = response_data.get('detail', 'No detail provided')
                    print(f"Error detail: {error_detail}")
                    test_result["response"] = response_data
                    test_result["error"] = error_detail
                except:
                    print("Could not parse error response")
                    test_result["response"] = response.text
                    test_result["error"] = "Could not parse error response"
                return False, {}

        except requests.exceptions.Timeout:
            print(f"❌ Failed - Request timed out after {timeout} seconds")
            test_result["error"] = f"Request timed out after {timeout} seconds"
            return False, {}
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            test_result["error"] = str(e)
            return False, {}
        finally:
            self.results["tests"].append(test_result)

    def create_test_wav_file(self, size_mb, filename="test_audio.wav"):
        """Create a WAV file of specified size in MB"""
        print(f"Creating test WAV file of size {size_mb}MB...")
        
        # Create a temporary file
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.wav')
        temp_file.close()
        
        # Calculate number of samples needed for target file size
        # WAV format: 16-bit samples, mono channel, 44.1kHz
        # Each sample is 2 bytes, so 1MB = 1024*1024/2 = 524288 samples
        num_samples = int(size_mb * 1024 * 1024 / 2)
        
        # Generate random audio data (white noise)
        audio_data = np.random.uniform(-1, 1, num_samples).astype(np.float32)
        
        # Normalize to 16-bit range
        audio_data = audio_data * 32767
        audio_data = audio_data.astype(np.int16)
        
        # Write to WAV file
        with wave.open(temp_file.name, 'wb') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 16-bit
            wav_file.setframerate(44100)  # 44.1kHz
            wav_file.writeframes(audio_data.tobytes())
        
        # Verify file size
        actual_size = os.path.getsize(temp_file.name) / (1024 * 1024)
        print(f"Created WAV file with actual size: {actual_size:.2f}MB")
        
        return temp_file.name

    def test_create_category(self):
        """Create a test category"""
        category_name = f"Test Category {int(time.time())}"
        
        with requests.Session() as session:
            url = f"{self.base_url}/api/categories"
            form_data = {
                "name": category_name,
                "color": "#3B82F6"
            }
            
            self.tests_run += 1
            print(f"\n🔍 Testing Create Category...")
            
            test_result = {
                "name": "Create Category",
                "method": "POST",
                "endpoint": "categories",
                "expected_status": 200,
                "actual_status": None,
                "success": False,
                "response": None,
                "error": None,
                "response_time_ms": None
            }
            
            try:
                start_time = time.time()
                response = session.post(url, data=form_data)
                end_time = time.time()
                response_time_ms = (end_time - start_time) * 1000
                test_result["response_time_ms"] = round(response_time_ms, 2)
                test_result["actual_status"] = response.status_code
                
                success = response.status_code == 200
                if success:
                    self.tests_passed += 1
                    print(f"✅ Passed - Status: {response.status_code}")
                    print(f"Response time: {response_time_ms:.2f}ms")
                    test_result["success"] = True
                    
                    response_data = response.json()
                    test_result["response"] = response_data
                    
                    if 'category_id' in response_data:
                        self.category_id = response_data['category_id']
                        self.category_name = category_name
                        return True
                else:
                    print(f"❌ Failed - Expected 200, got {response.status_code}")
                    print(f"Response time: {response_time_ms:.2f}ms")
                    try:
                        response_data = response.json()
                        error_detail = response_data.get('detail', 'No detail provided')
                        print(f"Error detail: {error_detail}")
                        test_result["response"] = response_data
                        test_result["error"] = error_detail
                    except:
                        print("Could not parse error response")
                        test_result["response"] = response.text
                        test_result["error"] = "Could not parse error response"
            except Exception as e:
                print(f"❌ Failed - Error: {str(e)}")
                test_result["error"] = str(e)
            finally:
                self.results["tests"].append(test_result)
                
        return False

    def test_upload_audio_file(self, size_mb, expected_success=True, timeout=60):
        """Test uploading an audio file of specified size with configurable timeout"""
        if not self.category_name:
            print("No category available for upload test")
            return False
            
        # Create a test WAV file
        wav_file_path = self.create_test_wav_file(size_mb)
        
        # Prepare form data
        title = f"Test Audio {size_mb}MB {int(time.time())}"
        
        with open(wav_file_path, 'rb') as f:
            files = {'file': ('test_audio.wav', f, 'audio/wav')}
            form_data = {
                'title': title,
                'category': self.category_name
            }
            
            expected_status = 200 if expected_success else 413
            success, response = self.run_test(
                f"Upload {size_mb}MB Audio File (Timeout: {timeout}s)",
                "POST",
                "upload-audio",
                expected_status,
                files=files,
                form_data=form_data,
                timeout=timeout
            )
        
        # Clean up the temporary file
        try:
            os.unlink(wav_file_path)
        except:
            pass
            
        return success

    def save_results(self, filename="file_size_limit_modification_results.json"):
        """Save test results to a JSON file"""
        # Add summary information
        self.results["summary"]["tests_run"] = self.tests_run
        self.results["summary"]["tests_passed"] = self.tests_passed
        
        with open(filename, 'w') as f:
            json.dump(self.results, f, indent=2)
            
        print(f"\nTest results saved to {filename}")

def modify_file_size_limit(new_limit_mb):
    """Modify the file size limit in the server.py file"""
    server_path = "/app/backend/server.py"
    
    # Read the current file
    with open(server_path, 'r') as f:
        content = f.read()
    
    # Replace the file size limit
    content = content.replace("max_size = 7 * 1024 * 1024  # 7MB", f"max_size = {new_limit_mb} * 1024 * 1024  # {new_limit_mb}MB")
    content = content.replace("raise HTTPException(status_code=413, detail=\"File size must be less than 7MB\")", 
                             f"raise HTTPException(status_code=413, detail=\"File size must be less than {new_limit_mb}MB\")")
    
    # Write the modified content back
    with open(server_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Modified file size limit to {new_limit_mb}MB in {server_path}")
    
    # Restart the backend service
    os.system("sudo supervisorctl restart backend")
    print("✅ Restarted backend service")
    
    # Wait for the service to restart
    time.sleep(5)
    print("✅ Waited for service to restart")

def main():
    # Setup
    tester = FileSizeLimitModifier()
    
    # Run tests with current limit
    print("\n===== Testing Current File Size Limit =====\n")
    
    # Create a category for testing
    if not tester.test_create_category():
        print("❌ Failed to create test category, aborting tests")
        return 1
    
    # Test the health endpoint
    tester.run_test("Health Check", "GET", "health", 200)
    
    # Test with current limit
    tester.test_upload_audio_file(6.9, expected_success=True)
    tester.test_upload_audio_file(7.1, expected_success=False)
    
    # Modify the file size limit to 10MB
    print("\n===== Modifying File Size Limit to 10MB =====\n")
    modify_file_size_limit(10)
    
    # Create a new category for testing after modification
    if not tester.test_create_category():
        print("❌ Failed to create test category after modification, aborting tests")
        return 1
    
    # Test with new limit
    print("\n===== Testing Modified File Size Limit (10MB) =====\n")
    tester.test_upload_audio_file(7.1, expected_success=True)
    tester.test_upload_audio_file(9.9, expected_success=True)
    tester.test_upload_audio_file(10.1, expected_success=False)
    
    # Modify the file size limit to 15MB
    print("\n===== Modifying File Size Limit to 15MB =====\n")
    modify_file_size_limit(15)
    
    # Create a new category for testing after modification
    if not tester.test_create_category():
        print("❌ Failed to create test category after modification, aborting tests")
        return 1
    
    # Test with new limit
    print("\n===== Testing Modified File Size Limit (15MB) =====\n")
    tester.test_upload_audio_file(10.1, expected_success=True)
    tester.test_upload_audio_file(14.9, expected_success=True)
    tester.test_upload_audio_file(15.1, expected_success=False)
    
    # Save results
    tester.save_results()
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    
    # Restore the original file size limit
    print("\n===== Restoring Original File Size Limit (7MB) =====\n")
    modify_file_size_limit(7)
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
