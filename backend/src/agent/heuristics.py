"""
Agent heuristics - rule-based fallback patterns for No-LLM mode
"""
import logging
from typing import Dict, Any, List
from ..builder_schema import slugify

logger = logging.getLogger(__name__)

class HeuristicPatterns:
    """Rule-based patterns for common application types"""
    
    @staticmethod
    def task_tracker() -> List[Dict[str, Any]]:
        """Generate task tracker pattern"""
        return [
            {
                "id": "tbl_tasks",
                "type": "db_table",
                "props": {
                    "name": "tasks",
                    "columns": [
                        {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
                        {"name": "title", "type": "TEXT"},
                        {"name": "completed", "type": "BOOLEAN DEFAULT 0"}
                    ]
                }
            },
            {
                "id": "api_tasks",
                "type": "rest_api",
                "props": {
                    "name": "Tasks API",
                    "route": "/api/tasks",
                    "method": "GET",
                    "sample_response": '[{"id":1,"title":"Example task","completed":false}]'
                }
            },
            {
                "id": "ui_taskspage",
                "type": "ui_page",
                "props": {
                    "name": "TasksPage",
                    "route": "/tasks",
                    "title": "Tasks",
                    "content": "<h1>Tasks</h1><p>Track your tasks below.</p>",
                    "consumes": {"api": "/api/tasks", "render": "list"},
                    "bind_table": "tasks",
                    "form": {"enabled": True, "fields": ["title"]}
                }
            }
        ]
    
    @staticmethod
    def blog() -> List[Dict[str, Any]]:
        """Generate blog pattern"""
        return [
            {
                "id": "tbl_posts",
                "type": "db_table",
                "props": {
                    "name": "posts",
                    "columns": [
                        {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
                        {"name": "title", "type": "TEXT"},
                        {"name": "content", "type": "TEXT"},
                        {"name": "created_at", "type": "TEXT"}
                    ]
                }
            },
            {
                "id": "api_posts",
                "type": "rest_api",
                "props": {
                    "name": "Posts API",
                    "route": "/api/posts",
                    "method": "GET",
                    "sample_response": '[{"id":1,"title":"First Post","content":"Welcome!","created_at":"2024-01-01"}]'
                }
            },
            {
                "id": "ui_postspage",
                "type": "ui_page",
                "props": {
                    "name": "PostsPage",
                    "route": "/posts",
                    "title": "Blog Posts",
                    "content": "<h1>Blog Posts</h1><p>Read our latest posts.</p>",
                    "consumes": {"api": "/api/posts", "render": "list"},
                    "bind_table": "posts",
                    "form": {"enabled": True, "fields": ["title", "content"]}
                }
            }
        ]
    
    @staticmethod
    def contact_form() -> List[Dict[str, Any]]:
        """Generate contact form pattern"""
        return [
            {
                "id": "tbl_messages",
                "type": "db_table",
                "props": {
                    "name": "messages",
                    "columns": [
                        {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
                        {"name": "name", "type": "TEXT"},
                        {"name": "email", "type": "TEXT"},
                        {"name": "message", "type": "TEXT"}
                    ]
                }
            },
            {
                "id": "api_messages",
                "type": "rest_api",
                "props": {
                    "name": "Messages API",
                    "route": "/api/messages",
                    "method": "GET",
                    "sample_response": '[{"id":1,"name":"Contact","email":"contact@example.com","message":"Hello!"}]'
                }
            },
            {
                "id": "ui_contactpage",
                "type": "ui_page",
                "props": {
                    "name": "ContactPage",
                    "route": "/contact",
                    "title": "Contact Us",
                    "content": "<h1>Contact Us</h1><p>Send us a message.</p>",
                    "consumes": {"api": "/api/messages", "render": "list"},
                    "bind_table": "messages",
                    "form": {"enabled": True, "fields": ["name", "email", "message"]}
                }
            }
        ]
    
    @staticmethod
    def user_system() -> List[Dict[str, Any]]:
        """Generate user system with auth pattern"""
        return [
            {
                "id": "auth_system",
                "type": "auth",
                "props": {
                    "name": "User Auth",
                    "strategy": "jwt",
                    "roles": ["admin", "user"],
                    "user_table": "users",
                    "user_columns": [
                        {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
                        {"name": "email", "type": "TEXT UNIQUE NOT NULL"},
                        {"name": "password_hash", "type": "TEXT NOT NULL"},
                        {"name": "role", "type": "TEXT DEFAULT 'user'"},
                        {"name": "subscription_plan", "type": "TEXT DEFAULT 'free'"},
                        {"name": "subscription_status", "type": "TEXT DEFAULT 'trial'"},
                        {"name": "trial_end", "type": "TEXT"},
                        {"name": "created_at", "type": "TEXT DEFAULT CURRENT_TIMESTAMP"},
                        {"name": "updated_at", "type": "TEXT DEFAULT CURRENT_TIMESTAMP"}
                    ]
                }
            },
            {
                "id": "api_auth",
                "type": "rest_api",
                "props": {
                    "name": "Auth API",
                    "route": "/api/auth",
                    "method": "GET",
                    "sample_response": '{"message": "Auth endpoints available at /api/auth/register, /api/auth/login"}',
                    "requires_auth": False
                }
            },
            {
                "id": "ui_loginpage",
                "type": "ui_page",
                "props": {
                    "name": "LoginPage",
                    "route": "/login",
                    "title": "Login",
                    "content": "<h1>Login</h1><p>Sign in to your account.</p>",
                    "requires_auth": False
                }
            },
            {
                "id": "ui_registerpage",
                "type": "ui_page",
                "props": {
                    "name": "RegisterPage",
                    "route": "/register",
                    "title": "Register",
                    "content": "<h1>Register</h1><p>Create a new account.</p>",
                    "requires_auth": False
                }
            },
            {
                "id": "ui_profilepage",
                "type": "ui_page",
                "props": {
                    "name": "ProfilePage",
                    "route": "/profile",
                    "title": "Profile",
                    "content": "<h1>Profile</h1><p>Your account information.</p>",
                    "requires_auth": True
                }
            }
        ]
    
    @staticmethod
    def subscription_saas() -> List[Dict[str, Any]]:
        """Generate subscription SaaS pattern"""
        return [
            {
                "id": "auth_system",
                "type": "auth",
                "props": {
                    "name": "User Auth",
                    "strategy": "jwt",
                    "roles": ["admin", "user"],
                    "user_table": "users",
                    "user_columns": [
                        {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
                        {"name": "email", "type": "TEXT UNIQUE NOT NULL"},
                        {"name": "password_hash", "type": "TEXT NOT NULL"},
                        {"name": "role", "type": "TEXT DEFAULT 'user'"},
                        {"name": "subscription_plan", "type": "TEXT DEFAULT 'free'"},
                        {"name": "subscription_status", "type": "TEXT DEFAULT 'trial'"},
                        {"name": "trial_end", "type": "TEXT"},
                        {"name": "created_at", "type": "TEXT DEFAULT CURRENT_TIMESTAMP"},
                        {"name": "updated_at", "type": "TEXT DEFAULT CURRENT_TIMESTAMP"}
                    ]
                }
            },
            {
                "id": "payment_system",
                "type": "payment",
                "props": {
                    "name": "Payments",
                    "provider": "stripe",
                    "plans": [
                        {"name": "Basic", "price": 9.99, "interval": "month"},
                        {"name": "Pro", "price": 29.99, "interval": "month"},
                        {"name": "Enterprise", "price": 99.99, "interval": "month"}
                    ],
                    "trial_days": 14,
                    "currency": "usd"
                }
            },
            {
                "id": "api_payments",
                "type": "rest_api",
                "props": {
                    "name": "Payments API",
                    "route": "/api/payments",
                    "method": "GET",
                    "sample_response": '{"message": "Payment endpoints available at /api/payments/plans, /api/payments/create-checkout"}',
                    "requires_auth": False
                }
            },
            {
                "id": "ui_subscriptionpage",
                "type": "ui_page",
                "props": {
                    "name": "SubscriptionPage",
                    "route": "/subscription",
                    "title": "Subscription",
                    "content": "<h1>Choose Your Plan</h1><p>Select a subscription plan to get started.</p>",
                    "consumes": {"api": "/api/payments/plans", "render": "list"},
                    "requires_auth": True
                }
            },
            {
                "id": "ui_dashboardpage",
                "type": "ui_page",
                "props": {
                    "name": "DashboardPage",
                    "route": "/dashboard",
                    "title": "Dashboard",
                    "content": "<h1>Dashboard</h1><p>Welcome to your dashboard.</p>",
                    "requires_auth": True,
                    "requires_subscription": True
                }
            }
        ]
    
    @staticmethod
    def file_sharing() -> List[Dict[str, Any]]:
        """Generate file sharing pattern"""
        return [
            {
                "id": "auth_system",
                "type": "auth",
                "props": {
                    "name": "User Auth",
                    "strategy": "jwt",
                    "roles": ["admin", "user"],
                    "user_table": "users",
                    "user_columns": [
                        {"name": "id", "type": "INTEGER PRIMARY KEY AUTOINCREMENT"},
                        {"name": "email", "type": "TEXT UNIQUE NOT NULL"},
                        {"name": "password_hash", "type": "TEXT NOT NULL"},
                        {"name": "role", "type": "TEXT DEFAULT 'user'"},
                        {"name": "subscription_plan", "type": "TEXT DEFAULT 'free'"},
                        {"name": "subscription_status", "type": "TEXT DEFAULT 'trial'"},
                        {"name": "trial_end", "type": "TEXT"},
                        {"name": "created_at", "type": "TEXT DEFAULT CURRENT_TIMESTAMP"},
                        {"name": "updated_at", "type": "TEXT DEFAULT CURRENT_TIMESTAMP"}
                    ]
                }
            },
            {
                "id": "file_store",
                "type": "file_store",
                "props": {
                    "name": "FileStore",
                    "provider": "local",
                    "local_path": "./instance/uploads",
                    "allowed_types": ["jpg", "jpeg", "png", "gif", "pdf", "doc", "docx", "txt"],
                    "max_size_mb": 20
                }
            },
            {
                "id": "ui_filespage",
                "type": "ui_page",
                "props": {
                    "name": "FilesPage",
                    "route": "/files",
                    "title": "File Sharing",
                    "content": "<h1>File Sharing</h1><p>Upload and share your files.</p>",
                    "bind_file_store": "filestore",
                    "requires_auth": True
                }
            },
            {
                "id": "ui_gallerypage",
                "type": "ui_page",
                "props": {
                    "name": "GalleryPage",
                    "route": "/gallery",
                    "title": "Photo Gallery",
                    "content": "<h1>Photo Gallery</h1><p>View and share your photos.</p>",
                    "bind_file_store": "filestore",
                    "requires_auth": True
                }
            }
        ]
    
    @staticmethod
    def generic_starter() -> List[Dict[str, Any]]:
        """Generate generic starter page"""
        return [
            {
                "id": "ui_homepage",
                "type": "ui_page",
                "props": {
                    "name": "HomePage",
                    "route": "/home",
                    "title": "Welcome",
                    "content": "<h1>Welcome</h1><p>Describe your app goals to get started.</p>"
                }
            }
        ]

def detect_pattern(goal: str) -> str:
    """Detect which pattern to use based on goal keywords"""
    g = goal.lower()
    
    if "task" in g:
        return "task_tracker"
    elif "blog" in g or "post" in g:
        return "blog"
    elif "contact" in g or "message" in g:
        return "contact_form"
    elif "upload" in g or "file" in g or "media" in g or "photo" in g or "document" in g or "share" in g:
        return "file_sharing"
    elif "subscription" in g or "payment" in g or "stripe" in g or "saas" in g or "plan" in g:
        return "subscription_saas"
    elif "login" in g or "user" in g or "auth" in g or "register" in g:
        return "user_system"
    else:
        return "generic_starter"

def get_pattern_nodes(pattern: str) -> List[Dict[str, Any]]:
    """Get nodes for a specific pattern"""
    if pattern == "task_tracker":
        return HeuristicPatterns.task_tracker()
    elif pattern == "blog":
        return HeuristicPatterns.blog()
    elif pattern == "contact_form":
        return HeuristicPatterns.contact_form()
    elif pattern == "user_system":
        return HeuristicPatterns.user_system()
    elif pattern == "subscription_saas":
        return HeuristicPatterns.subscription_saas()
    elif pattern == "file_sharing":
        return HeuristicPatterns.file_sharing()
    else:
        return HeuristicPatterns.generic_starter()
