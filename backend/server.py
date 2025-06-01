from fastapi import FastAPI, File, UploadFile, HTTPException, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from motor.motor_asyncio import AsyncIOMotorClient
import os
import uuid
import shutil
from pathlib import Path
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
import mimetypes

# Pydantic models
class AudioFile(BaseModel):
    id: str
    filename: str
    original_filename: str
    title: str
    category: str
    duration: Optional[float] = None
    file_size: int
    uploaded_at: datetime
    file_path: str

class Category(BaseModel):
    id: str
    name: str
    color: str
    created_at: datetime

app = FastAPI()

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# MongoDB connection
MONGO_URL = os.environ.get('MONGO_URL', 'mongodb://localhost:27017')
DB_NAME = os.environ.get('DB_NAME', 'podcast_service')

client = AsyncIOMotorClient(MONGO_URL)
db = client[DB_NAME]

# Create uploads directory
uploads_dir = Path("uploads")
uploads_dir.mkdir(exist_ok=True)

# Mount static files
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

# API Routes

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "wyEBIYA-podcast-service"}

@app.post("/api/upload-audio-chunk")
async def upload_audio_chunk(
    chunk: UploadFile = File(...),
    chunk_number: int = Form(...),
    total_chunks: int = Form(...),
    file_id: str = Form(...),
    title: str = Form(None),
    category: str = Form(None),
    original_filename: str = Form(...)
):
    """Upload a single chunk of an audio file"""
    
    try:
        # Create chunks directory if it doesn't exist
        chunks_dir = Path("chunks") / file_id
        chunks_dir.mkdir(parents=True, exist_ok=True)
        
        # Save chunk
        chunk_path = chunks_dir / f"chunk_{chunk_number}"
        chunk_content = await chunk.read()
        
        with open(chunk_path, "wb") as buffer:
            buffer.write(chunk_content)
        
        # Check if all chunks are uploaded
        uploaded_chunks = len(list(chunks_dir.glob("chunk_*")))
        
        if uploaded_chunks == total_chunks:
            # Combine all chunks
            combined_file_path = uploads_dir / f"{file_id}.wav"
            
            with open(combined_file_path, "wb") as combined_file:
                for i in range(total_chunks):
                    chunk_file_path = chunks_dir / f"chunk_{i}"
                    with open(chunk_file_path, "rb") as chunk_file:
                        combined_file.write(chunk_file.read())
            
            # Calculate file size
            file_size = os.path.getsize(combined_file_path)
            
            # Validate total file size (50MB limit for chunked uploads)
            if file_size > 50 * 1024 * 1024:  # 50MB
                os.remove(combined_file_path)
                shutil.rmtree(chunks_dir, ignore_errors=True)
                raise HTTPException(status_code=413, detail="File size must be less than 50MB")
            
            # Validate file type
            if not original_filename.endswith('.wav'):
                os.remove(combined_file_path)
                shutil.rmtree(chunks_dir, ignore_errors=True)
                raise HTTPException(status_code=400, detail="Only WAV files are supported")
            
            # Save to database
            audio_record = {
                "id": file_id,
                "filename": f"{file_id}.wav",
                "original_filename": original_filename,
                "title": title,
                "category": category,
                "file_size": file_size,
                "uploaded_at": datetime.utcnow(),
                "file_path": str(combined_file_path)
            }
            
            await db.audio_files.insert_one(audio_record)
            
            # Clean up chunks
            shutil.rmtree(chunks_dir, ignore_errors=True)
            
            return {
                "message": "File uploaded successfully", 
                "file_id": file_id, 
                "title": title,
                "file_size": file_size,
                "completed": True
            }
        else:
            return {
                "message": f"Chunk {chunk_number + 1}/{total_chunks} uploaded", 
                "chunks_uploaded": uploaded_chunks,
                "total_chunks": total_chunks,
                "completed": False
            }
    
    except HTTPException:
        raise
    except Exception as e:
        # Clean up on error
        chunks_dir = Path("chunks") / file_id
        if chunks_dir.exists():
            shutil.rmtree(chunks_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.post("/api/upload-audio")
async def upload_audio(
    file: UploadFile = File(..., description="WAV audio file (max 100MB)"),
    title: str = Form(..., description="Audio title"),
    category: str = Form(..., description="Audio category")
):
    """Upload a WAV audio file"""
    
    try:
        # Validate file type
        if not file.filename.endswith('.wav'):
            raise HTTPException(status_code=400, detail="Only WAV files are supported")
        
        # Check file size using file.file which is available in FastAPI
        file.file.seek(0, 2)  # Seek to end of file
        file_size = file.file.tell()  # Get file size
        file.file.seek(0)  # Reset to beginning
        
        # Validate file size (7MB limit - server environment constraint)
        max_size = 10 * 1024 * 1024  # 10MB
        if file_size > max_size:
            raise HTTPException(status_code=413, detail="File size must be less than 10MB")
        
        # Read file content
        file_content = await file.read()
        
        # Generate unique filename
        file_id = str(uuid.uuid4())
        file_extension = ".wav"
        filename = f"{file_id}{file_extension}"
        file_path = uploads_dir / filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            buffer.write(file_content)
        
        # Create audio file record
        audio_record = {
            "id": file_id,
            "filename": filename,
            "original_filename": file.filename,
            "title": title,
            "category": category,
            "file_size": file_size,
            "uploaded_at": datetime.utcnow(),
            "file_path": str(file_path)
        }
        
        # Save to database
        await db.audio_files.insert_one(audio_record)
        
        return {"message": "File uploaded successfully", "file_id": file_id, "title": title, "file_size": file_size}
    
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        # Handle any other errors
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

@app.get("/api/audio-files")
async def get_audio_files(category: Optional[str] = None):
    """Get all audio files, optionally filtered by category"""
    
    query = {}
    if category:
        query["category"] = category
    
    cursor = db.audio_files.find(query).sort("uploaded_at", -1)
    audio_files = await cursor.to_list(length=100)
    
    # Convert ObjectId to string and format response
    for audio in audio_files:
        audio["_id"] = str(audio["_id"])
        audio["file_url"] = f"/uploads/{audio['filename']}"
    
    return {"audio_files": audio_files}

@app.get("/api/audio-file/{file_id}")
async def get_audio_file(file_id: str):
    """Get specific audio file details"""
    
    audio_file = await db.audio_files.find_one({"id": file_id})
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    audio_file["_id"] = str(audio_file["_id"])
    audio_file["file_url"] = f"/uploads/{audio_file['filename']}"
    
    return audio_file

@app.delete("/api/audio-file/{file_id}")
async def delete_audio_file(file_id: str):
    """Delete an audio file"""
    
    audio_file = await db.audio_files.find_one({"id": file_id})
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    # Delete file from filesystem
    file_path = Path(audio_file["file_path"])
    if file_path.exists():
        file_path.unlink()
    
    # Delete from database
    await db.audio_files.delete_one({"id": file_id})
    
    return {"message": "Audio file deleted successfully"}

@app.get("/api/categories")
async def get_categories():
    """Get all categories"""
    
    cursor = db.categories.find({}).sort("name", 1)
    categories = await cursor.to_list(length=100)
    
    for category in categories:
        category["_id"] = str(category["_id"])
    
    return {"categories": categories}

@app.post("/api/categories")
async def create_category(name: str = Form(...), color: str = Form("#3B82F6")):
    """Create a new category"""
    
    # Check if category already exists
    existing = await db.categories.find_one({"name": name})
    if existing:
        raise HTTPException(status_code=400, detail="Category already exists")
    
    category_id = str(uuid.uuid4())
    category_record = {
        "id": category_id,
        "name": name,
        "color": color,
        "created_at": datetime.utcnow()
    }
    
    await db.categories.insert_one(category_record)
    
    return {"message": "Category created successfully", "category_id": category_id}

@app.delete("/api/categories/{category_name}")
async def delete_category(category_name: str):
    """Delete a category"""
    
    # Check if category exists
    category = await db.categories.find_one({"name": category_name})
    if not category:
        raise HTTPException(status_code=404, detail="Category not found")
    
    # Check if there are audio files using this category
    audio_files_count = await db.audio_files.count_documents({"category": category_name})
    if audio_files_count > 0:
        raise HTTPException(
            status_code=400, 
            detail=f"Cannot delete category. {audio_files_count} audio files are using this category."
        )
    
    # Delete the category
    await db.categories.delete_one({"name": category_name})
    
    return {"message": "Category deleted successfully", "category_name": category_name}

@app.get("/api/audio-stream/{file_id}")
async def stream_audio(file_id: str):
    """Stream audio file"""
    
    audio_file = await db.audio_files.find_one({"id": file_id})
    if not audio_file:
        raise HTTPException(status_code=404, detail="Audio file not found")
    
    file_path = Path(audio_file["file_path"])
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="Audio file not found on disk")
    
    return FileResponse(
        path=file_path,
        media_type="audio/wav",
        filename=audio_file["original_filename"]
    )

if __name__ == "__main__":
    import uvicorn
    # Configure uvicorn to handle larger file uploads
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8001,
        limit_max_requests=1000,
        timeout_keep_alive=30,
        limit_concurrency=1000
    )