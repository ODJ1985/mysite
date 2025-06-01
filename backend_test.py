import requests
import os
import io
import time
import uuid
from datetime import datetime

class PodcastUploadTester:
    def __init__(self, base_url):
        self.base_url = base_url
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.test_files = {}
        self.created_categories = []
        self.uploaded_files = []

    def run_test(self, name, test_func):
        """Run a single test and record results"""
        self.tests_run += 1
        print(f"\n🔍 Testing: {name}")
        
        start_time = time.time()
        try:
            result = test_func()
            success = True
            error = None
        except Exception as e:
            result = None
            success = False
            error = str(e)
        
        duration = time.time() - start_time
        
        if success:
            self.tests_passed += 1
            status = "✅ PASSED"
        else:
            status = "❌ FAILED"
        
        print(f"{status} - {name} ({duration:.2f}s)")
        if error:
            print(f"  Error: {error}")
        
        self.test_results.append({
            "name": name,
            "success": success,
            "duration": duration,
            "error": error,
            "result": result
        })
        
        return success, result

    def create_test_files(self):
        """Create test files of different sizes"""
        print("\n📁 Creating test files...")
        
        # Small file (5MB)
        small_file_size = 5 * 1024 * 1024  # 5MB
        small_file_data = os.urandom(small_file_size)
        self.test_files["small"] = {
            "name": "small_test.wav",
            "size": small_file_size,
            "data": small_file_data
        }
        print(f"  Created small test file: {small_file_size / (1024 * 1024):.1f}MB")
        
        # Medium file (10MB)
        medium_file_size = 10 * 1024 * 1024  # 10MB
        medium_file_data = os.urandom(medium_file_size)
        self.test_files["medium"] = {
            "name": "medium_test.wav",
            "size": medium_file_size,
            "data": medium_file_data
        }
        print(f"  Created medium test file: {medium_file_size / (1024 * 1024):.1f}MB")
        
        # Large file (30MB)
        large_file_size = 30 * 1024 * 1024  # 30MB
        large_file_data = os.urandom(large_file_size)
        self.test_files["large"] = {
            "name": "large_test.wav",
            "size": large_file_size,
            "data": large_file_data
        }
        print(f"  Created large test file: {large_file_size / (1024 * 1024):.1f}MB")
        
        # Oversized file (55MB)
        oversized_file_size = 55 * 1024 * 1024  # 55MB
        oversized_file_data = os.urandom(oversized_file_size)
        self.test_files["oversized"] = {
            "name": "oversized_test.wav",
            "size": oversized_file_size,
            "data": oversized_file_data
        }
        print(f"  Created oversized test file: {oversized_file_size / (1024 * 1024):.1f}MB")
        
        # Invalid file type
        invalid_file_size = 5 * 1024 * 1024  # 5MB
        invalid_file_data = os.urandom(invalid_file_size)
        self.test_files["invalid_type"] = {
            "name": "invalid_test.mp3",
            "size": invalid_file_size,
            "data": invalid_file_data
        }
        print(f"  Created invalid file type test: {invalid_file_size / (1024 * 1024):.1f}MB")

    def test_health_check(self):
        """Test the health check endpoint"""
        response = requests.get(f"{self.base_url}/api/health")
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        data = response.json()
        assert data["status"] == "healthy", f"Expected status 'healthy', got {data['status']}"
        return data

    def create_test_category(self):
        """Create a test category"""
        category_name = f"Test Category {datetime.now().strftime('%H%M%S')}"
        
        data = {
            "name": category_name,
            "color": "#3B82F6"
        }
        
        response = requests.post(
            f"{self.base_url}/api/categories",
            data=data
        )
        
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        result = response.json()
        assert "category_id" in result, "Response missing category_id"
        
        self.created_categories.append(category_name)
        return category_name

    def test_regular_upload(self):
        """Test regular upload for small files (< 7MB)"""
        # Create a test category if needed
        if not self.created_categories:
            category = self.create_test_category()
        else:
            category = self.created_categories[0]
        
        # Prepare the file
        file_info = self.test_files["small"]
        file_obj = io.BytesIO(file_info["data"])
        
        # Prepare form data
        files = {
            "file": (file_info["name"], file_obj, "audio/wav")
        }
        data = {
            "title": f"Small File Test {datetime.now().strftime('%H%M%S')}",
            "category": category
        }
        
        # Upload the file
        response = requests.post(
            f"{self.base_url}/api/upload-audio",
            files=files,
            data=data
        )
        
        # Check response
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        result = response.json()
        assert "file_id" in result, "Response missing file_id"
        
        # Store the file ID for cleanup
        self.uploaded_files.append(result["file_id"])
        
        return result

    def test_chunked_upload(self, file_key="medium"):
        """Test chunked upload for larger files"""
        # Create a test category if needed
        if not self.created_categories:
            category = self.create_test_category()
        else:
            category = self.created_categories[0]
        
        # Prepare the file
        file_info = self.test_files[file_key]
        file_data = file_info["data"]
        file_size = file_info["size"]
        
        # Generate a file ID
        file_id = str(uuid.uuid4())
        
        # Split into 5MB chunks
        chunk_size = 5 * 1024 * 1024  # 5MB
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        print(f"  Uploading {file_key} file ({file_size / (1024 * 1024):.1f}MB) in {total_chunks} chunks")
        
        # Upload each chunk
        for chunk_index in range(total_chunks):
            start = chunk_index * chunk_size
            end = min(start + chunk_size, file_size)
            chunk_data = file_data[start:end]
            
            # Prepare form data
            chunk_file = io.BytesIO(chunk_data)
            files = {
                "chunk": (f"chunk_{chunk_index}", chunk_file, "application/octet-stream")
            }
            
            data = {
                "chunk_number": str(chunk_index),
                "total_chunks": str(total_chunks),
                "file_id": file_id,
                "original_filename": file_info["name"]
            }
            
            # Add title and category only on the last chunk
            if chunk_index == total_chunks - 1:
                data["title"] = f"{file_key.capitalize()} File Test {datetime.now().strftime('%H%M%S')}"
                data["category"] = category
            
            # Upload the chunk
            response = requests.post(
                f"{self.base_url}/api/upload-audio-chunk",
                files=files,
                data=data
            )
            
            # Check response
            assert response.status_code == 200, f"Chunk {chunk_index} upload failed with status {response.status_code}"
            result = response.json()
            
            # Check if this is the last chunk
            if chunk_index == total_chunks - 1:
                assert result["completed"] == True, "Final chunk should mark upload as completed"
                assert "file_id" in result, "Response missing file_id"
                self.uploaded_files.append(result["file_id"])
                return result
            else:
                assert result["completed"] == False, "Non-final chunk should not mark upload as completed"
                assert result["chunks_uploaded"] == chunk_index + 1, f"Expected {chunk_index + 1} chunks uploaded, got {result['chunks_uploaded']}"
        
        return None  # Should not reach here

    def test_oversized_file(self):
        """Test upload of a file exceeding the 50MB limit"""
        # Create a test category if needed
        if not self.created_categories:
            category = self.create_test_category()
        else:
            category = self.created_categories[0]
        
        # Prepare the file
        file_info = self.test_files["oversized"]
        file_data = file_info["data"]
        file_size = file_info["size"]
        
        # Generate a file ID
        file_id = str(uuid.uuid4())
        
        # Split into 5MB chunks
        chunk_size = 5 * 1024 * 1024  # 5MB
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        print(f"  Uploading oversized file ({file_size / (1024 * 1024):.1f}MB) in {total_chunks} chunks")
        
        # Upload each chunk
        for chunk_index in range(total_chunks):
            start = chunk_index * chunk_size
            end = min(start + chunk_size, file_size)
            chunk_data = file_data[start:end]
            
            # Prepare form data
            chunk_file = io.BytesIO(chunk_data)
            files = {
                "chunk": (f"chunk_{chunk_index}", chunk_file, "application/octet-stream")
            }
            
            data = {
                "chunk_number": str(chunk_index),
                "total_chunks": str(total_chunks),
                "file_id": file_id,
                "original_filename": file_info["name"]
            }
            
            # Add title and category only on the last chunk
            if chunk_index == total_chunks - 1:
                data["title"] = f"Oversized File Test {datetime.now().strftime('%H%M%S')}"
                data["category"] = category
            
            # Upload the chunk
            response = requests.post(
                f"{self.base_url}/api/upload-audio-chunk",
                files=files,
                data=data
            )
            
            # For the last chunk, we expect a 413 error
            if chunk_index == total_chunks - 1:
                assert response.status_code == 413, f"Expected status code 413 for oversized file, got {response.status_code}"
                return response.json()
            else:
                # Earlier chunks should succeed
                assert response.status_code == 200, f"Chunk {chunk_index} upload failed with status {response.status_code}"
        
        return None  # Should not reach here

    def test_invalid_file_type(self):
        """Test upload of a non-WAV file"""
        # Create a test category if needed
        if not self.created_categories:
            category = self.create_test_category()
        else:
            category = self.created_categories[0]
        
        # Prepare the file
        file_info = self.test_files["invalid_type"]
        file_data = file_info["data"]
        file_size = file_info["size"]
        
        # Generate a file ID
        file_id = str(uuid.uuid4())
        
        # Split into chunks
        chunk_size = 5 * 1024 * 1024  # 5MB
        total_chunks = (file_size + chunk_size - 1) // chunk_size
        
        # Upload each chunk
        for chunk_index in range(total_chunks):
            start = chunk_index * chunk_size
            end = min(start + chunk_size, file_size)
            chunk_data = file_data[start:end]
            
            # Prepare form data
            chunk_file = io.BytesIO(chunk_data)
            files = {
                "chunk": (f"chunk_{chunk_index}", chunk_file, "application/octet-stream")
            }
            
            data = {
                "chunk_number": str(chunk_index),
                "total_chunks": str(total_chunks),
                "file_id": file_id,
                "original_filename": file_info["name"]
            }
            
            # Add title and category only on the last chunk
            if chunk_index == total_chunks - 1:
                data["title"] = f"Invalid Type Test {datetime.now().strftime('%H%M%S')}"
                data["category"] = category
            
            # Upload the chunk
            response = requests.post(
                f"{self.base_url}/api/upload-audio-chunk",
                files=files,
                data=data
            )
            
            # For the last chunk, we expect a 400 error
            if chunk_index == total_chunks - 1:
                assert response.status_code == 400, f"Expected status code 400 for invalid file type, got {response.status_code}"
                return response.json()
            else:
                # Earlier chunks should succeed
                assert response.status_code == 200, f"Chunk {chunk_index} upload failed with status {response.status_code}"
        
        return None  # Should not reach here

    def test_verify_uploaded_file(self, file_id):
        """Verify that an uploaded file can be retrieved and streamed"""
        # Get file details
        response = requests.get(f"{self.base_url}/api/audio-file/{file_id}")
        assert response.status_code == 200, f"Expected status code 200, got {response.status_code}"
        file_details = response.json()
        
        # Check file stream
        stream_response = requests.get(f"{self.base_url}/api/audio-stream/{file_id}")
        assert stream_response.status_code == 200, f"Expected status code 200, got {stream_response.status_code}"
        assert stream_response.headers["Content-Type"] == "audio/wav", f"Expected Content-Type audio/wav, got {stream_response.headers['Content-Type']}"
        
        return file_details

    def cleanup(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete uploaded files
        for file_id in self.uploaded_files:
            try:
                response = requests.delete(f"{self.base_url}/api/audio-file/{file_id}")
                if response.status_code == 200:
                    print(f"  Deleted file {file_id}")
                else:
                    print(f"  Failed to delete file {file_id}: {response.status_code}")
            except Exception as e:
                print(f"  Error deleting file {file_id}: {str(e)}")
        
        # Delete categories
        for category in self.created_categories:
            try:
                response = requests.delete(f"{self.base_url}/api/categories/{category}")
                if response.status_code == 200:
                    print(f"  Deleted category {category}")
                else:
                    print(f"  Failed to delete category {category}: {response.status_code}")
            except Exception as e:
                print(f"  Error deleting category {category}: {str(e)}")

    def run_all_tests(self):
        """Run all tests"""
        print(f"\n🚀 Starting tests against {self.base_url}")
        
        # Create test files
        self.create_test_files()
        
        # Run tests
        self.run_test("Health Check", self.test_health_check)
        
        # Test regular upload
        success, result = self.run_test("Regular Upload (Small File)", self.test_regular_upload)
        if success and result:
            small_file_id = result["file_id"]
            self.run_test("Verify Small File", lambda: self.test_verify_uploaded_file(small_file_id))
        
        # Test chunked upload with medium file
        success, result = self.run_test("Chunked Upload (Medium File)", lambda: self.test_chunked_upload("medium"))
        if success and result:
            medium_file_id = result["file_id"]
            self.run_test("Verify Medium File", lambda: self.test_verify_uploaded_file(medium_file_id))
        
        # Test chunked upload with large file
        success, result = self.run_test("Chunked Upload (Large File)", lambda: self.test_chunked_upload("large"))
        if success and result:
            large_file_id = result["file_id"]
            self.run_test("Verify Large File", lambda: self.test_verify_uploaded_file(large_file_id))
        
        # Test oversized file
        self.run_test("Oversized File Rejection", self.test_oversized_file)
        
        # Test invalid file type
        self.run_test("Invalid File Type Rejection", self.test_invalid_file_type)
        
        # Clean up
        self.cleanup()
        
        # Print summary
        print(f"\n📊 Test Summary: {self.tests_passed}/{self.tests_run} tests passed")
        
        return self.tests_passed == self.tests_run

if __name__ == "__main__":
    # Get backend URL from environment or use default
    backend_url = os.environ.get("BACKEND_URL", "https://9fe0c2b0-7831-40b8-a607-5c9b24890339.preview.emergentagent.com")
    
    tester = PodcastUploadTester(backend_url)
    success = tester.run_all_tests()
    
    # Exit with appropriate status code
    exit(0 if success else 1)
