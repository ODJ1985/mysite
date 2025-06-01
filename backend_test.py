
import requests
import os
import sys
import time
import tempfile
import wave
import numpy as np
from datetime import datetime

class PodcastAPITester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.categories = []
        self.uploaded_files = []

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, data=data, files=files, headers=headers)
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
                    print(f"Response text: {response.text}")
                return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test the health check endpoint"""
        success, response = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        return success

    def test_create_category(self, name, color="#3B82F6"):
        """Create a category"""
        success, response = self.run_test(
            f"Create Category: {name}",
            "POST",
            "categories",
            200,
            data={"name": name, "color": color}
        )
        if success and 'category_id' in response:
            self.categories.append(name)
            return response.get('category_id')
        return None

    def test_get_categories(self):
        """Get all categories"""
        success, response = self.run_test(
            "Get Categories",
            "GET",
            "categories",
            200
        )
        if success and 'categories' in response:
            return response['categories']
        return []

    def create_test_wav_file(self, duration=5, filename=None, size_mb=None):
        """Create a test WAV file with specified duration or size"""
        if filename is None:
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            filename = temp_file.name
            temp_file.close()
        
        # Set parameters
        sample_rate = 44100  # Hz
        
        if size_mb:
            # Calculate duration based on desired size
            # 44100 samples/sec * 2 bytes/sample * 2 channels
            bytes_per_second = 44100 * 2 * 2
            duration = (size_mb * 1024 * 1024) / bytes_per_second
        
        # Generate random audio data
        num_samples = int(duration * sample_rate)
        audio_data = np.random.uniform(-1, 1, num_samples).astype(np.float32)
        
        # Write to WAV file
        with wave.open(filename, 'w') as wav_file:
            wav_file.setnchannels(2)  # Stereo
            wav_file.setsampwidth(2)  # 2 bytes per sample
            wav_file.setframerate(sample_rate)
            wav_file.writeframes((audio_data * 32767).astype(np.int16).tobytes())
        
        print(f"Created test WAV file: {filename}, Duration: {duration:.2f}s, Size: {os.path.getsize(filename) / (1024 * 1024):.2f} MB")
        return filename

    def test_upload_audio(self, file_path, title, category):
        """Test uploading an audio file"""
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
        print(f"Uploading file: {file_path}, Size: {file_size:.2f} MB")
        
        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file, 'audio/wav')}
            data = {'title': title, 'category': category}
            
            success, response = self.run_test(
                f"Upload Audio ({file_size:.2f} MB)",
                "POST",
                "upload-audio",
                200,
                data=data,
                files=files
            )
            
            if success and 'file_id' in response:
                self.uploaded_files.append(response['file_id'])
                return response['file_id']
            return None

    def test_get_audio_files(self, category=None):
        """Get all audio files, optionally filtered by category"""
        endpoint = "audio-files"
        if category:
            endpoint += f"?category={category}"
            
        success, response = self.run_test(
            f"Get Audio Files{' (filtered by ' + category + ')' if category else ''}",
            "GET",
            endpoint,
            200
        )
        
        if success and 'audio_files' in response:
            return response['audio_files']
        return []

    def test_get_audio_file(self, file_id):
        """Get a specific audio file by ID"""
        success, response = self.run_test(
            f"Get Audio File (ID: {file_id})",
            "GET",
            f"audio-file/{file_id}",
            200
        )
        return success

    def test_delete_audio_file(self, file_id):
        """Delete an audio file"""
        success, _ = self.run_test(
            f"Delete Audio File (ID: {file_id})",
            "DELETE",
            f"audio-file/{file_id}",
            200
        )
        if success and file_id in self.uploaded_files:
            self.uploaded_files.remove(file_id)
        return success

    def test_stream_audio(self, file_id):
        """Test streaming an audio file"""
        url = f"{self.base_url}/api/audio-stream/{file_id}"
        
        self.tests_run += 1
        print(f"\n🔍 Testing Audio Streaming (ID: {file_id})...")
        
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                # Just check if we can get the first chunk of data
                next(response.iter_content(chunk_size=1024), None)
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}, Content-Type: {response.headers.get('Content-Type')}")
                return True
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                return False
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def cleanup(self):
        """Clean up any created resources"""
        print("\n🧹 Cleaning up resources...")
        
        # Delete uploaded files
        for file_id in self.uploaded_files[:]:
            self.test_delete_audio_file(file_id)

def main():
    # Get backend URL from environment or use the one from frontend/.env
    backend_url = "https://9fe0c2b0-7831-40b8-a607-5c9b24890339.preview.emergentagent.com"
    
    print(f"🚀 Starting Podcast API Tests against {backend_url}")
    tester = PodcastAPITester(backend_url)
    
    # Basic health check
    if not tester.test_health_check():
        print("❌ Health check failed, stopping tests")
        return 1
    
    # Test category functionality
    test_category = f"Test Category {datetime.now().strftime('%H%M%S')}"
    category_id = tester.test_create_category(test_category)
    if not category_id:
        print("❌ Category creation failed")
    
    categories = tester.test_get_categories()
    print(f"Found {len(categories)} categories")
    
    # Test file upload with different sizes
    test_files = []
    
    # Small file (1-5MB)
    small_file = tester.create_test_wav_file(size_mb=2)
    test_files.append(small_file)
    
    # Medium file (10-50MB)
    medium_file = tester.create_test_wav_file(size_mb=15)
    test_files.append(medium_file)
    
    # Large file (just under 100MB)
    large_file = tester.create_test_wav_file(size_mb=95)
    test_files.append(large_file)
    
    # Very large file (over 100MB) - should fail
    very_large_file = tester.create_test_wav_file(size_mb=105)
    test_files.append(very_large_file)
    
    # Upload files and test functionality
    for i, file_path in enumerate(test_files):
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        title = f"Test Audio {i+1} ({file_size:.1f} MB)"
        
        # Skip very large file test if we're not testing error cases
        if file_size > 100:
            print(f"\n🔍 Testing Upload of file larger than 100MB (expecting failure)...")
            with open(file_path, 'rb') as file:
                files = {'file': (os.path.basename(file_path), file, 'audio/wav')}
                data = {'title': title, 'category': test_category}
                
                # This should fail with 413 status code
                success, response = tester.run_test(
                    f"Upload Audio (Over Size Limit: {file_size:.2f} MB)",
                    "POST",
                    "upload-audio",
                    413,  # Expecting 413 Payload Too Large
                    data=data,
                    files=files
                )
                if success:
                    print("✅ Size limit check working correctly")
                else:
                    print("❌ Size limit check failed")
            continue
        
        file_id = tester.test_upload_audio(file_path, title, test_category)
        if file_id:
            print(f"Successfully uploaded file with ID: {file_id}")
            
            # Test getting the file details
            tester.test_get_audio_file(file_id)
            
            # Test streaming the file
            tester.test_stream_audio(file_id)
        else:
            print(f"❌ Failed to upload file: {file_path}")
    
    # Test getting all files
    all_files = tester.test_get_audio_files()
    print(f"Found {len(all_files)} audio files in total")
    
    # Test category filtering
    category_files = tester.test_get_audio_files(test_category)
    print(f"Found {len(category_files)} audio files in category '{test_category}'")
    
    # Clean up
    tester.cleanup()
    
    # Clean up test files
    for file_path in test_files:
        try:
            os.unlink(file_path)
            print(f"Deleted test file: {file_path}")
        except Exception as e:
            print(f"Failed to delete test file {file_path}: {str(e)}")
    
    # Print results
    print(f"\n📊 Tests passed: {tester.tests_passed}/{tester.tests_run}")
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())
