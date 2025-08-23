"""
Clerk Authentication Module for BOM2Pic
Simple and reliable authentication using Clerk
"""
import os
import json
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
import clerk

# Initialize Clerk
clerk.api_key = os.getenv("CLERK_SECRET_KEY")

# Simple user storage for trial tracking
USERS_FILE = "users.json"

class AuthError(Exception):
    """Custom authentication error."""
    pass

def load_users() -> Dict:
    """Load users from JSON file."""
    if Path(USERS_FILE).exists():
        with open(USERS_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_users(users: Dict) -> None:
    """Save users to JSON file."""
    with open(USERS_FILE, 'w') as f:
        json.dump(users, f, indent=2, default=str)

def verify_clerk_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify Clerk JWT token and return user info."""
    if not token:
        return None
    
    try:
        # Remove 'Bearer ' prefix if present
        if token.startswith('Bearer '):
            token = token[7:]
        
        # Verify token with Clerk
        session = clerk.Session.verify(token)
        if not session:
            return None
        
        # Get user info
        user = clerk.User.retrieve(session.user_id)
        if not user:
            return None
        
        return {
            "user_id": user.id,
            "email": user.email_addresses[0].email_address if user.email_addresses else None,
            "first_name": user.first_name,
            "last_name": user.last_name
        }
        
    except Exception as e:
        print(f"Token verification error: {e}")
        return None

def create_user(email: str, user_id: str = None) -> Dict[str, Any]:
    """Create a new user with 30-day trial."""
    users = load_users()
    
    user_data = {
        "email": email,
        "user_id": user_id,
        "plan": "trial",
        "trial_start": datetime.now().isoformat(),
        "trial_end": (datetime.now() + timedelta(days=30)).isoformat(),
        "subscription_status": "trial",
        "created_at": datetime.now().isoformat()
    }
    
    users[email] = user_data
    save_users(users)
    
    return user_data

def get_user(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    users = load_users()
    return users.get(email)

def get_or_create_user(email: str, user_id: str = None) -> Dict[str, Any]:
    """Get existing user or create new one with trial."""
    user = get_user(email)
    if not user:
        user = create_user(email, user_id)
    return user

def check_user_access(email: str) -> Dict[str, Any]:
    """Check if user has access to process files."""
    user = get_user(email)
    
    if not user:
        # Auto-create user with trial
        user = create_user(email)
    
    # Check if user has active subscription
    if user.get("subscription_status") == "active":
        return {
            "access": True,
            "user": user,
            "plan": "subscription",
            "message": "Active subscription"
        }
    
    # Check if user is in trial period
    if user.get("plan") == "trial" and user.get("trial_end"):
        trial_end = datetime.fromisoformat(user["trial_end"])
        if datetime.now() < trial_end:
            days_left = (trial_end - datetime.now()).days
            return {
                "access": True,
                "user": user,
                "plan": "trial",
                "days_left": max(0, days_left),
                "message": f"Free trial ({days_left} days left)"
            }
    
    # Trial expired
    return {
        "access": False,
        "reason": "trial_expired",
        "message": "Free trial expired. Please choose a plan to continue.",
        "user": user
    }

def update_subscription_status(email: str, status: str, plan: str = None) -> bool:
    """Update user's subscription status."""
    users = load_users()
    
    if email not in users:
        return False
    
    users[email]["subscription_status"] = status
    if plan:
        users[email]["plan"] = plan
    
    save_users(users)
    return True
