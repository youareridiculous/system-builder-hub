"""
WSGI entry point for production deployment
"""
from src.server import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
