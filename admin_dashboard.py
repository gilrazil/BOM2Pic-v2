#!/usr/bin/env python3
"""
BOM2Pic Admin Dashboard
View all users, trials, and subscriptions
"""
import json
from datetime import datetime
from pathlib import Path

def load_users():
    if Path("users.json").exists():
        with open("users.json", 'r') as f:
            return json.load(f)
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
