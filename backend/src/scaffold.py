"""
Scaffold System - Generate application files from templates
"""
import os
import json
import logging
import subprocess
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

# Configuration
GENERATED_ROOT = os.environ.get('GENERATED_ROOT', './generated')

def get_build_path(build_id: str) -> str:
    """Get the path for a specific build"""
    return os.path.join(GENERATED_ROOT, build_id)

def ensure_build_directory(build_id: str) -> str:
    """Ensure build directory exists and return path"""
    build_path = get_build_path(build_id)
    os.makedirs(build_path, exist_ok=True)
    return build_path

def scaffold_crm_flagship(build_id: str, build_data: Dict[str, Any]) -> Dict[str, str]:
    """Scaffold CRM Flagship template files"""
    build_path = ensure_build_directory(build_id)
    
    # Create backend structure
    backend_path = os.path.join(build_path, 'backend')
    os.makedirs(backend_path, exist_ok=True)
    os.makedirs(os.path.join(backend_path, 'routers'), exist_ok=True)
    os.makedirs(os.path.join(backend_path, 'data'), exist_ok=True)
    
    # Create frontend structure
    frontend_path = os.path.join(build_path, 'frontend')
    os.makedirs(frontend_path, exist_ok=True)
    os.makedirs(os.path.join(frontend_path, 'app'), exist_ok=True)
    os.makedirs(os.path.join(frontend_path, 'app', 'components'), exist_ok=True)
    os.makedirs(os.path.join(frontend_path, 'app', 'lib'), exist_ok=True)
    
    # Generate backend files
    _create_backend_app_py(backend_path, build_data)
    _create_backend_db_py(backend_path, build_id)
    _create_backend_seed_py(backend_path)
    _create_backend_requirements_txt(backend_path)
    _create_backend_routers(backend_path)
    
    # Generate frontend files
    _create_frontend_package_json(frontend_path, build_id)
    _create_frontend_next_config(frontend_path)
    _create_frontend_tailwind_config(frontend_path)
    _create_frontend_postcss_config(frontend_path)
    _create_frontend_globals_css(frontend_path)
    _create_frontend_layout_tsx(frontend_path)
    _create_frontend_api_ts(frontend_path)
    _create_frontend_components(frontend_path)
    _create_frontend_pages(frontend_path)
    _create_frontend_readme(frontend_path)
    
    # Create manifest
    _create_manifest(build_path, build_id, build_data)
    
    return {
        'artifact_url': f'/serve/{build_id}',
        'launch_url': f'/serve/{build_id}'
    }

def scaffold_tasks_template(build_id: str, build_data: Dict[str, Any]) -> Dict[str, str]:
    """Scaffold Tasks template files"""
    build_path = ensure_build_directory(build_id)
    
    # Create backend structure
    backend_path = os.path.join(build_path, 'backend')
    os.makedirs(backend_path, exist_ok=True)
    os.makedirs(os.path.join(backend_path, 'data'), exist_ok=True)
    
    # Create frontend structure
    frontend_path = os.path.join(build_path, 'frontend')
    os.makedirs(frontend_path, exist_ok=True)
    os.makedirs(os.path.join(frontend_path, 'src'), exist_ok=True)
    os.makedirs(os.path.join(frontend_path, 'dist'), exist_ok=True)
    
    # Generate backend files
    _create_tasks_backend_app_py(backend_path, build_data)
    _create_tasks_backend_db_py(backend_path, build_id)
    _create_tasks_backend_requirements_txt(backend_path)
    
    # Generate frontend files
    _create_tasks_frontend_package_json(frontend_path)
    _create_tasks_frontend_index_html(frontend_path)
    _create_tasks_frontend_main_jsx(frontend_path)
    
    # Create manifest
    _create_manifest(build_path, build_id, build_data)
    
    return {
        'artifact_url': f'/serve/{build_id}',
        'launch_url': f'/serve/{build_id}'
    }

def scaffold_blank_template(build_id: str, build_data: Dict[str, Any]) -> Dict[str, str]:
    """Scaffold Blank template files"""
    build_path = ensure_build_directory(build_id)
    
    # Create frontend structure
    frontend_path = os.path.join(build_path, 'frontend')
    os.makedirs(frontend_path, exist_ok=True)
    os.makedirs(os.path.join(frontend_path, 'dist'), exist_ok=True)
    
    # Generate simple frontend files
    _create_blank_frontend_index_html(frontend_path, build_data)
    
    # Create manifest
    _create_manifest(build_path, build_id, build_data)
    
    return {
        'artifact_url': f'/serve/{build_id}',
        'launch_url': f'/serve/{build_id}'
    }

def _create_backend_app_py(backend_path: str, build_data: Dict[str, Any]):
    """Create FastAPI app.py for CRM Flagship"""
    app_content = '''from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import uvicorn
import os
from routers import accounts, contacts, deals, pipelines, activities
from db import check_db_exists
from seed import initialize_database

app = FastAPI(title="CRM Flagship", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    """Initialize database on startup if it doesn't exist"""
    if not check_db_exists():
        print("Database not found, initializing with seed data...")
        initialize_database()
    else:
        print("Database found, skipping initialization")

# Include routers
app.include_router(accounts.router, prefix="/api/accounts", tags=["accounts"])
app.include_router(contacts.router, prefix="/api/contacts", tags=["contacts"])
app.include_router(deals.router, prefix="/api/deals", tags=["deals"])
app.include_router(pipelines.router, prefix="/api/pipelines", tags=["pipelines"])
app.include_router(activities.router, prefix="/api/activities", tags=["activities"])

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "CRM Flagship"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    
    with open(os.path.join(backend_path, 'app.py'), 'w') as f:
        f.write(app_content)

def _create_backend_db_py(backend_path: str, build_id: str):
    """Create database module for CRM Flagship"""
    db_content = f'''import sqlite3
import os
from pathlib import Path

DB_PATH = "data/app.db"

def ensure_db_directory():
    """Ensure the data directory exists"""
    db_dir = os.path.dirname(DB_PATH)
    if not os.path.exists(db_dir):
        os.makedirs(db_dir, exist_ok=True)

def get_db():
    """Get database connection"""
    ensure_db_directory()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize database tables"""
    ensure_db_directory()
    conn = get_db()
    
    # Create tables
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            industry TEXT,
            website TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS contacts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            title TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id)
        );
        
        CREATE TABLE IF NOT EXISTS deals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER,
            contact_id INTEGER,
            title TEXT NOT NULL,
            amount REAL,
            stage TEXT DEFAULT 'prospecting',
            close_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts (id),
            FOREIGN KEY (contact_id) REFERENCES contacts (id)
        );
        
        CREATE TABLE IF NOT EXISTS pipelines (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        CREATE TABLE IF NOT EXISTS activities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            deal_id INTEGER,
            contact_id INTEGER,
            type TEXT NOT NULL,
            subject TEXT NOT NULL,
            description TEXT,
            due_date DATE,
            completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (deal_id) REFERENCES deals (id),
            FOREIGN KEY (contact_id) REFERENCES contacts (id)
        );
    """)
    
    conn.commit()
    conn.close()

def check_db_exists():
    """Check if database file exists"""
    return os.path.exists(DB_PATH)

if __name__ == "__main__":
    init_db()
'''
    
    with open(os.path.join(backend_path, 'db.py'), 'w') as f:
        f.write(db_content)

def _create_backend_seed_py(backend_path: str):
    """Create seed data for CRM Flagship"""
    seed_content = '''import sqlite3
import os
from pathlib import Path
from db import get_db, init_db, DB_PATH

def create_schema():
    """Create database schema"""
    init_db()

def seed_data():
    """Seed database with demo data"""
    # Ensure schema exists
    create_schema()
    
    conn = get_db()
    
    # Insert demo accounts
    conn.executemany("""
        INSERT OR IGNORE INTO accounts (name, industry, website)
        VALUES (?, ?, ?)
    """, [
        ("Acme Corp", "Technology", "https://acme.com"),
        ("Global Industries", "Manufacturing", "https://global.com"),
        ("StartupXYZ", "SaaS", "https://startupxyz.com"),
        ("Enterprise Solutions", "Consulting", "https://enterprise.com")
    ])
    
    # Insert demo contacts
    conn.executemany("""
        INSERT OR IGNORE INTO contacts (account_id, first_name, last_name, email, title)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (1, "John", "Smith", "john@acme.com", "CEO"),
        (1, "Jane", "Doe", "jane@acme.com", "CTO"),
        (2, "Bob", "Johnson", "bob@global.com", "VP Sales"),
        (3, "Alice", "Brown", "alice@startupxyz.com", "Founder")
    ])
    
    # Insert demo deals
    conn.executemany("""
        INSERT OR IGNORE INTO deals (account_id, contact_id, title, amount, stage)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (1, 1, "Enterprise License", 50000.0, "negotiation"),
        (2, 3, "Annual Contract", 25000.0, "prospecting"),
        (3, 4, "Seed Investment", 100000.0, "closed_won")
    ])
    
    # Insert demo pipelines
    conn.executemany("""
        INSERT OR IGNORE INTO pipelines (name, description)
        VALUES (?, ?)
    """, [
        ("Sales Pipeline", "Standard sales process"),
        ("Enterprise Pipeline", "Enterprise sales process")
    ])
    
    # Insert demo activities
    conn.executemany("""
        INSERT OR IGNORE INTO activities (deal_id, contact_id, type, subject, description)
        VALUES (?, ?, ?, ?, ?)
    """, [
        (1, 1, "call", "Follow-up Call", "Discuss contract terms"),
        (2, 3, "meeting", "Product Demo", "Show product features"),
        (3, 4, "email", "Contract Review", "Review investment terms")
    ])
    
    conn.commit()
    conn.close()
    print(f"Database initialized with seed data at {DB_PATH}")

def initialize_database():
    """Initialize database with schema and seed data"""
    seed_data()

if __name__ == "__main__":
    initialize_database()
'''
    
    with open(os.path.join(backend_path, 'seed.py'), 'w') as f:
        f.write(seed_content)

def _create_backend_requirements_txt(backend_path: str):
    """Create requirements.txt for backend"""
    requirements = '''fastapi==0.104.1
uvicorn==0.24.0
sqlite3
'''
    
    with open(os.path.join(backend_path, 'requirements.txt'), 'w') as f:
        f.write(requirements)

def _create_backend_routers(backend_path: str):
    """Create router files for CRM modules"""
    routers_path = os.path.join(backend_path, 'routers')
    
    # Accounts router
    accounts_content = '''from fastapi import APIRouter, HTTPException
from db import get_db
from typing import List, Dict, Any

router = APIRouter()

@router.get("/")
async def list_accounts():
    conn = get_db()
    cursor = conn.execute("SELECT * FROM accounts ORDER BY created_at DESC")
    accounts = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return accounts

@router.get("/{account_id}")
async def get_account(account_id: int):
    conn = get_db()
    cursor = conn.execute("SELECT * FROM accounts WHERE id = ?", (account_id,))
    account = cursor.fetchone()
    conn.close()
    
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return dict(account)

@router.post("/")
async def create_account(account: Dict[str, Any]):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO accounts (name, industry, website) VALUES (?, ?, ?)",
        (account.get('name'), account.get('industry'), account.get('website'))
    )
    account_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    return {"id": account_id, **account}
'''
    
    with open(os.path.join(routers_path, 'accounts.py'), 'w') as f:
        f.write(accounts_content)
    
    # Similar routers for other modules (simplified)
    for module in ['contacts', 'deals', 'pipelines', 'activities']:
        module_content = f'''from fastapi import APIRouter
from db import get_db

router = APIRouter()

@router.get("/")
async def list_{module}():
    conn = get_db()
    cursor = conn.execute("SELECT * FROM {module} ORDER BY created_at DESC")
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return items

@router.get("/{{item_id}}")
async def get_{module[:-1]}(item_id: int):
    conn = get_db()
    cursor = conn.execute("SELECT * FROM {module} WHERE id = ?", (item_id,))
    item = cursor.fetchone()
    conn.close()
    return dict(item) if item else {{"error": "Not found"}}
'''
        
        with open(os.path.join(routers_path, f'{module}.py'), 'w') as f:
            f.write(module_content)

def _create_frontend_package_json(frontend_path: str, build_id: str):
    """Create package.json for Next.js frontend"""
    package_json = {
        "name": "crm-flagship-frontend",
        "version": "1.0.0",
        "private": True,
        "scripts": {
            "dev": "next dev",
            "build": "next build",
            "start": "next start",
            "lint": "next lint"
        },
        "dependencies": {
            "next": "14.0.0",
            "react": "^18.2.0",
            "react-dom": "^18.2.0",
            "lucide-react": "^0.294.0",
            "@radix-ui/react-slot": "^1.0.2",
            "class-variance-authority": "^0.7.0",
            "clsx": "^2.0.0",
            "tailwind-merge": "^2.0.0"
        },
        "devDependencies": {
            "@types/node": "^20.8.0",
            "@types/react": "^18.2.0",
            "@types/react-dom": "^18.2.0",
            "autoprefixer": "^10.4.16",
            "eslint": "^8.52.0",
            "eslint-config-next": "14.0.0",
            "postcss": "^8.4.31",
            "tailwindcss": "^3.3.5",
            "typescript": "^5.2.2"
        }
    }
    
    with open(os.path.join(frontend_path, 'package.json'), 'w') as f:
        json.dump(package_json, f, indent=2)
    
    # Create .sbhrc.json for build_id
    sbhrc = {"build_id": build_id}
    with open(os.path.join(frontend_path, '.sbhrc.json'), 'w') as f:
        json.dump(sbhrc, f, indent=2)

def _create_frontend_next_config(frontend_path: str):
    """Create next.config.mjs for Next.js frontend"""
    next_config = '''/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  experimental: {
    appDir: true,
  },
}

export default nextConfig
'''
    
    with open(os.path.join(frontend_path, 'next.config.mjs'), 'w') as f:
        f.write(next_config)

def _create_frontend_tailwind_config(frontend_path: str):
    """Create tailwind.config.js for Next.js frontend"""
    tailwind_config = '''/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    './pages/**/*.{js,ts,jsx,tsx,mdx}',
    './components/**/*.{js,ts,jsx,tsx,mdx}',
    './app/**/*.{js,ts,jsx,tsx,mdx}',
  ],
  theme: {
    extend: {
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
    },
  },
  plugins: [],
}
'''
    
    with open(os.path.join(frontend_path, 'tailwind.config.js'), 'w') as f:
        f.write(tailwind_config)

def _create_frontend_postcss_config(frontend_path: str):
    """Create postcss.config.js for Next.js frontend"""
    postcss_config = '''module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}
'''
    
    with open(os.path.join(frontend_path, 'postcss.config.js'), 'w') as f:
        f.write(postcss_config)

def _create_frontend_globals_css(frontend_path: str):
    """Create globals.css for Next.js frontend"""
    globals_css = '''@tailwind base;
@tailwind components;
@tailwind utilities;

@layer base {
  :root {
    --background: 0 0% 100%;
    --foreground: 222.2 84% 4.9%;
    --card: 0 0% 100%;
    --card-foreground: 222.2 84% 4.9%;
    --popover: 0 0% 100%;
    --popover-foreground: 222.2 84% 4.9%;
    --primary: 222.2 47.4% 11.2%;
    --primary-foreground: 210 40% 98%;
    --secondary: 210 40% 96%;
    --secondary-foreground: 222.2 84% 4.9%;
    --muted: 210 40% 96%;
    --muted-foreground: 215.4 16.3% 46.9%;
    --accent: 210 40% 96%;
    --accent-foreground: 222.2 84% 4.9%;
    --destructive: 0 84.2% 60.2%;
    --destructive-foreground: 210 40% 98%;
    --border: 214.3 31.8% 91.4%;
    --input: 214.3 31.8% 91.4%;
    --ring: 222.2 84% 4.9%;
    --radius: 0.5rem;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}
'''
    
    with open(os.path.join(frontend_path, 'app', 'globals.css'), 'w') as f:
        f.write(globals_css)

def _create_frontend_layout_tsx(frontend_path: str):
    """Create layout.tsx for Next.js frontend"""
    layout_tsx = '''import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Nav } from './components/Nav'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'CRM Flagship',
  description: 'Production-grade CRM application',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-gray-50">
          <Nav />
          <main className="container mx-auto px-4 py-8">
            {children}
          </main>
        </div>
      </body>
    </html>
  )
}
'''
    
    with open(os.path.join(frontend_path, 'app', 'layout.tsx'), 'w') as f:
        f.write(layout_tsx)

def _create_frontend_api_ts(frontend_path: str):
    """Create lib/api.ts for Next.js frontend"""
    api_ts = '''// lib/api.ts
let base = '';
if (typeof window !== 'undefined') {
  // Browser: infer from current path /serve/<id>/
  const m = window.location.pathname.match(/^\/serve\/([^/]+)/);
  base = m ? `/serve/${m[1]}` : '';
} else {
  // Server components (Next): read from .sbhrc.json if present
  try {
    const cfg = require('../.sbhrc.json');
    if (cfg?.build_id) base = `/serve/${cfg.build_id}`;
  } catch {}
}
const API_BASE = `${base}/api`;

export async function apiGet<T>(path: string): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, { cache: 'no-store' });
  if (!res.ok) throw new Error(`GET ${path} ${res.status}`);
  return res.json();
}

// Convenience wrappers:
export const getHealth     = () => apiGet<{status:string,service:string}>(`/health`);
export const getAccounts   = () => apiGet<any[]>(`/accounts/`);
export const getContacts   = () => apiGet<any[]>(`/contacts/`);
export const getDeals      = () => apiGet<any[]>(`/deals/`);
export const getPipelines  = () => apiGet<any[]>(`/pipelines/`);
export const getActivities = () => apiGet<any[]>(`/activities/`);
'''
    
    with open(os.path.join(frontend_path, 'app', 'lib', 'api.ts'), 'w') as f:
        f.write(api_ts)

def _create_frontend_components(frontend_path: str):
    """Create components for Next.js frontend"""
    # Create components directory
    components_path = os.path.join(frontend_path, 'app', 'components')
    os.makedirs(components_path, exist_ok=True)
    
    # Nav.tsx
    nav_tsx = ''''use client'

import { getHealth } from '../lib/api'
import { useState, useEffect } from 'react'
import { Activity } from 'lucide-react'

export function Nav() {
  const [health, setHealth] = useState<{status: string, service: string} | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const checkHealth = async () => {
      try {
        const healthData = await getHealth()
        setHealth(healthData)
      } catch (error) {
        console.error('Health check failed:', error)
      } finally {
        setLoading(false)
      }
    }

    checkHealth()
    const interval = setInterval(checkHealth, 30000) // Check every 30 seconds
    return () => clearInterval(interval)
  }, [])

  return (
    <nav className="bg-white shadow-sm border-b">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-8">
            <div className="flex items-center space-x-2">
              <Activity className="w-6 h-6 text-blue-600" />
              <span className="text-xl font-bold text-gray-900">CRM Flagship</span>
            </div>
            
            <div className="hidden md:flex space-x-6">
              <a href="/" className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium">
                Dashboard
              </a>
              <a href="/accounts" className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium">
                Accounts
              </a>
              <a href="/contacts" className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium">
                Contacts
              </a>
              <a href="/deals" className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium">
                Deals
              </a>
              <a href="/activities" className="text-gray-700 hover:text-blue-600 px-3 py-2 rounded-md text-sm font-medium">
                Activities
              </a>
            </div>
          </div>
          
          <div className="flex items-center space-x-2">
            <div className={`w-2 h-2 rounded-full ${health?.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm text-gray-600">
              {loading ? 'Checking...' : (health?.status === 'healthy' ? 'Healthy' : 'Unreachable')}
            </span>
          </div>
        </div>
      </div>
    </nav>
  )
}
'''
    
    with open(os.path.join(components_path, 'Nav.tsx'), 'w') as f:
        f.write(nav_tsx)
    
    # Card.tsx
    card_tsx = '''import { cn } from '../lib/utils'

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {}

export function Card({ className, ...props }: CardProps) {
  return (
    <div
      className={cn(
        "rounded-lg border bg-card text-card-foreground shadow-sm",
        className
      )}
      {...props}
    />
  )
}
'''
    
    with open(os.path.join(components_path, 'Card.tsx'), 'w') as f:
        f.write(card_tsx)
    
    # Pill.tsx
    pill_tsx = '''import { cn } from '../lib/utils'

interface PillProps extends React.HTMLAttributes<HTMLSpanElement> {
  variant?: 'default' | 'secondary' | 'destructive' | 'outline'
}

export function Pill({ className, variant = 'default', ...props }: PillProps) {
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium",
        {
          'bg-primary text-primary-foreground': variant === 'default',
          'bg-secondary text-secondary-foreground': variant === 'secondary',
          'bg-destructive text-destructive-foreground': variant === 'destructive',
          'border border-input bg-background': variant === 'outline',
        },
        className
      )}
      {...props}
    />
  )
}
'''
    
    with open(os.path.join(components_path, 'Pill.tsx'), 'w') as f:
        f.write(pill_tsx)
    
    # utils.ts
    utils_ts = '''import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}
'''
    
    with open(os.path.join(components_path, '..', 'lib', 'utils.ts'), 'w') as f:
        f.write(utils_ts)

def _create_frontend_pages(frontend_path: str):
    """Create page components for Next.js frontend"""
    # Create pages directory structure
    pages_dirs = [
        'accounts',
        'accounts/[id]',
        'contacts',
        'contacts/[id]',
        'deals',
        'activities'
    ]
    
    for page_dir in pages_dirs:
        os.makedirs(os.path.join(frontend_path, 'app', page_dir), exist_ok=True)
    
    # Dashboard page
    page_tsx = '''import { getHealth } from './lib/api'
import { Card } from './components/Card'
import { Activity, Users, Building2, Target, Calendar } from 'lucide-react'

export default async function DashboardPage() {
  let health = null
  try {
    health = await getHealth()
  } catch (error) {
    console.error('Health check failed:', error)
  }

  const quickLinks = [
    {
      title: 'Accounts',
      description: 'Manage company accounts',
      href: '/accounts',
      icon: Building2,
      count: 'View all'
    },
    {
      title: 'Contacts',
      description: 'Manage contact information',
      href: '/contacts',
      icon: Users,
      count: 'View all'
    },
    {
      title: 'Deals',
      description: 'Track sales opportunities',
      href: '/deals',
      icon: Target,
      count: 'View all'
    },
    {
      title: 'Activities',
      description: 'View recent activities',
      href: '/activities',
      icon: Calendar,
      count: 'View all'
    }
  ]

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-2 text-gray-600">Welcome to your CRM dashboard</p>
      </div>

      {/* Health Status */}
      <Card>
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-lg font-semibold text-gray-900">System Status</h2>
            <p className="text-sm text-gray-600">Backend API health</p>
          </div>
          <div className="flex items-center space-x-2">
            <div className={`w-3 h-3 rounded-full ${health?.status === 'healthy' ? 'bg-green-500' : 'bg-red-500'}`} />
            <span className="text-sm font-medium">
              {health?.status === 'healthy' ? 'Healthy' : 'Unreachable'}
            </span>
          </div>
        </div>
      </Card>

      {/* Quick Links */}
      <div>
        <h2 className="text-xl font-semibold text-gray-900 mb-4">Quick Links</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {quickLinks.map((link) => (
            <Card key={link.href} className="hover:shadow-md transition-shadow">
              <a href={link.href} className="block">
                <div className="flex items-center space-x-3">
                  <link.icon className="w-6 h-6 text-blue-600" />
                  <div>
                    <h3 className="font-medium text-gray-900">{link.title}</h3>
                    <p className="text-sm text-gray-600">{link.description}</p>
                  </div>
                </div>
                <div className="mt-3 text-sm text-blue-600">{link.count} →</div>
              </a>
            </Card>
          ))}
        </div>
      </div>
    </div>
  )
}
'''
    
    with open(os.path.join(frontend_path, 'app', 'page.tsx'), 'w') as f:
        f.write(page_tsx)
    
    # Accounts page
    accounts_page = '''import { getAccounts } from '../lib/api'
import { Card } from '../components/Card'
import { Building2, Mail, Globe } from 'lucide-react'

export default async function AccountsPage() {
  let accounts = []
  try {
    accounts = await getAccounts()
  } catch (error) {
    console.error('Failed to fetch accounts:', error)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Accounts</h1>
        <p className="mt-2 text-gray-600">Manage your company accounts</p>
      </div>

      <div className="grid gap-4">
        {accounts.map((account) => (
          <Card key={account.id} className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-blue-100 rounded-lg flex items-center justify-center">
                  <Building2 className="w-5 h-5 text-blue-600" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">
                    <a href={`/accounts/${account.id}`} className="hover:text-blue-600">
                      {account.name}
                    </a>
                  </h3>
                  <p className="text-sm text-gray-600">{account.industry}</p>
                </div>
              </div>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                {account.website && (
                  <a href={account.website} className="flex items-center space-x-1 hover:text-blue-600">
                    <Globe className="w-4 h-4" />
                    <span>Website</span>
                  </a>
                )}
                <span className="flex items-center space-x-1">
                  <Mail className="w-4 h-4" />
                  <span>Created {new Date(account.created_at).toLocaleDateString()}</span>
                </span>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {accounts.length === 0 && (
        <Card className="p-8 text-center">
          <Building2 className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No accounts found</h3>
          <p className="text-gray-600">Get started by creating your first account.</p>
        </Card>
      )}
    </div>
  )
}
'''
    
    with open(os.path.join(frontend_path, 'app', 'accounts', 'page.tsx'), 'w') as f:
        f.write(accounts_page)
    
    # Account detail page
    account_detail_page = '''import { getAccounts } from '../../lib/api'
import { Card } from '../../components/Card'
import { Building2, Mail, Globe, Calendar } from 'lucide-react'

export default async function AccountDetailPage({ params }: { params: { id: string } }) {
  let accounts = []
  let account = null
  
  try {
    accounts = await getAccounts()
    account = accounts.find(a => a.id.toString() === params.id)
  } catch (error) {
    console.error('Failed to fetch account:', error)
  }

  if (!account) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Account Not Found</h1>
          <p className="mt-2 text-gray-600">The requested account could not be found.</p>
        </div>
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div>
        <a href="/accounts" className="text-blue-600 hover:text-blue-800 mb-4 inline-block">
          ← Back to Accounts
        </a>
        <h1 className="text-3xl font-bold text-gray-900">{account.name}</h1>
        <p className="mt-2 text-gray-600">Account details and information</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Account Information</h2>
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <Building2 className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900">Industry</p>
                <p className="text-sm text-gray-600">{account.industry}</p>
              </div>
            </div>
            {account.website && (
              <div className="flex items-center space-x-3">
                <Globe className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Website</p>
                  <a href={account.website} className="text-sm text-blue-600 hover:text-blue-800">
                    {account.website}
                  </a>
                </div>
              </div>
            )}
            <div className="flex items-center space-x-3">
              <Calendar className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900">Created</p>
                <p className="text-sm text-gray-600">
                  {new Date(account.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <a href="/contacts" className="block w-full text-left p-3 rounded-lg border hover:bg-gray-50 transition-colors">
              <div className="flex items-center space-x-3">
                <Mail className="w-5 h-5 text-blue-600" />
                <span className="text-sm font-medium text-gray-900">View Contacts</span>
              </div>
            </a>
            <a href="/deals" className="block w-full text-left p-3 rounded-lg border hover:bg-gray-50 transition-colors">
              <div className="flex items-center space-x-3">
                <Building2 className="w-5 h-5 text-green-600" />
                <span className="text-sm font-medium text-gray-900">View Deals</span>
              </div>
            </a>
          </div>
        </Card>
      </div>
    </div>
  )
}
'''
    
    with open(os.path.join(frontend_path, 'app', 'accounts', '[id]', 'page.tsx'), 'w') as f:
        f.write(account_detail_page)
    
    # Contacts page
    contacts_page = '''import { getContacts, getAccounts } from '../lib/api'
import { Card } from '../components/Card'
import { User, Mail, Phone, Building2 } from 'lucide-react'

export default async function ContactsPage() {
  let contacts = []
  let accounts = []
  
  try {
    [contacts, accounts] = await Promise.all([getContacts(), getAccounts()])
  } catch (error) {
    console.error('Failed to fetch contacts:', error)
  }

  // Create accounts lookup
  const accountsMap = new Map(accounts.map(acc => [acc.id, acc]))

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Contacts</h1>
        <p className="mt-2 text-gray-600">Manage your contact information</p>
      </div>

      <div className="grid gap-4">
        {contacts.map((contact) => {
          const account = accountsMap.get(contact.account_id)
          return (
            <Card key={contact.id} className="p-6">
              <div className="flex items-center justify-between">
                <div className="flex items-center space-x-4">
                  <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
                    <User className="w-5 h-5 text-green-600" />
                  </div>
                  <div>
                    <h3 className="text-lg font-medium text-gray-900">
                      <a href={`/contacts/${contact.id}`} className="hover:text-blue-600">
                        {contact.first_name} {contact.last_name}
                      </a>
                    </h3>
                    <p className="text-sm text-gray-600">{contact.email}</p>
                    {account && (
                      <p className="text-sm text-gray-500">
                        {account.name}
                      </p>
                    )}
                  </div>
                </div>
                <div className="flex items-center space-x-4 text-sm text-gray-500">
                  {contact.phone && (
                    <span className="flex items-center space-x-1">
                      <Phone className="w-4 h-4" />
                      <span>{contact.phone}</span>
                    </span>
                  )}
                  <span className="flex items-center space-x-1">
                    <Mail className="w-4 h-4" />
                    <span>{contact.email}</span>
                  </span>
                </div>
              </div>
            </Card>
          )
        })}
      </div>

      {contacts.length === 0 && (
        <Card className="p-8 text-center">
          <User className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No contacts found</h3>
          <p className="text-gray-600">Get started by creating your first contact.</p>
        </Card>
      )}
    </div>
  )
}
'''
    
    with open(os.path.join(frontend_path, 'app', 'contacts', 'page.tsx'), 'w') as f:
        f.write(contacts_page)
    
    # Contact detail page
    contact_detail_page = '''import { getContacts, getAccounts } from '../../lib/api'
import { Card } from '../../components/Card'
import { User, Mail, Phone, Building2, Calendar } from 'lucide-react'

export default async function ContactDetailPage({ params }: { params: { id: string } }) {
  let contacts = []
  let accounts = []
  let contact = null
  
  try {
    [contacts, accounts] = await Promise.all([getContacts(), getAccounts()])
    contact = contacts.find(c => c.id.toString() === params.id)
  } catch (error) {
    console.error('Failed to fetch contact:', error)
  }

  if (!contact) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Contact Not Found</h1>
          <p className="mt-2 text-gray-600">The requested contact could not be found.</p>
        </div>
      </div>
    )
  }

  const account = accounts.find(a => a.id === contact.account_id)

  return (
    <div className="space-y-6">
      <div>
        <a href="/contacts" className="text-blue-600 hover:text-blue-800 mb-4 inline-block">
          ← Back to Contacts
        </a>
        <h1 className="text-3xl font-bold text-gray-900">
          {contact.first_name} {contact.last_name}
        </h1>
        <p className="mt-2 text-gray-600">Contact details and information</p>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Contact Information</h2>
          <div className="space-y-4">
            <div className="flex items-center space-x-3">
              <Mail className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900">Email</p>
                <a href={`mailto:${contact.email}`} className="text-sm text-blue-600 hover:text-blue-800">
                  {contact.email}
                </a>
              </div>
            </div>
            {contact.phone && (
              <div className="flex items-center space-x-3">
                <Phone className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Phone</p>
                  <a href={`tel:${contact.phone}`} className="text-sm text-blue-600 hover:text-blue-800">
                    {contact.phone}
                  </a>
                </div>
              </div>
            )}
            {account && (
              <div className="flex items-center space-x-3">
                <Building2 className="w-5 h-5 text-gray-400" />
                <div>
                  <p className="text-sm font-medium text-gray-900">Account</p>
                  <a href={`/accounts/${account.id}`} className="text-sm text-blue-600 hover:text-blue-800">
                    {account.name}
                  </a>
                </div>
              </div>
            )}
            <div className="flex items-center space-x-3">
              <Calendar className="w-5 h-5 text-gray-400" />
              <div>
                <p className="text-sm font-medium text-gray-900">Created</p>
                <p className="text-sm text-gray-600">
                  {new Date(contact.created_at).toLocaleDateString()}
                </p>
              </div>
            </div>
          </div>
        </Card>

        <Card className="p-6">
          <h2 className="text-lg font-semibold text-gray-900 mb-4">Quick Actions</h2>
          <div className="space-y-3">
            <a href="/deals" className="block w-full text-left p-3 rounded-lg border hover:bg-gray-50 transition-colors">
              <div className="flex items-center space-x-3">
                <Building2 className="w-5 h-5 text-green-600" />
                <span className="text-sm font-medium text-gray-900">View Deals</span>
              </div>
            </a>
            <a href="/activities" className="block w-full text-left p-3 rounded-lg border hover:bg-gray-50 transition-colors">
              <div className="flex items-center space-x-3">
                <Calendar className="w-5 h-5 text-blue-600" />
                <span className="text-sm font-medium text-gray-900">View Activities</span>
              </div>
            </a>
          </div>
        </Card>
      </div>
    </div>
  )
}
'''
    
    with open(os.path.join(frontend_path, 'app', 'contacts', '[id]', 'page.tsx'), 'w') as f:
        f.write(contact_detail_page)
    
    # Deals page
    deals_page = '''import { getDeals } from '../lib/api'
import { Card } from '../components/Card'
import { Pill } from '../components/Pill'
import { Target, DollarSign, Calendar } from 'lucide-react'

export default async function DealsPage() {
  let deals = []
  
  try {
    deals = await getDeals()
  } catch (error) {
    console.error('Failed to fetch deals:', error)
  }

  const getStageColor = (stage: string) => {
    switch (stage) {
      case 'prospecting':
        return 'bg-blue-100 text-blue-800'
      case 'negotiation':
        return 'bg-yellow-100 text-yellow-800'
      case 'closed_won':
        return 'bg-green-100 text-green-800'
      case 'closed_lost':
        return 'bg-red-100 text-red-800'
      default:
        return 'bg-gray-100 text-gray-800'
    }
  }

  const formatCurrency = (amount: number) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
    }).format(amount)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Deals</h1>
        <p className="mt-2 text-gray-600">Track your sales opportunities</p>
      </div>

      <div className="grid gap-4">
        {deals.map((deal) => (
          <Card key={deal.id} className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-purple-100 rounded-lg flex items-center justify-center">
                  <Target className="w-5 h-5 text-purple-600" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">{deal.name}</h3>
                  <p className="text-sm text-gray-600">{deal.description}</p>
                </div>
              </div>
              <div className="flex items-center space-x-4">
                <div className="text-right">
                  <p className="text-sm font-medium text-gray-900">
                    {formatCurrency(deal.amount)}
                  </p>
                  <p className="text-sm text-gray-600">Value</p>
                </div>
                <Pill className={getStageColor(deal.stage)}>
                  {deal.stage.replace('_', ' ').toUpperCase()}
                </Pill>
                <div className="text-right text-sm text-gray-500">
                  <div className="flex items-center space-x-1">
                    <Calendar className="w-4 h-4" />
                    <span>{new Date(deal.created_at).toLocaleDateString()}</span>
                  </div>
                </div>
              </div>
            </div>
          </Card>
        ))}
      </div>

      {deals.length === 0 && (
        <Card className="p-8 text-center">
          <Target className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No deals found</h3>
          <p className="text-gray-600">Get started by creating your first deal.</p>
        </Card>
      )}
    </div>
  )
}
'''
    
    with open(os.path.join(frontend_path, 'app', 'deals', 'page.tsx'), 'w') as f:
        f.write(deals_page)
    
    # Activities page
    activities_page = '''import { getActivities } from '../lib/api'
import { Card } from '../components/Card'
import { Calendar, Clock, User } from 'lucide-react'

export default async function ActivitiesPage() {
  let activities = []
  
  try {
    activities = await getActivities()
  } catch (error) {
    console.error('Failed to fetch activities:', error)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Activities</h1>
        <p className="mt-2 text-gray-600">View recent activities and tasks</p>
      </div>

      <div className="grid gap-4">
        {activities.map((activity) => (
          <Card key={activity.id} className="p-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-4">
                <div className="w-10 h-10 bg-orange-100 rounded-lg flex items-center justify-center">
                  <Calendar className="w-5 h-5 text-orange-600" />
                </div>
                <div>
                  <h3 className="text-lg font-medium text-gray-900">{activity.title}</h3>
                  <p className="text-sm text-gray-600">{activity.description}</p>
                  <p className="text-sm text-gray-500">Type: {activity.type}</p>
                </div>
              </div>
              <div className="flex items-center space-x-4 text-sm text-gray-500">
                <div className="flex items-center space-x-1">
                  <Clock className="w-4 h-4" />
                  <span>{new Date(activity.created_at).toLocaleDateString()}</span>
                </div>
                {activity.assigned_to && (
                  <div className="flex items-center space-x-1">
                    <User className="w-4 h-4" />
                    <span>{activity.assigned_to}</span>
                  </div>
                )}
              </div>
            </div>
          </Card>
        ))}
      </div>

      {activities.length === 0 && (
        <Card className="p-8 text-center">
          <Calendar className="w-12 h-12 text-gray-400 mx-auto mb-4" />
          <h3 className="text-lg font-medium text-gray-900 mb-2">No activities found</h3>
          <p className="text-gray-600">Get started by creating your first activity.</p>
        </Card>
      )}
    </div>
  )
}
'''
    
    with open(os.path.join(frontend_path, 'app', 'activities', 'page.tsx'), 'w') as f:
        f.write(activities_page)

def _create_frontend_readme(frontend_path: str):
    """Create README.md for frontend"""
    readme = '''# CRM Flagship Frontend

This is a Next.js 14 application for the CRM Flagship template.

## Development

To run the development server:

```bash
npm install
npm run dev -- -p 3000
```

Open [http://localhost:3000](http://localhost:3000) with your browser to see the result.

## Build

To build for production:

```bash
npm run build
npm start
```

## Features

- Dashboard with health status and quick links
- Accounts management
- Contacts management  
- Deals tracking with stage indicators
- Activities log
- Real-time backend health monitoring
- Responsive design with Tailwind CSS
'''
    
    with open(os.path.join(frontend_path, 'README.md'), 'w') as f:
        f.write(readme)

def _create_tasks_backend_app_py(backend_path: str, build_data: Dict[str, Any]):
    """Create FastAPI app.py for Tasks template"""
    app_content = '''from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from db import get_db
from typing import List, Dict, Any

app = FastAPI(title="Task Manager", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/tasks")
async def list_tasks():
    conn = get_db()
    cursor = conn.execute("SELECT * FROM tasks ORDER BY created_at DESC")
    tasks = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return tasks

@app.post("/api/tasks")
async def create_task(task: Dict[str, Any]):
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO tasks (title, description, completed) VALUES (?, ?, ?)",
        (task.get('title'), task.get('description'), task.get('completed', False))
    )
    task_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return {"id": task_id, **task}

@app.get("/api/health")
async def health_check():
    return {"status": "healthy", "service": "Task Manager"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
'''
    
    with open(os.path.join(backend_path, 'app.py'), 'w') as f:
        f.write(app_content)

def _create_tasks_backend_db_py(backend_path: str, build_id: str):
    """Create database module for Tasks template"""
    db_path = os.path.join(backend_path, 'data', 'app.db')
    db_content = f'''import sqlite3
import os

DB_PATH = "{db_path}"

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tasks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            completed BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        
        INSERT OR IGNORE INTO tasks (title, description) VALUES
        ("Complete project setup", "Set up development environment"),
        ("Write documentation", "Create user and API documentation"),
        ("Test application", "Run comprehensive tests");
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    init_db()
'''
    
    with open(os.path.join(backend_path, 'db.py'), 'w') as f:
        f.write(db_content)

def _create_tasks_backend_requirements_txt(backend_path: str):
    """Create requirements.txt for Tasks backend"""
    requirements = '''fastapi==0.104.1
uvicorn==0.24.0
sqlite3
'''
    
    with open(os.path.join(backend_path, 'requirements.txt'), 'w') as f:
        f.write(requirements)

def _create_tasks_frontend_package_json(frontend_path: str):
    """Create package.json for Tasks frontend"""
    package_json = {
        "name": "task-manager-frontend",
        "version": "1.0.0",
        "type": "module",
        "scripts": {
            "dev": "vite",
            "build": "vite build",
            "preview": "vite preview"
        },
        "dependencies": {
            "react": "^18.2.0",
            "react-dom": "^18.2.0"
        },
        "devDependencies": {
            "@types/react": "^18.0.28",
            "@types/react-dom": "^18.0.11",
            "@vitejs/plugin-react": "^3.1.0",
            "vite": "^4.1.0"
        }
    }
    
    with open(os.path.join(frontend_path, 'package.json'), 'w') as f:
        json.dump(package_json, f, indent=2)

def _create_tasks_frontend_index_html(frontend_path: str):
    """Create index.html for Tasks frontend"""
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Task Manager</title>
</head>
<body>
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
</body>
</html>
'''
    
    with open(os.path.join(frontend_path, 'index.html'), 'w') as f:
        f.write(html_content)

def _create_tasks_frontend_main_jsx(frontend_path: str):
    """Create main.jsx for Tasks frontend"""
    main_content = '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
'''
    
    with open(os.path.join(frontend_path, 'src', 'main.jsx'), 'w') as f:
        f.write(main_content)

def _create_blank_frontend_index_html(frontend_path: str, build_data: Dict[str, Any]):
    """Create simple HTML for Blank template"""
    html_content = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{build_data.get('name', 'Blank App')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 2rem;
            line-height: 1.6;
        }}
        .header {{
            text-align: center;
            margin-bottom: 3rem;
        }}
        .content {{
            background: #f8f9fa;
            padding: 2rem;
            border-radius: 8px;
            border: 1px solid #dee2e6;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>{build_data.get('name', 'Blank App')}</h1>
        <p>{build_data.get('description', 'A blank application template')}</p>
    </div>
    
    <div class="content">
        <h2>Welcome to your new application!</h2>
        <p>This is a blank template that you can customize for your needs.</p>
        <p>Build ID: {build_data.get('id', 'unknown')}</p>
        <p>Template: {build_data.get('template', 'blank')}</p>
        <p>Created: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    </div>
</body>
</html>
'''
    
    with open(os.path.join(frontend_path, 'dist', 'index.html'), 'w') as f:
        f.write(html_content)

def _create_manifest(build_path: str, build_id: str, build_data: Dict[str, Any]):
    """Create manifest.json for the build"""
    manifest = {
        "name": build_data.get('name', 'Generated App'),
        "template": build_data.get('template', 'unknown'),
        "created_at": datetime.now().isoformat(),
        "build_id": build_id,
        "ports": {
            "backend": 8000,
            "frontend": 3000
        }
    }
    
    with open(os.path.join(build_path, 'manifest.json'), 'w') as f:
        json.dump(manifest, f, indent=2)

def run_seed(build_id: str, template: str):
    """Run seed script for the build"""
    build_path = get_build_path(build_id)
    
    if template == 'crm_flagship':
        seed_script = os.path.join(build_path, 'backend', 'seed.py')
        if os.path.exists(seed_script):
            try:
                subprocess.run(['python', seed_script], cwd=os.path.join(build_path, 'backend'), check=True)
                logger.info(f"Seeded database for build {build_id}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to seed database for build {build_id}: {e}")
    elif template == 'tasks':
        # Tasks template seeds data in db.py init
        db_script = os.path.join(build_path, 'backend', 'db.py')
        if os.path.exists(db_script):
            try:
                subprocess.run(['python', db_script], cwd=os.path.join(build_path, 'backend'), check=True)
                logger.info(f"Initialized database for build {build_id}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to initialize database for build {build_id}: {e}")

def scaffold_build(build_id: str, build_data: Dict[str, Any]) -> Dict[str, str]:
    """Main scaffold function that routes to appropriate template"""
    template = build_data.get('template', 'blank')
    
    logger.info(f"Starting scaffold for build {build_id} with template {template}")
    
    try:
        if template == 'crm_flagship':
            result = scaffold_crm_flagship(build_id, build_data)
        elif template == 'tasks':
            result = scaffold_tasks_template(build_id, build_data)
        else:
            result = scaffold_blank_template(build_id, build_data)
        
        # Run seed if applicable
        run_seed(build_id, template)
        
        logger.info(f"Completed scaffold for build {build_id}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to scaffold build {build_id}: {e}")
        raise
