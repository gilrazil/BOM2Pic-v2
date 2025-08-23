"""
Simple PayPal payment integration for BOM2Pic.
Handles $10 monthly subscriptions and $5 per-file payments.
"""
import os
import base64
from typing import Dict, Any

import httpx


# PayPal configuration
PAYPAL_CLIENT_ID = os.getenv("PAYPAL_CLIENT_ID")
PAYPAL_CLIENT_SECRET = os.getenv("PAYPAL_CLIENT_SECRET")
PAYPAL_ENVIRONMENT = os.getenv("PAYPAL_ENVIRONMENT", "sandbox")  # sandbox or live

PAYPAL_BASE_URL = {
    "sandbox": "https://api-m.sandbox.paypal.com",
    "live": "https://api-m.paypal.com"
}

# Simple pricing plans
PLANS = {
    "monthly": {
        "name": "Monthly Unlimited",
        "price": 10,
        "description": "Unlimited image processing for $10/month"
    },
    "per_file": {
        "name": "Pay Per File",
        "price": 5,
        "description": "Process one file for $5 (no subscription)"
    }
}


class PaymentError(Exception):
    """Custom payment error."""
    pass


async def get_paypal_access_token() -> str:
    """Get PayPal access token for API requests."""
    if not PAYPAL_CLIENT_ID or not PAYPAL_CLIENT_SECRET:
        raise PaymentError("PayPal credentials not configured")
    
    # Create basic auth header
    auth_string = f"{PAYPAL_CLIENT_ID}:{PAYPAL_CLIENT_SECRET}"
    auth_bytes = auth_string.encode('ascii')
    auth_header = base64.b64encode(auth_bytes).decode('ascii')
    
    headers = {
        "Accept": "application/json",
        "Accept-Language": "en_US",
        "Authorization": f"Basic {auth_header}"
    }
    
    data = "grant_type=client_credentials"
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PAYPAL_BASE_URL[PAYPAL_ENVIRONMENT]}/v1/oauth2/token",
                headers=headers,
                content=data
            )
            
            if response.status_code == 200:
                token_data = response.json()
                return token_data["access_token"]
            else:
                raise PaymentError(f"PayPal auth failed: {response.text}")
                
    except httpx.RequestError as e:
        raise PaymentError(f"PayPal connection failed: {e}")


async def create_payment_session(plan: str, user_email: str, success_url: str, cancel_url: str) -> Dict[str, Any]:
    """
    Create PayPal payment session.
    
    Args:
        plan: 'monthly' or 'per_file'
        user_email: User's email address
        success_url: URL to redirect after successful payment
        cancel_url: URL to redirect after cancelled payment
        
    Returns:
        Dict with checkout URL and session ID
    """
    if plan not in PLANS:
        raise PaymentError(f"Invalid plan: {plan}")
    
    plan_info = PLANS[plan]
    access_token = await get_paypal_access_token()
    
    # Create payment payload
    if plan == "monthly":
        # For subscription, we'd need to create a subscription plan first
        # For now, we'll create a simple one-time payment
        payment_data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": str(plan_info["price"])
                },
                "description": plan_info["description"]
            }],
            "application_context": {
                "brand_name": "BOM2Pic",
                "landing_page": "NO_PREFERENCE",
                "shipping_preference": "NO_SHIPPING",
                "user_action": "PAY_NOW",
                "return_url": success_url,
                "cancel_url": cancel_url
            }
        }
    else:  # per_file
        payment_data = {
            "intent": "CAPTURE",
            "purchase_units": [{
                "amount": {
                    "currency_code": "USD",
                    "value": str(plan_info["price"])
                },
                "description": plan_info["description"]
            }],
            "application_context": {
                "brand_name": "BOM2Pic",
                "landing_page": "NO_PREFERENCE",
                "shipping_preference": "NO_SHIPPING",
                "user_action": "PAY_NOW",
                "return_url": success_url,
                "cancel_url": cancel_url
            }
        }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{PAYPAL_BASE_URL[PAYPAL_ENVIRONMENT]}/v2/checkout/orders",
                json=payment_data,
                headers=headers
            )
            
            if response.status_code == 201:
                order = response.json()
                
                # Find approval URL
                approval_url = None
                for link in order.get("links", []):
                    if link.get("rel") == "approve":
                        approval_url = link.get("href")
                        break
                
                if approval_url:
                    return {
                        "checkout_url": approval_url,
                        "session_id": order.get("id"),
                        "status": order.get("status")
                    }
                else:
                    raise PaymentError("PayPal order created but no approval URL found")
            else:
                raise PaymentError(f"PayPal order creation failed: {response.text}")
                
    except httpx.RequestError as e:
        raise PaymentError(f"PayPal request failed: {e}")


async def verify_payment(session_id: str) -> Dict[str, Any]:
    """
    Verify PayPal payment completion.
    
    Args:
        session_id: PayPal order ID
        
    Returns:
        Payment verification result
    """
    access_token = await get_paypal_access_token()
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{PAYPAL_BASE_URL[PAYPAL_ENVIRONMENT]}/v2/checkout/orders/{session_id}",
                headers=headers
            )
            
            if response.status_code == 200:
                order = response.json()
                return {
                    "verified": order.get("status") == "COMPLETED",
                    "order_id": order.get("id"),
                    "status": order.get("status"),
                    "amount": order.get("purchase_units", [{}])[0].get("amount", {}).get("value"),
                    "currency": order.get("purchase_units", [{}])[0].get("amount", {}).get("currency_code")
                }
            else:
                return {"verified": False, "error": f"PayPal verification failed: {response.text}"}
                
    except Exception as e:
        return {"verified": False, "error": f"Payment verification error: {e}"}


def get_plans() -> Dict[str, Any]:
    """Get available pricing plans."""
    return PLANS
