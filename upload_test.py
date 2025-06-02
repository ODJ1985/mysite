import requests
import os
import time
import tempfile
import wave
import numpy as np
import sys

def create_test_wav_file(size_mb, filename="test_audio.wav"):
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

def test_upload_file(base_url, size_mb, category_name="Test Category"):
    """Test uploading a file of specified size"""
    print(f"\n===== Testing {size_mb}MB File Upload =====")
    
    # Create test file
    wav_file_path = create_test_wav_file(size_mb)
    
    # Prepare request
    url = f"{base_url}/api/upload-audio"
    title = f"Test Audio {size_mb}MB {int(time.time())}"
    
    with open(wav_file_path, 'rb') as f:
        files = {'file': ('test_audio.wav', f, 'audio/wav')}
        form_data = {
            'title': title,
            'category': category_name
        }
        
        print(f"Sending request to {url}")
        start_time = time.time()
        
        try:
            response = requests.post(url, files=files, data=form_data, timeout=60)
            elapsed = time.time() - start_time
            
            print(f"Response status: {response.status_code} (took {elapsed:.2f} seconds)")
            
            if response.status_code == 200:
                print("✅ Upload successful")
                try:
                    print(f"Response: {response.json()}")
                except:
                    print("Could not parse JSON response")
            else:
                print("❌ Upload failed")
                try:
                    error = response.json()
                    print(f"Error details: {error}")
                except:
                    print(f"Raw response: {response.text[:500]}")
                    
        except requests.exceptions.RequestException as e:
            elapsed = time.time() - start_time
            print(f"❌ Request failed after {elapsed:.2f} seconds: {str(e)}")
    
    # Clean up
    try:
        os.unlink(wav_file_path)
    except:
        pass

def create_test_category(base_url):
    """Create a test category for uploads"""
    category_name = f"Test Category {int(time.time())}"
    url = f"{base_url}/api/categories"
    
    print(f"\nCreating test category: {category_name}")
    
    try:
        response = requests.post(url, data={
            "name": category_name,
            "color": "#3B82F6"
        })
        
        if response.status_code == 200:
            print("✅ Category created successfully")
            return category_name
        else:
            print(f"❌ Failed to create category: {response.status_code}")
            try:
                print(f"Error: {response.json()}")
            except:
                pass
            return None
    except Exception as e:
        print(f"❌ Error creating category: {str(e)}")
        return None

def main():
    base_url = "https://1e3d862d-5dd1-4551-a519-06c14af7772e.preview.emergentagent.com"
    
    # Create a test category
    category_name = create_test_category(base_url)
    if not category_name:
        print("Could not create category, using default")
        category_name = "Test Category"
    
    # Test various file sizes
    test_sizes = [5, 10, 15, 20, 24, 25, 26]
    
    for size in test_sizes:
        test_upload_file(base_url, size, category_name)
        # Add a short delay between tests
        time.sleep(2)
    
    print("\nAll tests completed")

if __name__ == "__main__":
    main()