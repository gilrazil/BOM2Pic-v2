"""
Secure admin authentication for BOM2Pic
"""
import os
import secrets
import hashlib
import time
from typing import Optional, Dict

try:
    from fastapi import HTTPException, Request, Response
    from fastapi.responses import RedirectResponse
except ImportError as e:
    print(f"Warning: FastAPI import failed: {e}")
    # Fallback for development
    pass

class AdminAuth:
    def __init__(self):
        # Store active admin sessions
        self.active_sessions: Dict[str, float] = {}
        self.session_timeout = 3600  # 1 hour
        
        # Get secure admin key from environment
        self.admin_key_hash = self._get_admin_key_hash()
    
    def _get_admin_key_hash(self) -> str:
        """Get hashed admin key from environment"""
        admin_key = os.getenv("ADMIN_KEY")
        
        if not admin_key:
            print("Warning: ADMIN_KEY not set, using default for now")
            admin_key = "bom2pic_admin_2024"
        
        # Warn about weak default in production but don't block
        if admin_key == "bom2pic_admin_2024" and os.getenv("RENDER"):
            print("WARNING: Using default admin key in production. Please set secure ADMIN_KEY environment variable.")
        
        # Hash the admin key for comparison
        return hashlib.sha256(admin_key.encode()).hexdigest()
    
    def verify_admin_key(self, provided_key: str) -> bool:
        """Verify admin key against hashed version"""
        if not provided_key:
            return False
        
        provided_hash = hashlib.sha256(provided_key.encode()).hexdigest()
        return secrets.compare_digest(provided_hash, self.admin_key_hash)
    
    def create_admin_session(self) -> str:
        """Create secure admin session token"""
        session_token = secrets.token_urlsafe(32)
        self.active_sessions[session_token] = time.time()
        return session_token
    
    def verify_admin_session(self, session_token: str) -> bool:
        """Verify admin session token and check expiry"""
        if not session_token or session_token not in self.active_sessions:
            return False
        
        # Check if session expired
        session_time = self.active_sessions[session_token]
        if time.time() - session_time > self.session_timeout:
            # Remove expired session
            del self.active_sessions[session_token]
            return False
        
        # Refresh session time
        self.active_sessions[session_token] = time.time()
        return True
    
    def invalidate_session(self, session_token: str):
        """Invalidate admin session"""
        if session_token in self.active_sessions:
            del self.active_sessions[session_token]
    
    def cleanup_expired_sessions(self):
        """Clean up expired sessions"""
        current_time = time.time()
        expired_sessions = [
            token for token, session_time in self.active_sessions.items()
            if current_time - session_time > self.session_timeout
        ]
        
        for token in expired_sessions:
            del self.active_sessions[token]

# Global admin auth instance
admin_auth = AdminAuth()

def require_admin_session(request: Request) -> bool:
    """
    Check if user has valid admin session
    
    Args:
        request: FastAPI request object
        
    Returns:
        True if valid admin session
        
    Raises:
        HTTPException: If not authorized
    """
    # Check for session cookie
    session_token = request.cookies.get("admin_session")
    
    if not session_token or not admin_auth.verify_admin_session(session_token):
        raise HTTPException(
            status_code=401,
            detail="Admin session required. Please log in."
        )
    
    return True

def admin_login_required(request: Request) -> Optional[RedirectResponse]:
    """
    Check admin authentication, redirect to login if needed
    
    Returns:
        RedirectResponse to login page if not authenticated, None if authenticated
    """
    try:
        require_admin_session(request)
        return None  # Authenticated
    except HTTPException:
        # Not authenticated, redirect to login
        return RedirectResponse(url="/admin/login", status_code=302)
