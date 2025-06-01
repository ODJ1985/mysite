import requests
import os
import time
import tempfile
import wave
import numpy as np
import sys
import json

class PodcastAppTester:
    def __init__(self, base_url="https://9fe0c2b0-7831-40b8-a607-5c9b24890339.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, headers=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        
        if headers is None:
            headers = {}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, json=data, files=files, headers=headers)
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                result = {"name": name, "status": "PASS", "actual_status": response.status_code}
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                result = {"name": name, "status": "FAIL", "expected_status": expected_status, "actual_status": response.status_code}
            
            try:
                response_data = response.json()
                print(f"Response: {json.dumps(response_data, indent=2)}")
                result["response"] = response_data
            except:
                if response.text:
                    print(f"Raw response: {response.text[:500]}")
                    result["raw_response"] = response.text[:500]
            
            self.test_results.append(result)
            return success, response
        
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            result = {"name": name, "status": "ERROR", "error": str(e)}
            self.test_results.append(result)
            return False, None

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
        return self.run_test(
            "Health Check",
            "GET",
            "api/health",
            200
        )

    def test_create_category(self, name=None):
        """Test creating a category"""
        if name is None:
            name = f"Test Category {int(time.time())}"
        
        success, response = self.run_test(
            "Create Category",
            "POST",
            "api/categories",
            200,
            data={"name": name, "color": "#3B82F6"}
        )
        
        if success and response.json().get("id"):
            return name, response.json().get("id")
        return None, None

    def test_get_categories(self):
        """Test getting all categories"""
        return self.run_test(
            "Get Categories",
            "GET",
            "api/categories",
            200
        )

    def test_upload_audio(self, size_mb, category_name="Test Category"):
        """Test uploading an audio file of specified size"""
        wav_file_path = self.create_test_wav_file(size_mb)
        
        with open(wav_file_path, 'rb') as f:
            files = {'file': ('test_audio.wav', f, 'audio/wav')}
            form_data = {
                'title': f"Test Audio {size_mb}MB {int(time.time())}",
                'category': category_name
            }
            
            success, response = self.run_test(
                f"Upload {size_mb}MB Audio File",
                "POST",
                "api/upload-audio",
                200,
                files=files,
                data=form_data
            )
        
        # Clean up
        try:
            os.unlink(wav_file_path)
        except:
            pass
        
        return success, response

    def test_get_audio_files(self):
        """Test getting all audio files"""
        return self.run_test(
            "Get Audio Files",
            "GET",
            "api/audio-files",
            200
        )

    def generate_report(self):
        """Generate a test report"""
        print("\n===== Test Report =====")
        print(f"Tests Run: {self.tests_run}")
        print(f"Tests Passed: {self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed / self.tests_run * 100) if self.tests_run > 0 else 0:.2f}%")
        
        print("\nDetailed Results:")
        for result in self.test_results:
            status_icon = "✅" if result["status"] == "PASS" else "❌"
            print(f"{status_icon} {result['name']}: {result['status']}")
        
        return self.tests_passed == self.tests_run

def main():
    print("\n===== Testing Podcast App API =====\n")
    
    tester = PodcastAppTester()
    
    # Basic health check
    tester.test_health_check()
    
    # Test categories
    category_name, _ = tester.test_create_category()
    tester.test_get_categories()
    
    # Test file uploads with different sizes
    test_sizes = [5, 10, 15, 24, 25, 26]
    
    for size in test_sizes:
        tester.test_upload_audio(size, category_name or "Test Category")
    
    # Test getting audio files
    tester.test_get_audio_files()
    
    # Generate report
    success = tester.generate_report()
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())