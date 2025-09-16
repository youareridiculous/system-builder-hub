import os
import psycopg2
from urllib.parse import urlparse

database_url = os.getenv('DATABASE_URL')
print(f"DATABASE_URL: {database_url}")
parsed = urlparse(database_url)
print(f"Host: {parsed.hostname}, Port: {parsed.port}, DB: {parsed.path.lstrip('/')}")
try:
    conn = psycopg2.connect(
        host=parsed.hostname,
        port=parsed.port or 5432,
        database=parsed.path.lstrip('/'),
        user=parsed.username,
        password=parsed.password
    )
    print("✅ PostgreSQL connection successful!")
    cursor = conn.cursor()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"Version: {version[0]}")
    cursor.close()
    conn.close()
except Exception as e:
    print(f"❌ Connection failed: {e}")
