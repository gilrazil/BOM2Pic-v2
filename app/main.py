"""
BOM2Pic - Clean Excel Image Extractor
FastAPI application with simple authentication
"""
# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

import os
from datetime import datetime
from typing import List

from fastapi import FastAPI, File, UploadFile, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .auth import get_or_create_user, check_user_access, update_subscription_status
from .payment import get_plans
from .excel_processor import process_excel_files

# Configuration
MAX_UPLOAD_MB = int(os.getenv("MAX_UPLOAD_MB", "20"))

app = FastAPI(title="BOM2Pic", version="2.0.0", description="Excel Image Extractor")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure properly in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

@app.get("/", include_in_schema=False)
def root():
    """Serve the main page."""
    return FileResponse("app/static/index.html")

@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok", "version": "2.0.0", "auth": "simple"}

@app.get("/api/plans")
def api_get_plans():
    """Get available pricing plans."""
    return {"plans": get_plans()}

@app.post("/api/auth/signup")
async def signup(email: str = Form(...)):
    """Simple signup - creates user with trial."""
    try:
        user = get_or_create_user(email)
        return {
            "message": "Welcome! Your 30-day free trial has started.",
            "user": user
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/process")
async def process_files(
    files: List[UploadFile] = File(...),
    imageColumn: str = Form(...),
    nameColumn: str = Form(...),
    user_email: str = Form(...)
):
    """Process Excel files and extract images."""
    
    # Check user access
    access_info = check_user_access(user_email)
    if not access_info["access"]:
        if access_info["reason"] == "trial_expired":
            return JSONResponse(
                status_code=402,
                content={
                    "error": "trial_expired",
                    "message": access_info["message"],
                    "plans_available": True
                }
            )
        else:
            return JSONResponse(
                status_code=401,
                content={"error": access_info["reason"], "message": access_info["message"]}
            )
    
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
        
        # Process all files
        zip_buffer, total_images, saved_count, duplicate_count = process_excel_files(
            files_data, imageColumn, nameColumn
        )
        
        # Create response
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"bom2pic_images_{timestamp}.zip"
        
        headers = {
            "Content-Disposition": f"attachment; filename={filename}",
            "X-Content-Type-Options": "nosniff",
            "X-B2P-Processed": str(total_images),
            "X-B2P-Saved": str(saved_count),
            "X-B2P-Duplicate": str(duplicate_count),
            "X-B2P-Plan": access_info.get("plan", "unknown"),
            "X-B2P-Message": access_info.get("message", "")
        }
        
        return StreamingResponse(zip_buffer, media_type="application/zip", headers=headers)
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)

@app.get("/admin", include_in_schema=False)
def admin_dashboard():
    """Admin dashboard to view users."""
    from .auth import load_users
    from datetime import datetime
    
    users = load_users()
    
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>BOM2Pic Admin Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container py-5">
            <h1>🚀 BOM2Pic Admin Dashboard</h1>
            <div class="row mt-4">
                <div class="col-md-12">
                    <div class="card">
                        <div class="card-header">
                            <h5>📊 User Overview</h5>
                        </div>
                        <div class="card-body">
    """
    
    if not users:
        html_content += "<p>No users yet.</p>"
    else:
        html_content += f"<p><strong>Total Users:</strong> {len(users)}</p>"
        html_content += '<div class="table-responsive"><table class="table table-striped">'
        html_content += '<thead><tr><th>Email</th><th>Plan</th><th>Status</th><th>Trial Days Left</th><th>Created</th></tr></thead><tbody>'
        
        for email, user in users.items():
            trial_end = datetime.fromisoformat(user['trial_end']) if user.get('trial_end') else None
            days_left = (trial_end - datetime.now()).days if trial_end else 0
            
            status_badge = "success" if days_left > 0 else "danger"
            status_text = f"{days_left} days left" if days_left > 0 else f"Expired {abs(days_left)} days ago"
            
            html_content += f"""
            <tr>
                <td>{email}</td>
                <td><span class="badge bg-info">{user.get('plan', 'unknown')}</span></td>
                <td><span class="badge bg-{status_badge}">{user.get('subscription_status', 'unknown')}</span></td>
                <td>{status_text}</td>
                <td>{user.get('created_at', 'unknown')[:10]}</td>
            </tr>
            """
        
        html_content += '</tbody></table></div>'
    
    html_content += """
                        </div>
                    </div>
                </div>
            </div>
            <div class="mt-4">
                <a href="/" class="btn btn-primary">← Back to App</a>
                <button onclick="location.reload()" class="btn btn-secondary">🔄 Refresh</button>
            </div>
        </div>
    </body>
    </html>
    """
    
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content)
