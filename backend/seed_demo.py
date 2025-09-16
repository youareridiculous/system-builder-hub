#!/usr/bin/env python3
"""
Demo seed data for System Builder Hub
"""
import os
import sys
from pathlib import Path

# Add the src directory to the path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.database_manager import init_database, get_db_session
from src.models import User, Tenant, UserTenant, Conversation, Message, MessageRole
from src.auth import get_or_create_user, get_or_create_tenant, ensure_user_tenant_access

def seed_demo_data():
    """Create demo tenant, user, and conversation"""
    print("Seeding demo data...")
    
    # Initialize database
    if not init_database():
        print("Failed to initialize database")
        return False
    
    try:
        with get_db_session() as session:
            # Create demo tenant
            demo_tenant = get_or_create_tenant('demo', 'Demo Tenant')
            print(f"Created/found demo tenant: {demo_tenant.slug}")
            
            # Create demo user
            demo_user = get_or_create_user('demo@sbh.com', 'Demo User')
            print(f"Created/found demo user: {demo_user.email}")
            
            # Ensure user has access to tenant
            user_tenant = ensure_user_tenant_access(demo_user, demo_tenant, 'admin')
            print(f"Granted {demo_user.email} access to {demo_tenant.slug}")
            
            # Create demo conversation
            existing_conv = session.query(Conversation).filter(
                Conversation.tenant_id == demo_tenant.id,
                Conversation.title == 'Welcome to System Builder Hub'
            ).first()
            
            if not existing_conv:
                conversation = Conversation(
                    tenant_id=demo_tenant.id,
                    user_id=demo_user.id,
                    title='Welcome to System Builder Hub'
                )
                session.add(conversation)
                session.commit()
                session.refresh(conversation)
                print(f"Created demo conversation: {conversation.title}")
                
                # Add welcome messages
                welcome_messages = [
                    {
                        'role': MessageRole.SYSTEM,
                        'content': 'Welcome to System Builder Hub! I can help you build complete applications from specifications.'
                    },
                    {
                        'role': MessageRole.USER,
                        'content': 'Hi! I want to build a simple blog website.'
                    },
                    {
                        'role': MessageRole.ASSISTANT,
                        'content': 'Great! I can help you build a blog website. Let me ask a few questions to understand your requirements:\n\n1. What type of content will you be blogging about?\n2. Do you need user authentication for comments?\n3. What design style do you prefer (modern, minimalist, colorful)?\n4. Do you need any specific features like search, categories, or tags?'
                    }
                ]
                
                for msg_data in welcome_messages:
                    message = Message(
                        conversation_id=conversation.id,
                        role=msg_data['role'],
                        content=msg_data['content']
                    )
                    session.add(message)
                
                session.commit()
                print(f"Added {len(welcome_messages)} welcome messages")
            else:
                print("Demo conversation already exists")
            
            print("Demo data seeding completed successfully!")
            return True
            
    except Exception as e:
        print(f"Failed to seed demo data: {e}")
        return False

if __name__ == "__main__":
    success = seed_demo_data()
    sys.exit(0 if success else 1)
