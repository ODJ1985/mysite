import requests
import os
import time
import random
import string
import tempfile
import wave
import numpy as np
import sys

class PodcastAppTester:
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

    def test_health_check(self):
        """Test the health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        return success

    def test_create_category(self):
        """Create a test category"""
        category_name = f"Test Category {int(time.time())}"
        form_data = {
            "name": category_name,
            "color": "#3B82F6"
        }
        
        success, response = self.run_test(
            "Create Category",
            "POST",
            "categories",
            200,
            form_data=form_data
        )
        
        if success and 'category_id' in response:
            self.category_id = response['category_id']
            self.category_name = category_name
            return True
        return False

    def test_get_categories(self):
        """Test getting categories"""
        success, response = self.run_test(
            "Get Categories",
            "GET",
            "categories",
            200
        )
        return success

    def test_upload_audio_file(self, size_mb):
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
            
            expected_status = 200 if size_mb <= 50 else 413
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

    def test_get_audio_files(self):
        """Test getting audio files"""
        success, response = self.run_test(
            "Get Audio Files",
            "GET",
            "audio-files",
            200
        )
        return success

def main():
    # Setup
    tester = PodcastAppTester()
    
    # Run tests
    print("\n===== Testing Podcast App API =====\n")
    
    # Basic API tests
    tester.test_health_check()
    tester.test_create_category()
    tester.test_get_categories()
    
    # File upload tests with different sizes
    print("\n===== Testing File Size Limits =====\n")
    
    # Small file (should succeed)
    tester.test_upload_audio_file(1)
    
    # Medium file (should succeed)
    tester.test_upload_audio_file(25)
    
    # Large file within limit (should succeed)
    tester.test_upload_audio_file(49)
    
    # File at exact limit (should succeed)
    tester.test_upload_audio_file(50)
    
    # File exceeding limit (should fail with 413)
    tester.test_upload_audio_file(51)
    
    # Get audio files after uploads
    tester.test_get_audio_files()
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
