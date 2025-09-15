"""
BOM2Pic - Test version without authentication
Simple FastAPI application for local testing of core functionality.
"""
import os
from datetime import datetime
from typing import List

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from .excel_processor import process_excel_files


# Configuration
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))

app = FastAPI(title="BOM2Pic Test", version="2.0.0-test", description="Clean Excel Image Extractor - Test Mode")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", include_in_schema=False)
def root():
    """Redirect to test page."""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="/static/test.html")


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "2.0.0-test", "mode": "testing"}


@app.post("/process")
async def process_files(
    files: List[UploadFile] = File(...),
    imageColumn: str = Form(...),
    nameColumn: str = Form(...)
):
    """Process Excel files and extract images - TEST MODE (no auth required)."""
    
    print(f"🧪 TEST MODE: Processing {len(files)} files")
    print(f"   Image column: {imageColumn}")
    print(f"   Name column: {nameColumn}")
    
    # Validate files
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
    
    # Validate columns
    if not imageColumn or not nameColumn:
        raise HTTPException(status_code=400, detail="Both image and name columns are required")
    
    if imageColumn == nameColumn:
        raise HTTPException(status_code=400, detail="Image and name columns must be different")
    
    # Process files
    try:
        files_data = []
        for file in files:
            if not file.filename.lower().endswith('.xlsx'):
                raise HTTPException(status_code=400, detail=f"Only .xlsx files supported: {file.filename}")
            
            contents = await file.read()
            size_mb = len(contents) / (1024 * 1024)
            if size_mb > MAX_UPLOAD_MB:
                raise HTTPException(status_code=400, detail=f"File too large: {file.filename}")
            
            files_data.append((file.filename, contents))
            print(f"   Loaded: {file.filename} ({size_mb:.1f}MB)")
        
        # Process all files
        zip_buffer, total_images, saved_count, duplicate_count = process_excel_files(
            files_data, imageColumn, nameColumn
        )
        
        print(f"   Results: {total_images} total, {saved_count} saved, {duplicate_count} duplicates")
        
        # Create response
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"bom2pic_images_{timestamp}.zip"
        
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Content-Type-Options": "nosniff",
            "X-B2P-Processed": str(total_images),
            "X-B2P-Saved": str(saved_count),
            "X-B2P-Duplicate": str(duplicate_count),
            "X-B2P-Mode": "test"
        }
        
        return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        print(f"❌ Processing error: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    print("🧪 Starting BOM2Pic in TEST MODE (no authentication required)")
    print("   Open http://localhost:8000 in your browser")
    uvicorn.run("app.main_test:app", host="0.0.0.0", port=8000, reload=True)
