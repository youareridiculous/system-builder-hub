#!/usr/bin/env python3
"""
Fix Vite/React frontends to use TypeScript entry points
"""
import os
import glob
import json
import shutil
import subprocess
import re
from pathlib import Path

def is_vite_frontend(frontend_dir):
    """Detect if this is a Vite/React frontend (not Next.js)"""
    # Skip Next.js frontends
    if (os.path.exists(os.path.join(frontend_dir, 'app')) or 
        os.path.exists(os.path.join(frontend_dir, 'next.config.js')) or
        os.path.exists(os.path.join(frontend_dir, 'next.config.ts')) or
        os.path.exists(os.path.join(frontend_dir, 'next.config.mjs'))):
        return False
    
    # Must have index.html and src/ directory
    return (os.path.exists(os.path.join(frontend_dir, 'index.html')) and 
            os.path.exists(os.path.join(frontend_dir, 'src')))

def fix_index_html(frontend_dir):
    """Fix index.html to point to main.tsx"""
    index_path = os.path.join(frontend_dir, 'index.html')
    if not os.path.exists(index_path):
        return False
    
    with open(index_path, 'r') as f:
        content = f.read()
    
    # Replace any main.jsx reference with main.tsx
    content = re.sub(
        r'<script[^>]*src=["\']/src/main\.jsx["\'][^>]*>',
        '<script type="module" src="/src/main.tsx"></script>',
        content
    )
    
    # If no script tag found, add it
    if '<script type="module" src="/src/main.tsx">' not in content:
        # Find the closing </head> tag and insert before it
        if '</head>' in content:
            content = content.replace('</head>', 
                '  <script type="module" src="/src/main.tsx"></script>\n</head>')
        else:
            # If no head tag, add at the end of body
            content = content.replace('</body>', 
                '  <script type="module" src="/src/main.tsx"></script>\n</body>')
    
    with open(index_path, 'w') as f:
        f.write(content)
    
    return True

def ensure_main_tsx(frontend_dir):
    """Ensure src/main.tsx exists with proper content"""
    src_dir = os.path.join(frontend_dir, 'src')
    main_tsx_path = os.path.join(src_dir, 'main.tsx')
    main_jsx_path = os.path.join(src_dir, 'main.jsx')
    
    if os.path.exists(main_tsx_path):
        # Already exists, just fix imports
        with open(main_tsx_path, 'r') as f:
            content = f.read()
        
        # Fix .jsx imports
        content = re.sub(r'from ["\']\./App\.jsx["\']', "from './App'", content)
        
        with open(main_tsx_path, 'w') as f:
            f.write(content)
        return True
    
    elif os.path.exists(main_jsx_path):
        # Rename and fix
        with open(main_jsx_path, 'r') as f:
            content = f.read()
        
        # Fix .jsx imports
        content = re.sub(r'from ["\']\./App\.jsx["\']', "from './App'", content)
        
        # Ensure modern React root
        if 'ReactDOM.createRoot' not in content:
            content = '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)'''
        
        with open(main_tsx_path, 'w') as f:
            f.write(content)
        
        os.remove(main_jsx_path)
        return True
    
    else:
        # Create new main.tsx
        content = '''import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)'''
        
        with open(main_tsx_path, 'w') as f:
            f.write(content)
        return True

def ensure_app_tsx(frontend_dir):
    """Ensure src/App.tsx exists"""
    src_dir = os.path.join(frontend_dir, 'src')
    app_tsx_path = os.path.join(src_dir, 'App.tsx')
    app_jsx_path = os.path.join(src_dir, 'App.jsx')
    
    if os.path.exists(app_tsx_path):
        # Already exists, just fix imports
        with open(app_tsx_path, 'r') as f:
            content = f.read()
        
        # Fix .jsx imports
        content = re.sub(r'from ["\']\./pages/.*\.jsx["\']', lambda m: m.group(0).replace('.jsx', ''), content)
        content = re.sub(r'from ["\']\./components/.*\.jsx["\']', lambda m: m.group(0).replace('.jsx', ''), content)
        
        with open(app_tsx_path, 'w') as f:
            f.write(content)
        return True
    
    elif os.path.exists(app_jsx_path):
        # Rename and fix
        with open(app_jsx_path, 'r') as f:
            content = f.read()
        
        # Fix .jsx imports
        content = re.sub(r'from ["\']\./pages/.*\.jsx["\']', lambda m: m.group(0).replace('.jsx', ''), content)
        content = re.sub(r'from ["\']\./components/.*\.jsx["\']', lambda m: m.group(0).replace('.jsx', ''), content)
        
        with open(app_tsx_path, 'w') as f:
            f.write(content)
        
        os.remove(app_jsx_path)
        return True
    
    else:
        # Create minimal App.tsx
        content = '''export default function App() {
  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold">CRM Frontend</h1>
    </div>
  )
}'''
        
        with open(app_tsx_path, 'w') as f:
            f.write(content)
        return True

def fix_jsx_imports(frontend_dir):
    """Remove .jsx suffixes from all imports in src/"""
    src_dir = os.path.join(frontend_dir, 'src')
    if not os.path.exists(src_dir):
        return 0
    
    fixed_count = 0
    for root, dirs, files in os.walk(src_dir):
        for file in files:
            if file.endswith(('.tsx', '.ts', '.jsx', '.js')):
                file_path = os.path.join(root, file)
                with open(file_path, 'r') as f:
                    content = f.read()
                
                original_content = content
                
                # Fix relative imports
                content = re.sub(r'from ["\']\./.*\.jsx["\']', lambda m: m.group(0).replace('.jsx', ''), content)
                content = re.sub(r'from ["\']\.\./.*\.jsx["\']', lambda m: m.group(0).replace('.jsx', ''), content)
                content = re.sub(r'from ["\']\.\./\.\./.*\.jsx["\']', lambda m: m.group(0).replace('.jsx', ''), content)
                
                if content != original_content:
                    with open(file_path, 'w') as f:
                        f.write(content)
                    fixed_count += 1
    
    return fixed_count

def ensure_tsconfig(frontend_dir):
    """Ensure tsconfig.json exists with proper config"""
    tsconfig_path = os.path.join(frontend_dir, 'tsconfig.json')
    
    config = {
        "compilerOptions": {
            "target": "ES2020",
            "useDefineForClassFields": True,
            "lib": ["ES2020", "DOM", "DOM.Iterable"],
            "module": "ESNext",
            "skipLibCheck": True,
            "jsx": "react-jsx",
            "moduleResolution": "bundler",
            "resolveJsonModule": True,
            "isolatedModules": True,
            "noEmit": True,
            "strict": True
        },
        "include": ["src"]
    }
    
    with open(tsconfig_path, 'w') as f:
        json.dump(config, f, indent=2)
    
    return True

def ensure_vite_config(frontend_dir):
    """Ensure vite.config.ts exists"""
    vite_ts_path = os.path.join(frontend_dir, 'vite.config.ts')
    vite_js_path = os.path.join(frontend_dir, 'vite.config.js')
    
    if os.path.exists(vite_ts_path):
        return True
    
    if os.path.exists(vite_js_path):
        # Keep existing JS config
        return True
    
    # Create new vite.config.ts
    content = '''import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
})'''
    
    with open(vite_ts_path, 'w') as f:
        f.write(content)
    
    return True

def ensure_tailwind_css(frontend_dir):
    """Ensure Tailwind CSS is properly configured if already present"""
    # Check if Tailwind is already configured
    tailwind_config = any([
        os.path.exists(os.path.join(frontend_dir, 'tailwind.config.js')),
        os.path.exists(os.path.join(frontend_dir, 'tailwind.config.ts')),
        os.path.exists(os.path.join(frontend_dir, 'postcss.config.js'))
    ])
    
    if not tailwind_config:
        return False
    
    # Find CSS file
    css_files = ['src/index.css', 'src/styles.css', 'src/globals.css']
    css_path = None
    
    for css_file in css_files:
        if os.path.exists(os.path.join(frontend_dir, css_file)):
            css_path = os.path.join(frontend_dir, css_file)
            break
    
    if not css_path:
        # Create index.css
        css_path = os.path.join(frontend_dir, 'src', 'index.css')
        os.makedirs(os.path.dirname(css_path), exist_ok=True)
    
    with open(css_path, 'r') as f:
        content = f.read()
    
    # Ensure Tailwind directives are present
    if '@tailwind base;' not in content:
        content = '''@tailwind base;
@tailwind components;
@tailwind utilities;

''' + content
    
    with open(css_path, 'w') as f:
        f.write(content)
    
    return True

def ensure_dependencies(frontend_dir):
    """Ensure required dependencies are present"""
    package_path = os.path.join(frontend_dir, 'package.json')
    if not os.path.exists(package_path):
        return False
    
    with open(package_path, 'r') as f:
        package_data = json.load(f)
    
    # Ensure dev dependencies
    if 'devDependencies' not in package_data:
        package_data['devDependencies'] = {}
    
    dev_deps = {
        'typescript': '^5.0.0',
        '@types/react': '^18.2.0',
        '@types/react-dom': '^18.2.0',
        '@vitejs/plugin-react': '^4.0.0'
    }
    
    for dep, version in dev_deps.items():
        if dep not in package_data['devDependencies']:
            package_data['devDependencies'][dep] = version
    
    # Ensure runtime dependencies
    if 'dependencies' not in package_data:
        package_data['dependencies'] = {}
    
    runtime_deps = {
        'react': '^18.2.0',
        'react-dom': '^18.2.0'
    }
    
    for dep, version in runtime_deps.items():
        if dep not in package_data['dependencies']:
            package_data['dependencies'][dep] = version
    
    with open(package_path, 'w') as f:
        json.dump(package_data, f, indent=2)
    
    return True

def install_dependencies(frontend_dir):
    """Install dependencies if node_modules is missing"""
    node_modules_path = os.path.join(frontend_dir, 'node_modules')
    if not os.path.exists(node_modules_path):
        print(f"  Installing dependencies...")
        try:
            subprocess.run(['npm', 'install'], cwd=frontend_dir, 
                         capture_output=True, text=True, timeout=120)
            return True
        except subprocess.TimeoutExpired:
            print(f"  Timeout installing dependencies")
            return False
        except Exception as e:
            print(f"  Error installing dependencies: {e}")
            return False
    return True

def verify_compilation(frontend_dir):
    """Verify the frontend compiles with Vite"""
    print(f"  Verifying compilation...")
    try:
        # Start dev server in background
        process = subprocess.Popen(
            ['npm', 'run', 'dev', '--', '--port', '3000'],
            cwd=frontend_dir,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        
        # Wait for ready message
        import time
        time.sleep(10)
        
        # Check if process is still running
        if process.poll() is None:
            # Process is running, check for ready message
            stdout, stderr = process.communicate(timeout=5)
            if 'ready' in stdout.lower() or 'localhost:3000' in stdout:
                process.terminate()
                return True
            else:
                process.terminate()
                return False
        else:
            # Process exited
            stdout, stderr = process.communicate()
            print(f"  Compilation failed: {stderr}")
            return False
            
    except Exception as e:
        print(f"  Verification error: {e}")
        return False

def fix_vite_frontend(frontend_dir):
    """Fix a single Vite frontend"""
    print(f"Fixing: {frontend_dir}")
    
    changes = []
    
    # 1. Fix index.html
    if fix_index_html(frontend_dir):
        changes.append("Fixed index.html")
    
    # 2. Ensure main.tsx
    if ensure_main_tsx(frontend_dir):
        changes.append("Fixed main.tsx")
    
    # 3. Ensure App.tsx
    if ensure_app_tsx(frontend_dir):
        changes.append("Fixed App.tsx")
    
    # 4. Fix .jsx imports
    fixed_imports = fix_jsx_imports(frontend_dir)
    if fixed_imports > 0:
        changes.append(f"Fixed {fixed_imports} import statements")
    
    # 5. Ensure tsconfig.json
    if ensure_tsconfig(frontend_dir):
        changes.append("Updated tsconfig.json")
    
    # 6. Ensure vite.config.ts
    if ensure_vite_config(frontend_dir):
        changes.append("Updated vite.config.ts")
    
    # 7. Ensure Tailwind CSS
    if ensure_tailwind_css(frontend_dir):
        changes.append("Updated Tailwind CSS")
    
    # 8. Ensure dependencies
    if ensure_dependencies(frontend_dir):
        changes.append("Updated dependencies")
    
    # 9. Install dependencies
    if install_dependencies(frontend_dir):
        changes.append("Installed dependencies")
    
    # 10. Verify compilation
    if verify_compilation(frontend_dir):
        changes.append("Compilation verified")
    else:
        changes.append("Compilation failed")
    
    for change in changes:
        print(f"  ✓ {change}")
    
    return changes

def main():
    """Main function to fix all Vite frontends"""
    generated_root = "./generated"
    
    # Find all frontend directories
    frontend_dirs = []
    for frontend_dir in glob.glob(f"{generated_root}/*/frontend"):
        if is_vite_frontend(frontend_dir):
            frontend_dirs.append(frontend_dir)
    
    print(f"Found {len(frontend_dirs)} Vite frontends to fix")
    print()
    
    total_fixed = 0
    for frontend_dir in frontend_dirs:
        changes = fix_vite_frontend(frontend_dir)
        if changes:
            total_fixed += 1
        print()
    
    print(f"✅ Fixed {total_fixed} Vite frontends")
    
    # Special verification for the main build
    main_build = "./generated/2f61e8d4-e8e5-4066-9adc-2150c1fc46c0/frontend"
    if os.path.exists(main_build):
        print(f"\n🎯 Main build verification:")
        print(f"cd {main_build} && npm run dev -- --port 3000")

if __name__ == "__main__":
    main()
