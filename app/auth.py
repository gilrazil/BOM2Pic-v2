"""
Simple authentication and user management for BOM2Pic.
Updated to support lifetime access from PayPal LTD.
"""
import os
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import uuid

# Database configuration
DB_FILE = "/opt/render/project/data/users.db" if os.getenv("RENDER") else "data/users.db"

def init_database():
    """Initialize SQLite database with users table."""
    try:
        # Ensure directory exists on Render
        if os.getenv("RENDER"):
            os.makedirs("/opt/render/project/data", exist_ok=True)
        
        conn = sqlite3.connect(DB_FILE)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                email TEXT PRIMARY KEY,
                user_id TEXT,
                plan TEXT DEFAULT 'trial',
                trial_start TEXT,
                trial_end TEXT,
                subscription_status TEXT DEFAULT 'trial',
                subscription_type TEXT,
                expires_at TEXT,
                created_at TEXT,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        conn.commit()
        conn.close()
    except Exception as e:
        raise

# Initialize database on module import
init_database()

def load_users() -> Dict[str, Any]:
    """Load users from SQLite database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        cursor = conn.execute("""
            SELECT email, user_id, plan, trial_start, trial_end, subscription_status, 
                   subscription_type, expires_at, created_at, is_active 
            FROM users
        """)
        rows = cursor.fetchall()
        
        users = {}
        for row in rows:
            email = row[0]
            users[email] = {
                "email": row[0],
                "user_id": row[1],
                "plan": row[2],
                "trial_start": row[3],
                "trial_end": row[4],
                "subscription_status": row[5],
                "subscription_type": row[6],
                "expires_at": row[7],
                "created_at": row[8],
                "is_active": bool(row[9]) if row[9] is not None else True
            }
        
        conn.close()
        return users
        
    except Exception as e:
        return {}

def save_users(users: Dict[str, Any]):
    """Save users to SQLite database."""
    try:
        conn = sqlite3.connect(DB_FILE)
        
        # Clear existing data and insert new data
        conn.execute("DELETE FROM users")
        
        for email, user_data in users.items():
            conn.execute("""
                INSERT INTO users (email, user_id, plan, trial_start, trial_end, subscription_status, subscription_type, expires_at, created_at, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                email,
                user_data.get("user_id"),
                user_data.get("plan", "trial"),
                user_data.get("trial_start"),
                user_data.get("trial_end"),
                user_data.get("subscription_status", "trial"),
                user_data.get("subscription_type"),
                user_data.get("expires_at"),
                user_data.get("created_at"),
                user_data.get("is_active", True)
            ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        raise

def create_user(email: str, user_id: str = None) -> Dict[str, Any]:
    """Create a new user with 30-day trial."""
    users = load_users()
    
    user_data = {
        "email": email,
        "user_id": user_id or str(uuid.uuid4()),
        "plan": "trial",
        "trial_start": datetime.now().isoformat(),
        "trial_end": (datetime.now() + timedelta(days=30)).isoformat(),
        "subscription_status": "trial",
        "subscription_type": "trial",
        "expires_at": None,
        "created_at": datetime.now().isoformat(),
        "is_active": True
    }
    
    users[email] = user_data
    save_users(users)
    
    return user_data

def get_user(email: str) -> Optional[Dict[str, Any]]:
    """Get user by email."""
    users = load_users()
    return users.get(email)

def get_or_create_user(email: str, user_id: str = None) -> Dict[str, Any]:
    """Get existing user or create new one."""
    user = get_user(email)
    if not user:
        user = create_user(email, user_id)
    return user

def check_user_access(user: Dict[str, Any]) -> Dict[str, Any]:
    """Check if user has access to process files."""
    email = user.get("email")
    
    if not user:
        return {
            "access": False,
            "reason": "no_user",
            "message": "User not found"
        }
    
    # Check for lifetime access
    if user.get("subscription_type") == "lifetime":
        return {
            "access": True,
            "user": user,
            "plan": "lifetime",
            "message": "Lifetime access - unlimited forever!"
        }
    
    # Check if user has active subscription
    if user.get("subscription_status") == "active":
        # Check if subscription has expired
        expires_at = user.get("expires_at")
        if expires_at and expires_at != "lifetime":
            try:
                expiry_date = datetime.fromisoformat(expires_at)
                if datetime.now() > expiry_date:
                    # Subscription expired
                    return {
                        "access": False,
                        "reason": "subscription_expired",
                        "message": "Subscription expired. Please renew to continue.",
                        "user": user
                    }
            except ValueError:
                # Invalid date format, treat as expired
                return {
                    "access": False,
                    "reason": "invalid_expiry",
                    "message": "Invalid subscription data. Please contact support.",
                    "user": user
                }
        
        return {
            "access": True,
            "user": user,
            "plan": user.get("subscription_type", "subscription"),
            "message": f"Active {user.get('subscription_type', 'subscription')} plan"
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
    
    # Check per-file credits
    if user.get("subscription_type") == "per_file":
        # For per-file, we'll assume they have access once (could be improved with credit tracking)
        return {
            "access": True,
            "user": user,
            "plan": "per_file",
            "message": "Per-file access granted"
        }
    
    # Trial expired or no valid subscription
    return {
        "access": False,
        "reason": "trial_expired",
        "message": "Free trial expired. Please choose a plan to continue.",
        "user": user
    }

def update_subscription_status(email: str, subscription_type: str, expires_at: str = None) -> bool:
    """Update user's subscription status and type."""
    users = load_users()
    
    if email not in users:
        # Create user if doesn't exist
        users[email] = create_user(email)
    
    user = users[email]
    
    # Update subscription details
    if subscription_type == "lifetime":
        user["subscription_status"] = "active"
        user["subscription_type"] = "lifetime"
        user["expires_at"] = None  # Never expires
        user["plan"] = "lifetime"
    elif subscription_type == "monthly":
        user["subscription_status"] = "active"
        user["subscription_type"] = "monthly"
        user["expires_at"] = expires_at
        user["plan"] = "monthly"
    elif subscription_type == "per_file":
        user["subscription_status"] = "active"
        user["subscription_type"] = "per_file"
        user["expires_at"] = None  # Single use
        user["plan"] = "per_file"
    
    user["is_active"] = True
    
    users[email] = user
    save_users(users)
    
    return True