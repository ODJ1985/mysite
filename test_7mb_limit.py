import requests
import os
import time
import random
import string
import tempfile
import wave
import numpy as np
import sys

class PodcastFileSizeTester:
    def __init__(self, base_url="https://9fe0c2b0-7831-40b8-a607-5c9b24890339.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.category_id = None
        self.category_name = None
        
    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, form_data=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                if files:
                    response = requests.post(url, files=files, data=form_data)
                else:
                    response = requests.post(url, json=data, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)

            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json()
                except:
                    return success, {}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json().get('detail', 'No detail provided')
                    print(f"Error detail: {error_detail}")
                except:
                    print("Could not parse error response")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

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
            
            try:
                response = session.post(url, data=form_data)
                
                success = response.status_code == 200
                if success:
                    self.tests_passed += 1
                    print(f"✅ Passed - Status: {response.status_code}")
                    response_data = response.json()
                    if 'category_id' in response_data:
                        self.category_id = response_data['category_id']
                        self.category_name = category_name
                        return True
                else:
                    print(f"❌ Failed - Expected 200, got {response.status_code}")
                    try:
                        error_detail = response.json().get('detail', 'No detail provided')
                        print(f"Error detail: {error_detail}")
                    except:
                        print("Could not parse error response")
            except Exception as e:
                print(f"❌ Failed - Error: {str(e)}")
                
        return False

    def test_upload_audio_file(self, size_mb, expected_success=True):
        """Test uploading an audio file of specified size"""
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
                f"Upload {size_mb}MB Audio File",
                "POST",
                "upload-audio",
                expected_status,
                files=files,
                form_data=form_data
            )
        
        # Clean up the temporary file
        try:
            os.unlink(wav_file_path)
        except:
            pass
            
        return success

def main():
    # Setup
    tester = PodcastFileSizeTester()
    
    # Run tests
    print("\n===== Testing Podcast App 7MB File Size Limit =====\n")
    
    # Create a category for testing
    if not tester.test_create_category():
        print("❌ Failed to create test category, aborting tests")
        return 1
    
    # File upload tests with different sizes
    print("\n===== Testing File Size Limits =====\n")
    
    # Test files under the 7MB limit (should succeed)
    tester.test_upload_audio_file(1, expected_success=True)
    tester.test_upload_audio_file(3, expected_success=True)
    tester.test_upload_audio_file(5, expected_success=True)
    tester.test_upload_audio_file(6, expected_success=True)
    
    # Test file at exact 7MB limit (should succeed)
    tester.test_upload_audio_file(7, expected_success=True)
    
    # Test files exceeding the 7MB limit (should fail with 413)
    tester.test_upload_audio_file(8, expected_success=False)
    tester.test_upload_audio_file(10, expected_success=False)
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
