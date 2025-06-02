import requests
import io
import sys
import os

def test_file_size_limit():
    """Test the 100MB file size limit for audio uploads"""
    
    # Get the backend URL from environment or use the default
    backend_url = "https://1e3d862d-5dd1-4551-a519-06c14af7772e.preview.emergentagent.com"
    
    print("🔍 Testing file size limit functionality...")
    
    # Test uploading a file that's just over 100MB (should fail)
    print("\n🔍 Testing Upload of file exceeding 100MB limit...")
    
    # Create a file-like object with content just over 100MB
    file_size_mb = 101
    file_content = io.BytesIO(b"0" * (file_size_mb * 1024 * 1024))
    
    # Prepare the form data
    files = {
        'file': ('test_large.wav', file_content, 'audio/wav')
    }
    data = {
        'title': 'Test Large File',
        'category': 'Test Category 153158'
    }
    
    try:
        response = requests.post(
            f"{backend_url}/api/upload-audio",
            files=files,
            data=data
        )
        
        # Check if the request was rejected with a 400 status code
        if response.status_code == 400 and "File size must be less than 100MB" in response.text:
            print("✅ Passed - Server correctly rejected file over 100MB")
            print(f"Response: {response.json()}")
            return True
        else:
            print(f"❌ Failed - Expected 400 status code with size limit message, got {response.status_code}")
            print(f"Response: {response.text}")
            return False
    except Exception as e:
        print(f"❌ Failed - Error: {str(e)}")
        return False

if __name__ == "__main__":
    success = test_file_size_limit()
    sys.exit(0 if success else 1)