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
        self.test_results = {}

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

    def test_health_check(self):
        """Test the health check endpoint"""
        success, response, response_time = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        self.test_results["health_check"] = {
            "success": success,
            "response_time": response_time
        }
        return success

    def test_create_category(self, name, color="#3B82F6"):
        """Create a category"""
        success, response, response_time = self.run_test(
            f"Create Category: {name}",
            "POST",
            "categories",
            200,
            data={"name": name, "color": color}
        )
        if success and 'category_id' in response:
            self.categories.append(name)
            self.test_results[f"create_category_{name}"] = {
                "success": success,
                "response_time": response_time
            }
            return response.get('category_id')
        self.test_results[f"create_category_{name}"] = {
            "success": False,
            "response_time": response_time
        }
        return None

    def test_get_categories(self):
        """Get all categories"""
        success, response, response_time = self.run_test(
            "Get Categories",
            "GET",
            "categories",
            200
        )
        self.test_results["get_categories"] = {
            "success": success,
            "response_time": response_time,
            "count": len(response.get('categories', []))
        }
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
        
        file_size = os.path.getsize(filename) / (1024 * 1024)
        print(f"Created test WAV file: {filename}, Duration: {duration:.2f}s, Size: {file_size:.2f} MB")
        return filename

    def test_upload_audio(self, file_path, title, category):
        """Test uploading an audio file"""
        file_size = os.path.getsize(file_path) / (1024 * 1024)  # Size in MB
        print(f"Uploading file: {file_path}, Size: {file_size:.2f} MB")
        
        with open(file_path, 'rb') as file:
            files = {'file': (os.path.basename(file_path), file, 'audio/wav')}
            data = {'title': title, 'category': category}
            
            success, response, response_time = self.run_test(
                f"Upload Audio ({file_size:.2f} MB)",
                "POST",
                "upload-audio",
                200,
                data=data,
                files=files
            )
            
            self.test_results[f"upload_audio_{file_size:.1f}MB"] = {
                "success": success,
                "response_time": response_time,
                "file_size": file_size
            }
            
            if success and 'file_id' in response:
                self.uploaded_files.append(response['file_id'])
                return response['file_id']
            return None

    def test_get_audio_files(self, category=None):
        """Get all audio files, optionally filtered by category"""
        endpoint = "audio-files"
        test_name = "get_audio_files"
        if category:
            endpoint += f"?category={category}"
            test_name = f"get_audio_files_{category}"
            
        success, response, response_time = self.run_test(
            f"Get Audio Files{' (filtered by ' + category + ')' if category else ''}",
            "GET",
            endpoint,
            200
        )
        
        self.test_results[test_name] = {
            "success": success,
            "response_time": response_time,
            "count": len(response.get('audio_files', []))
        }
        
        if success and 'audio_files' in response:
            return response['audio_files']
        return []

    def test_get_audio_file(self, file_id):
        """Get a specific audio file by ID"""
        success, response, response_time = self.run_test(
            f"Get Audio File (ID: {file_id})",
            "GET",
            f"audio-file/{file_id}",
            200
        )
        
        self.test_results[f"get_audio_file_{file_id[:8]}"] = {
            "success": success,
            "response_time": response_time
        }
        
        return success

    def test_delete_audio_file(self, file_id):
        """Delete an audio file"""
        success, _, response_time = self.run_test(
            f"Delete Audio File (ID: {file_id})",
            "DELETE",
            f"audio-file/{file_id}",
            200
        )
        
        self.test_results[f"delete_audio_file_{file_id[:8]}"] = {
            "success": success,
            "response_time": response_time
        }
        
        if success and file_id in self.uploaded_files:
            self.uploaded_files.remove(file_id)
        return success

    def test_stream_audio(self, file_id):
        """Test streaming an audio file"""
        url = f"{self.base_url}/api/audio-stream/{file_id}"
        
        self.tests_run += 1
        print(f"\n🔍 Testing Audio Streaming (ID: {file_id})...")
        
        try:
            start_time = time.time()
            response = requests.get(url, stream=True)
            # Just check if we can get the first chunk of data
            next(response.iter_content(chunk_size=1024), None)
            response_time = time.time() - start_time
            
            if response.status_code == 200:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}, Content-Type: {response.headers.get('Content-Type')}, Response time: {response_time:.2f}s")
                
                self.test_results[f"stream_audio_{file_id[:8]}"] = {
                    "success": True,
                    "response_time": response_time,
                    "content_type": response.headers.get('Content-Type')
                }
                
                return True
            else:
                print(f"❌ Failed - Expected 200, got {response.status_code}")
                
                self.test_results[f"stream_audio_{file_id[:8]}"] = {
                    "success": False,
                    "response_time": response_time
                }
                
                return False
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            
            self.test_results[f"stream_audio_{file_id[:8]}"] = {
                "success": False,
                "response_time": 0,
                "error": str(e)
            }
            
            return False

    def test_file_size_limits(self):
        """Test file size limits by uploading files of increasing size"""
        print("\n🔍 Testing file size limits...")
        
        # Test with different file sizes
        test_sizes = [1, 5, 10, 20, 30, 40, 45, 47, 48]
        max_successful_size = 0
        min_failed_size = float('inf')
        
        test_category = f"Size Test {datetime.now().strftime('%H%M%S')}"
        category_id = self.test_create_category(test_category)
        
        if not category_id:
            print("❌ Failed to create test category for size testing")
            return None
        
        test_files = []
        results = {}
        
        for size_mb in test_sizes:
            test_file = self.create_test_wav_file(size_mb=size_mb)
            test_files.append(test_file)
            
            title = f"Size Test {size_mb}MB"
            file_id = self.test_upload_audio(test_file, title, test_category)
            
            results[size_mb] = {
                "success": file_id is not None,
                "file_id": file_id
            }
            
            if file_id:
                max_successful_size = max(max_successful_size, size_mb)
                # Test streaming for successful uploads
                streaming_success = self.test_stream_audio(file_id)
                results[size_mb]["streaming"] = streaming_success
            else:
                min_failed_size = min(min_failed_size, size_mb)
        
        # Clean up test files
        for file_path in test_files:
            try:
                os.unlink(file_path)
                print(f"Deleted test file: {file_path}")
            except Exception as e:
                print(f"Failed to delete test file {file_path}: {str(e)}")
        
        self.test_results["file_size_limits"] = {
            "max_successful_size": max_successful_size,
            "min_failed_size": min_failed_size if min_failed_size != float('inf') else "Not found",
            "detailed_results": results
        }
        
        print(f"\n📊 File size limit test results:")
        print(f"Maximum successful upload size: {max_successful_size} MB")
        print(f"Minimum failed upload size: {min_failed_size if min_failed_size != float('inf') else 'Not found'} MB")
        
        return max_successful_size

    def cleanup(self):
        """Clean up any created resources"""
        print("\n🧹 Cleaning up resources...")
        
        # Delete uploaded files
        for file_id in self.uploaded_files[:]:
            self.test_delete_audio_file(file_id)

    def print_performance_summary(self):
        """Print a summary of performance metrics"""
        print("\n📊 Performance Summary:")
        
        # Calculate average response times by operation type
        operation_times = {
            "upload": [],
            "download": [],
            "list": [],
            "create": [],
            "delete": []
        }
        
        for key, result in self.test_results.items():
            if "response_time" not in result:
                continue
                
            if key.startswith("upload_audio"):
                operation_times["upload"].append(result["response_time"])
            elif key.startswith("stream_audio"):
                operation_times["download"].append(result["response_time"])
            elif key.startswith("get_audio_files"):
                operation_times["list"].append(result["response_time"])
            elif key.startswith("create_category"):
                operation_times["create"].append(result["response_time"])
            elif key.startswith("delete_audio_file"):
                operation_times["delete"].append(result["response_time"])
        
        # Print average times
        for operation, times in operation_times.items():
            if times:
                avg_time = sum(times) / len(times)
                print(f"Average {operation} response time: {avg_time:.3f}s")
        
        # Print file size limit information
        if "file_size_limits" in self.test_results:
            limits = self.test_results["file_size_limits"]
            print(f"\nFile size limits:")
            print(f"Maximum successful upload size: {limits['max_successful_size']} MB")
            print(f"Minimum failed upload size: {limits['min_failed_size']} MB")

def main():
    # Get backend URL from environment or use the one from frontend/.env
    backend_url = "https://69b0f385-191d-4d9c-8f85-af6b574a2e14.preview.emergentagent.com"
    
    print(f"🚀 Starting Comprehensive Podcast API Tests against {backend_url}")
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
    
    # Test file upload with different sizes for normal operation
    test_files = []
    
    # Small file (1MB)
    small_file = tester.create_test_wav_file(size_mb=1)
    test_files.append(small_file)
    
    # Medium file (5MB)
    medium_file = tester.create_test_wav_file(size_mb=5)
    test_files.append(medium_file)
    
    # Larger file (10MB)
    larger_file = tester.create_test_wav_file(size_mb=10)
    test_files.append(larger_file)
    
    # Upload files and test functionality
    for i, file_path in enumerate(test_files):
        file_size = os.path.getsize(file_path) / (1024 * 1024)
        title = f"Test Audio {i+1} ({file_size:.1f} MB)"
        
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
    
    # Test file size limits
    max_size = tester.test_file_size_limits()
    print(f"Maximum file size that can be uploaded: {max_size} MB")
    
    # Print performance summary
    tester.print_performance_summary()
    
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