#!/usr/bin/env python3
import requests
import os
import json
import uuid
import time
from pathlib import Path
import tempfile
import sys

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
    return "https://1e3d862d-5dd1-4551-a519-06c14af7772e.preview.emergentagent.com"

# Create a test WAV file
def create_test_wav_file(file_path, duration_seconds=1, size_mb=None):
    """Create a simple WAV file for testing with either specified duration or size"""
    try:
        import wave
        import struct
        import numpy as np
        
        # Parameters for the WAV file
        nchannels = 1
        sampwidth = 2
        framerate = 44100
        
        if size_mb:
            # Calculate number of frames needed to reach the desired size
            # Each frame is 2 bytes (16-bit)
            bytes_per_frame = sampwidth * nchannels
            target_bytes = size_mb * 1024 * 1024
            # Subtract WAV header size (44 bytes)
            data_bytes = target_bytes - 44
            nframes = data_bytes // bytes_per_frame
            duration_seconds = nframes / framerate
        else:
            nframes = int(framerate * duration_seconds)
        
        comptype = "NONE"
        compname = "not compressed"
        
        # Generate a simple sine wave
        amplitude = 32767  # Max amplitude for 16-bit audio
        frequency = 440  # 440 Hz = A4 note
        
        # For large files, generate in chunks to avoid memory issues
        chunk_size = min(nframes, 1000000)  # 1 million frames per chunk
        
        with wave.open(file_path, "w") as wav_file:
            wav_file.setparams((nchannels, sampwidth, framerate, nframes, comptype, compname))
            
            for chunk_start in range(0, nframes, chunk_size):
                chunk_end = min(chunk_start + chunk_size, nframes)
                chunk_frames = chunk_end - chunk_start
                
                # Calculate time values for this chunk
                time_array = np.linspace(
                    chunk_start / framerate, 
                    chunk_end / framerate, 
                    chunk_frames
                )
                
                # Generate audio data for this chunk
                audio_data = amplitude * np.sin(2 * np.pi * frequency * time_array)
                
                # Write frames
                for sample in audio_data:
                    wav_file.writeframes(struct.pack('h', int(sample)))
        
        actual_size_mb = os.path.getsize(file_path) / (1024 * 1024)
        print(f"Created test audio file: {file_path}")
        print(f"  - Duration: {duration_seconds:.2f} seconds")
        print(f"  - Size: {actual_size_mb:.2f} MB")
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
    print(f"File size: {os.path.getsize(file_path) / (1024 * 1024):.2f} MB")
    
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
            elif response.status_code == 413:
                print("✅ Expected rejection of large file (413 Payload Too Large)")
                return True, None
            else:
                print(f"❌ Regular upload test failed with status code {response.status_code}")
                
            return response.status_code in [200, 413], None
    except Exception as e:
        print(f"❌ Error during regular upload test: {e}")
        return False, None

# Test chunked audio upload
def test_chunked_upload(base_url, file_path, chunk_size=1024*1024):
    print("\n=== Testing Chunked Audio Upload (/api/upload-audio-chunk) ===")
    
    try:
        # Read the file
        file_size = os.path.getsize(file_path)
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        print(f"File size: {file_size} bytes ({file_size / (1024 * 1024):.2f} MB)")
        print(f"Chunk size: {chunk_size} bytes ({chunk_size / (1024 * 1024):.2f} MB)")
        print(f"Total chunks: {total_chunks}")
        
        # Generate a unique file ID
        file_id = str(uuid.uuid4())
        filename = f"test_chunked_{uuid.uuid4().hex[:6]}.wav"
        
        print(f"File ID: {file_id}")
        print(f"Filename: {filename}")
        
        # Upload each chunk
        with open(file_path, "rb") as f:
            for i in range(total_chunks):
                chunk_data = f.read(chunk_size)
                
                print(f"\nUploading chunk {i+1}/{total_chunks} ({len(chunk_data) / (1024 * 1024):.2f} MB)")
                
                # Prepare the request
                url = f"{base_url}/api/upload-audio-chunk"
                
                # Create a temporary file for the chunk
                with tempfile.NamedTemporaryFile(delete=False, suffix='.wav') as temp_file:
                    temp_file.write(chunk_data)
                    temp_file_path = temp_file.name
                
                # Open the temporary file for the request
                with open(temp_file_path, "rb") as chunk_file:
                    files = {
                        "chunk": (filename, chunk_file, "audio/wav")
                    }
                    
                    data = {
                        "chunk_number": i,
                        "total_chunks": total_chunks,
                        "file_id": file_id,
                        "title": f"Chunked Test Audio {uuid.uuid4().hex[:6]}",
                        "category": "Test Category",
                        "original_filename": filename
                    }
                    
                    # Send the request
                    response = requests.post(url, data=data, files=files)
                
                # Clean up the temporary file
                os.unlink(temp_file_path)
                
                print(f"Status code: {response.status_code}")
                print(f"Response: {response.text[:200]}")
                
                if response.status_code != 200:
                    print(f"❌ Chunk {i+1} upload failed with status code {response.status_code}")
                    return False, None
                
                # For the last chunk, we expect to get a file_id and completed=True
                if i == total_chunks - 1:
                    try:
                        result = response.json()
                        if "file_id" in result and result.get("completed", False):
                            print(f"✅ File ID received: {result['file_id']}")
                            return True, result["file_id"]
                        else:
                            print("❌ No file_id or completed=False in response for the last chunk")
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
                    
                    # Verify file can be downloaded
                    file_url = f"{base_url}{result.get('file_url')}"
                    print(f"   Checking file download from: {file_url}")
                    download_response = requests.get(file_url)
                    if download_response.status_code == 200:
                        print(f"✅ File download successful ({len(download_response.content) / (1024 * 1024):.2f} MB)")
                    else:
                        print(f"❌ File download failed with status code {download_response.status_code}")
                    
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
    
    # Create test files
    small_file_path = "/app/test_audio_small.wav"
    if not os.path.exists(small_file_path):
        create_test_wav_file(small_file_path, duration_seconds=2)
    
    medium_file_path = "/app/test_audio_medium.wav"
    if not os.path.exists(medium_file_path):
        create_test_wav_file(medium_file_path, size_mb=5)
    
    large_file_path = "/app/test_audio_large.wav"
    if not os.path.exists(large_file_path):
        create_test_wav_file(large_file_path, size_mb=12)
    
    # Test results
    results = {}
    
    # Test 1: Small file regular upload
    print("\n🔍 TEST 1: Small file regular upload")
    results["small_regular"] = test_regular_upload(backend_url, small_file_path)
    
    # Test 2: Medium file regular upload
    print("\n🔍 TEST 2: Medium file regular upload")
    results["medium_regular"] = test_regular_upload(backend_url, medium_file_path)
    
    # Test 3: Large file regular upload (should fail with 413)
    print("\n🔍 TEST 3: Large file regular upload (should fail with 413)")
    results["large_regular"] = test_regular_upload(backend_url, large_file_path)
    
    # Test 4: Small file chunked upload
    print("\n🔍 TEST 4: Small file chunked upload")
    results["small_chunked"] = test_chunked_upload(backend_url, small_file_path, chunk_size=100*1024)
    
    # Test 5: Medium file chunked upload
    print("\n🔍 TEST 5: Medium file chunked upload")
    results["medium_chunked"] = test_chunked_upload(backend_url, medium_file_path, chunk_size=1*1024*1024)
    
    # Test 6: Large file chunked upload
    print("\n🔍 TEST 6: Large file chunked upload")
    results["large_chunked"] = test_chunked_upload(backend_url, large_file_path, chunk_size=2*1024*1024)
    
    # Verify uploaded files
    for test_name, (success, file_id) in results.items():
        if success and file_id:
            print(f"\n🔍 Verifying {test_name} upload")
            verify_uploaded_file(backend_url, file_id)
    
    # Print summary
    print("\n" + "="*50)
    print("📊 Audio Upload Tests Summary:")
    for test_name, (success, _) in results.items():
        print(f"{test_name}: {'✅ Passed' if success else '❌ Failed'}")
    print("="*50)
    
    # Overall success if at least one upload method works for each file size
    small_success = results["small_regular"][0] or results["small_chunked"][0]
    medium_success = results["medium_regular"][0] or results["medium_chunked"][0]
    large_success = results["large_chunked"][0]  # Only chunked should work for large files
    
    overall_success = small_success and medium_success and large_success
    
    print(f"\nOverall test result: {'✅ PASSED' if overall_success else '❌ FAILED'}")
    
    return 0 if overall_success else 1

if __name__ == "__main__":
    main()
