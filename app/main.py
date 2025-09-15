"""
BOM2Pic - Clean Excel Image Extractor
FastAPI application with simple authentication and PayPal LTD integration
"""
# Load environment variables FIRST
from dotenv import load_dotenv
load_dotenv()

import io
import os
import uuid
from datetime import datetime, timedelta
from typing import List

from fastapi import FastAPI, File, UploadFile, Form, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse, RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles

from .auth import get_or_create_user, check_user_access, update_subscription_status
from .payment import get_plans, create_payment_session, verify_payment, PaymentError
from .excel_processor import process_excel_files

app = FastAPI(
    title="BOM2Pic",
    description="Extract images from Excel files with ease",
    version="2.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ============================================================================
# CORE ROUTES
# ============================================================================

@app.get("/")
def read_root():
    """Serve the main HTML page"""
    return FileResponse('app/static/index.html')

@app.get("/health")
def health_check():
    """Simple health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

# ============================================================================
# API ENDPOINTS  
# ============================================================================

@app.get("/api/plans")
def api_plans():
    """Get available pricing plans"""
    return get_plans()

@app.post("/api/auth/signup")
async def signup(email: str = Form(...)):
    try:
        user = get_or_create_user(email)
        return {"success": True, "message": "Account created successfully!", "user": user}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/api/process")
async def process_files(
    files: List[UploadFile] = File(...),
    email: str = Form(...),
    imageColumn: str = Form(...),
    nameColumn: str = Form(...)
):
    """Process uploaded Excel files and extract images"""
    try:
        # Check user access
        user = get_or_create_user(email)
        access_info = check_user_access(user)
        if not access_info["access"]:
            raise HTTPException(
                status_code=402, 
                detail="Payment required. Please subscribe to process files."
            )
        
        # Convert UploadFile objects to the format expected by processor
        files_data = []
        for file in files:
            content = await file.read()
            files_data.append((file.filename, content))
        
        # Process files with column selection
        zip_buffer, total_images, saved_count, duplicate_count = process_excel_files(files_data, imageColumn, nameColumn)
        
        # Return ZIP file as download
        return StreamingResponse(
            io.BytesIO(zip_buffer.getvalue()),
            media_type="application/zip",
            headers={"Content-Disposition": "attachment; filename=extracted_images.zip"}
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# PayPal LTD Integration
@app.post("/api/payment/create-session")
async def create_payment(
    plan: str = Form(...),
    email: str = Form(...)
):
    """Create PayPal payment session for LTD or other plans"""
    # SECURITY: Disable payment creation on production until PayPal is configured
    if os.getenv("RENDER"):
        raise HTTPException(
            status_code=503,
            detail="Payment system temporarily unavailable. Please try again later."
        )
        
    try:
        user = get_or_create_user(email)
        
        # LOCALHOST TEST MODE - Only allow bypass in development
        is_development = (
            "localhost" in os.getenv("BASE_URL", "") or 
            os.getenv("NODE_ENV") == "development" or
            not os.getenv("RENDER")  # Not on Render = development
        )
        
        if is_development:
            # TEST MODE: Simulating payment for development
            
            # Create fake session ID for testing
            test_session_id = str(uuid.uuid4())
            
            # Redirect to success page immediately (simulating PayPal success)
            base_url = "http://localhost:8000"
            success_url = f"{base_url}/payment/success?session_id={test_session_id}&plan={plan}&email={email}"
            
            return {
                "success": True,
                "checkout_url": success_url,
                "session_id": test_session_id
            }
        
        # PRODUCTION MODE - Real PayPal integration
        # Create success and cancel URLs
        base_url = os.getenv("BASE_URL", "http://localhost:8000")
        success_url = f"{base_url}/payment/success?session_id={{session_id}}&plan={plan}&email={email}"
        cancel_url = f"{base_url}/payment/cancel?plan={plan}"
        
        # Create PayPal session
        session = await create_payment_session(
            plan=plan,
            user_email=email,
            success_url=success_url,
            cancel_url=cancel_url
        )
        
        return {
            "success": True,
            "checkout_url": session["checkout_url"],
            "session_id": session["session_id"]
        }
        
    except PaymentError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment creation failed: {e}")

@app.get("/payment/success")
async def payment_success(
    session_id: str,
    plan: str,
    email: str,
    request: Request
):
    """Handle successful PayPal payment"""
    try:
        # LOCALHOST TEST MODE - Skip PayPal verification ONLY in development
        is_development = (
            "localhost" in str(request.base_url) or 
            not os.getenv("RENDER")  # Not on Render = development
        )
        
        if is_development:
            # TEST MODE: Simulating successful payment for development
            verification = {
                "verified": True,
                "order_id": session_id,
                "amount": "39" if plan == "lifetime" else ("10" if plan == "monthly" else "5")
            }
        else:
            # PRODUCTION MODE - Verify payment with PayPal
            verification = await verify_payment(session_id)
        
        if verification["verified"]:
            # Update user subscription based on plan
            user = get_or_create_user(email)
            
            if plan == "lifetime":
                # Grant lifetime access
                update_subscription_status(email, "lifetime", expires_at=None)
                message = "🎉 Lifetime Access Activated! You now have unlimited access to BOM2Pic forever!"
            elif plan == "monthly":
                # Grant monthly access (you might want to implement proper subscription logic)
                expires_at = (datetime.now() + timedelta(days=30)).isoformat()
                update_subscription_status(email, "monthly", expires_at=expires_at)
                message = "✅ Monthly Subscription Activated! You have unlimited access for 30 days."
            elif plan == "per_file":
                # Grant single file processing credit
                update_subscription_status(email, "per_file", expires_at=None)
                message = "✅ File Credit Added! You can now process one Excel file."
            
            # Return success page
            html_content = f"""
            <!DOCTYPE html>
            <html lang="en">
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <title>Payment Successful - BOM2Pic</title>
                <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
                <link href="/static/styles.css" rel="stylesheet">
            </head>
            <body>
                <div class="container py-5">
                    <div class="row justify-content-center">
                        <div class="col-md-8 text-center">
                            <div class="card border-success">
                                <div class="card-header bg-success text-white">
                                    <h2>🎉 Payment Successful!</h2>
                                </div>
                                <div class="card-body p-5">
                                    <h3 class="text-success mb-4">{message}</h3>
                                    <p class="lead">Your payment of ${verification['amount']} has been processed successfully.</p>
                                    <p><strong>Order ID:</strong> {verification['order_id']}</p>
                                    <p><strong>Email:</strong> {email}</p>
                                    
                                    <div class="mt-4">
                                        <a href="/tool?email={email}" class="btn btn-primary btn-lg me-3">Start Using BOM2Pic</a>
                                        <a href="/ltd-deal" class="btn btn-outline-secondary">Back to Pricing</a>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </body>
            </html>
            """
            return HTMLResponse(content=html_content)
        else:
            raise HTTPException(status_code=400, detail="Payment verification failed")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Payment processing failed: {e}")

@app.get("/payment/cancel")
async def payment_cancel(plan: str):
    """Handle cancelled PayPal payment"""
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Payment Cancelled - BOM2Pic</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="/static/styles.css" rel="stylesheet">
    </head>
    <body>
        <div class="container py-5">
            <div class="row justify-content-center">
                <div class="col-md-8 text-center">
                    <div class="card border-warning">
                        <div class="card-header bg-warning text-dark">
                            <h2>⚠️ Payment Cancelled</h2>
                        </div>
                        <div class="card-body p-5">
                            <h3 class="text-warning mb-4">No worries! Your payment was cancelled.</h3>
                            <p class="lead">You can try again anytime. The {plan} plan will be waiting for you!</p>
                            
                            <div class="mt-4">
                                <a href="/ltd-deal" class="btn btn-warning btn-lg me-3">Try Again</a>
                                <a href="/" class="btn btn-outline-secondary">Back to Home</a>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/admin", include_in_schema=False)
def admin_dashboard(admin_key: str = None):
    """Web-based admin dashboard for user management"""
    ADMIN_KEY = os.getenv("ADMIN_KEY", "bom2pic_admin_2024")
    
    if admin_key != ADMIN_KEY:
        raise HTTPException(
            status_code=401, 
            detail="Unauthorized: Admin access required. Use ?admin_key=YOUR_KEY"
        )
    
    from .auth import load_users
    users = load_users()
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>BOM2Pic Admin Dashboard</title>
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
    </head>
    <body>
        <div class="container py-4">
            <h1>BOM2Pic Admin Dashboard</h1>
            <p class="text-muted">Total Users: {len(users)}</p>
            
            <table class="table table-striped">
                <thead>
                    <tr>
                        <th>Email</th>
                        <th>Created</th>
                        <th>Subscription</th>
                        <th>Status</th>
                        <th>Expires</th>
                    </tr>
                </thead>
                <tbody>
                    {''.join([f'''
                    <tr>
                        <td>{user["email"]}</td>
                        <td>{user.get("created_at", "Unknown")}</td>
                        <td><span class="badge bg-primary">{user.get("subscription_type", "free")}</span></td>
                        <td><span class="badge bg-{"success" if user.get("is_active", True) else "danger"}">{"Active" if user.get("is_active", True) else "Inactive"}</span></td>
                        <td>{user.get("expires_at", "Never")}</td>
                    </tr>
                    ''' for user in users])}
                </tbody>
            </table>
        </div>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/ltd-deal", include_in_schema=False)
def ltd_deal_page():
    """$39 Lifetime Deal Landing Page - TEMPORARILY DISABLED"""
    # SECURITY: Completely disabled until PayPal is properly configured
    if os.getenv("RENDER"):  # On production
        return HTMLResponse(
            content="""
            <!DOCTYPE html>
            <html><head><title>Coming Soon - BOM2Pic</title>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
            </head><body>
            <div class="container mt-5 text-center">
                <h1 class="text-primary">🚀 Lifetime Deal Coming Soon!</h1>
                <p class="lead">We're preparing an amazing $39 Lifetime Deal for you.</p>
                <p>Please check back in a few days for the launch!</p>
                <a href="/" class="btn btn-primary">Back to Homepage</a>
            </div></body></html>
            """,
            status_code=503
        )
    # Local development only
    return FileResponse('app/static/ltd-deal.html')

@app.get("/tool", include_in_schema=False)
def tool_page(email: str = None):
    """Clean tool page for paid users - just upload interface"""
    if not email:
        return RedirectResponse(url="/")

    # Check user access
    try:
        user = get_or_create_user(email)
        access_info = check_user_access(user)

        if not access_info["access"]:
            return RedirectResponse(url="/ltd-deal")
    except Exception as e:
        return RedirectResponse(url="/")

    # Show clean tool with user status
    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>BOM2Pic Tool - Extract Images from Excel</title>
        
        <!-- Fonts -->
        <link rel="preconnect" href="https://fonts.googleapis.com">
        <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
        
        <!-- Bootstrap CSS -->
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <!-- Custom CSS -->
        <link href="/static/styles.css" rel="stylesheet">
    </head>
    <body>
        <!-- Navigation -->
        <nav class="navbar navbar-light bg-white shadow-sm">
            <div class="container">
                <a class="navbar-brand fw-bold" href="/">🚀 BOM2Pic</a>
                <div>
                    <span class="badge bg-success me-2">✅ {(access_info.get('plan') or 'ACTIVE').upper()} ACCESS</span>
                    <span class="text-muted">{email}</span>
                </div>
            </div>
        </nav>

        <!-- Welcome Section -->
        <section class="py-4 bg-light">
            <div class="container">
                <div class="text-center">
                    <h1 class="h3 fw-bold text-primary">Welcome to BOM2Pic!</h1>
                    <p class="text-success mb-0">{access_info['message']}</p>
                </div>
            </div>
        </section>

        <!-- Upload Interface Section -->
        <section id="upload-interface" class="py-5">
            <div class="container">
                <div class="row justify-content-center">
                    <div class="col-lg-8">
                        <div class="upload-container bg-white p-5 rounded-3 shadow-sm border">
                            <div class="text-center mb-4">
                                <h3>Upload Your Excel File</h3>
                                <p class="text-muted">Drag and drop your Excel file or click to browse. We support .xlsx and .xls formats.</p>
                            </div>

                            <form id="uploadForm" class="text-center">
                                <input type="hidden" name="email" value="{email}">

                                <div class="upload-area border border-dashed border-primary rounded-3 p-5 mb-4"
                                     ondrop="dropHandler(event);" ondragover="dragOverHandler(event);" ondragenter="dragEnterHandler(event);" ondragleave="dragLeaveHandler(event);">
                                    <div class="upload-icon mb-3">
                                        <svg width="64" height="64" fill="currentColor" class="text-primary" viewBox="0 0 16 16">
                                            <path d="M.5 9.9a.5.5 0 0 1 .5.5v2.5a1 1 0 0 0 1 1h12a1 1 0 0 0 1-1v-2.5a.5.5 0 0 1 1 0v2.5a2 2 0 0 1-2 2H2a2 2 0 0 1-2-2v-2.5a.5.5 0 0 1 .5-.5z"/>
                                            <path d="M7.646 1.146a.5.5 0 0 1 .708 0l3 3a.5.5 0 0 1-.708.708L8.5 2.707V11.5a.5.5 0 0 1-1 0V2.707L5.354 4.854a.5.5 0 1 1-.708-.708l3-3z"/>
                                        </svg>
                                    </div>
                                    <h5>Drop your Excel file here</h5>
                                    <p class="text-muted mb-3">or</p>
                                    <input type="file" id="fileInput" name="files" multiple accept=".xlsx,.xls" style="display: none;" onchange="handleFileSelect(event)">
                                    <button type="button" class="btn btn-primary" onclick="document.getElementById('fileInput').click()">
                                        Choose Files
                                    </button>
                                    <p class="small text-muted mt-3">Supported formats: .xlsx, .xls (up to 50MB)</p>
                                </div>

                                <!-- Column Selection (hidden initially) -->
                                <div id="columnSelection" class="mt-4" style="display: none;">
                                    <h4 class="mb-3">Select Columns</h4>
                                    <div class="row">
                                        <div class="col-md-6">
                                            <label for="imageColumn" class="form-label">Image Column:</label>
                                            <select id="imageColumn" name="imageColumn" class="form-select" required>
                                                <option value="">Choose image column...</option>
                                            </select>
                                        </div>
                                        <div class="col-md-6">
                                            <label for="nameColumn" class="form-label">Part Number Column:</label>
                                            <select id="nameColumn" name="nameColumn" class="form-select" required>
                                                <option value="">Choose P/N column...</option>
                                            </select>
                                        </div>
                                    </div>
                                    
                                    <div class="text-center mt-4">
                                        <button type="submit" id="processBtn" class="btn btn-success btn-lg">
                                            🚀 Extract Images
                                        </button>
                                    </div>
                                </div>
                            </form>

                            <div id="results" class="mt-4"></div>
                        </div>
                    </div>
                </div>
            </div>
        </section>

        <style>
        .upload-area.drag-over {{
            border-color: #0d6efd !important;
            background-color: rgba(13, 110, 253, 0.1) !important;
        }}
        </style>
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
        <script>
        // Drag and drop functionality for the tool page
        function dropHandler(ev) {{
            ev.preventDefault();
            const files = ev.dataTransfer.files;
            handleFileSelect({{ target: {{ files: files }} }});
            ev.target.classList.remove('drag-over');
        }}

        function dragOverHandler(ev) {{
            ev.preventDefault();
        }}

        function dragEnterHandler(ev) {{
            ev.preventDefault();
            ev.target.classList.add('drag-over');
        }}

        function dragLeaveHandler(ev) {{
            ev.preventDefault();
            ev.target.classList.remove('drag-over');
        }}

        function handleFileSelect(event) {{
            const files = event.target.files;
            const columnSelection = document.getElementById('columnSelection');
            
            if (files.length > 0) {{
                // Store files globally for later processing
                window.selectedFiles = files;
                
                // Show success message
                const uploadArea = document.querySelector('.upload-area');
                uploadArea.innerHTML = `
                    <div class="text-success mb-3">
                        <svg width="48" height="48" fill="currentColor" viewBox="0 0 16 16">
                            <path d="M16 8A8 8 0 1 1 0 8a8 8 0 0 1 16 0zm-3.97-3.03a.75.75 0 0 0-1.08.022L7.477 9.417 5.384 7.323a.75.75 0 0 0-1.06 1.061L6.97 11.03a.75.75 0 0 0 1.079-.02l3.992-4.99a.75.75 0 0 0-.01-1.05z"/>
                        </svg>
                    </div>
                    <h5 class="text-success">Files Uploaded Successfully!</h5>
                    <p class="text-muted mb-0">${{files.length}} file(s) ready for processing</p>
                `;
                
                // Load column headers from the first file
                loadColumnHeaders(files[0]);
                
                // Show column selection
                columnSelection.style.display = 'block';
            }}
        }}
        
        function loadColumnHeaders(file) {{
            // This would typically read the Excel file to get column headers
            // For now, we'll populate with common column letters/names
            const imageSelect = document.getElementById('imageColumn');
            const nameSelect = document.getElementById('nameColumn');
            
            // Clear existing options
            imageSelect.innerHTML = '<option value="">Choose image column...</option>';
            nameSelect.innerHTML = '<option value="">Choose P/N column...</option>';
            
            // Add column options (A-Z)
            const columns = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H', 'I', 'J', 'K', 'L', 'M', 'N', 'O', 'P', 'Q', 'R', 'S', 'T', 'U', 'V', 'W', 'X', 'Y', 'Z'];
            columns.forEach(col => {{
                imageSelect.innerHTML += `<option value="${{col}}">Column ${{col}}</option>`;
                nameSelect.innerHTML += `<option value="${{col}}">Column ${{col}}</option>`;
            }});
        }}
        
        // Handle form submission
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {{
            e.preventDefault();
            
            const imageColumn = document.getElementById('imageColumn').value;
            const nameColumn = document.getElementById('nameColumn').value;
            const email = document.querySelector('input[name="email"]').value;
            
            if (!imageColumn || !nameColumn) {{
                alert('Please select both image and part number columns.');
                return;
            }}
            
            if (imageColumn === nameColumn) {{
                alert('Image and part number columns must be different.');
                return;
            }}
            
            if (!window.selectedFiles || window.selectedFiles.length === 0) {{
                alert('Please select files first.');
                return;
            }}
            
            // Show processing state
            const processBtn = document.getElementById('processBtn');
            const originalText = processBtn.innerHTML;
            processBtn.disabled = true;
            processBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
            
            try {{
                // Create FormData with files and column selections
                const formData = new FormData();
                formData.append('email', email);
                formData.append('imageColumn', imageColumn);
                formData.append('nameColumn', nameColumn);
                
                for (let i = 0; i < window.selectedFiles.length; i++) {{
                    formData.append('files', window.selectedFiles[i]);
                }}
                
                // Submit to processing endpoint
                const response = await fetch('/api/process', {{
                    method: 'POST',
                    body: formData
                }});
                
                if (response.ok) {{
                    // Handle successful processing (download file)
                    const blob = await response.blob();
                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = 'extracted_images.zip';
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);
                    
                    // Show success message
                    document.getElementById('results').innerHTML = `
                        <div class="alert alert-success">
                            <h4>✅ Processing Complete!</h4>
                            <p>Your images have been extracted and downloaded as a ZIP file.</p>
                        </div>
                    `;
                }} else {{
                    throw new Error('Processing failed');
                }}
            }} catch (error) {{
                // Show error message
                document.getElementById('results').innerHTML = `
                    <div class="alert alert-danger">
                        <h4>❌ Processing Error</h4>
                        <p>There was an error processing your files. Please try again.</p>
                    </div>
                `;
            }} finally {{
                // Reset button
                processBtn.disabled = false;
                processBtn.innerHTML = originalText;
            }}
        }});
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)


@app.get("/how-to-export-images-from-excel", include_in_schema=False)
def blog_post_export_images():
    """SEO-optimized blog post about exporting images from Excel"""
    html_content = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        
        <!-- SEO Meta Tags -->
        <title>How to Export Images from Excel Files: Complete Guide 2024 | BOM2Pic</title>
        <meta name="description" content="Learn how to export and extract images from Excel files easily. Step-by-step guide with manual methods and automated tools like BOM2Pic for bulk image extraction.">
        <meta name="keywords" content="export images from excel, extract images excel, excel to image, save images from spreadsheet, bulk image extraction">
        
        <!-- Open Graph -->
        <meta property="og:title" content="How to Export Images from Excel Files: Complete Guide 2024">
        <meta property="og:description" content="Learn how to export and extract images from Excel files easily. Step-by-step guide with manual methods and automated tools.">
        <meta property="og:type" content="article">
        <meta property="og:url" content="https://bom2pic.com/how-to-export-images-from-excel">
        
        <!-- Structured Data -->
        <script type="application/ld+json">
        {
            "@context": "https://schema.org",
            "@type": "Article",
            "headline": "How to Export Images from Excel Files: Complete Guide 2024",
            "description": "Learn how to export and extract images from Excel files easily. Step-by-step guide with manual methods and automated tools like BOM2Pic for bulk image extraction.",
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
        
        <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/css/bootstrap.min.css" rel="stylesheet">
        <link href="/static/styles.css" rel="stylesheet">
    </head>
    <body>
        <nav class="navbar navbar-light bg-white shadow-sm">
            <div class="container">
                <a class="navbar-brand fw-bold" href="/">🚀 BOM2Pic</a>
            </div>
        </nav>
        
        <div class="container py-5">
            <div class="row justify-content-center">
                <div class="col-lg-8">
                    <article>
                        <header class="mb-5">
                            <h1 class="display-4 fw-bold mb-3">How to Export Images from Excel Files: Complete Guide 2024</h1>
                            <p class="lead text-muted">Learn multiple methods to extract and save images from Excel spreadsheets, from manual techniques to automated bulk processing.</p>
                            <small class="text-muted">Published on January 15, 2024 • 8 min read</small>
                        </header>
                        
                        <div class="mb-5">
                            <h2>Why Export Images from Excel?</h2>
                            <p>Excel files often contain valuable images - product photos, charts, diagrams, or embedded pictures. Whether you're managing a product catalog, creating presentations, or organizing visual content, extracting these images efficiently is crucial.</p>
                        </div>
                        
                        <div class="mb-5">
                            <h2>Method 1: Manual Copy-Paste (Small Scale)</h2>
                            <ol>
                                <li><strong>Right-click the image</strong> in Excel</li>
                                <li><strong>Select "Copy"</strong> from the context menu</li>
                                <li><strong>Open image editor</strong> (Paint, Photoshop, etc.)</li>
                                <li><strong>Paste and save</strong> as desired format</li>
                            </ol>
                            <div class="alert alert-warning">
                                <strong>Limitation:</strong> Time-consuming for multiple images. Not practical for bulk extraction.
                            </div>
                        </div>
                        
                        <div class="mb-5">
                            <h2>Method 2: Save As Web Page</h2>
                            <ol>
                                <li><strong>File → Save As</strong></li>
                                <li><strong>Choose "Web Page, Complete"</strong></li>
                                <li><strong>Save to folder</strong></li>
                                <li><strong>Check the "_files" folder</strong> created alongside</li>
                            </ol>
                            <div class="alert alert-info">
                                <strong>Pro:</strong> Extracts all images at once<br>
                                <strong>Con:</strong> Creates additional HTML files and folders
                            </div>
                        </div>
                        
                        <div class="mb-5">
                            <h2>Method 3: Automated Extraction with BOM2Pic</h2>
                            <p>For bulk image extraction, especially from product catalogs or large spreadsheets, automated tools save significant time:</p>
                            
                            <div class="card bg-light p-4 mb-4">
                                <h4>🚀 BOM2Pic Features:</h4>
                                <ul class="mb-3">
                                    <li>Extract hundreds of images in seconds</li>
                                    <li>Organized output with proper naming</li>
                                    <li>Support for .xlsx and .xls files</li>
                                    <li>Batch processing multiple files</li>
                                    <li>No software installation required</li>
                                </ul>
                                <a href="/" class="btn btn-primary">Try BOM2Pic Free →</a>
                            </div>
                        </div>
                        
                        <div class="mb-5">
                            <h2>Comparison Table</h2>
                            <div class="table-responsive">
                                <table class="table table-bordered">
                                    <thead class="table-dark">
                                        <tr>
                                            <th>Method</th>
                                            <th>Speed</th>
                                            <th>Bulk Processing</th>
                                            <th>Organization</th>
                                            <th>Best For</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr>
                                            <td>Manual Copy-Paste</td>
                                            <td>Slow</td>
                                            <td>❌</td>
                                            <td>Manual</td>
                                            <td>1-2 images</td>
                                        </tr>
                                        <tr>
                                            <td>Save as Web Page</td>
                                            <td>Medium</td>
                                            <td>✅</td>
                                            <td>Basic</td>
                                            <td>Single file</td>
                                        </tr>
                                        <tr class="table-success">
                                            <td>BOM2Pic</td>
                                            <td>Fast</td>
                                            <td>✅</td>
                                            <td>Excellent</td>
                                            <td>Multiple files, catalogs</td>
                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        
                        <div class="mb-5">
                            <h2>Frequently Asked Questions</h2>
                            
                            <div class="accordion" id="faqAccordion">
                                <div class="accordion-item">
                                    <h3 class="accordion-header">
                                        <button class="accordion-button" type="button" data-bs-toggle="collapse" data-bs-target="#faq1">
                                            Can I extract images from password-protected Excel files?
                                        </button>
                                    </h3>
                                    <div id="faq1" class="accordion-collapse collapse show" data-bs-parent="#faqAccordion">
                                        <div class="accordion-body">
                                            You'll need to unlock the file first. Most extraction methods, including BOM2Pic, require access to the unprotected file content.
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="accordion-item">
                                    <h3 class="accordion-header">
                                        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq2">
                                            What image formats are supported?
                                        </button>
                                    </h3>
                                    <div id="faq2" class="accordion-collapse collapse" data-bs-parent="#faqAccordion">
                                        <div class="accordion-body">
                                            Excel typically stores images as PNG, JPEG, or GIF. BOM2Pic extracts them in their original format and can convert to PNG for consistency.
                                        </div>
                                    </div>
                                </div>
                                
                                <div class="accordion-item">
                                    <h3 class="accordion-header">
                                        <button class="accordion-button collapsed" type="button" data-bs-toggle="collapse" data-bs-target="#faq3">
                                            How do I maintain image quality during extraction?
                                        </button>
                                    </h3>
                                    <div id="faq3" class="accordion-collapse collapse" data-bs-parent="#faqAccordion">
                                        <div class="accordion-body">
                                            Automated tools like BOM2Pic preserve original image quality. Manual methods may compress images depending on your paste destination.
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        
                        <div class="mb-5">
                            <h2>Conclusion</h2>
                            <p>Extracting images from Excel files doesn't have to be tedious. While manual methods work for occasional use, automated tools like BOM2Pic dramatically improve efficiency for regular or bulk extraction needs.</p>
                            
                            <div class="card border-primary">
                                <div class="card-body text-center">
                                    <h4>Ready to Extract Images Efficiently?</h4>
                                    <p>Try BOM2Pic's automated image extraction - free for your first files!</p>
                                    <a href="/" class="btn btn-primary btn-lg">Start Free Trial</a>
                                </div>
                            </div>
                        </div>
                    </article>
                </div>
            </div>
        </div>
        
        <footer class="bg-light py-4 mt-5">
            <div class="container text-center">
                <p class="mb-0">&copy; 2024 BOM2Pic. All rights reserved. | <a href="/">Home</a> | <a href="/ltd-deal">Pricing</a></p>
            </div>
        </footer>
        
        <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.2/dist/js/bootstrap.bundle.min.js"></script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)