#!/usr/bin/env python3
"""
Test database connection script
"""
import os
import sys

def main():
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./db/sbh.db')
    print(f"Testing connection to: {database_url}")
    
    if database_url.startswith('postgresql://'):
        try:
            import psycopg2
            from urllib.parse import urlparse
            
            parsed = urlparse(database_url)
            print(f"Connecting to PostgreSQL:")
            print(f"  Host: {parsed.hostname}")
            print(f"  Port: {parsed.port}")
            print(f"  Database: {parsed.path.lstrip('/')}")
            print(f"  Username: {parsed.username}")
            
            conn = psycopg2.connect(
                host=parsed.hostname,
                port=parsed.port or 5432,
                database=parsed.path.lstrip('/'),
                user=parsed.username,
                password=parsed.password
            )
            
            cursor = conn.cursor()
            cursor.execute("SELECT version();")
            version = cursor.fetchone()
            print(f"✅ PostgreSQL connection successful!")
            print(f"   Version: {version[0]}")
            
            # Test if tables exist
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """)
            tables = cursor.fetchall()
            print(f"   Tables found: {len(tables)}")
            if tables:
                print("   Table names:", [t[0] for t in tables[:10]])
            else:
                print("   No tables found - migrations needed!")
            
            cursor.close()
            conn.close()
            return 0
            
        except Exception as e:
            print(f"❌ PostgreSQL connection failed: {e}")
            return 1
    else:
        print("Not a PostgreSQL URL, skipping test")
        return 0

if __name__ == "__main__":
    sys.exit(main())
