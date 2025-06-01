import requests
import os
import tempfile
import wave
import numpy as np
import sys
import time
import json

class FileSizeLimitTester:
    def __init__(self, base_url="https://69b0f385-191d-4d9c-8f85-af6b574a2e14.preview.emergentagent.com"):
        self.base_url = base_url
        self.category_name = None
        self.results = []
        
    def create_test_wav_file(self, size_mb):
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

    def ensure_category_exists(self):
        """Make sure we have a category for testing"""
        if self.category_name:
            return True
            
        category_name = f"Test Category {int(time.time())}"
        
        try:
            response = requests.post(
                f"{self.base_url}/api/categories",
                data={"name": category_name, "color": "#3B82F6"}
            )
            
            if response.status_code == 200:
                print(f"✅ Created category: {category_name}")
                self.category_name = category_name
                return True
            else:
                print(f"❌ Failed to create category: {response.status_code}")
                try:
                    error_detail = response.json().get('detail', 'No detail provided')
                    print(f"Error detail: {error_detail}")
                except:
                    pass
                return False
                
        except Exception as e:
            print(f"❌ Error creating category: {str(e)}")
            return False

    def test_upload_file(self, size_mb):
        """Test uploading a file of specified size"""
        print(f"\n🔍 Testing upload of {size_mb}MB file...")
        
        # Ensure we have a category
        if not self.ensure_category_exists():
            print("❌ Cannot proceed without a category")
            return False
        
        # Create test file
        file_path = self.create_test_wav_file(size_mb)
        
        # Upload file
        try:
            with open(file_path, 'rb') as f:
                files = {'file': ('test_audio.wav', f, 'audio/wav')}
                form_data = {
                    'title': f"Test Audio {size_mb}MB {int(time.time())}",
                    'category': self.category_name
                }
                
                start_time = time.time()
                response = requests.post(
                    f"{self.base_url}/api/upload-audio",
                    files=files,
                    data=form_data
                )
                end_time = time.time()
                
                # Record result
                result = {
                    "size_mb": size_mb,
                    "status_code": response.status_code,
                    "upload_time": round(end_time - start_time, 2),
                    "success": False,
                    "error": None,
                    "file_id": None
                }
                
                # Check if successful
                if response.status_code == 200:
                    result["success"] = True
                    result["file_id"] = response.json().get('file_id')
                    print(f"✅ {size_mb}MB upload succeeded in {result['upload_time']}s")
                    print(f"   File ID: {result['file_id']}")
                else:
                    try:
                        error_detail = response.json().get('detail', 'No detail provided')
                        result["error"] = error_detail
                        print(f"❌ {size_mb}MB upload failed with status {response.status_code}")
                        print(f"   Error: {error_detail}")
                    except:
                        result["error"] = f"Status code: {response.status_code}"
                        print(f"❌ {size_mb}MB upload failed with status {response.status_code}")
                
                self.results.append(result)
                return result["success"]
                
        except Exception as e:
            print(f"❌ Error during upload: {str(e)}")
            self.results.append({
                "size_mb": size_mb,
                "status_code": None,
                "upload_time": None,
                "success": False,
                "error": str(e),
                "file_id": None
            })
            return False
        finally:
            # Clean up
            try:
                os.unlink(file_path)
            except:
                pass

    def get_existing_files(self):
        """Get information about existing files in the system"""
        print("\n🔍 Checking existing files in the system...")
        
        try:
            response = requests.get(f"{self.base_url}/api/audio-files")
            
            if response.status_code == 200:
                files = response.json().get('audio_files', [])
                print(f"✅ Found {len(files)} existing files")
                
                # Sort by file size
                files.sort(key=lambda x: x.get('file_size', 0), reverse=True)
                
                # Print the largest files
                if files:
                    print("\nLargest files in the system:")
                    for i, file in enumerate(files[:5]):
                        size_mb = file.get('file_size', 0) / (1024 * 1024)
                        uploaded = file.get('uploaded_at', 'unknown')
                        print(f"{i+1}. {file.get('title')} - {size_mb:.2f}MB - Uploaded: {uploaded}")
                
                return files
            else:
                print(f"❌ Failed to get files: {response.status_code}")
                return []
                
        except Exception as e:
            print(f"❌ Error getting files: {str(e)}")
            return []

    def print_summary(self):
        """Print a summary of test results"""
        print("\n===== Test Results Summary =====")
        
        if self.results:
            print("\nFile Upload Results:")
            print("-" * 80)
            print(f"{'Size (MB)':<10} {'Status':<10} {'Upload Time':<15} {'Result':<10} {'Error/ID'}")
            print("-" * 80)
            
            for result in self.results:
                status = result.get('status_code', 'Error')
                time_str = f"{result.get('upload_time', 'N/A')}s" if result.get('upload_time') else 'N/A'
                success = "Success" if result.get('success') else "Failed"
                error_or_id = result.get('file_id') if result.get('success') else result.get('error', 'Unknown error')
                
                print(f"{result.get('size_mb'):<10} {status:<10} {time_str:<15} {success:<10} {error_or_id}")
        
        # Determine the actual limit based on results
        if self.results:
            successful_sizes = [r['size_mb'] for r in self.results if r['success']]
            failed_sizes = [r['size_mb'] for r in self.results if not r['success']]
            
            if successful_sizes:
                max_successful = max(successful_sizes)
                print(f"\nLargest successful upload: {max_successful}MB")
            
            if failed_sizes:
                min_failed = min(failed_sizes)
                print(f"Smallest failed upload: {min_failed}MB")
            
            # Determine the boundary
            if successful_sizes and failed_sizes:
                boundary = (max_successful + min_failed) / 2
                print(f"\nEstimated file size limit boundary: {boundary}MB")
                
                # Recommend a safe limit for UI
                safe_limit = int(max_successful * 0.95)  # 95% of max successful size
                print(f"Recommended UI file size limit: {safe_limit}MB")
            elif successful_sizes:
                print("\nAll tested sizes were successful. The limit may be higher than tested.")
            elif failed_sizes:
                print("\nAll tested sizes failed. The limit may be lower than tested.")

def main():
    tester = FileSizeLimitTester()
    
    print("===== wyEBIYA Podcast File Size Limit Test =====")
    
    # Check existing files first
    existing_files = tester.get_existing_files()
    
    # Test with various file sizes as specified in the requirements
    test_sizes = [1, 3, 5, 6, 7, 8, 10, 15, 20]
    
    for size in test_sizes:
        tester.test_upload_file(size)
        # Small delay between tests
        time.sleep(1)
    
    # Print summary
    tester.print_summary()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())