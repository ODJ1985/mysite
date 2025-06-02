import requests
import os
import tempfile
import wave
import numpy as np
import sys
import time

def create_test_wav_file(size_mb):
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

def test_upload_file(base_url, file_path, file_size_mb):
    """Test uploading a file and check the response"""
    print(f"\n🔍 Testing upload of {file_size_mb}MB file...")
    
    # First create a category if needed
    category_name = f"Boundary Test {int(time.time())}"
    
    # Create category
    try:
        category_response = requests.post(
            f"{base_url}/api/categories",
            data={"name": category_name, "color": "#3B82F6"}
        )
        if category_response.status_code == 200:
            print("✅ Category created successfully")
        elif category_response.status_code == 400 and "already exists" in category_response.json().get("detail", ""):
            print("✅ Category already exists")
        else:
            print(f"❌ Failed to create category: {category_response.status_code}")
            try:
                print(f"Error: {category_response.json().get('detail', 'No detail')}")
            except:
                pass
            return False
    except Exception as e:
        print(f"❌ Error creating category: {str(e)}")
        return False
    
    # Upload file
    try:
        print(f"Starting upload of {file_size_mb}MB file...")
        start_time = time.time()
        
        with open(file_path, 'rb') as f:
            files = {'file': (f'test_{file_size_mb}mb.wav', f, 'audio/wav')}
            form_data = {
                'title': f"Test {file_size_mb}MB",
                'category': category_name
            }
            
            response = requests.post(
                f"{base_url}/api/upload-audio",
                files=files,
                data=form_data
            )
            
        end_time = time.time()
        upload_time = end_time - start_time
        print(f"Upload took {upload_time:.2f} seconds")
            
        if response.status_code == 200:
            print(f"✅ File uploaded successfully: {response.json().get('file_id', 'No ID')}")
            return True
        else:
            print(f"❌ Upload failed with status code: {response.status_code}")
            try:
                error_detail = response.json().get('detail', 'No detail')
                print(f"Error: {error_detail}")
            except:
                print("Could not parse error response")
            return False
                
    except Exception as e:
        print(f"❌ Error during upload: {str(e)}")
        return False

def main():
    base_url = "https://1e3d862d-5dd1-4551-a519-06c14af7772e.preview.emergentagent.com"
    
    print("\n===== Testing File Uploads at Boundary =====\n")
    
    # Test sizes
    test_sizes = [8, 9]
    results = []
    
    for size_mb in test_sizes:
        # Create test file
        file_path = create_test_wav_file(size_mb)
        
        # Test upload
        result = test_upload_file(base_url, file_path, size_mb)
        results.append((size_mb, result))
        
        # Clean up
        try:
            os.unlink(file_path)
            print(f"✅ Temporary {size_mb}MB file cleaned up")
        except:
            print(f"⚠️ Failed to clean up {size_mb}MB temporary file")
    
    # Print summary
    print("\n===== Test Results =====")
    for size_mb, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{status} - {size_mb}MB file upload")
    
    # Overall result
    success = all(result for _, result in results)
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
