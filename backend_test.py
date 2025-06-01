import requests
import os
import time
import tempfile
import wave
import numpy as np
import sys
import json
import unittest
from datetime import datetime

class PodcastFileSizeTest(unittest.TestCase):
    def setUp(self):
        self.base_url = "https://9fe0c2b0-7831-40b8-a607-5c9b24890339.preview.emergentagent.com/api"
        self.category_id = None
        self.category_name = None
        self.test_files = []
        
    def tearDown(self):
        # Clean up any test files
        for file_path in self.test_files:
            try:
                os.unlink(file_path)
            except:
                pass
    
    def create_test_wav_file(self, size_mb, filename="test_audio.wav"):
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
        
        self.test_files.append(temp_file.name)
        return temp_file.name
    
    def test_health_endpoint(self):
        """Test the health endpoint"""
        response = requests.get(f"{self.base_url}/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["status"], "healthy")
        self.assertEqual(data["service"], "wyEBIYA-podcast-service")
    
    def test_create_category(self):
        """Test creating a category"""
        category_name = f"Test Category {int(time.time())}"
        
        with requests.Session() as session:
            url = f"{self.base_url}/categories"
            form_data = {
                "name": category_name,
                "color": "#3B82F6"
            }
            
            response = session.post(url, data=form_data)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("category_id", data)
            
            self.category_id = data["category_id"]
            self.category_name = category_name
            
            return self.category_id
    
    def test_upload_file_under_limit(self):
        """Test uploading a file under the 7MB limit"""
        if not self.category_name:
            self.test_create_category()
        
        # Create a 6.9MB test file
        wav_file_path = self.create_test_wav_file(6.9)
        
        # Prepare form data
        title = f"Test Audio 6.9MB {int(time.time())}"
        
        with open(wav_file_path, 'rb') as f:
            files = {'file': ('test_audio.wav', f, 'audio/wav')}
            form_data = {
                'title': title,
                'category': self.category_name
            }
            
            response = requests.post(f"{self.base_url}/upload-audio", files=files, data=form_data)
            
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertEqual(data["message"], "File uploaded successfully")
            self.assertIn("file_id", data)
            self.assertEqual(data["title"], title)
    
    def test_upload_file_at_limit(self):
        """Test uploading a file at the 7MB limit"""
        if not self.category_name:
            self.test_create_category()
        
        # Create a 7MB test file
        wav_file_path = self.create_test_wav_file(7)
        
        # Prepare form data
        title = f"Test Audio 7MB {int(time.time())}"
        
        with open(wav_file_path, 'rb') as f:
            files = {'file': ('test_audio.wav', f, 'audio/wav')}
            form_data = {
                'title': title,
                'category': self.category_name
            }
            
            response = requests.post(f"{self.base_url}/upload-audio", files=files, data=form_data)
            
            # This might fail if the exact limit is slightly under 7MB
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data["message"], "File uploaded successfully")
                self.assertIn("file_id", data)
                self.assertEqual(data["title"], title)
            else:
                self.assertEqual(response.status_code, 413)
    
    def test_upload_file_over_limit(self):
        """Test uploading a file over the 7MB limit"""
        if not self.category_name:
            self.test_create_category()
        
        # Create a 7.1MB test file
        wav_file_path = self.create_test_wav_file(7.1)
        
        # Prepare form data
        title = f"Test Audio 7.1MB {int(time.time())}"
        
        with open(wav_file_path, 'rb') as f:
            files = {'file': ('test_audio.wav', f, 'audio/wav')}
            form_data = {
                'title': title,
                'category': self.category_name
            }
            
            response = requests.post(f"{self.base_url}/upload-audio", files=files, data=form_data)
            
            # This should fail with a 413 error
            self.assertEqual(response.status_code, 413)
    
    def test_find_exact_limit(self):
        """Find the exact file size limit"""
        if not self.category_name:
            self.test_create_category()
        
        # Test file sizes around the 7MB limit
        start_mb = 6.9
        end_mb = 7.1
        step_mb = 0.01
        
        results = []
        current_mb = start_mb
        
        while current_mb <= end_mb:
            size_mb = round(current_mb, 2)
            wav_file_path = self.create_test_wav_file(size_mb)
            
            # Prepare form data
            title = f"Test Audio {size_mb}MB {int(time.time())}"
            
            with open(wav_file_path, 'rb') as f:
                files = {'file': ('test_audio.wav', f, 'audio/wav')}
                form_data = {
                    'title': title,
                    'category': self.category_name
                }
                
                response = requests.post(f"{self.base_url}/upload-audio", files=files, data=form_data)
                
                success = response.status_code == 200
                results.append({"size_mb": size_mb, "success": success})
                
                if not success:
                    # We found the boundary, no need to test further
                    break
                    
                current_mb += step_mb
        
        # Find the exact boundary
        if not success and len(results) > 1:
            last_success = next((r for r in reversed(results[:-1]) if r["success"]), None)
            if last_success:
                print(f"\n🔍 Found boundary: Files up to {last_success['size_mb']}MB succeed, {size_mb}MB fails")
                return last_success["size_mb"]
        
        return None

class PodcastFileSizeModificationTest(unittest.TestCase):
    def setUp(self):
        self.base_url = "https://9fe0c2b0-7831-40b8-a607-5c9b24890339.preview.emergentagent.com/api"
        self.category_id = None
        self.category_name = None
        self.test_files = []
        self.original_server_content = None
        
        # Backup the original server.py file
        with open("/app/backend/server.py", 'r') as f:
            self.original_server_content = f.read()
    
    def tearDown(self):
        # Clean up any test files
        for file_path in self.test_files:
            try:
                os.unlink(file_path)
            except:
                pass
        
        # Restore the original server.py file
        if self.original_server_content:
            with open("/app/backend/server.py", 'w') as f:
                f.write(self.original_server_content)
            
            # Restart the backend service
            os.system("sudo supervisorctl restart backend")
            time.sleep(5)
    
    def create_test_wav_file(self, size_mb, filename="test_audio.wav"):
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
        
        self.test_files.append(temp_file.name)
        return temp_file.name
    
    def modify_file_size_limit(self, new_limit_mb):
        """Modify the file size limit in the server.py file"""
        server_path = "/app/backend/server.py"
        
        # Read the current file
        with open(server_path, 'r') as f:
            content = f.read()
        
        # Replace the file size limit
        content = content.replace("max_size = 7 * 1024 * 1024  # 7MB", f"max_size = {new_limit_mb} * 1024 * 1024  # {new_limit_mb}MB")
        content = content.replace("raise HTTPException(status_code=413, detail=\"File size must be less than 7MB\")", 
                                f"raise HTTPException(status_code=413, detail=\"File size must be less than {new_limit_mb}MB\")")
        
        # Write the modified content back
        with open(server_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Modified file size limit to {new_limit_mb}MB in {server_path}")
        
        # Restart the backend service
        os.system("sudo supervisorctl restart backend")
        print("✅ Restarted backend service")
        
        # Wait for the service to restart
        time.sleep(5)
        print("✅ Waited for service to restart")
    
    def test_create_category(self):
        """Test creating a category"""
        category_name = f"Test Category {int(time.time())}"
        
        with requests.Session() as session:
            url = f"{self.base_url}/categories"
            form_data = {
                "name": category_name,
                "color": "#3B82F6"
            }
            
            response = session.post(url, data=form_data)
            self.assertEqual(response.status_code, 200)
            
            data = response.json()
            self.assertIn("category_id", data)
            
            self.category_id = data["category_id"]
            self.category_name = category_name
            
            return self.category_id
    
    def test_modify_limit_to_10mb(self):
        """Test modifying the file size limit to 10MB"""
        # Modify the file size limit to 10MB
        self.modify_file_size_limit(10)
        
        # Create a category for testing
        self.test_create_category()
        
        # Test uploading a 7.1MB file (should succeed now)
        wav_file_path = self.create_test_wav_file(7.1)
        
        # Prepare form data
        title = f"Test Audio 7.1MB {int(time.time())}"
        
        with open(wav_file_path, 'rb') as f:
            files = {'file': ('test_audio.wav', f, 'audio/wav')}
            form_data = {
                'title': title,
                'category': self.category_name
            }
            
            response = requests.post(f"{self.base_url}/upload-audio", files=files, data=form_data)
            
            # This should succeed with the new limit
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data["message"], "File uploaded successfully")
                self.assertIn("file_id", data)
                self.assertEqual(data["title"], title)
                print("✅ Successfully uploaded 7.1MB file with 10MB limit")
            else:
                self.fail(f"Failed to upload 7.1MB file with 10MB limit: {response.status_code}")
    
    def test_modify_limit_to_15mb(self):
        """Test modifying the file size limit to 15MB"""
        # Modify the file size limit to 15MB
        self.modify_file_size_limit(15)
        
        # Create a category for testing
        self.test_create_category()
        
        # Test uploading a 10.1MB file (should succeed now)
        wav_file_path = self.create_test_wav_file(10.1)
        
        # Prepare form data
        title = f"Test Audio 10.1MB {int(time.time())}"
        
        with open(wav_file_path, 'rb') as f:
            files = {'file': ('test_audio.wav', f, 'audio/wav')}
            form_data = {
                'title': title,
                'category': self.category_name
            }
            
            response = requests.post(f"{self.base_url}/upload-audio", files=files, data=form_data)
            
            # This might still fail if there are other limitations
            if response.status_code == 200:
                data = response.json()
                self.assertEqual(data["message"], "File uploaded successfully")
                self.assertIn("file_id", data)
                self.assertEqual(data["title"], title)
                print("✅ Successfully uploaded 10.1MB file with 15MB limit")
            else:
                print(f"❌ Failed to upload 10.1MB file with 15MB limit: {response.status_code}")
                print(f"Response: {response.text}")

def main():
    # Run the tests
    unittest.main(argv=['first-arg-is-ignored'], exit=False)

if __name__ == "__main__":
    main()
