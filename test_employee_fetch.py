"""
Standalone test script to fetch employee details from Microsoft Graph.
Run this to see the raw user data from Microsoft 365.
"""

import requests
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

CLIENT_ID = os.getenv('CLIENT_ID')
CLIENT_SECRET = os.getenv('CLIENT_SECRET')
TENANT_ID = os.getenv('TENANT_ID')

def get_access_token():
    """Get OAuth token from Microsoft"""
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

def fetch_user_details(email):
    """Fetch user details from Microsoft Graph"""
    print(f"\n{'='*60}")
    print(f"Fetching details for: {email}")
    print('='*60)
    
    token = get_access_token()
    
    url = f'https://graph.microsoft.com/v1.0/users/{email}'
    
    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }
    
    try:
        # First, try to get ALL user properties to see what's available
        response = requests.get(url, headers=headers)
        
        if response.status_code == 404:
            print(f"❌ User not found: {email}")
            return None
        
        response.raise_for_status()
        user_data = response.json()
        
        print(f"\n✅ User found!")
        print(f"\n📋 FULL USER DATA:")
        print("-" * 60)
        
        # Print all available fields
        for key, value in sorted(user_data.items()):
            if value:  # Only print non-empty values
                print(f"  {key}: {value}")
        
        print("\n" + "="*60)
        print("📊 EMPLOYEE DATA FIELDS (What we're extracting):")
        print("="*60)
        print(f"  Email: {user_data.get('mail', 'N/A')}")
        print(f"  Display Name: {user_data.get('displayName', 'N/A')}")
        print(f"  Job Title: {user_data.get('jobTitle', 'N/A')}")
        print(f"  Department: {user_data.get('department', 'N/A')}")
        print(f"  Office Location: {user_data.get('officeLocation', 'N/A')}")
        print(f"  City: {user_data.get('city', 'N/A')}")
        print(f"  Country: {user_data.get('country', 'N/A')}")
        print(f"  State: {user_data.get('state', 'N/A')}")
        print(f"  Street Address: {user_data.get('streetAddress', 'N/A')}")
        print(f"  Postal Code: {user_data.get('postalCode', 'N/A')}")
        print(f"  Mobile Phone: {user_data.get('mobilePhone', 'N/A')}")
        print(f"  Business Phones: {user_data.get('businessPhones', 'N/A')}")
        
        return user_data
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        return None

if __name__ == "__main__":
    print("\n" + "="*60)
    print("🔍 MICROSOFT GRAPH USER DETAILS TEST")
    print("="*60)
    
    # Test emails
    test_emails = [
        "it.ops@babajishivram.com",
        "javed.shaikh@babajishivram.com"
    ]
    
    for email in test_emails:
        fetch_user_details(email)
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETE")
    print("="*60)
    print("\nℹ️  If all fields show as 'N/A', the user profiles are not set up")
    print("   in Microsoft 365 Admin Center.")
    print("\n💡 To fix: Go to Microsoft 365 Admin → Users → Active users")
    print("   → Click user → Edit contact information and job info")
    print("="*60 + "\n")
