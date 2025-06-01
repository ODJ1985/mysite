import requests
import unittest
import sys
import os
import io
import random
import time
from datetime import datetime

class FileUploadImprovementsTester:
    def __init__(self, base_url="https://9fe0c2b0-7831-40b8-a607-5c9b24890339.preview.emergentagent.com"):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_category = None
        
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
    
    def setup_test_category(self):
        """Set up a test category for uploads"""
        # Get existing categories
        success, response = self.run_test(
            "Get Categories",
            "GET",
            "api/categories",
            200
        )
        
        if success:
            categories = response.get('categories', [])
            if len(categories) > 0:
                self.test_category = categories[0].get('name')
                print(f"Using existing category: {self.test_category}")
                return True
            else:
                # Create a test category
                test_category_name = f"Test Category {datetime.now().strftime('%H%M%S')}"
                success, _ = self.run_test(
                    f"Create Category '{test_category_name}'",
                    "POST",
                    "api/categories",
                    200,
                    data={"name": test_category_name, "color": "#3B82F6"}
                )
                if success:
                    self.test_category = test_category_name
                    print(f"Created new category: {self.test_category}")
                    return True
        
        print("❌ Failed to set up test category")
        return False
    
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
    
    def test_upload_audio_file(self, file_size_mb, expected_status=200):
        """Test uploading an audio file with specified size"""
        if not self.test_category:
            print("❌ No test category available")
            return False, None
            
        # Generate a random WAV file of specified size
        print(f"Generating {file_size_mb}MB test WAV file...")
        file_content = self._generate_test_wav_file(file_size_mb)
        
        # Prepare the file for upload
        files = {
            'file': (f'test_audio_{file_size_mb}MB.wav', file_content, 'audio/wav')
        }
        
        # Prepare form data
        data = {
            'title': f'Test Audio {file_size_mb}MB',
            'category': self.test_category
        }
        
        # Run the test
        test_name = f"Upload {file_size_mb}MB Audio File"
        start_time = time.time()
        success, response = self.run_test(
            test_name,
            "POST",
            "api/upload-audio",
            expected_status,
            data=data,
            files=files
        )
        end_time = time.time()
        
        if success:
            upload_time = end_time - start_time
            print(f"Successfully uploaded {file_size_mb}MB audio file in {upload_time:.2f} seconds")
            return True, response.get('file_id', None)
        else:
            error_detail = response.get('detail', 'Unknown error')
            print(f"Failed to upload {file_size_mb}MB audio file: {error_detail}")
            return False, None
    
    def test_file_size_limit(self):
        """Test the 100MB file size limit for audio uploads"""
        print("\n🔍 Testing file size limit functionality...")
        
        # Test uploading a file that's just over 100MB (should fail with 413 status code)
        file_size_mb = 101
        print(f"\nGenerating {file_size_mb}MB test WAV file (exceeding limit)...")
        file_content = self._generate_test_wav_file(file_size_mb)
        
        # Prepare the form data
        files = {
            'file': (f'test_audio_{file_size_mb}MB.wav', file_content, 'audio/wav')
        }
        data = {
            'title': f'Test Audio {file_size_mb}MB',
            'category': self.test_category
        }
        
        self.tests_run += 1
        print(f"\n🔍 Testing Upload of file exceeding 100MB limit...")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/upload-audio",
                files=files,
                data=data
            )
            
            # Check if the request was rejected with a 413 status code
            if response.status_code == 413 and "File size must be less than 100MB" in response.text:
                self.tests_passed += 1
                print("✅ Passed - Server correctly rejected file over 100MB with 413 status code")
                try:
                    print(f"Response: {response.json()}")
                except:
                    print(f"Response: {response.text}")
                return True
            else:
                print(f"❌ Failed - Expected 413 status code with size limit message, got {response.status_code}")
                print(f"Response: {response.text}")
                return False
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False
    
    def test_upload_performance(self):
        """Test upload performance with different file sizes"""
        print("\n🔍 Testing upload performance with different file sizes...")
        
        results = []
        
        # Test with different file sizes
        for size_mb in [1, 5, 10, 20]:
            print(f"\nTesting {size_mb}MB file upload performance...")
            
            # Generate a random WAV file
            file_content = self._generate_test_wav_file(size_mb)
            
            # Prepare the form data
            files = {
                'file': (f'test_audio_{size_mb}MB.wav', file_content, 'audio/wav')
            }
            data = {
                'title': f'Performance Test {size_mb}MB',
                'category': self.test_category
            }
            
            self.tests_run += 1
            print(f"🔍 Uploading {size_mb}MB file...")
            
            try:
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}/api/upload-audio",
                    files=files,
                    data=data
                )
                end_time = time.time()
                
                upload_time = end_time - start_time
                
                if response.status_code == 200:
                    self.tests_passed += 1
                    print(f"✅ Passed - {size_mb}MB file uploaded in {upload_time:.2f} seconds")
                    results.append((size_mb, upload_time))
                else:
                    print(f"❌ Failed - Upload failed with status code {response.status_code}")
                    print(f"Response: {response.text}")
            except Exception as e:
                print(f"❌ Failed - Error: {str(e)}")
        
        # Print performance results
        if results:
            print("\n📊 Upload Performance Results:")
            print("="*50)
            print("File Size (MB) | Upload Time (s) | Speed (MB/s)")
            print("-"*50)
            for size_mb, upload_time in results:
                speed = size_mb / upload_time if upload_time > 0 else 0
                print(f"{size_mb:13} | {upload_time:14.2f} | {speed:11.2f}")
            print("="*50)
        
        return len(results) > 0
    
    def print_summary(self):
        """Print test results summary"""
        print("\n" + "="*50)
        print(f"📊 FILE UPLOAD IMPROVEMENTS TEST SUMMARY: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*50)
        if self.tests_passed == self.tests_run:
            print("✅ All tests passed!")
        else:
            print(f"❌ {self.tests_run - self.tests_passed} tests failed")
        print("="*50)

def main():
    # Setup
    tester = FileUploadImprovementsTester()
    
    # Run tests
    print("\n🚀 Starting File Upload Improvements Tests...")
    
    # Setup test category
    if not tester.setup_test_category():
        print("❌ Failed to set up test category, stopping tests")
        tester.print_summary()
        return 1
    
    # Test small file upload (1MB)
    small_file_ok, small_file_id = tester.test_upload_audio_file(1)
    
    # Test medium file upload (10MB)
    medium_file_ok, medium_file_id = tester.test_upload_audio_file(10)
    
    # Test larger file upload (20MB)
    larger_file_ok, larger_file_id = tester.test_upload_audio_file(20)
    
    # Test file just under the limit (99MB)
    # Note: This test is optional as it takes a long time
    # under_limit_ok, under_limit_id = tester.test_upload_audio_file(99)
    
    # Test file size limit (101MB)
    tester.test_file_size_limit()
    
    # Test upload performance
    tester.test_upload_performance()
    
    # Print summary
    tester.print_summary()
    return 0 if tester.tests_passed == tester.tests_run else 1

if __name__ == "__main__":
    sys.exit(main())