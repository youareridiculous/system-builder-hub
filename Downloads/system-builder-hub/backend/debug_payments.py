"""
Debug script to test payments functionality
"""
import os
import sys
sys.path.insert(0, 'src')

from app import create_app

def test_payments():
    """Test payments functionality"""
    print("Testing payments functionality...")
    
    app = create_app()
    
    with app.test_client() as client:
        # Test plans endpoint
        print("\n1. Testing plans endpoint:")
        response = client.get('/api/payments/plans')
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.get_json()
            print(f"Plans: {len(data['plans'])} available")
            for plan in data['plans']:
                print(f"  - {plan['name']}: ${plan['price']}/{plan['interval']}")
        else:
            print(f"Error: {response.get_json()}")
        
        # Test user registration
        print("\n2. Testing user registration:")
        response = client.post('/api/auth/register', json={
            'email': 'debug@example.com',
            'password': 'password123'
        })
        print(f"Status: {response.status_code}")
        if response.status_code == 201:
            data = response.get_json()
            print(f"User created: {data['user']['email']}")
            token = data['token']
            
            # Test subscription status
            print("\n3. Testing subscription status:")
            status_response = client.get('/api/payments/status',
                headers={'Authorization': f'Bearer {token}'}
            )
            print(f"Status: {status_response.status_code}")
            if status_response.status_code == 200:
                status_data = status_response.get_json()
                subscription = status_data['subscription']
                print(f"Plan: {subscription['plan']}")
                print(f"Status: {subscription['status']}")
                print(f"Active: {subscription['is_active']}")
            else:
                print(f"Error: {status_response.get_json()}")
            
            # Test checkout creation
            print("\n4. Testing checkout creation:")
            checkout_response = client.post('/api/payments/create-checkout',
                headers={'Authorization': f'Bearer {token}'},
                json={'plan_id': 'pro'}
            )
            print(f"Status: {checkout_response.status_code}")
            if checkout_response.status_code == 200:
                checkout_data = checkout_response.get_json()
                print(f"Checkout URL: {checkout_data['checkout_url']}")
                print(f"Session ID: {checkout_data['session_id']}")
            else:
                print(f"Error: {checkout_response.get_json()}")
        else:
            print(f"Error: {response.get_json()}")

if __name__ == "__main__":
    test_payments()
