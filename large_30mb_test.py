#!/usr/bin/env python3
import requests
import os
import tempfile
import wave
import numpy as np
import uuid
import time

def create_large_test_wav_file(size_mb, filename):
    """Create a larger test WAV file with specified size in MB"""
    
    # Set parameters for a more realistic WAV file
    sample_rate = 44100  # Hz
    channels = 2  # Stereo
    sample_width = 2  # 2 bytes per sample (16-bit)
    
    # Calculate duration based on desired size
    bytes_per_second = sample_rate * sample_width * channels
    target_size_bytes = size_mb * 1024 * 1024
    duration = target_size_bytes / bytes_per_second
    
    # Generate audio data
    num_samples = int(duration * sample_rate)
    
    # Create more realistic audio: sine waves with some variation
    t = np.linspace(0, duration, num_samples)
    frequency = 440  # A note
    audio_data = 0.3 * np.sin(2 * np.pi * frequency * t)  # Base sine wave
    audio_data += 0.1 * np.sin(2 * np.pi * frequency * 2 * t)  # Harmonic
    audio_data += 0.05 * np.random.normal(0, 1, num_samples)  # Add some noise
    
    # Convert to 16-bit integers
    audio_data_int = (audio_data * 32767).astype(np.int16)
    
    # Create stereo by duplicating the mono signal
    stereo_data = np.column_stack((audio_data_int, audio_data_int))
    
    # Write to WAV file
    with wave.open(filename, 'w') as wav_file:
        wav_file.setnchannels(channels)
        wav_file.setsampwidth(sample_width)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(stereo_data.tobytes())
    
    file_size = os.path.getsize(filename) / (1024 * 1024)
    print(f"Created large test WAV file: {filename}")
    print(f"Duration: {duration:.2f}s, Target size: {size_mb:.2f}MB, Actual size: {file_size:.2f} MB")
    return filename, file_size

def test_large_chunked_upload(file_path, file_size, base_url, category_name, chunk_size_mb=5):
    """Test chunked upload endpoint with a large file"""
    print(f"\n🔍 Testing LARGE chunked upload with {file_size:.2f} MB file (chunk size: {chunk_size_mb} MB)...")
    
    # Generate a file ID for this upload
    file_id = str(uuid.uuid4())
    original_filename = os.path.basename(file_path)
    title = f"LARGE Test {file_size:.1f}MB {time.strftime('%H:%M:%S')}"
    
    # Calculate chunk size in bytes
    chunk_size_bytes = chunk_size_mb * 1024 * 1024
    
    # Read the file
    print(f"Reading file: {file_path} ({file_size:.2f} MB)")
    with open(file_path, 'rb') as f:
        file_data = f.read()
    
    print(f"File read successfully, size: {len(file_data) / (1024*1024):.2f} MB")
    
    # Calculate total chunks
    total_chunks = (len(file_data) + chunk_size_bytes - 1) // chunk_size_bytes
    print(f"File will be split into {total_chunks} chunks")
    
    # Upload each chunk with progress tracking
    for chunk_number in range(total_chunks):
        chunk_start = chunk_number * chunk_size_bytes
        chunk_end = min(chunk_start + chunk_size_bytes, len(file_data))
        chunk_data = file_data[chunk_start:chunk_end]
        
        print(f"\n📦 Chunk {chunk_number+1}/{total_chunks}: {len(chunk_data)/1024/1024:.2f} MB")
        
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
                
                print(f"   Uploading chunk to {base_url}/api/upload-audio-chunk...")
                start_time = time.time()
                response = requests.post(f"{base_url}/api/upload-audio-chunk", data=data, files=files, timeout=60)
                response_time = time.time() - start_time
                
                if response.status_code == 200:
                    print(f"   ✅ SUCCESS - Response time: {response_time:.2f}s")
                    
                    # Check if this was the last chunk
                    if chunk_number == total_chunks - 1:
                        response_data = response.json()
                        if 'completed' in response_data and response_data['completed']:
                            print(f"\n🎉 ALL CHUNKS UPLOADED SUCCESSFULLY!")
                            print(f"   File ID: {file_id}")
                            print(f"   Total upload time: {time.time() - start_time:.2f}s")
                            return file_id
                        else:
                            print(f"   ⚠️ Last chunk uploaded but file not marked as completed")
                            print(f"   Response: {response_data}")
                else:
                    print(f"   ❌ FAILED - Status: {response.status_code}")
                    try:
                        error_detail = response.json().get('detail', 'No detail provided')
                        print(f"   Error detail: {error_detail}")
                    except:
                        print(f"   Response text: {response.text[:200]}...")
                    return None
                    
        except Exception as e:
            print(f"   ❌ Error uploading chunk {chunk_number+1}: {str(e)}")
            return None
        finally:
            # Clean up the temporary chunk file
            if os.path.exists(chunk_file_path):
                os.unlink(chunk_file_path)
    
    return None

def main():
    base_url = "https://1e3d862d-5dd1-4551-a519-06c14af7772e.preview.emergentagent.com"
    category_name = f"LARGE_Test_{uuid.uuid4().hex[:6]}"
    
    print(f"🚀 Testing LARGE file upload (close to 30MB) at: {base_url}")
    
    # Create test category
    print(f"\n🔍 Creating test category: {category_name}")
    
    try:
        data = {"name": category_name, "color": "#FF5733"}
        response = requests.post(f"{base_url}/api/categories", data=data)
        
        if response.status_code == 200:
            print(f"✅ Category created successfully")
        else:
            print(f"❌ Category creation failed - Status: {response.status_code}")
            return
    except Exception as e:
        print(f"❌ Error creating category: {str(e)}")
        return
    
    # Test with files closer to 30MB
    test_sizes = [28.0, 29.5]  # MB - closer to real 30MB
    
    for size_mb in test_sizes:
        print(f"\n{'='*80}")
        print(f"🎯 Testing {size_mb} MB file upload (Large File Test)")
        print('='*80)
        
        # Create test file
        temp_file = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
        temp_file.close()
        
        try:
            file_path, actual_size = create_large_test_wav_file(size_mb, temp_file.name)
            
            # Test chunked upload
            file_id = test_large_chunked_upload(file_path, actual_size, base_url, category_name)
            
            if file_id:
                print(f"\n🔍 Testing file retrieval for ID: {file_id}")
                
                try:
                    response = requests.get(f"{base_url}/api/audio-file/{file_id}")
                    if response.status_code == 200:
                        data = response.json()
                        print(f"✅ File retrieval successful")
                        print(f"   Title: {data.get('title', 'N/A')}")
                        print(f"   Size: {data.get('file_size', 0) / (1024*1024):.2f} MB")
                        print(f"   Category: {data.get('category', 'N/A')}")
                        
                        # Test streaming
                        print(f"\n🔍 Testing audio streaming for ID: {file_id}")
                        stream_response = requests.get(f"{base_url}/api/audio-stream/{file_id}", stream=True)
                        if stream_response.status_code == 200:
                            print(f"✅ Audio streaming successful")
                            print(f"   Content-Type: {stream_response.headers.get('content-type', 'N/A')}")
                            
                            print(f"\n🎉 {size_mb} MB file upload test: COMPLETELY SUCCESSFUL!")
                        else:
                            print(f"❌ Audio streaming failed - Status: {stream_response.status_code}")
                    else:
                        print(f"❌ File retrieval failed - Status: {response.status_code}")
                except Exception as e:
                    print(f"❌ Error testing retrieval/streaming: {str(e)}")
            else:
                print(f"\n❌ {size_mb} MB file upload test: FAILED (upload issue)")
                
        except Exception as e:
            print(f"❌ Error testing {size_mb} MB file: {str(e)}")
        finally:
            # Clean up
            if os.path.exists(temp_file.name):
                os.unlink(temp_file.name)
                print(f"🧹 Cleaned up temporary file")
    
    print(f"\n🏁 LARGE file upload testing completed!")
    print(f"📊 Summary: Tested files approaching 30MB with chunked upload system")

if __name__ == "__main__":
    main()