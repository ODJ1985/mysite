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
        
        # Read file content in chunks to handle large files
        file_content = bytearray()
        max_size = 100 * 1024 * 1024  # 100MB
        
        async for chunk in file.stream():
            if len(file_content) + len(chunk) > max_size:
                raise HTTPException(status_code=413, detail="File size must be less than 100MB")
            file_content.extend(chunk)
        
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
            "file_size": len(file_content),
            "uploaded_at": datetime.utcnow(),
            "file_path": str(file_path)
        }
        
        # Save to database
        await db.audio_files.insert_one(audio_record)
        
        return {"message": "File uploaded successfully", "file_id": file_id, "title": title, "file_size": len(file_content)}
    
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
    uvicorn.run(app, host="0.0.0.0", port=8001)