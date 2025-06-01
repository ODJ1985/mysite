#!/usr/bin/env python3
import requests
import os
import json
import uuid
import time
from pathlib import Path

# Get the backend URL from the frontend .env file
def get_backend_url():
    env_file_path = "/app/frontend/.env"
    try:
        with open(env_file_path, "r") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.strip().split("=", 1)[1].strip('"\'')
    except Exception as e:
        print(f"Error reading frontend/.env file: {e}")
    
    # Fallback to hardcoded URL
    return "https://69b0f385-191d-4d9c-8f85-af6b574a2e14.preview.emergentagent.com"

# Create a test WAV file
def create_test_wav_file(file_path, duration_seconds=1):
    """Create a simple WAV file for testing"""
    try:
        import wave
        import struct
        import numpy as np
        
        # Parameters for the WAV file
        nchannels = 1
        sampwidth = 2
        framerate = 44100
        nframes = int(framerate * duration_seconds)
        comptype = "NONE"
        compname = "not compressed"
        
        # Generate a simple sine wave
        amplitude = 32767  # Max amplitude for 16-bit audio
        frequency = 440  # 440 Hz = A4 note
        time_array = np.linspace(0, duration_seconds, nframes)
        audio_data = amplitude * np.sin(2 * np.pi * frequency * time_array)
        
        with wave.open(file_path, "w") as wav_file:
            wav_file.setparams((nchannels, sampwidth, framerate, nframes, comptype, compname))
            for sample in audio_data:
                wav_file.writeframes(struct.pack('h', int(sample)))
        
        print(f"Created test audio file: {file_path}")
        return True
    except Exception as e:
        print(f"Error creating test audio file: {e}")
        # Create an empty file as fallback
        with open(file_path, "wb") as f:
            f.write(b"\x52\x49\x46\x46\x24\x00\x00\x00\x57\x41\x56\x45\x66\x6d\x74\x20\x10\x00\x00\x00\x01\x00\x01\x00\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00\x64\x61\x74\x61\x00\x00\x00\x00")
        print(f"Created minimal test audio file: {file_path}")
        return True

# Test regular audio upload
def test_regular_upload(base_url, file_path):
    print("\n=== Testing Regular Audio Upload (/api/upload-audio) ===")
    
    try:
        with open(file_path, "rb") as audio_file:
            files = {"file": (f"test_audio_{uuid.uuid4().hex[:6]}.wav", audio_file, "audio/wav")}
            data = {
                "title": f"Test Audio {uuid.uuid4().hex[:6]}",
                "category": "Test Category"
            }
            
            url = f"{base_url}/api/upload-audio"
            print(f"Sending request to: {url}")
            
            response = requests.post(url, data=data, files=files)
            
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text[:500]}")
            
            if response.status_code == 200:
                print("✅ Regular upload test passed")
                try:
                    result = response.json()
                    if "file_id" in result:
                        print(f"✅ File ID received: {result['file_id']}")
                        return True, result["file_id"]
                    else:
                        print("❌ No file_id in response")
                except json.JSONDecodeError:
                    print("❌ Response is not valid JSON")
            else:
                print(f"❌ Regular upload test failed with status code {response.status_code}")
                
            return response.status_code == 200, None
    except Exception as e:
        print(f"❌ Error during regular upload test: {e}")
        return False, None

# Test chunked audio upload
def test_chunked_upload(base_url, file_path, chunk_size=1024*1024):
    print("\n=== Testing Chunked Audio Upload (/api/upload-audio-chunk) ===")
    
    try:
        # Read the file
        with open(file_path, "rb") as f:
            file_content = f.read()
        
        file_size = len(file_content)
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        print(f"File size: {file_size} bytes")
        print(f"Chunk size: {chunk_size} bytes")
        print(f"Total chunks: {total_chunks}")
        
        # Generate a unique upload ID
        upload_id = str(uuid.uuid4())
        filename = f"test_chunked_{uuid.uuid4().hex[:6]}.wav"
        
        print(f"Upload ID: {upload_id}")
        print(f"Filename: {filename}")
        
        # Upload each chunk
        for i in range(total_chunks):
            start_byte = i * chunk_size
            end_byte = min(file_size, start_byte + chunk_size)
            chunk_data = file_content[start_byte:end_byte]
            
            is_last_chunk = (i == total_chunks - 1)
            
            print(f"\nUploading chunk {i+1}/{total_chunks} (bytes {start_byte}-{end_byte})")
            
            # Prepare the request
            url = f"{base_url}/api/upload-audio-chunk"
            
            files = {
                "file": (filename, chunk_data, "audio/wav")
            }
            
            data = {
                "upload_id": upload_id,
                "chunk_index": i,
                "total_chunks": total_chunks,
                "is_last_chunk": "true" if is_last_chunk else "false",
                "title": f"Chunked Test Audio {uuid.uuid4().hex[:6]}",
                "category": "Test Category"
            }
            
            # Send the request
            response = requests.post(url, data=data, files=files)
            
            print(f"Status code: {response.status_code}")
            print(f"Response: {response.text[:200]}")
            
            if response.status_code != 200:
                print(f"❌ Chunk {i+1} upload failed with status code {response.status_code}")
                return False, None
            
            # For the last chunk, we expect to get a file_id
            if is_last_chunk:
                try:
                    result = response.json()
                    if "file_id" in result:
                        print(f"✅ File ID received: {result['file_id']}")
                        return True, result["file_id"]
                    else:
                        print("❌ No file_id in response for the last chunk")
                        return False, None
                except json.JSONDecodeError:
                    print("❌ Response for last chunk is not valid JSON")
                    return False, None
        
        print("❌ Chunked upload test failed - didn't reach last chunk")
        return False, None
    except Exception as e:
        print(f"❌ Error during chunked upload test: {e}")
        return False, None

# Verify uploaded file
def verify_uploaded_file(base_url, file_id):
    print(f"\n=== Verifying Uploaded File (ID: {file_id}) ===")
    
    try:
        url = f"{base_url}/api/audio-file/{file_id}"
        print(f"Sending request to: {url}")
        
        response = requests.get(url)
        
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
        if response.status_code == 200:
            print("✅ File verification passed")
            try:
                result = response.json()
                if "id" in result and result["id"] == file_id:
                    print(f"✅ File details retrieved successfully")
                    print(f"   Title: {result.get('title')}")
                    print(f"   Category: {result.get('category')}")
                    print(f"   File URL: {result.get('file_url')}")
                    return True
                else:
                    print("❌ File details don't match")
            except json.JSONDecodeError:
                print("❌ Response is not valid JSON")
        else:
            print(f"❌ File verification failed with status code {response.status_code}")
            
        return response.status_code == 200
    except Exception as e:
        print(f"❌ Error during file verification: {e}")
        return False

# Main function
def main():
    # Get the backend URL
    backend_url = get_backend_url()
    print(f"Testing backend at: {backend_url}")
    
    # Create test file
    test_file_path = "/app/test_audio_small.wav"
    if not os.path.exists(test_file_path):
        create_test_wav_file(test_file_path, duration_seconds=2)
    
    # Test regular upload
    regular_success, regular_file_id = test_regular_upload(backend_url, test_file_path)
    
    # Verify regular upload
    if regular_success and regular_file_id:
        verify_uploaded_file(backend_url, regular_file_id)
    
    # Test chunked upload
    chunked_success, chunked_file_id = test_chunked_upload(backend_url, test_file_path, chunk_size=512*1024)
    
    # Verify chunked upload
    if chunked_success and chunked_file_id:
        verify_uploaded_file(backend_url, chunked_file_id)
    
    # Print summary
    print("\n" + "="*50)
    print("📊 Audio Upload Tests Summary:")
    print(f"Regular Upload: {'✅ Passed' if regular_success else '❌ Failed'}")
    print(f"Chunked Upload: {'✅ Passed' if chunked_success else '❌ Failed'}")
    print("="*50)
    
    return 0 if (regular_success or chunked_success) else 1

if __name__ == "__main__":
    main()
