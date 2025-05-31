import requests
import unittest
import sys
import os
import io
import random
from datetime import datetime

class PodcastHubAPITester:
    def __init__(self, base_url="https://9fe0c2b0-7831-40b8-a607-5c9b24890339.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0

    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
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
                    print(f"Response: {response.text}")
                    return False, response.json()
                except:
                    return False, {}

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}

    def test_health_endpoint(self):
        """Test the health endpoint"""
        success, response = self.run_test(
            "Health Endpoint",
            "GET",
            "api/health",
            200
        )
        if success:
            print(f"Health check response: {response}")
        return success

    def test_get_categories(self):
        """Test getting all categories"""
        success, response = self.run_test(
            "Get Categories",
            "GET",
            "api/categories",
            200
        )
        if success:
            categories = response.get('categories', [])
            print(f"Found {len(categories)} categories")
            for category in categories:
                print(f"  - {category.get('name', 'Unknown')}")
        return success, response.get('categories', [])

    def test_create_category(self, name):
        """Test creating a new category"""
        success, response = self.run_test(
            f"Create Category '{name}'",
            "POST",
            "api/categories",
            200,
            data={"name": name, "color": "#3B82F6"}
        )
        if success:
            print(f"Category created with ID: {response.get('category_id', 'Unknown')}")
        return success

    def test_get_audio_files(self, category=None):
        """Test getting audio files, optionally filtered by category"""
        endpoint = "api/audio-files"
        if category:
            endpoint += f"?category={category}"
            
        success, response = self.run_test(
            f"Get Audio Files{' for category: ' + category if category else ''}",
            "GET",
            endpoint,
            200
        )
        if success:
            audio_files = response.get('audio_files', [])
            print(f"Found {len(audio_files)} audio files")
            for audio in audio_files[:5]:  # Show first 5 only to avoid too much output
                print(f"  - {audio.get('title', 'Unknown')} ({audio.get('category', 'No category')})")
            if len(audio_files) > 5:
                print(f"  ... and {len(audio_files) - 5} more")
        return success, response.get('audio_files', [])

    def test_audio_file_endpoint(self, file_id):
        """Test getting a specific audio file"""
        success, response = self.run_test(
            f"Get Audio File {file_id}",
            "GET",
            f"api/audio-file/{file_id}",
            200
        )
        if success:
            print(f"Audio file details: {response.get('title', 'Unknown')}")
        return success

    def test_audio_stream_endpoint(self, file_id):
        """Test the audio streaming endpoint"""
        url = f"{self.base_url}/api/audio-stream/{file_id}"
        print(f"\n🔍 Testing Audio Stream for file {file_id}...")
        
        self.tests_run += 1
        try:
            response = requests.get(url, stream=True)
            if response.status_code == 200:
                self.tests_passed += 1
                content_type = response.headers.get('Content-Type', '')
                print(f"✅ Passed - Status: {response.status_code}, Content-Type: {content_type}")
                # Just read a small part to verify stream works
                chunk = next(response.iter_content(chunk_size=1024), None)
                if chunk:
                    print(f"Successfully read {len(chunk)} bytes from audio stream")
                return True
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False
            
    def test_upload_audio_file(self, file_size_mb, category_name, expected_status=200):
        """Test uploading an audio file with specified size"""
        # Generate a random WAV file of specified size
        file_content = self._generate_test_wav_file(file_size_mb)
        
        # Prepare the file for upload
        files = {
            'file': ('test_audio.wav', file_content, 'audio/wav')
        }
        
        # Prepare form data
        data = {
            'title': f'Test Audio {file_size_mb}MB',
            'category': category_name
        }
        
        # Run the test
        test_name = f"Upload {file_size_mb}MB Audio File"
        success, response = self.run_test(
            test_name,
            "POST",
            "api/upload-audio",
            expected_status,
            data=data,
            files=files
        )
        
        if success:
            print(f"Successfully uploaded {file_size_mb}MB audio file")
            return True, response.get('file_id', None)
        else:
            error_detail = response.get('detail', 'Unknown error')
            print(f"Failed to upload {file_size_mb}MB audio file: {error_detail}")
            return False, None
    
    def _generate_test_wav_file(self, size_mb):
        """Generate a test WAV file of specified size in MB"""
        # Simple WAV header (44 bytes)
        wav_header = bytes([
            # RIFF header
            0x52, 0x49, 0x46, 0x46,  # "RIFF"
            0x24, 0x00, 0x00, 0x00,  # Chunk size (placeholder)
            0x57, 0x41, 0x56, 0x45,  # "WAVE"
            
            # Format subchunk
            0x66, 0x6d, 0x74, 0x20,  # "fmt "
            0x10, 0x00, 0x00, 0x00,  # Subchunk1 size (16 bytes)
            0x01, 0x00,              # Audio format (1 = PCM)
            0x01, 0x00,              # Num channels (1)
            0x44, 0xac, 0x00, 0x00,  # Sample rate (44100)
            0x88, 0x58, 0x01, 0x00,  # Byte rate
            0x02, 0x00,              # Block align
            0x10, 0x00,              # Bits per sample (16)
            
            # Data subchunk
            0x64, 0x61, 0x74, 0x61,  # "data"
            0x00, 0x00, 0x00, 0x00   # Subchunk2 size (placeholder)
        ])
        
        # Calculate data size (1MB = 1048576 bytes)
        data_size = int(size_mb * 1024 * 1024) - len(wav_header)
        
        # Update chunk sizes in header
        wav_header_list = bytearray(wav_header)
        # RIFF chunk size = file size - 8
        riff_chunk_size = data_size + 36  # 36 = size of header - 8
        wav_header_list[4:8] = riff_chunk_size.to_bytes(4, byteorder='little')
        # Data chunk size
        wav_header_list[40:44] = data_size.to_bytes(4, byteorder='little')
        
        # Create file content with header and random data
        file_content = io.BytesIO()
        file_content.write(bytes(wav_header_list))
        
        # Generate random audio data in chunks to avoid memory issues
        chunk_size = min(1024 * 1024, data_size)  # 1MB chunks or smaller
        remaining = data_size
        
        while remaining > 0:
            current_chunk = min(chunk_size, remaining)
            random_data = bytes([random.randint(0, 255) for _ in range(current_chunk)])
            file_content.write(random_data)
            remaining -= current_chunk
        
        file_content.seek(0)
        return file_content

    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*50)
        print(f"📊 API TEST SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*50)
        if self.tests_passed == self.tests_run:
            print("✅ All tests passed!")
        else:
            print(f"❌ {self.tests_run - self.tests_passed} tests failed")
        print("="*50)

def main():
    # Setup
    tester = PodcastHubAPITester()
    
    # Run tests
    print("\n🚀 Starting PodcastHub API Tests...")
    
    # Test health endpoint
    health_ok = tester.test_health_endpoint()
    if not health_ok:
        print("❌ Health check failed, stopping tests")
        tester.print_summary()
        return 1
    
    # Test categories
    categories_ok, existing_categories = tester.test_get_categories()
    
    # Create a test category if none exist
    if categories_ok and len(existing_categories) == 0:
        test_category_name = f"Test Category {datetime.now().strftime('%H%M%S')}"
        tester.test_create_category(test_category_name)
        # Refresh categories
        categories_ok, existing_categories = tester.test_get_categories()
    
    # Test audio files
    audio_ok, audio_files = tester.test_get_audio_files()
    
    # Test category filtering if we have categories and audio files
    if categories_ok and audio_ok and len(existing_categories) > 0 and len(audio_files) > 0:
        # Get the first category name
        first_category = existing_categories[0].get('name')
        if first_category:
            tester.test_get_audio_files(first_category)
    
    # Test specific audio file if we have any
    if audio_ok and len(audio_files) > 0:
        first_audio = audio_files[0]
        file_id = first_audio.get('id')
        if file_id:
            tester.test_audio_file_endpoint(file_id)
            tester.test_audio_stream_endpoint(file_id)
    
    # Print summary
    tester.print_summary()
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())