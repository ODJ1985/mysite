import requests
import io
import sys
import os
import wave
import numpy as np
from datetime import datetime

def create_wav_file(filename, size_mb, duration_sec=5):
    """Create a WAV file of specified size in MB"""
    # Create test files directory if it doesn't exist
    test_files_dir = "test_files"
    if not os.path.exists(test_files_dir):
        os.makedirs(test_files_dir)
        
    filepath = os.path.join(test_files_dir, filename)
    
    # Calculate required sample rate to achieve target file size
    # WAV file size = sample_rate * duration * channels * bytes_per_sample
    channels = 2
    bytes_per_sample = 2  # 16-bit audio
    
    # Target size in bytes
    target_size = size_mb * 1024 * 1024
    
    # Calculate sample rate needed to achieve target size
    # We'll adjust the sample rate to get close to the target size
    sample_rate = int(target_size / (duration_sec * channels * bytes_per_sample))
    
    # Generate random audio data
    samples = np.random.randint(-32768, 32767, size=(channels, int(sample_rate * duration_sec)))
    samples = samples.astype(np.int16)
    
    # Write WAV file
    with wave.open(filepath, 'wb') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(bytes_per_sample)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(samples.tobytes())
    
    # Verify file size
    actual_size = os.path.getsize(filepath) / (1024 * 1024)
    print(f"Created {filename}: {actual_size:.2f} MB")
    
    return filepath, actual_size

def test_10mb_file_size_limit():
    """Test the 10MB file size limit for audio uploads"""
    
    # Get the backend URL from environment or use the default
    backend_url = "https://9fe0c2b0-7831-40b8-a607-5c9b24890339.preview.emergentagent.com"
    
    print("🚀 Starting 10MB File Size Limit Tests")
    
    # Create a test category
    category_name = f"Test Category {datetime.now().strftime('%H%M%S')}"
    try:
        response = requests.post(
            f"{backend_url}/api/categories",
            data={'name': category_name, 'color': '#3B82F6'}
        )
        if response.status_code == 200:
            print(f"✅ Created test category: {category_name}")
        else:
            print(f"❌ Failed to create test category: {response.text}")
            category_name = "Test Category"  # Fallback to a generic category name
    except Exception as e:
        print(f"❌ Error creating category: {str(e)}")
        category_name = "Test Category"  # Fallback to a generic category name
    
    # Create test files of different sizes
    test_files = [
        ("small_1mb.wav", 1),  # 1MB file
        ("medium_5mb.wav", 5),  # 5MB file
        ("large_10mb.wav", 10),  # 10MB file - should be at the limit
        ("oversized_11mb.wav", 11)  # 11MB file - should be rejected
    ]
    
    created_files = []
    for filename, size_mb in test_files:
        try:
            file_path, actual_size = create_wav_file(filename, size_mb)
            created_files.append((file_path, actual_size))
        except Exception as e:
            print(f"❌ Error creating test file {filename}: {str(e)}")
    
    tests_run = 0
    tests_passed = 0
    
    # Test uploading files of different sizes
    for file_path, file_size in created_files:
        tests_run += 1
        title = f"Test Audio {datetime.now().strftime('%H%M%S')}"
        
        # Files over 10MB should be rejected with 413 status or 400 with error message
        expected_status = 200 if file_size <= 10 else [400, 413]
        
        print(f"\n🔍 Testing upload with file size: {file_size:.2f} MB")
        
        try:
            with open(file_path, 'rb') as file:
                files = {'file': (os.path.basename(file_path), file, 'audio/wav')}
                data = {'title': title, 'category': category_name}
                
                response = requests.post(
                    f"{backend_url}/api/upload-audio",
                    files=files,
                    data=data
                )
                
                # Check if response matches expected status
                if isinstance(expected_status, list):
                    success = response.status_code in expected_status
                else:
                    success = response.status_code == expected_status
                
                if success:
                    tests_passed += 1
                    if file_size <= 10:
                        print(f"✅ Successfully uploaded {file_size:.2f} MB file (Status: {response.status_code})")
                    else:
                        print(f"✅ Correctly rejected {file_size:.2f} MB file (Status: {response.status_code})")
                        if response.status_code == 400:
                            try:
                                error_detail = response.json().get('detail', '')
                                print(f"Error message: {error_detail}")
                                if "10MB" in error_detail:
                                    print("✅ Error message correctly mentions 10MB limit")
                                else:
                                    print("❌ Error message does not mention 10MB limit")
                            except:
                                print(f"Response text: {response.text}")
                else:
                    if file_size <= 10:
                        print(f"❌ Failed to upload {file_size:.2f} MB file that should be accepted (Status: {response.status_code})")
                    else:
                        print(f"❌ Incorrectly handled {file_size:.2f} MB file that should be rejected (Status: {response.status_code})")
                    
                    try:
                        print(f"Response: {response.json()}")
                    except:
                        print(f"Response text: {response.text}")
        
        except Exception as e:
            print(f"❌ Error during upload test: {str(e)}")
    
    # Print results
    print(f"\n📊 Tests passed: {tests_passed}/{tests_run}")
    return tests_passed == tests_run

if __name__ == "__main__":
    success = test_10mb_file_size_limit()
    sys.exit(0 if success else 1)