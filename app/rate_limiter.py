"""
Rate limiting middleware for BOM2Pic
"""
import time
from typing import Dict, Tuple
from fastapi import HTTPException, Request
from collections import defaultdict, deque

class SimpleRateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        # Store request timestamps per IP
        self.requests: Dict[str, deque] = defaultdict(deque)
    
    def is_allowed(self, client_ip: str, window_seconds: int = 60, max_requests: int = 10) -> Tuple[bool, int]:
        """
        Check if request is allowed based on rate limit
        
        Args:
            client_ip: Client IP address
            window_seconds: Time window in seconds
            max_requests: Maximum requests per window
            
        Returns:
            Tuple of (is_allowed, requests_remaining)
        """
        current_time = time.time()
        
        # Clean old requests outside the window
        while (self.requests[client_ip] and 
               current_time - self.requests[client_ip][0] > window_seconds):
            self.requests[client_ip].popleft()
        
        # Check if under limit
        current_requests = len(self.requests[client_ip])
        
        if current_requests < max_requests:
            # Add current request
            self.requests[client_ip].append(current_time)
            return True, max_requests - current_requests - 1
        else:
            return False, 0

# Global rate limiter instance
rate_limiter = SimpleRateLimiter()

def check_rate_limit(request: Request, max_requests: int = 10, window_seconds: int = 60):
    """
    Check rate limit for a request
    
    Args:
        request: FastAPI request object
        max_requests: Maximum requests per window
        window_seconds: Time window in seconds
        
    Raises:
        HTTPException: If rate limit exceeded
    """
    # Get client IP
    client_ip = request.client.host if request.client else "unknown"
    
    # Check forwarded headers for real IP (behind proxy)
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        client_ip = forwarded_for.split(",")[0].strip()
    
    # Check rate limit
    allowed, remaining = rate_limiter.is_allowed(client_ip, window_seconds, max_requests)
    
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds.",
            headers={"Retry-After": str(window_seconds)}
        )
    
    return remaining

def check_payment_rate_limit(request: Request):
    """Stricter rate limiting for payment endpoints"""
    return check_rate_limit(request, max_requests=3, window_seconds=300)  # 3 requests per 5 minutes

def check_signup_rate_limit(request: Request):
    """Rate limiting for signup endpoint"""
    return check_rate_limit(request, max_requests=5, window_seconds=300)  # 5 signups per 5 minutes

def check_processing_rate_limit(request: Request):
    """Rate limiting for file processing"""
    return check_rate_limit(request, max_requests=10, window_seconds=3600)  # 10 files per hour
