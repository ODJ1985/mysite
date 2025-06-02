#!/usr/bin/env python3
import requests
import os
import sys
import time
import tempfile
import wave
import numpy as np
import uuid
import json
from datetime import datetime

class LargeFileUploadTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_category = f"LargeFileTest_{uuid.uuid4().hex[:6]}"
        self.uploaded_files = []
        self.test_results = {}
        
    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, json_data=None):
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
                if json_data:
                    headers['Content-Type'] = 'application/json'
                    response = requests.post(url, json=json_data, headers=headers)
                else:
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

    def test_regular_upload(self, file_path, file_size):
        """Test regular upload endpoint with a file"""
        print(f"\n🔍 Testing regular upload with {file_size:.2f} MB file...")
        
        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file, 'audio/wav')}
            data = {
                'title': f"Regular Upload Test {file_size:.2f}MB",
                'category': self.test_category
            }
            
            success, response, response_time = self.run_test(
                f"Regular Upload ({file_size:.2f} MB)",
                "POST",
                "upload-audio",
                200 if file_size <= 10 else 413,  # Expect 413 if file is too large
                data=data,
                files=files
            )
            
            self.test_results[f"regular_upload_{file_size:.1f}MB"] = {
                "success": success,
                "response_time": response_time,
                "file_size": file_size,
                "expected_status": 200 if file_size <= 10 else 413
            }
            
            if success and file_size <= 10 and 'file_id' in response:
                self.uploaded_files.append(response['file_id'])
                return response['file_id']
            return None

    def test_chunked_upload(self, file_path, file_size, chunk_size_mb=5):
        """Test chunked upload endpoint with a file"""
        print(f"\n🔍 Testing chunked upload with {file_size:.2f} MB file (chunk size: {chunk_size_mb} MB)...")
        
        # Generate a file ID for this upload
        file_id = str(uuid.uuid4())
        original_filename = os.path.basename(file_path)
        title = f"Chunked Upload Test {file_size:.2f}MB"
        
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
                        
                        self.test_results[f"chunked_upload_{file_size:.1f}MB"] = {
                            "success": True,
                            "response_time": response_time,
                            "file_size": file_size,
                            "chunks": total_chunks,
                            "chunk_size_mb": chunk_size_mb
                        }
                        
                        return file_id
                    else:
                        print(f"❌ Final chunk uploaded but file not marked as completed")
                        return None
        
        return None

    def test_oversized_upload(self, file_path, file_size):
        """Test uploading a file that exceeds the maximum allowed size"""
        print(f"\n🔍 Testing oversized file upload with {file_size:.2f} MB file...")
        
        # For regular upload (should fail)
        regular_result = self.test_regular_upload(file_path, file_size)
        
        # For chunked upload (should fail if > 50MB)
        if file_size > 50:
            # Use a smaller chunk size to ensure we're testing the total file size limit
            chunked_result = self.test_chunked_upload(file_path, file_size, chunk_size_mb=10)
            
            self.test_results[f"oversized_upload_{file_size:.1f}MB"] = {
                "success": chunked_result is None,  # Success means the upload was rejected
                "file_size": file_size,
                "regular_upload_rejected": regular_result is None,
                "chunked_upload_rejected": chunked_result is None
            }
            
            return chunked_result is None
        else:
            self.test_results[f"oversized_upload_{file_size:.1f}MB"] = {
                "success": True,  # Not applicable for files under 50MB
                "file_size": file_size,
                "regular_upload_rejected": regular_result is None,
                "note": "File is under 50MB limit for chunked uploads"
            }
            
            return True

    def test_invalid_chunk_data(self):
        """Test error handling with invalid chunk data"""
        print("\n🔍 Testing invalid chunk data handling...")
        
        # Generate a file ID
        file_id = str(uuid.uuid4())
        
        # Test with missing chunk number
        with tempfile.NamedTemporaryFile(suffix='.chunk', delete=False) as chunk_file:
            chunk_file.write(b"test data")
            chunk_file_path = chunk_file.name
        
        with open(chunk_file_path, 'rb') as chunk_file:
            files = {'chunk': ('chunk_0', chunk_file, 'application/octet-stream')}
            data = {
                # Missing chunk_number
                'total_chunks': 3,
                'file_id': file_id,
                'title': "Invalid Chunk Test",
                'category': self.test_category,
                'original_filename': "test.wav"
            }
            
            success, _, _ = self.run_test(
                "Upload with Missing Chunk Number",
                "POST",
                "upload-audio-chunk",
                422,  # Expect validation error
                data=data,
                files=files
            )
        
        # Clean up
        os.unlink(chunk_file_path)
        
        # Test with invalid total chunks
        with tempfile.NamedTemporaryFile(suffix='.chunk', delete=False) as chunk_file:
            chunk_file.write(b"test data")
            chunk_file_path = chunk_file.name
        
        with open(chunk_file_path, 'rb') as chunk_file:
            files = {'chunk': ('chunk_0', chunk_file, 'application/octet-stream')}
            data = {
                'chunk_number': 0,
                'total_chunks': 0,  # Invalid total chunks
                'file_id': file_id,
                'title': "Invalid Chunk Test",
                'category': self.test_category,
                'original_filename': "test.wav"
            }
            
            success2, _, _ = self.run_test(
                "Upload with Invalid Total Chunks",
                "POST",
                "upload-audio-chunk",
                400,  # Expect bad request
                data=data,
                files=files
            )
        
        # Clean up
        os.unlink(chunk_file_path)
        
        self.test_results["invalid_chunk_data"] = {
            "success": success and success2,
            "missing_chunk_number_rejected": success,
            "invalid_total_chunks_rejected": success2
        }
        
        return success and success2

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
            
            self.test_results[f"get_audio_file_{file_id[:8]}"] = {
                "success": success,
                "response_time": response_time,
                "file_size_mb": response.get('file_size', 0) / (1024 * 1024)
            }
            
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
                
                self.test_results[f"stream_audio_{file_id[:8]}"] = {
                    "success": True,
                    "response_time": response_time,
                    "content_type": response.headers.get('Content-Type'),
                    "first_chunk_size_kb": len(first_chunk)/1024
                }
                
                return True
            else:
                print(f"❌ Failed - Status: {response.status_code}")
                if first_chunk:
                    print(f"   First chunk size: {len(first_chunk)/1024:.2f} KB")
                else:
                    print("   No data received")
                
                self.test_results[f"stream_audio_{file_id[:8]}"] = {
                    "success": False,
                    "response_time": response_time,
                    "status_code": response.status_code
                }
                
                return False
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            
            self.test_results[f"stream_audio_{file_id[:8]}"] = {
                "success": False,
                "error": str(e)
            }
            
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
        
        # Print file upload results
        print("\n📁 File Upload Results:")
        
        for key, result in sorted(self.test_results.items()):
            if "file_size" in result:
                status = "✅ Success" if result["success"] else "❌ Failed"
                print(f"{status} - {key}: {result['file_size']:.2f} MB")
        
        # Print streaming results
        print("\n🎵 Audio Streaming Results:")
        
        for key, result in sorted(self.test_results.items()):
            if key.startswith("stream_audio_"):
                status = "✅ Success" if result["success"] else "❌ Failed"
                print(f"{status} - {key}")
        
        print("\n" + "="*80)
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
    tester = LargeFileUploadTester(backend_url)
    
    # Create test category
    if not tester.create_test_category():
        print("❌ Failed to create test category, aborting tests")
        return 1
    
    # Test files to create
    test_files = [
        (5, "small_test.wav"),      # 5MB - Should work with regular upload
        (10, "medium_test.wav"),    # 10MB - Should work with regular upload (at the limit)
        (15, "large_test.wav"),     # 15MB - Should require chunked upload
        (30, "xlarge_test.wav"),    # 30MB - Should require chunked upload (main test case)
        (45, "xxlarge_test.wav"),   # 45MB - Should require chunked upload (near the limit)
        (55, "oversized_test.wav")  # 55MB - Should be rejected by both methods
    ]
    
    created_files = []
    
    try:
        # Create and test each file
        for size_mb, filename in test_files:
            # Create test file
            file_path, actual_size = tester.create_test_wav_file(size_mb, filename=f"/tmp/{filename}")
            created_files.append(file_path)
            
            # Test regular upload (should work for files <= 10MB)
            if actual_size <= 10:
                file_id = tester.test_regular_upload(file_path, actual_size)
                if file_id:
                    # Test retrieving and streaming the file
                    tester.test_get_audio_file(file_id)
                    tester.test_stream_audio(file_id)
            else:
                # Test that regular upload rejects files > 10MB
                tester.test_regular_upload(file_path, actual_size)
            
            # Test chunked upload (should work for files <= 50MB)
            if actual_size <= 50:
                # Use different chunk sizes based on file size
                chunk_size = 5 if actual_size < 30 else 10
                file_id = tester.test_chunked_upload(file_path, actual_size, chunk_size_mb=chunk_size)
                if file_id:
                    # Test retrieving and streaming the file
                    tester.test_get_audio_file(file_id)
                    tester.test_stream_audio(file_id)
            else:
                # Test that chunked upload rejects files > 50MB
                tester.test_oversized_upload(file_path, actual_size)
        
        # Test error handling with invalid chunk data
        tester.test_invalid_chunk_data()
        
        # Print summary
        tester.print_summary()
        
        # Clean up
        tester.cleanup()
        
        return 0 if tester.tests_passed == tester.tests_run else 1
        
    finally:
        # Clean up test files
        for file_path in created_files:
            try:
                if os.path.exists(file_path):
                    os.unlink(file_path)
                    print(f"Deleted test file: {file_path}")
            except Exception as e:
                print(f"Failed to delete test file {file_path}: {str(e)}")

if __name__ == "__main__":
    sys.exit(main())