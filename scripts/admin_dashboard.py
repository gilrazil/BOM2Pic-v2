#!/usr/bin/env python3
"""
BOM2Pic Admin Dashboard
View all users, trials, and subscriptions from SQLite database
"""
import sqlite3
import os
from datetime import datetime
from typing import Dict, Any

def load_users() -> Dict[str, Any]:
    """Load users from SQLite database."""
    DB_FILE = "data/users.db" if not os.getenv("RENDER") else "/opt/render/project/data/users.db"
    
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
        print(f"Error loading users from database: {e}")
        return {}

def show_dashboard():
    users = load_users()
    
    print("🚀 BOM2Pic Admin Dashboard")
    print("=" * 50)
    
    if not users:
        print("No users yet.")
        return
    
    print(f"📊 Total Users: {len(users)}")
    print()
    
    active_trials = 0
    expired_trials = 0
    active_subscriptions = 0
    
    for email, user in users.items():
        print(f"📧 Email: {email}")
        print(f"   Plan: {user.get('plan', 'unknown')}")
        print(f"   Status: {user.get('subscription_status', 'unknown')}")
        print(f"   Trial Start: {user.get('trial_start', 'unknown')}")
        print(f"   Trial End: {user.get('trial_end', 'unknown')}")
        
        # Check trial status
        if user.get('trial_end'):
            trial_end = datetime.fromisoformat(user['trial_end'])
            days_left = (trial_end - datetime.now()).days
            
            if days_left > 0:
                print(f"   ✅ Trial Active ({days_left} days left)")
                active_trials += 1
            else:
                print(f"   ⏰ Trial Expired ({abs(days_left)} days ago)")
                expired_trials += 1
        
        if user.get('subscription_status') == 'active':
            active_subscriptions += 1
            
        print(f"   Created: {user.get('created_at', 'unknown')}")
        print("-" * 30)
    
    print("\n📈 Summary:")
    print(f"   Active Trials: {active_trials}")
    print(f"   Expired Trials: {expired_trials}")
    print(f"   Active Subscriptions: {active_subscriptions}")

if __name__ == "__main__":
    show_dashboard()
