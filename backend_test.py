import requests
import unittest
import uuid
import os
from datetime import datetime

class CategoryDeletionTest(unittest.TestCase):
    def setUp(self):
        # Get the backend URL from environment or use the public endpoint
        self.base_url = os.environ.get('REACT_APP_BACKEND_URL', 'https://9fe0c2b0-7831-40b8-a607-5c9b24890339.preview.emergentagent.com')
        self.api_url = f"{self.base_url}/api"
        
        # Generate unique test category names
        self.timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        self.test_category_empty = f"TestEmpty_{self.timestamp}"
        self.test_category_with_files = f"TestWithFiles_{self.timestamp}"
        
        # Create test categories
        self.create_test_category(self.test_category_empty)
        self.create_test_category(self.test_category_with_files)
        
        # Upload a test audio file to the second category
        self.upload_test_audio_file(self.test_category_with_files)

    def create_test_category(self, category_name):
        """Create a test category"""
        url = f"{self.api_url}/categories"
        data = {
            "name": category_name,
            "color": "#FF5733"
        }
        response = requests.post(url, data=data)
        self.assertEqual(response.status_code, 200, f"Failed to create test category: {response.text}")
        print(f"Created test category: {category_name}")
        return response.json()

    def upload_test_audio_file(self, category_name):
        """Upload a test audio file to a category"""
        url = f"{self.api_url}/upload-audio"
        
        # Create a small test WAV file
        test_file_path = "/tmp/test_audio.wav"
        with open(test_file_path, "wb") as f:
            # Write a minimal WAV header and some data
            # RIFF header
            f.write(b'RIFF')
            f.write((36).to_bytes(4, byteorder='little'))  # File size - 8
            f.write(b'WAVE')
            
            # Format chunk
            f.write(b'fmt ')
            f.write((16).to_bytes(4, byteorder='little'))  # Chunk size
            f.write((1).to_bytes(2, byteorder='little'))   # Audio format (PCM)
            f.write((1).to_bytes(2, byteorder='little'))   # Num channels
            f.write((44100).to_bytes(4, byteorder='little'))  # Sample rate
            f.write((44100 * 2).to_bytes(4, byteorder='little'))  # Byte rate
            f.write((2).to_bytes(2, byteorder='little'))   # Block align
            f.write((16).to_bytes(2, byteorder='little'))  # Bits per sample
            
            # Data chunk
            f.write(b'data')
            f.write((8).to_bytes(4, byteorder='little'))  # Chunk size
            f.write((0).to_bytes(8, byteorder='little'))  # 8 bytes of silence
        
        # Upload the file
        with open(test_file_path, "rb") as f:
            files = {"file": ("test_audio.wav", f, "audio/wav")}
            data = {
                "title": f"Test Audio for {category_name}",
                "category": category_name
            }
            response = requests.post(url, files=files, data=data)
        
        # Clean up
        os.remove(test_file_path)
        
        self.assertEqual(response.status_code, 200, f"Failed to upload test audio file: {response.text}")
        print(f"Uploaded test audio file to category: {category_name}")
        return response.json()

    def test_delete_empty_category(self):
        """Test deleting a category with no audio files"""
        url = f"{self.api_url}/categories/{self.test_category_empty}"
        response = requests.delete(url)
        
        self.assertEqual(response.status_code, 200, f"Failed to delete empty category: {response.text}")
        print(f"Successfully deleted empty category: {self.test_category_empty}")
        
        # Verify the category is gone
        categories_response = requests.get(f"{self.api_url}/categories")
        categories = categories_response.json().get("categories", [])
        category_names = [cat["name"] for cat in categories]
        
        self.assertNotIn(self.test_category_empty, category_names, 
                         f"Category {self.test_category_empty} still exists after deletion")

    def test_delete_category_with_files(self):
        """Test deleting a category that has audio files (should fail)"""
        url = f"{self.api_url}/categories/{self.test_category_with_files}"
        response = requests.delete(url)
        
        self.assertEqual(response.status_code, 400, 
                         f"Expected 400 error when deleting category with files, got {response.status_code}")
        
        error_detail = response.json().get("detail", "")
        self.assertIn("Cannot delete category", error_detail, 
                      f"Expected error message about files using category, got: {error_detail}")
        
        print(f"Correctly prevented deletion of category with files: {self.test_category_with_files}")
        print(f"Error message: {error_detail}")

    def test_delete_nonexistent_category(self):
        """Test deleting a category that doesn't exist"""
        nonexistent_category = f"NonExistent_{uuid.uuid4()}"
        url = f"{self.api_url}/categories/{nonexistent_category}"
        response = requests.delete(url)
        
        self.assertEqual(response.status_code, 404, 
                         f"Expected 404 error when deleting nonexistent category, got {response.status_code}")
        
        print(f"Correctly returned 404 for nonexistent category: {nonexistent_category}")

    def tearDown(self):
        """Clean up test data"""
        # Try to delete the test categories (may fail for the one with files, which is expected)
        try:
            requests.delete(f"{self.api_url}/categories/{self.test_category_empty}")
        except:
            pass
            
        # For the category with files, we need to delete the files first
        try:
            # Get all audio files in the category
            response = requests.get(f"{self.api_url}/audio-files?category={self.test_category_with_files}")
            audio_files = response.json().get("audio_files", [])
            
            # Delete each audio file
            for audio in audio_files:
                requests.delete(f"{self.api_url}/audio-file/{audio['id']}")
                
            # Now try to delete the category
            requests.delete(f"{self.api_url}/categories/{self.test_category_with_files}")
        except:
            pass

if __name__ == "__main__":
    unittest.main()
