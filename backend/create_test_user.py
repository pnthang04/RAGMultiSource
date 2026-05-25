#!/usr/bin/env python3
"""
Get or create a test user and get auth token for testing
"""
import asyncio
import sys
sys.path.insert(0, 'd:\\Project\\Chatbot\\backend')

from app.services.user_service import UserService

async def get_or_create_test_user():
    service = UserService()
    email = "test_pipeline@example.com"
    password = "test_password_123"
    
    # Try to login first
    try:
        user, token = await service.login_user(email=email, password=password)
        print(f"✅ User already exists, logged in!")
    except ValueError:
        # User doesn't exist, create new one
        user, token = await service.register_user(
            name="Test User Pipeline",
            email=email,
            password=password
        )
        print(f"✅ New user created!")
    
    print(f"   Name: {user.name}")
    print(f"   Email: {user.email}")
    print(f"   User ID: {user.id}")
    print(f"   Token: {token}")
    print()
    print(f"🔐 Use this token in requests:")
    print(f'   Authorization: Bearer {token}')
    print()
    return token

if __name__ == '__main__':
    token = asyncio.run(get_or_create_test_user())
