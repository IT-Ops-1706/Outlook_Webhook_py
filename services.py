import requests
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from fastapi import HTTPException

load_dotenv()

# Configuration
CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
TENANT_ID = os.getenv('TENANT_ID')
USER_EMAIL = os.getenv('USER_EMAIL')
WEBHOOK_URL = os.getenv('WEBHOOK_URL', 'https://outlook-webhook-py.onrender.com/webhook')
WEBHOOK_CLIENT_STATE = os.getenv('WEBHOOK_CLIENT_STATE', 'SecretClientState')

def get_access_token():
    """Get access token using client credentials flow"""
    try:
        token_url = f'https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token'
        
        data = {
            'client_id': CLIENT_ID,
            'client_secret': CLIENT_SECRET,
            'scope': 'https://graph.microsoft.com/.default',
            'grant_type': 'client_credentials'
        }
        
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        
        token_data = response.json()
        return token_data['access_token']
    
    except Exception as e:
        print(f"Error getting access token: {e}")
        raise HTTPException(status_code=500, detail=f"Token error: {str(e)}")

def get_latest_emails(user_email: str, top: int = 10):
    """Fetch latest emails for a user"""
    try:
        token = get_access_token()
        
        url = f'https://graph.microsoft.com/v1.0/users/{user_email}/messages'
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        params = {
            '$top': top,
            '$orderby': 'receivedDateTime DESC',
            '$select': 'id,subject,from,receivedDateTime,bodyPreview,isRead,hasAttachments'
        }
        
        response = requests.get(url, headers=headers, params=params)
        response.raise_for_status()
        
        return response.json()['value']
    
    except Exception as e:
        print(f"Error fetching emails: {e}")
        raise HTTPException(status_code=500, detail=f"Email fetch error: {str(e)}")

def get_email_details(user_email: str, message_id: str):
    """Get detailed information for a specific email"""
    try:
        token = get_access_token()
        
        url = f'https://graph.microsoft.com/v1.0/users/{user_email}/messages/{message_id}'
        
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }
        
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        
        return response.json()
    
    except Exception as e:
        print(f"Error fetching email details: {e}")
        raise HTTPException(status_code=500, detail=f"Email details error: {str(e)}")

def create_subscription(access_token, webhook_url, user_email):
    """Create a new webhook subscription"""
    subscription_url = 'https://graph.microsoft.com/v1.0/subscriptions'
    
    # Microsoft allows max 3 days for mail subscriptions
    expiration_time = datetime.utcnow() + timedelta(days=2, hours=23)
    expiration_str = expiration_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    subscription_data = {
        'changeType': 'created',
        'notificationUrl': webhook_url,
        'resource': f'users/{user_email}/messages',
        'expirationDateTime': expiration_str,
        'clientState': WEBHOOK_CLIENT_STATE
    }
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.post(subscription_url, headers=headers, json=subscription_data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error creating subscription: {e}")
        if hasattr(e, 'response') and e.response is not None:
            try:
                print(f"Error Details: {e.response.json()}")
            except:
                print(f"Response Body: {e.response.text}")
        raise

def list_subscriptions(access_token):
    """List all active subscriptions"""
    subscription_url = 'https://graph.microsoft.com/v1.0/subscriptions'
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.get(subscription_url, headers=headers)
        response.raise_for_status()
        return response.json().get('value', [])
    except Exception as e:
        print(f"Error listing subscriptions: {e}")
        raise

def renew_subscription(access_token, subscription_id):
    """Renew/extend a subscription"""
    subscription_url = f'https://graph.microsoft.com/v1.0/subscriptions/{subscription_id}'
    
    # Extend by 3 days
    expiration_time = datetime.utcnow() + timedelta(days=2, hours=23)
    expiration_str = expiration_time.strftime('%Y-%m-%dT%H:%M:%S.%f')[:-3] + 'Z'
    
    data = {
        'expirationDateTime': expiration_str
    }
    
    headers = {
        'Authorization': f'Bearer {access_token}',
        'Content-Type': 'application/json'
    }
    
    try:
        response = requests.patch(subscription_url, headers=headers, json=data)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Error renewing subscription: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response: {e.response.text}")
        raise

async def ensure_subscription():
    """Ensures a valid subscription exists (Integrated Logic)"""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Checking subscription status...")
    
    try:
        token = get_access_token()
        subs = list_subscriptions(token)
        
        active_sub = None
        for sub in subs:
            if sub.get('resource') == f'users/{USER_EMAIL}/messages':
                active_sub = sub
                break
        
        if not active_sub:
            print("No active subscription found. Creating new...")
            new_sub = create_subscription(token, WEBHOOK_URL, USER_EMAIL)
            print(f"Subscription created. ID: {new_sub['id']} | Expires: {new_sub['expirationDateTime']}")
        else:
            exp_str = active_sub['expirationDateTime']
            exp_time = datetime.strptime(exp_str.split('.')[0], '%Y-%m-%dT%H:%M:%S')
            hours_left = (exp_time - datetime.utcnow()).total_seconds() / 3600
            
            print(f"Active Subscription: {active_sub['id']} | Expires in: {hours_left:.1f}h")
            
            if hours_left < 24:
                print("Subscription expiring soon. Renewing...")
                renewed = renew_subscription(token, active_sub['id'])
                print(f"Subscription renewed. New Expiration: {renewed['expirationDateTime']}")
            else:
                print("Subscription status: Healthy")

    except Exception as e:
        print(f"Error in subscription check: {e}")
