"""
Security utilities and validation models for BOM2Pic
"""
import re
from typing import Optional
from pydantic import BaseModel, EmailStr, validator
from fastapi import HTTPException

# Valid payment plans
VALID_PLANS = {"monthly", "per_file", "lifetime"}

class PaymentRequest(BaseModel):
    """Validated payment request model"""
    plan: str
    email: EmailStr
    
    @validator('plan')
    def validate_plan(cls, v):
        if v not in VALID_PLANS:
            raise ValueError(f'Invalid plan. Must be one of: {", ".join(VALID_PLANS)}')
        return v
    
    @validator('email')
    def validate_email_format(cls, v):
        # Additional email validation beyond EmailStr
        if len(v) > 254:  # RFC 5321 limit
            raise ValueError('Email address too long')
        return v.lower()

class SignupRequest(BaseModel):
    """Validated signup request model"""
    email: EmailStr
    
    @validator('email')
    def validate_email_format(cls, v):
        if len(v) > 254:
            raise ValueError('Email address too long')
        return v.lower()

class ProcessingRequest(BaseModel):
    """Validated file processing request"""
    email: EmailStr
    imageColumn: str
    nameColumn: str
    
    @validator('imageColumn', 'nameColumn')
    def validate_column(cls, v):
        # Excel columns should be A-Z or AA-ZZ format
        if not re.match(r'^[A-Z]{1,2}$', v.upper()):
            raise ValueError('Column must be in Excel format (A, B, C, ..., AA, AB, etc.)')
        return v.upper()
    
    @validator('email')
    def validate_email_format(cls, v):
        if len(v) > 254:
            raise ValueError('Email address too long')
        return v.lower()

def validate_file_upload(files) -> None:
    """Validate uploaded files"""
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'.xlsx', '.xls'}
    
    for file in files:
        # Check file size
        if hasattr(file, 'size') and file.size > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=400, 
                detail=f"File {file.filename} is too large. Maximum size is 50MB"
            )
        
        # Check file extension
        if file.filename:
            file_ext = file.filename.lower().split('.')[-1]
            if f'.{file_ext}' not in ALLOWED_EXTENSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"File {file.filename} has invalid extension. Only .xlsx and .xls files are allowed"
                )

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to prevent path traversal"""
    if not filename:
        return "unknown_file"
    
    # Remove path components
    filename = filename.split('/')[-1].split('\\')[-1]
    
    # Remove dangerous characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    
    # Limit length
    if len(filename) > 255:
        filename = filename[:255]
    
    return filename
