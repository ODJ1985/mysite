#!/usr/bin/env python3
import requests
import os
import sys
import time
import tempfile
import wave
import numpy as np
import uuid
from datetime import datetime

class ThirtyMBUploadTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_category = f"30MB_Test_{uuid.uuid4().hex[:6]}"
        self.uploaded_files = []
        
    def run_test(self, name, method, endpoint, expected_status, data=None, files=None):
        """Run a single API test"""
        url = f"{self.base_url}/api/{endpoint}"
        headers = {}
        
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            start_time = time.time()
            if method == 'GET':
                response = requests.get(url, headers=headers)
            elif method == 'POST':
                response = requests.post(url, data=data, files=files, headers=headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers)
            response_time = time.time() - start_time
            
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}, Response time: {response_time:.2f}s")
                try:
                    return success, response.json(), response_time
                except:
                    return success, {}, response_time
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                try:
                    error_detail = response.json().get('detail', 'No detail provided')
                    print(f"Error detail: {error_detail}")
                except:
                    print(f"Response text: {response.text}")
                return False, {}, response_time

        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}, 0

    def create_test_category(self):
        """Create a test category for file uploads"""
        success, response, _ = self.run_test(
            f"Create Category: {self.test_category}",
            "POST",
            "categories",
            200,
            data={"name": self.test_category, "color": "#FF5733"}
        )
        
        if success and 'category_id' in response:
            print(f"✅ Created test category: {self.test_category}")
            return True
        return False

    def create_test_wav_file(self, size_mb, filename=None):
        """Create a test WAV file with specified size in MB"""
        if filename is None:
            temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
            filename = temp_file.name
            temp_file.close()
        
        # Set parameters
        sample_rate = 44100  # Hz
        
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
        
        file_size = os.path.getsize(filename) / (1024 * 1024)
        print(f"Created test WAV file: {filename}, Duration: {duration:.2f}s, Size: {file_size:.2f} MB")
        return filename, file_size

    def test_chunked_upload(self, file_path, file_size, chunk_size_mb=5):
        """Test chunked upload endpoint with a file"""
        print(f"\n🔍 Testing chunked upload with {file_size:.2f} MB file (chunk size: {chunk_size_mb} MB)...")
        
        # Generate a file ID for this upload
        file_id = str(uuid.uuid4())
        original_filename = os.path.basename(file_path)
        title = f"30MB Test {datetime.now().strftime('%H:%M:%S')}"
        
        # Calculate chunk size in bytes
        chunk_size_bytes = chunk_size_mb * 1024 * 1024
        
        # Read the file
        with open(file_path, 'rb') as f:
            file_data = f.read()
        
        # Calculate total chunks
        total_chunks = (len(file_data) + chunk_size_bytes - 1) // chunk_size_bytes
        print(f"File will be split into {total_chunks} chunks")
        
        # Upload each chunk
        for chunk_number in range(total_chunks):
            chunk_start = chunk_number * chunk_size_bytes
            chunk_end = min(chunk_start + chunk_size_bytes, len(file_data))
            chunk_data = file_data[chunk_start:chunk_end]
            
            # Create a temporary file for the chunk
            with tempfile.NamedTemporaryFile(suffix='.chunk', delete=False) as chunk_file:
                chunk_file.write(chunk_data)
                chunk_file_path = chunk_file.name
            
            # Upload the chunk
            with open(chunk_file_path, 'rb') as chunk_file:
                files = {'chunk': (f'chunk_{chunk_number}', chunk_file, 'application/octet-stream')}
                data = {
                    'chunk_number': chunk_number,
                    'total_chunks': total_chunks,
                    'file_id': file_id,
                    'title': title,
                    'category': self.test_category,
                    'original_filename': original_filename
                }
                
                success, response, response_time = self.run_test(
                    f"Upload Chunk {chunk_number+1}/{total_chunks} ({len(chunk_data)/1024/1024:.2f} MB)",
                    "POST",
                    "upload-audio-chunk",
                    200,
                    data=data,
                    files=files
                )
                
                # Clean up the temporary chunk file
                os.unlink(chunk_file_path)
                
                if not success:
                    print(f"❌ Failed to upload chunk {chunk_number+1}/{total_chunks}")
                    return None
                
                # Check if this was the last chunk
                if chunk_number == total_chunks - 1:
                    if 'completed' in response and response['completed']:
                        print(f"✅ All chunks uploaded successfully. File ID: {file_id}")
                        self.uploaded_files.append(file_id)
                        return file_id
                    else:
                        print(f"❌ Final chunk uploaded but file not marked as completed")
                        return None
        
        return None

    def test_get_audio_file(self, file_id):
        """Test retrieving an uploaded audio file"""
        success, response, response_time = self.run_test(
            f"Get Audio File (ID: {file_id})",
            "GET",
            f"audio-file/{file_id}",
            200
        )
        
        if success:
            print(f"✅ Retrieved audio file details:")
            print(f"   Title: {response.get('title')}")
            print(f"   Size: {response.get('file_size', 0) / (1024 * 1024):.2f} MB")
            print(f"   Category: {response.get('category')}")
            print(f"   File URL: {response.get('file_url')}")
            return response
        return None

    def test_stream_audio(self, file_id):
        """Test streaming an uploaded audio file"""
        url = f"{self.base_url}/api/audio-stream/{file_id}"
        
        self.tests_run += 1
        print(f"\n🔍 Testing Audio Streaming (ID: {file_id})...")
        
        try:
            start_time = time.time()
            response = requests.get(url, stream=True)
            
            # Get the first chunk to verify streaming works
            first_chunk = next(response.iter_content(chunk_size=1024*1024), None)
            response_time = time.time() - start_time
            
            if response.status_code == 200 and first_chunk:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}, Content-Type: {response.headers.get('Content-Type')}")
                print(f"   First chunk size: {len(first_chunk)/1024:.2f} KB, Response time: {response_time:.2f}s")
                return True
            else:
                print(f"❌ Failed - Status: {response.status_code}")
                if first_chunk:
                    print(f"   First chunk size: {len(first_chunk)/1024:.2f} KB")
                else:
                    print("   No data received")
                return False
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False

    def cleanup(self):
        """Clean up test resources"""
        print("\n🧹 Cleaning up resources...")
        
        # Delete uploaded files
        for file_id in self.uploaded_files[:]:
            success, _, _ = self.run_test(
                f"Delete Audio File (ID: {file_id})",
                "DELETE",
                f"audio-file/{file_id}",
                200
            )
            
            if success:
                self.uploaded_files.remove(file_id)
                print(f"✅ Deleted audio file: {file_id}")
            else:
                print(f"❌ Failed to delete audio file: {file_id}")

    def print_summary(self):
        """Print a summary of test results"""
        print("\n" + "="*80)
        print(f"📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        print("="*80)
        
        if self.tests_passed == self.tests_run:
            print("🎉 All tests passed successfully!")
        else:
            print(f"⚠️ {self.tests_run - self.tests_passed} tests failed. See details above.")
        print("="*80)

def get_backend_url():
    """Get the backend URL from the frontend .env file"""
    env_file_path = "/app/frontend/.env"
    try:
        with open(env_file_path, "r") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.strip().split("=", 1)[1].strip('"\'')
    except Exception as e:
        print(f"Error reading frontend/.env file: {e}")
    
    # Fallback to hardcoded URL
    return "http://localhost:8001"

def main():
    # Get the backend URL
    backend_url = get_backend_url()
    print(f"🚀 Testing backend at: {backend_url}")
    
    # Initialize tester
    tester = ThirtyMBUploadTester(backend_url)
    
    # Create test category
    if not tester.create_test_category():
        print("❌ Failed to create test category, aborting tests")
        return 1
    
    try:
        # Create a 30MB test file
        file_path, actual_size = tester.create_test_wav_file(30, filename="/tmp/thirty_mb_test.wav")
        
        # Test with different chunk sizes
        chunk_sizes = [5, 10, 15]
        
        for chunk_size in chunk_sizes:
            print(f"\n=== Testing with {chunk_size}MB chunk size ===")
            
            # Test chunked upload
            file_id = tester.test_chunked_upload(file_path, actual_size, chunk_size_mb=chunk_size)
            
            if file_id:
                # Test retrieving the file
                tester.test_get_audio_file(file_id)
                
                # Test streaming the file
                tester.test_stream_audio(file_id)
                
                # Delete the file to save space
                tester.cleanup()
            else:
                print(f"❌ Failed to upload 30MB file with {chunk_size}MB chunks")
        
        # Print summary
        tester.print_summary()
        
        # Clean up
        os.unlink(file_path)
        print(f"Deleted test file: {file_path}")
        
        return 0 if tester.tests_passed == tester.tests_run else 1
        
    except Exception as e:
        print(f"❌ Test failed with error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())