#!/usr/bin/env python3
import requests
import os
import tempfile
import wave
import numpy as np
import uuid
import time

def create_test_wav_file(size_mb, filename):
    """Create a test WAV file with specified size in MB"""
    
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
    print(f"Created test WAV file: {filename}")
    print(f"Duration: {duration:.2f}s, Size: {file_size:.2f} MB")
    return filename, file_size

def test_chunked_upload(file_path, file_size, base_url, category_name, chunk_size_mb=5):
    """Test chunked upload endpoint with a file"""
    print(f"\n🔍 Testing chunked upload with {file_size:.2f} MB file (chunk size: {chunk_size_mb} MB)...")
    
    # Generate a file ID for this upload
    file_id = str(uuid.uuid4())
    original_filename = os.path.basename(file_path)
    title = f"30MB Test {time.strftime('%H:%M:%S')}"
    
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
        try:
            with open(chunk_file_path, 'rb') as chunk_file:
                files = {'chunk': (f'chunk_{chunk_number}', chunk_file, 'application/octet-stream')}
                data = {
                    'chunk_number': chunk_number,
                    'total_chunks': total_chunks,
                    'file_id': file_id,
                    'title': title,
                    'category': category_name,
                    'original_filename': original_filename
                }
                
                start_time = time.time()
                response = requests.post(f"{base_url}/api/upload-audio-chunk", data=data, files=files)
                response_time = time.time() - start_time
                
                print(f"🔍 Upload Chunk {chunk_number+1}/{total_chunks} ({len(chunk_data)/1024/1024:.2f} MB)")
                
                if response.status_code == 200:
                    print(f"✅ Passed - Status: {response.status_code}, Response time: {response_time:.2f}s")
                    
                    # Check if this was the last chunk
                    if chunk_number == total_chunks - 1:
                        response_data = response.json()
                        if 'completed' in response_data and response_data['completed']:
                            print(f"✅ All chunks uploaded successfully. File ID: {file_id}")
                            return file_id
                else:
                    print(f"❌ Failed - Status: {response.status_code}")
                    try:
                        error_detail = response.json().get('detail', 'No detail provided')
                        print(f"Error detail: {error_detail}")
                    except:
                        print(f"Response text: {response.text}")
                    return None
                    
        except Exception as e:
            print(f"❌ Error uploading chunk {chunk_number+1}: {str(e)}")
            return None
        finally:
            # Clean up the temporary chunk file
            if os.path.exists(chunk_file_path):
                os.unlink(chunk_file_path)
    
    return None

def test_file_retrieval(file_id, base_url):
    """Test retrieving the uploaded file"""
    print(f"\n🔍 Testing file retrieval for ID: {file_id}")
    
    try:
        response = requests.get(f"{base_url}/api/audio-file/{file_id}")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ File retrieval successful")
            print(f"   Title: {data.get('title', 'N/A')}")
            print(f"   Size: {data.get('file_size', 0) / (1024*1024):.2f} MB")
            print(f"   Category: {data.get('category', 'N/A')}")
            return True
        else:
            print(f"❌ File retrieval failed - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error retrieving file: {str(e)}")
        return False

def test_audio_streaming(file_id, base_url):
    """Test audio streaming"""
    print(f"\n🔍 Testing audio streaming for ID: {file_id}")
    
    try:
        response = requests.get(f"{base_url}/api/audio-stream/{file_id}", stream=True)
        if response.status_code == 200:
            print(f"✅ Audio streaming successful")
            print(f"   Content-Type: {response.headers.get('content-type', 'N/A')}")
            
            # Read first chunk to verify content
            first_chunk = next(response.iter_content(chunk_size=1024), b'')
            if first_chunk:
                print(f"   First chunk size: {len(first_chunk)} bytes")
                return True
            else:
                print(f"❌ No content received")
                return False
        else:
            print(f"❌ Audio streaming failed - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error streaming audio: {str(e)}")
        return False

def create_test_category(base_url, category_name):
    """Create a test category"""
    print(f"\n🔍 Creating test category: {category_name}")
    
    try:
        data = {"name": category_name, "color": "#FF5733"}
        response = requests.post(f"{base_url}/api/categories", data=data)
        
        if response.status_code == 200:
            print(f"✅ Category created successfully")
            return True
        else:
            print(f"❌ Category creation failed - Status: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error creating category: {str(e)}")
        return False

def main():
    base_url = "https://1e3d862d-5dd1-4551-a519-06c14af7772e.preview.emergentagent.com"
    category_name = f"30MB_Test_{uuid.uuid4().hex[:6]}"
    
    print(f"🚀 Testing 30MB file upload at: {base_url}")
    
    # Create test category
    if not create_test_category(base_url, category_name):
        print("❌ Failed to create test category, exiting")
        return
    
    # Test different file sizes
    test_sizes = [25.0, 30.0]  # MB
    
    for size_mb in test_sizes:
        print(f"\n{'='*60}")
        print(f"🎯 Testing {size_mb} MB file upload")
        print('='*60)
        
        # Create test file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_file.close()
        
        try:
            file_path, actual_size = create_test_wav_file(size_mb, temp_file.name)
            
            # Test chunked upload
            file_id = test_chunked_upload(file_path, actual_size, base_url, category_name)
            
            if file_id:
                # Test file retrieval
                retrieval_success = test_file_retrieval(file_id, base_url)
                
                # Test audio streaming
                streaming_success = test_audio_streaming(file_id, base_url)
                
                if retrieval_success and streaming_success:
                    print(f"\n✅ {size_mb} MB file upload test: PASSED")
                else:
                    print(f"\n❌ {size_mb} MB file upload test: FAILED (retrieval or streaming issue)")
            else:
                print(f"\n❌ {size_mb} MB file upload test: FAILED (upload issue)")
                
        except Exception as e:
            print(f"❌ Error testing {size_mb} MB file: {str(e)}")
        finally:
            # Clean up
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
    
    print(f"\n🏁 30MB file upload testing completed!")

if __name__ == "__main__":
    main()