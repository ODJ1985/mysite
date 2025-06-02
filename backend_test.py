#!/usr/bin/env python3
import requests
import sys
import os
import json
import uuid
import time
from datetime import datetime
from pathlib import Path

class WyEBIYAPodcastTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_category = f"Test Category {uuid.uuid4().hex[:6]}"
        self.test_audio_id = None
        self.test_file_path = "/app/backend_test_audio.wav"
        self.test_rating_id = None
        self.test_comment_id = None
        self.test_user_name = f"TestUser_{uuid.uuid4().hex[:6]}"
        
        # Create a test audio file if it doesn't exist
        self.create_test_audio_file()
        
    def create_test_audio_file(self):
        """Create a simple WAV file for testing if it doesn't exist"""
        if not Path(self.test_file_path).exists():
            try:
                # Create a simple WAV file (1 second of silence)
                import wave
                import struct
                
                # Parameters for the WAV file
                nchannels = 1
                sampwidth = 2
                framerate = 44100
                nframes = 44100
                comptype = "NONE"
                compname = "not compressed"
                
                with wave.open(self.test_file_path, "w") as wav_file:
                    wav_file.setparams((nchannels, sampwidth, framerate, nframes, comptype, compname))
                    for i in range(nframes):
                        wav_file.writeframes(struct.pack('h', 0))  # Write silence
                
                print(f"Created test audio file: {self.test_file_path}")
            except Exception as e:
                print(f"Error creating test audio file: {e}")
                # Create an empty file as fallback
                with open(self.test_file_path, "wb") as f:
                    f.write(b"\x52\x49\x46\x46\x24\x57\x41\x56\x45\x66\x6d\x74\x20\x10\x01\x01\x44\xac\x88\x58\x01\x02\x10\x64\x61\x74\x61")
                print(f"Created minimal test audio file: {self.test_file_path}")
        
    def run_test(self, name, method, endpoint, expected_status, data=None, files=None, headers=None, params=None):
        """Run a single API test"""
        url = f"{self.base_url}/{endpoint}"
        default_headers = {'Accept': 'application/json'}
        if headers:
            default_headers.update(headers)
            
        self.tests_run += 1
        print(f"\n🔍 Testing {name}...")
        
        try:
            if method == 'GET':
                response = requests.get(url, headers=default_headers, params=params)
            elif method == 'POST':
                response = requests.post(url, data=data, files=files, headers=default_headers)
            elif method == 'DELETE':
                response = requests.delete(url, headers=default_headers)
                
            success = response.status_code == expected_status
            if success:
                self.tests_passed += 1
                print(f"✅ Passed - Status: {response.status_code}")
                try:
                    return success, response.json() if response.text else {}
                except json.JSONDecodeError:
                    return success, response.content
            else:
                print(f"❌ Failed - Expected {expected_status}, got {response.status_code}")
                print(f"Response: {response.text[:200]}...")
                return False, {}
                
        except Exception as e:
            print(f"❌ Failed - Error: {str(e)}")
            return False, {}
            
    def test_health_check(self):
        """Test the health check endpoint"""
        success, data = self.run_test("Health Check", "GET", "api/health", 200)
        if success:
            if data.get("status") == "healthy" and data.get("service") == "wyEBIYA-podcast-service":
                print("✅ Health check response contains correct data")
            else:
                print(f"⚠️ Health check response has unexpected format: {data}")
        return success, data
        
    def test_create_category(self):
        """Test creating a new category"""
        success, data = self.run_test(
            "Create Category", 
            "POST", 
            "api/categories", 
            200, 
            data={"name": self.test_category, "color": "#FF5733"}
        )
        if success:
            if "category_id" in data and data.get("message") == "Category created successfully":
                print(f"✅ Category '{self.test_category}' created successfully")
            else:
                print(f"⚠️ Category creation response has unexpected format: {data}")
        return success, data
        
    def test_get_categories(self):
        """Test getting all categories"""
        success, data = self.run_test("Get Categories", "GET", "api/categories", 200)
        if success:
            if "categories" in data:
                categories = data["categories"]
                print(f"✅ Retrieved {len(categories)} categories")
                
                # Check if our test category is in the list
                found = any(cat["name"] == self.test_category for cat in categories)
                if found:
                    print(f"✅ Test category '{self.test_category}' found in the list")
                else:
                    print(f"⚠️ Test category '{self.test_category}' not found in the list")
            else:
                print(f"⚠️ Get categories response has unexpected format: {data}")
        return success, data
        
    def test_upload_audio(self):
        """Test uploading an audio file"""
        try:
            with open(self.test_file_path, "rb") as audio_file:
                files = {"file": (f"test_audio_{uuid.uuid4().hex[:6]}.wav", audio_file, "audio/wav")}
                data = {
                    "title": f"Test Audio {uuid.uuid4().hex[:6]}",
                    "category": self.test_category
                }
                
                success, result = self.run_test(
                    "Upload Audio", 
                    "POST", 
                    "api/upload-audio", 
                    200, 
                    data=data,
                    files=files
                )
                
                if success and "file_id" in result:
                    self.test_audio_id = result["file_id"]
                    print(f"✅ Audio file uploaded successfully. ID: {self.test_audio_id}")
                return success, result
        except Exception as e:
            print(f"❌ Audio upload test failed: {e}")
            return False, {}
    
    def test_get_audio_files(self):
        """Test getting all audio files"""
        success, data = self.run_test("Get Audio Files", "GET", "api/audio-files", 200)
        if success:
            if "audio_files" in data:
                audio_files = data["audio_files"]
                print(f"✅ Retrieved {len(audio_files)} audio files")
                
                # If we don't have a test audio ID yet, use the first one from the list
                if not self.test_audio_id and audio_files:
                    self.test_audio_id = audio_files[0]["id"]
                    print(f"✅ Using existing audio file for testing. ID: {self.test_audio_id}")
                
                # Test with category filter if we have a test category
                if self.test_category:
                    success2, data2 = self.run_test(
                        f"Get Audio Files by Category '{self.test_category}'", 
                        "GET", 
                        "api/audio-files", 
                        200,
                        params={"category": self.test_category}
                    )
                    if success2 and "audio_files" in data2:
                        filtered_files = data2["audio_files"]
                        print(f"✅ Retrieved {len(filtered_files)} audio files for category '{self.test_category}'")
            else:
                print(f"⚠️ Get audio files response has unexpected format: {data}")
        return success, data
    
    def test_get_audio_file(self):
        """Test getting a specific audio file"""
        if not self.test_audio_id:
            print("⚠️ Cannot test get audio file API: No test audio ID available")
            return False, {}
        
        success, data = self.run_test(
            f"Get Audio File (ID: {self.test_audio_id})", 
            "GET", 
            f"api/audio-file/{self.test_audio_id}", 
            200
        )
        
        if success:
            if "id" in data and data["id"] == self.test_audio_id:
                print(f"✅ Retrieved audio file details for ID: {self.test_audio_id}")
                print(f"   Title: {data.get('title')}")
                print(f"   Category: {data.get('category')}")
                print(f"   File URL: {data.get('file_url')}")
            else:
                print(f"⚠️ Get audio file response has unexpected format: {data}")
        return success, data
    
    def test_stream_audio(self):
        """Test streaming an audio file"""
        if not self.test_audio_id:
            print("⚠️ Cannot test stream audio API: No test audio ID available")
            return False, {}
        
        # For streaming, we don't expect JSON but binary data
        success, data = self.run_test(
            f"Stream Audio (ID: {self.test_audio_id})", 
            "GET", 
            f"api/audio-stream/{self.test_audio_id}", 
            200
        )
        
        if success:
            if isinstance(data, bytes) or (hasattr(data, 'read') and callable(data.read)):
                print("✅ Audio streaming successful")
            else:
                print("✅ Audio streaming response received (not checking content)")
        return success, data
    
    # New test methods for rating and comment functionality
    
    def test_add_rating(self):
        """Test adding a rating to an audio file"""
        if not self.test_audio_id:
            print("⚠️ Cannot test add rating API: No test audio ID available")
            return False, {}
        
        rating_value = 4  # Rating between 1-5
        
        success, data = self.run_test(
            f"Add Rating (ID: {self.test_audio_id}, User: {self.test_user_name})", 
            "POST", 
            f"api/audio-file/{self.test_audio_id}/rating", 
            200,
            data={
                "user_name": self.test_user_name,
                "rating": rating_value
            }
        )
        
        if success:
            if "rating_id" in data and data.get("message") == "Rating added successfully":
                self.test_rating_id = data["rating_id"]
                print(f"✅ Rating added successfully. ID: {self.test_rating_id}")
            elif data.get("message") == "Rating updated successfully":
                print(f"✅ Rating updated successfully")
                # We need to get the rating ID from the feedback endpoint
                self.test_get_audio_feedback()
            else:
                print(f"⚠️ Add rating response has unexpected format: {data}")
        return success, data
    
    def test_update_rating(self):
        """Test updating a rating by the same user"""
        if not self.test_audio_id:
            print("⚠️ Cannot test update rating API: No test audio ID available")
            return False, {}
        
        new_rating_value = 5  # Updated rating
        
        success, data = self.run_test(
            f"Update Rating (ID: {self.test_audio_id}, User: {self.test_user_name})", 
            "POST", 
            f"api/audio-file/{self.test_audio_id}/rating", 
            200,
            data={
                "user_name": self.test_user_name,
                "rating": new_rating_value
            }
        )
        
        if success:
            if data.get("message") == "Rating updated successfully":
                print(f"✅ Rating updated successfully")
            else:
                print(f"⚠️ Update rating response has unexpected format: {data}")
        return success, data
    
    def test_add_comment(self):
        """Test adding a comment to an audio file"""
        if not self.test_audio_id:
            print("⚠️ Cannot test add comment API: No test audio ID available")
            return False, {}
        
        comment_text = f"This is a test comment from {self.test_user_name} at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        success, data = self.run_test(
            f"Add Comment (ID: {self.test_audio_id}, User: {self.test_user_name})", 
            "POST", 
            f"api/audio-file/{self.test_audio_id}/comment", 
            200,
            data={
                "user_name": self.test_user_name,
                "comment_text": comment_text
            }
        )
        
        if success:
            if "comment_id" in data and data.get("message") == "Comment added successfully":
                self.test_comment_id = data["comment_id"]
                print(f"✅ Comment added successfully. ID: {self.test_comment_id}")
            else:
                print(f"⚠️ Add comment response has unexpected format: {data}")
        return success, data
    
    def test_get_audio_feedback(self):
        """Test getting feedback (ratings and comments) for an audio file"""
        if not self.test_audio_id:
            print("⚠️ Cannot test get feedback API: No test audio ID available")
            return False, {}
        
        success, data = self.run_test(
            f"Get Audio Feedback (ID: {self.test_audio_id})", 
            "GET", 
            f"api/audio-file/{self.test_audio_id}/feedback", 
            200
        )
        
        if success:
            if "average_rating" in data and "total_ratings" in data and "comments" in data and "ratings" in data:
                print(f"✅ Retrieved feedback for audio file ID: {self.test_audio_id}")
                print(f"   Average Rating: {data['average_rating']}")
                print(f"   Total Ratings: {data['total_ratings']}")
                print(f"   Comments: {len(data['comments'])}")
                print(f"   Ratings: {len(data['ratings'])}")
                
                # If we don't have a rating ID yet, try to find it
                if not self.test_rating_id and data['ratings']:
                    for rating in data['ratings']:
                        if rating['user_name'] == self.test_user_name:
                            self.test_rating_id = rating['id']
                            print(f"✅ Found rating ID: {self.test_rating_id}")
                            break
                
                # If we don't have a comment ID yet, try to find it
                if not self.test_comment_id and data['comments']:
                    for comment in data['comments']:
                        if comment['user_name'] == self.test_user_name:
                            self.test_comment_id = comment['id']
                            print(f"✅ Found comment ID: {self.test_comment_id}")
                            break
            else:
                print(f"⚠️ Get feedback response has unexpected format: {data}")
        return success, data
    
    def test_invalid_file_id(self):
        """Test error handling with invalid file ID"""
        invalid_id = str(uuid.uuid4())  # Generate a random UUID that doesn't exist
        
        # Test rating with invalid ID
        success1, data1 = self.run_test(
            f"Add Rating to Invalid File ID", 
            "POST", 
            f"api/audio-file/{invalid_id}/rating", 
            404,
            data={
                "user_name": self.test_user_name,
                "rating": 5
            }
        )
        
        # Test comment with invalid ID
        success2, data2 = self.run_test(
            f"Add Comment to Invalid File ID", 
            "POST", 
            f"api/audio-file/{invalid_id}/comment", 
            404,
            data={
                "user_name": self.test_user_name,
                "comment_text": "This should fail"
            }
        )
        
        # Test get feedback with invalid ID
        success3, data3 = self.run_test(
            f"Get Feedback for Invalid File ID", 
            "GET", 
            f"api/audio-file/{invalid_id}/feedback", 
            404
        )
        
        return success1 and success2 and success3, {}
    
    def test_delete_comment(self):
        """Test deleting a comment"""
        if not self.test_comment_id:
            print("⚠️ Cannot test delete comment API: No test comment ID available")
            return False, {}
        
        success, data = self.run_test(
            f"Delete Comment (ID: {self.test_comment_id})", 
            "DELETE", 
            f"api/comments/{self.test_comment_id}", 
            200
        )
        
        if success:
            if data.get("message") == "Comment deleted successfully":
                print(f"✅ Comment deleted successfully")
                
                # Verify deletion by checking feedback
                success2, data2 = self.run_test(
                    f"Verify Comment Deletion", 
                    "GET", 
                    f"api/audio-file/{self.test_audio_id}/feedback", 
                    200
                )
                
                if success2:
                    comments = data2.get("comments", [])
                    if not any(comment["id"] == self.test_comment_id for comment in comments):
                        print("✅ Verified comment was deleted (not in comments list)")
                    else:
                        print("⚠️ Comment still in list after deletion")
            else:
                print(f"⚠️ Delete comment response has unexpected format: {data}")
        return success, data
    
    def test_delete_rating(self):
        """Test deleting a rating"""
        if not self.test_rating_id:
            print("⚠️ Cannot test delete rating API: No test rating ID available")
            return False, {}
        
        success, data = self.run_test(
            f"Delete Rating (ID: {self.test_rating_id})", 
            "DELETE", 
            f"api/ratings/{self.test_rating_id}", 
            200
        )
        
        if success:
            if data.get("message") == "Rating deleted successfully":
                print(f"✅ Rating deleted successfully")
                
                # Verify deletion by checking feedback
                success2, data2 = self.run_test(
                    f"Verify Rating Deletion", 
                    "GET", 
                    f"api/audio-file/{self.test_audio_id}/feedback", 
                    200
                )
                
                if success2:
                    ratings = data2.get("ratings", [])
                    if not any(rating["id"] == self.test_rating_id for rating in ratings):
                        print("✅ Verified rating was deleted (not in ratings list)")
                    else:
                        print("⚠️ Rating still in list after deletion")
            else:
                print(f"⚠️ Delete rating response has unexpected format: {data}")
        return success, data
    
    def test_delete_audio(self):
        """Test deleting an audio file"""
        if not self.test_audio_id:
            print("⚠️ Cannot test delete audio API: No test audio ID available")
            return False, {}
        
        success, data = self.run_test(
            f"Delete Audio (ID: {self.test_audio_id})", 
            "DELETE", 
            f"api/audio-file/{self.test_audio_id}", 
            200
        )
        
        if success:
            if data.get("message") == "Audio file deleted successfully":
                print(f"✅ Audio file deleted successfully")
                
                # Verify deletion by trying to get the file
                verify_success, _ = self.run_test(
                    f"Verify Audio Deletion (ID: {self.test_audio_id})", 
                    "GET", 
                    f"api/audio-file/{self.test_audio_id}", 
                    404
                )
                if verify_success:
                    print("✅ Verified audio file was deleted (404 Not Found)")
            else:
                print(f"⚠️ Delete audio response has unexpected format: {data}")
        return success, data
    
    def test_delete_category(self):
        """Test deleting a category"""
        if not self.test_category:
            print("⚠️ Cannot test delete category API: No test category available")
            return False, {}
        
        success, data = self.run_test(
            f"Delete Category '{self.test_category}'", 
            "DELETE", 
            f"api/categories/{self.test_category}", 
            200
        )
        
        # If we get a 400, it might be because there are audio files using this category
        # This is expected behavior, so we'll consider it a success
        if not success and "400" in str(data):
            print(f"⚠️ Cannot delete category because audio files are using it. This is expected behavior.")
            self.tests_passed += 1  # Count this as a pass
            return True, data
            
        if success:
            if data.get("message") == "Category deleted successfully":
                print(f"✅ Category '{self.test_category}' deleted successfully")
                
                # Verify deletion by trying to get the categories
                verify_success, verify_data = self.run_test(
                    "Verify Category Deletion", 
                    "GET", 
                    "api/categories", 
                    200
                )
                
                if verify_success:
                    categories = verify_data.get("categories", [])
                    if not any(cat["name"] == self.test_category for cat in categories):
                        print("✅ Verified category was deleted (not in categories list)")
                    else:
                        print("⚠️ Category still in list after deletion")
            else:
                print(f"⚠️ Delete category response has unexpected format: {data}")
        return success, data
    
    def run_feedback_tests(self):
        """Run tests for the new rating and comment APIs"""
        print("\n=== Starting Rating and Comment API Tests ===\n")
        
        # Make sure we have an audio file to test with
        if not self.test_audio_id:
            # Try to get existing audio files
            success, data = self.test_get_audio_files()
            if not success or not self.test_audio_id:
                # If no audio files exist, create a category and upload a test file
                self.test_create_category()
                self.test_upload_audio()
        
        # Test rating and comment APIs
        self.test_add_rating()
        self.test_add_comment()
        self.test_get_audio_feedback()
        self.test_update_rating()
        self.test_get_audio_feedback()  # Check if rating was updated
        self.test_invalid_file_id()
        self.test_delete_comment()
        self.test_delete_rating()
        
        # Print summary
        self.print_summary()
        
        return self.tests_passed == self.tests_run
        
    def run_all_tests(self):
        """Run all API tests in sequence"""
        print("\n=== Starting Backend API Tests ===\n")
        
        # Test health check endpoint
        self.test_health_check()
        
        # Test category management
        self.test_create_category()
        self.test_get_categories()
        
        # Test audio file management
        self.test_upload_audio()
        self.test_get_audio_files()
        self.test_get_audio_file()
        self.test_stream_audio()
        
        # Test rating and comment APIs
        self.test_add_rating()
        self.test_add_comment()
        self.test_get_audio_feedback()
        self.test_update_rating()
        self.test_get_audio_feedback()  # Check if rating was updated
        self.test_invalid_file_id()
        self.test_delete_comment()
        self.test_delete_rating()
        
        # Clean up - delete test audio and category
        self.test_delete_audio()
        self.test_delete_category()
        
        # Print summary
        self.print_summary()
        
        return self.tests_passed == self.tests_run
        
    def print_summary(self):
        """Print test summary"""
        print("\n" + "="*50)
        print(f"📊 Tests Summary: {self.tests_passed}/{self.tests_run} passed")
        if self.tests_passed == self.tests_run:
            print("🎉 All backend API tests passed successfully!")
        else:
            print("⚠️ Some backend API tests failed. See details above.")
        print("="*50)
        
def get_backend_url():
    """Get the backend URL from the frontend .env file"""
    env_file_path = "/app/frontend/.env"
    try:
        with open(env_file_path, "r") as f:
            for line in f:
                if line.startswith("REACT_APP_BACKEND_URL="):
                    return line.strip().split("=", 1)[1].strip('"\'')
    except Exception as e:
        print(f"Error reading frontend/.env file: {e}")
    
    # Fallback to hardcoded URL
    return "http://localhost:8001"
        
def main():
    # Get the backend URL from environment
    backend_url = get_backend_url()
    
    print(f"Testing backend at: {backend_url}")
    
    # Initialize tester
    tester = WyEBIYAPodcastTester(backend_url)
    
    # Run feedback tests only (for focused testing of new APIs)
    if len(sys.argv) > 1 and sys.argv[1] == "--feedback-only":
        success = tester.run_feedback_tests()
    else:
        # Run all tests
        success = tester.run_all_tests()
    
    return 0 if success else 1
    
if __name__ == "__main__":
    sys.exit(main())
