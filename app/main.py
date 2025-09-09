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
def admin_dashboard(admin_key: str = None):
    """Admin dashboard to view users - PROTECTED."""
    # Simple admin key protection
    ADMIN_KEY = os.getenv("ADMIN_KEY", "bom2pic_admin_2024")
    
    if admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=401, 
            detail="Unauthorized: Admin access required. Use ?admin_key=YOUR_KEY"
        )
    
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

@app.get("/how-to-export-images-from-excel", include_in_schema=False)
def how_to_export_guide():
    """SEO blog post: How to Export Images from Excel Automatically"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>How to Export Images from Excel Automatically - Complete Guide 2024</title>
        <meta name="description" content="Learn 3 proven methods to automatically export images from Excel files. Step-by-step guide with BOM2Pic, VBA macros, and manual methods. Save hours of work!">
        <meta name="keywords" content="export images from Excel, Excel image extraction, BOM2Pic tutorial, Excel automation, extract pictures from spreadsheet">
        
        <!-- Open Graph -->
        <meta property="og:title" content="How to Export Images from Excel Automatically - Complete Guide">
        <meta property="og:description" content="Learn the fastest way to extract hundreds of images from Excel files without manual work.">
        <meta property="og:type" content="article">
        
        <!-- Fonts -->
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="/static/styles.css" rel="stylesheet">
        
        <!-- Structured Data -->
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "How to Export Images from Excel Automatically",
            "description": "Complete guide to automatically extracting images from Excel files",
            "author": {
                "@type": "Organization",
                "name": "BOM2Pic"
            },
            "publisher": {
                "@type": "Organization",
                "name": "BOM2Pic"
            },
            "datePublished": "2024-01-15",
            "dateModified": "2024-01-15"
        }
        </script>
    </head>
    <body>
        <!-- Navigation -->
        <nav class="navbar navbar-light bg-white shadow-sm">
            <div class="container">
                <a class="navbar-brand fw-bold" href="/">🚀 BOM2Pic</a>
                <a href="/" class="btn btn-primary">Try Free</a>
            </div>
        </nav>
        
        <div class="container py-5">
            <div class="row justify-content-center">
                <div class="col-lg-8">
                    <article>
                        <header class="mb-5">
                            <h1 class="display-5 fw-bold mb-4">How to Export Images from Excel Automatically</h1>
                            <p class="lead">Learn the fastest way to extract hundreds of images from Excel files without manual work or complex VBA programming. Complete guide with 3 proven methods.</p>
                            <div class="d-flex align-items-center text-muted mb-4">
                                <small>📅 Updated January 2024 • ⏱️ 5 min read • 💼 For Excel professionals</small>
                            </div>
                        </header>
                        
                        <div class="alert alert-info">
                            <h4>💡 Quick Answer</h4>
                            <p class="mb-0">The fastest way to export images from Excel is using <strong>BOM2Pic</strong> - upload your file, select columns, download organized images in seconds. No coding required.</p>
                        </div>
                        
                        <h2>The Problem: Manual Image Extraction is Painful</h2>
                        <p>If you work with parts catalogs, product listings, or BOMs in Excel, you know the frustration:</p>
                        <ul class="mb-4">
                            <li>📸 <strong>Hundreds of images</strong> embedded in spreadsheets</li>
                            <li>⏰ <strong>Hours of manual work</strong> - right-click, save, rename, organize</li>
                            <li>❌ <strong>Error-prone process</strong> - missing images, wrong names, poor organization</li>
                            <li>🔧 <strong>Technical barriers</strong> - VBA programming knowledge required</li>
                        </ul>
                        
                        <div class="bg-light p-4 rounded-3 mb-4">
                            <h3>💸 The Real Cost</h3>
                            <p class="mb-2"><strong>Manual extraction:</strong> 500 images = 4-6 hours of work</p>
                            <p class="mb-0"><strong>Automated extraction:</strong> 500 images = 2 minutes</p>
                        </div>
                        
                        <h2>Method 1: BOM2Pic (Recommended) ⭐</h2>
                        <p>BOM2Pic is a web-based tool designed specifically for extracting images from Excel files. Here's how it works:</p>
                        
                        <div class="row g-4 my-4">
                            <div class="col-md-4 text-center">
                                <div class="bg-primary text-white rounded-circle d-inline-flex align-items-center justify-content-center mb-3" style="width: 60px; height: 60px; font-size: 1.5rem;">1</div>
                                <h4 class="h5">Upload Excel File</h4>
                                <p class="small">Upload your .xlsx file containing images and product data</p>
                            </div>
                            <div class="col-md-4 text-center">
                                <div class="bg-success text-white rounded-circle d-inline-flex align-items-center justify-content-center mb-3" style="width: 60px; height: 60px; font-size: 1.5rem;">2</div>
                                <h4 class="h5">Select Columns</h4>
                                <p class="small">Choose which columns contain images and product IDs</p>
                            </div>
                            <div class="col-md-4 text-center">
                                <div class="bg-warning text-white rounded-circle d-inline-flex align-items-center justify-content-center mb-3" style="width: 60px; height: 60px; font-size: 1.5rem;">3</div>
                                <h4 class="h5">Download ZIP</h4>
                                <p class="small">Get organized PNG files with proper naming</p>
                            </div>
                        </div>
                        
                        <div class="alert alert-success">
                            <h4>✅ BOM2Pic Advantages</h4>
                            <ul class="mb-0">
                                <li><strong>No technical knowledge</strong> - Works in any web browser</li>
                                <li><strong>Batch processing</strong> - Handle multiple files at once</li>
                                <li><strong>Smart organization</strong> - Automatic file naming and folder structure</li>
                                <li><strong>30-day free trial</strong> - Test with your files risk-free</li>
                                <li><strong>Enterprise security</strong> - Files processed securely, nothing stored</li>
                            </ul>
                        </div>
                        
                        <h2>Method 2: VBA Macro Programming</h2>
                        <p>For Excel power users, VBA macros can automate image extraction. However, this method requires:</p>
                        <ul>
                            <li>🔧 <strong>VBA programming knowledge</strong></li>
                            <li>⏱️ <strong>Hours of setup and debugging</strong></li>
                            <li>🐛 <strong>Error handling and maintenance</strong></li>
                            <li>📁 <strong>Manual file organization</strong></li>
                        </ul>
                        
                        <h2>Method 3: Manual Extraction</h2>
                        <p>The traditional right-click and save method:</p>
                        <ol>
                            <li>Right-click on each image in Excel</li>
                            <li>Select "Save as Picture"</li>
                            <li>Choose location and rename file</li>
                            <li>Repeat for every image</li>
                        </ol>
                        <p><strong>Time required:</strong> 30-60 seconds per image</p>
                        
                        <h2>Comparison: Which Method Should You Choose?</h2>
                        <div class="table-responsive mb-4">
                            <table class="table table-striped">
                                <thead class="table-dark">
                                    <tr>
                                        <th>Method</th>
                                        <th>Setup Time</th>
                                        <th>Technical Skills</th>
                                        <th>Speed (500 images)</th>
                                        <th>Organization</th>
                                        <th>Best For</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr class="table-success">
                                        <td><strong>BOM2Pic</strong></td>
                                        <td>✅ Instant</td>
                                        <td>✅ None required</td>
                                        <td>✅ 2 minutes</td>
                                        <td>✅ Automatic</td>
                                        <td>Everyone</td>
                                    </tr>
                                    <tr>
                                        <td>VBA Macros</td>
                                        <td>❌ 2-4 hours</td>
                                        <td>❌ Advanced</td>
                                        <td>⚠️ 10-15 minutes</td>
                                        <td>❌ Manual setup</td>
                                        <td>Developers</td>
                                    </tr>
                                    <tr>
                                        <td>Manual</td>
                                        <td>✅ None</td>
                                        <td>✅ Basic</td>
                                        <td>❌ 4-6 hours</td>
                                        <td>❌ Manual</td>
                                        <td>Small datasets</td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                        
                        <h2>Step-by-Step: Using BOM2Pic</h2>
                        <div class="alert alert-primary">
                            <h4>📋 What You'll Need</h4>
                            <ul class="mb-0">
                                <li>Excel file (.xlsx) with embedded images</li>
                                <li>Column with images</li>
                                <li>Column with product names/IDs (for file naming)</li>
                                <li>Web browser (Chrome, Firefox, Safari, Edge)</li>
                            </ul>
                        </div>
                        
                        <ol class="mb-4">
                            <li class="mb-3">
                                <strong>Visit BOM2Pic:</strong> Go to the homepage and start your free trial
                            </li>
                            <li class="mb-3">
                                <strong>Upload your Excel file:</strong> Drag and drop or browse to select your .xlsx file
                            </li>
                            <li class="mb-3">
                                <strong>Select columns:</strong> Choose which column contains images and which contains product names
                            </li>
                            <li class="mb-3">
                                <strong>Process files:</strong> Click "Process Files" and wait for extraction
                            </li>
                            <li class="mb-3">
                                <strong>Download results:</strong> Get a ZIP file with organized images, ready to use
                            </li>
                        </ol>
                        
                        <h2>Pro Tips for Better Results</h2>
                        <div class="row g-4 mb-4">
                            <div class="col-md-6">
                                <div class="card border-success">
                                    <div class="card-header bg-success text-white">
                                        <h5 class="mb-0">✅ Do This</h5>
                                    </div>
                                    <div class="card-body">
                                        <ul class="mb-0">
                                            <li>Use clear, unique product names</li>
                                            <li>Keep images in consistent columns</li>
                                            <li>Test with small files first</li>
                                            <li>Use descriptive file names</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                            <div class="col-md-6">
                                <div class="card border-danger">
                                    <div class="card-header bg-danger text-white">
                                        <h5 class="mb-0">❌ Avoid This</h5>
                                    </div>
                                    <div class="card-body">
                                        <ul class="mb-0">
                                            <li>Duplicate product names</li>
                                            <li>Special characters in names</li>
                                            <li>Very large files (>50MB)</li>
                                            <li>Password-protected files</li>
                                        </ul>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <h2>Frequently Asked Questions</h2>
                        <div class="accordion mb-4" id="faqAccordion">
                            <div class="accordion-item">
                                <h3 class="accordion-header">
                                    <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#faq1">
                                        What file formats are supported?
                                    </button>
                                </h3>
                                <div id="faq1" class="accordion-collapse collapse show">
                                    <div class="accordion-body">
                                        BOM2Pic supports .xlsx Excel files and exports images as PNG files for maximum compatibility.
                                    </div>
                                </div>
                            </div>
                            <div class="accordion-item">
                                <h3 class="accordion-header">
                                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq2">
                                        How many images can I extract at once?
                                    </button>
                                </h3>
                                <div id="faq2" class="accordion-collapse collapse">
                                    <div class="accordion-body">
                                        BOM2Pic can handle hundreds of images in a single file. The free trial allows up to 20 images, while paid plans support unlimited extraction.
                                    </div>
                                </div>
                            </div>
                            <div class="accordion-item">
                                <h3 class="accordion-header">
                                    <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq3">
                                        Is my data secure?
                                    </button>
                                </h3>
                                <div id="faq3" class="accordion-collapse collapse">
                                    <div class="accordion-body">
                                        Yes! Files are processed securely with end-to-end encryption and are never stored on our servers after processing.
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="bg-primary text-white p-4 rounded-3 text-center">
                            <h2 class="h3 mb-3">Ready to Save Hours of Work?</h2>
                            <p class="mb-3">Join hundreds of professionals who've automated their image extraction process with BOM2Pic.</p>
                            <a href="/" class="btn btn-light btn-lg">Start Free Trial - No Credit Card Required</a>
                        </div>
                    </article>
                </div>
            </div>
        </div>
        
        <footer class="bg-light py-4 mt-5">
            <div class="container text-center">
                <p class="mb-0"><a href="/" class="text-decoration-none">← Back to BOM2Pic</a></p>
            </div>
        </footer>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    from fastapi.responses import HTMLResponse
    return HTMLResponse(content=html_content)
