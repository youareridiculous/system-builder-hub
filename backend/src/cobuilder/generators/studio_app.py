"""
Studio App Generator - Creates the control plane Next.js app
"""
import os
import json
from typing import Dict, Any
from ..file_ops import write_file, ensure_parents


def generate_studio_app(build_id: str, workspace: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Generate the Studio control plane app"""
    workspace_path = os.path.join(workspace, build_id)
    
    def log_fn(msg):
        print(f"[STUDIO] {msg}")
    
    log_fn("Generating Studio app...")
    
    try:
        # Create Studio app directory structure
        studio_path = os.path.join(workspace_path, "apps", "studio")
        ensure_parents(studio_path)
        
        # Create Studio package.json
        _create_studio_package_json(studio_path, log_fn)
        
        # Create Next.js config
        _create_studio_next_config(studio_path, log_fn)
        
        # Create app structure
        _create_studio_app_structure(studio_path, log_fn)
        
        # Create pages/routes
        _create_studio_pages(studio_path, log_fn)
        
        # Create components
        _create_studio_components(studio_path, log_fn)
        
        # Create utilities
        _create_studio_utils(studio_path, log_fn)
        
        log_fn("Studio app generation complete")
        
        return {
            "success": True,
            "path": studio_path,
            "is_directory": True,
            "sha256": "studio_app_generated"
        }
    except Exception as e:
        log_fn(f"Studio app generation failed: {e}")
        return {"success": False, "error": str(e)}


def generate_studio_routes(build_id: str, workspace: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Studio routes"""
    workspace_path = os.path.join(workspace, build_id)
    
    def log_fn(msg):
        print(f"[STUDIO] {msg}")
    
    log_fn("Generating Studio routes...")
    
    try:
        studio_path = os.path.join(workspace_path, "apps", "studio")
        
        # Create route files
        routes = [
            ("app/spec/page.tsx", _create_spec_page),
            ("app/compile/page.tsx", _create_compile_page),
            ("app/preview/page.tsx", _create_preview_page),
            ("app/diff/page.tsx", _create_diff_page),
            ("app/deploy/page.tsx", _create_deploy_page),
            ("app/pricing/page.tsx", _create_pricing_page)
        ]
        
        for route_path, create_func in routes:
            full_path = os.path.join(studio_path, route_path)
            ensure_parents(full_path)
            create_func(full_path, log_fn)
        
        log_fn("Studio routes generation complete")
        
        return {
            "success": True,
            "path": os.path.join(studio_path, "app"),
            "is_directory": True,
            "sha256": "studio_routes_generated"
        }
    except Exception as e:
        log_fn(f"Studio routes generation failed: {e}")
        return {"success": False, "error": str(e)}


def generate_studio_ui(build_id: str, workspace: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Generate Studio UI components"""
    workspace_path = os.path.join(workspace, build_id)
    
    def log_fn(msg):
        print(f"[STUDIO] {msg}")
    
    log_fn("Generating Studio UI components...")
    
    try:
        studio_path = os.path.join(workspace_path, "apps", "studio")
        
        # Create UI components
        components = [
            ("components/SpecEditor.tsx", _create_spec_editor),
            ("components/CompileButton.tsx", _create_compile_button),
            ("components/PreviewPanel.tsx", _create_preview_panel),
            ("components/DeployButton.tsx", _create_deploy_button)
        ]
        
        for component_path, create_func in components:
            full_path = os.path.join(studio_path, component_path)
            ensure_parents(full_path)
            create_func(full_path, log_fn)
        
        log_fn("Studio UI components generation complete")
        
        return {
            "success": True,
            "path": os.path.join(studio_path, "components"),
            "is_directory": True,
            "sha256": "studio_ui_generated"
        }
    except Exception as e:
        log_fn(f"Studio UI generation failed: {e}")
        return {"success": False, "error": str(e)}


def generate_studio_app_old(workspace_path: str, spec: Dict[str, Any], log_fn) -> None:
    """Generate the Studio control plane app"""
    log_fn("[STUDIO] Generating Studio app...")
    
    # Create Studio app directory structure
    studio_path = os.path.join(workspace_path, "apps", "studio")
    ensure_parents(studio_path)
    
    # Create Studio package.json
    _create_studio_package_json(studio_path, log_fn)
    
    # Create Next.js config
    _create_studio_next_config(studio_path, log_fn)
    
    # Create app structure
    _create_studio_app_structure(studio_path, log_fn)
    
    # Create pages/routes
    _create_studio_pages(studio_path, log_fn)
    
    # Create components
    _create_studio_components(studio_path, log_fn)
    
    # Create utilities
    _create_studio_utils(studio_path, log_fn)
    
    log_fn("[STUDIO] Studio app generation complete")


def _create_studio_package_json(studio_path: str, log_fn) -> None:
    """Create Studio package.json"""
    package_json = {
        "name": "@app/studio",
        "version": "0.1.0",
        "private": True,
        "scripts": {
            "dev": "next dev -p 3001",
            "build": "next build",
            "start": "next start -p 3001",
            "lint": "next lint"
        },
        "dependencies": {
            "next": "14.2.4",
            "react": "18.3.1",
            "react-dom": "18.3.1",
            "@monaco-editor/react": "^4.6.0",
            "zod": "^3.23.8",
            "lucide-react": "^0.400.0",
            "clsx": "^2.1.0",
            "tailwind-merge": "^2.2.0"
        },
        "devDependencies": {
            "@types/node": "^20 || ^22 || ^24",
            "@types/react": "^18 || ^19",
            "@types/react-dom": "^18 || ^19",
            "typescript": "^5.5.4",
            "tailwindcss": "^3.4.7",
            "postcss": "^8.4.41",
            "autoprefixer": "^10.4.19",
            "eslint": "^8.57.0",
            "eslint-config-next": "14.2.4"
        }
    }
    
    write_file(
        os.path.join(studio_path, "package.json"),
        json.dumps(package_json, indent=2),
        log_fn
    )


def _create_studio_next_config(studio_path: str, log_fn) -> None:
    """Create Studio Next.js config"""
    next_config = '''/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ['@sbh/core', '@sbh/compiler', '@sbh/validators'],
};

export default nextConfig;'''
    
    write_file(
        os.path.join(studio_path, "next.config.mjs"),
        next_config,
        log_fn
    )


def _create_studio_app_structure(studio_path: str, log_fn) -> None:
    """Create Studio app directory structure"""
    directories = [
        "app",
        "app/api",
        "app/api/compile",
        "app/api/spec",
        "components",
        "components/ui",
        "lib",
        "types",
        "storage"
    ]
    
    for directory in directories:
        ensure_parents(os.path.join(studio_path, directory))
    
    # Create TypeScript config
    tsconfig = '''{
  "compilerOptions": {
    "target": "es5",
    "lib": ["dom", "dom.iterable", "es6"],
    "allowJs": true,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "plugins": [
      {
        "name": "next"
      }
    ],
    "baseUrl": ".",
    "paths": {
      "@/*": ["./*"]
    }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx", ".next/types/**/*.ts"],
  "exclude": ["node_modules"]
}'''
    
    write_file(
        os.path.join(studio_path, "tsconfig.json"),
        tsconfig,
        log_fn
    )
    
    # Create Tailwind config
    tailwind_config = '''import type { Config } from 'tailwindcss'

const config: Config = {
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
    },
  },
  plugins: [],
}
export default config'''
    
    write_file(
        os.path.join(studio_path, "tailwind.config.ts"),
        tailwind_config,
        log_fn
    )
    
    # Create PostCSS config
    postcss_config = '''module.exports = {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
}'''
    
    write_file(
        os.path.join(studio_path, "postcss.config.js"),
        postcss_config,
        log_fn
    )


def _create_studio_pages(studio_path: str, log_fn) -> None:
    """Create Studio pages and routes"""
    
    # Create layout
    layout = '''import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'AI Website Builder Studio',
  description: 'Control plane for the AI Website Builder platform',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={inter.className}>
        <div className="min-h-screen bg-background">
          {children}
        </div>
      </body>
    </html>
  )
}'''
    
    write_file(
        os.path.join(studio_path, "app", "layout.tsx"),
        layout,
        log_fn
    )
    
    # Create globals.css
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
  }

  .dark {
    --background: 222.2 84% 4.9%;
    --foreground: 210 40% 98%;
    --card: 222.2 84% 4.9%;
    --card-foreground: 210 40% 98%;
    --popover: 222.2 84% 4.9%;
    --popover-foreground: 210 40% 98%;
    --primary: 210 40% 98%;
    --primary-foreground: 222.2 47.4% 11.2%;
    --secondary: 217.2 32.6% 17.5%;
    --secondary-foreground: 210 40% 98%;
    --muted: 217.2 32.6% 17.5%;
    --muted-foreground: 215 20.2% 65.1%;
    --accent: 217.2 32.6% 17.5%;
    --accent-foreground: 210 40% 98%;
    --destructive: 0 62.8% 30.6%;
    --destructive-foreground: 210 40% 98%;
    --border: 217.2 32.6% 17.5%;
    --input: 217.2 32.6% 17.5%;
    --ring: 212.7 26.8% 83.9%;
  }
}

@layer base {
  * {
    @apply border-border;
  }
  body {
    @apply bg-background text-foreground;
  }
}'''
    
    write_file(
        os.path.join(studio_path, "app", "globals.css"),
        globals_css,
        log_fn
    )
    
    # Create home page
    home_page = '''import Link from 'next/link'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { FileText, Play, Eye, GitBranch, DollarSign, Settings } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="container mx-auto px-4 py-8">
      <div className="mb-8">
        <h1 className="text-4xl font-bold mb-2">AI Website Builder Studio</h1>
        <p className="text-muted-foreground text-lg">
          Control plane for building and managing AI-generated websites
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <FileText className="h-5 w-5" />
              Spec Editor
            </CardTitle>
            <CardDescription>
              Upload and edit your website specification
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/spec">
              <Button className="w-full">Edit Specification</Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Play className="h-5 w-5" />
              Compile
            </CardTitle>
            <CardDescription>
              Generate your website from the specification
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/compile">
              <Button className="w-full">Compile Website</Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Eye className="h-5 w-5" />
              Preview
            </CardTitle>
            <CardDescription>
              Preview your generated website
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/preview">
              <Button className="w-full">Preview Site</Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <GitBranch className="h-5 w-5" />
              Diff
            </CardTitle>
            <CardDescription>
              View changes from last compilation
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/diff">
              <Button className="w-full">View Diff</Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <DollarSign className="h-5 w-5" />
              Pricing
            </CardTitle>
            <CardDescription>
              Generate pricing from specification
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/pricing">
              <Button className="w-full">Generate Pricing</Button>
            </Link>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Settings className="h-5 w-5" />
              Deploy
            </CardTitle>
            <CardDescription>
              Deploy your website to production
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Link href="/deploy">
              <Button className="w-full">Deploy Site</Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}'''
    
    write_file(
        os.path.join(studio_path, "app", "page.tsx"),
        home_page,
        log_fn
    )


def _create_studio_components(studio_path: str, log_fn) -> None:
    """Create Studio UI components"""
    
    # Create Button component
    button_component = '''import * as React from "react"
import { cva, type VariantProps } from "class-variance-authority"
import { cn } from "@/lib/utils"

const buttonVariants = cva(
  "inline-flex items-center justify-center whitespace-nowrap rounded-md text-sm font-medium ring-offset-background transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-primary text-primary-foreground hover:bg-primary/90",
        destructive:
          "bg-destructive text-destructive-foreground hover:bg-destructive/90",
        outline:
          "border border-input bg-background hover:bg-accent hover:text-accent-foreground",
        secondary:
          "bg-secondary text-secondary-foreground hover:bg-secondary/80",
        ghost: "hover:bg-accent hover:text-accent-foreground",
        link: "text-primary underline-offset-4 hover:underline",
      },
      size: {
        default: "h-10 px-4 py-2",
        sm: "h-9 rounded-md px-3",
        lg: "h-11 rounded-md px-8",
        icon: "h-10 w-10",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  }
)

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement>,
    VariantProps<typeof buttonVariants> {
  asChild?: boolean
}

const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant, size, asChild = false, ...props }, ref) => {
    return (
      <button
        className={cn(buttonVariants({ variant, size, className }))}
        ref={ref}
        {...props}
      />
    )
  }
)
Button.displayName = "Button"

export { Button, buttonVariants }'''
    
    write_file(
        os.path.join(studio_path, "components", "ui", "button.tsx"),
        button_component,
        log_fn
    )
    
    # Create Card component
    card_component = '''import * as React from "react"
import { cn } from "@/lib/utils"

const Card = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn(
      "rounded-lg border bg-card text-card-foreground shadow-sm",
      className
    )}
    {...props}
  />
))
Card.displayName = "Card"

const CardHeader = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex flex-col space-y-1.5 p-6", className)}
    {...props}
  />
))
CardHeader.displayName = "CardHeader"

const CardTitle = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLHeadingElement>
>(({ className, ...props }, ref) => (
  <h3
    ref={ref}
    className={cn(
      "text-2xl font-semibold leading-none tracking-tight",
      className
    )}
    {...props}
  />
))
CardTitle.displayName = "CardTitle"

const CardDescription = React.forwardRef<
  HTMLParagraphElement,
  React.HTMLAttributes<HTMLParagraphElement>
>(({ className, ...props }, ref) => (
  <p
    ref={ref}
    className={cn("text-sm text-muted-foreground", className)}
    {...props}
  />
))
CardDescription.displayName = "CardDescription"

const CardContent = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div ref={ref} className={cn("p-6 pt-0", className)} {...props} />
))
CardContent.displayName = "CardContent"

const CardFooter = React.forwardRef<
  HTMLDivElement,
  React.HTMLAttributes<HTMLDivElement>
>(({ className, ...props }, ref) => (
  <div
    ref={ref}
    className={cn("flex items-center p-6 pt-0", className)}
    {...props}
  />
))
CardFooter.displayName = "CardFooter"

export { Card, CardHeader, CardFooter, CardTitle, CardDescription, CardContent }'''
    
    write_file(
        os.path.join(studio_path, "components", "ui", "card.tsx"),
        card_component,
        log_fn
    )


def _create_spec_page(file_path: str, log_fn) -> None:
    """Create spec page"""
    content = '''import { SpecEditor } from '../../components/SpecEditor'

export default function SpecPage() {
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Spec Editor</h1>
      <SpecEditor />
    </div>
  )
}'''
    write_file(file_path, content)
    log_fn(f"Created {file_path}")


def _create_compile_page(file_path: str, log_fn) -> None:
    """Create compile page"""
    content = '''import { CompileButton } from '../../components/CompileButton'

export default function CompilePage() {
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Compile Website</h1>
      <CompileButton />
    </div>
  )
}'''
    write_file(file_path, content)
    log_fn(f"Created {file_path}")


def _create_preview_page(file_path: str, log_fn) -> None:
    """Create preview page"""
    content = '''import { PreviewPanel } from '../../components/PreviewPanel'

export default function PreviewPage() {
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Preview</h1>
      <PreviewPanel />
    </div>
  )
}'''
    write_file(file_path, content)
    log_fn(f"Created {file_path}")


def _create_diff_page(file_path: str, log_fn) -> None:
    """Create diff page"""
    content = '''export default function DiffPage() {
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Changes Diff</h1>
      <p>Compare changes between versions</p>
    </div>
  )
}'''
    write_file(file_path, content)
    log_fn(f"Created {file_path}")


def _create_deploy_page(file_path: str, log_fn) -> None:
    """Create deploy page"""
    content = '''import { DeployButton } from '../../components/DeployButton'

export default function DeployPage() {
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Deploy Website</h1>
      <DeployButton />
    </div>
  )
}'''
    write_file(file_path, content)
    log_fn(f"Created {file_path}")


def _create_pricing_page(file_path: str, log_fn) -> None:
    """Create pricing page"""
    content = '''export default function PricingPage() {
  return (
    <div className="container mx-auto p-6">
      <h1 className="text-3xl font-bold mb-6">Pricing</h1>
      <div className="grid grid-cols-3 gap-6">
        <div className="border p-6 rounded">
          <h2 className="text-xl font-bold">Starter</h2>
          <p className="text-2xl font-bold">$29/month</p>
          <ul>
            <li>1 hosted site</li>
            <li>5k visits</li>
            <li>1 custom domain</li>
          </ul>
        </div>
        <div className="border p-6 rounded">
          <h2 className="text-xl font-bold">Pro</h2>
          <p className="text-2xl font-bold">$79/month</p>
          <ul>
            <li>5 sites</li>
            <li>100k visits</li>
            <li>forms/surveys/chat</li>
          </ul>
        </div>
        <div className="border p-6 rounded">
          <h2 className="text-xl font-bold">Studio</h2>
          <p className="text-2xl font-bold">$199/month</p>
          <ul>
            <li>unlimited sites</li>
            <li>multi-region hosting</li>
            <li>white-label</li>
          </ul>
        </div>
      </div>
    </div>
  )
}'''
    write_file(file_path, content)
    log_fn(f"Created {file_path}")


def _create_spec_editor(file_path: str, log_fn) -> None:
    """Create spec editor component"""
    content = ''''use client'

import { useState } from 'react'

export function SpecEditor() {
  const [spec, setSpec] = useState('')

  return (
    <div className="border rounded p-4">
      <textarea
        value={spec}
        onChange={(e) => setSpec(e.target.value)}
        placeholder="Enter your website specification..."
        className="w-full h-64 p-2 border rounded"
      />
      <button className="mt-4 px-4 py-2 bg-blue-500 text-white rounded">
        Save Spec
      </button>
    </div>
  )
}'''
    write_file(file_path, content)
    log_fn(f"Created {file_path}")


def _create_compile_button(file_path: str, log_fn) -> None:
    """Create compile button component"""
    content = ''''use client'

import { useState } from 'react'

export function CompileButton() {
  const [isCompiling, setIsCompiling] = useState(false)

  const handleCompile = async () => {
    setIsCompiling(true)
    try {
      // Call compile API
      const response = await fetch('/api/cobuilder/compile', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ spec: 'current_spec' })
      })
      const result = await response.json()
      console.log('Compile result:', result)
    } catch (error) {
      console.error('Compile error:', error)
    } finally {
      setIsCompiling(false)
    }
  }

  return (
    <button
      onClick={handleCompile}
      disabled={isCompiling}
      className="px-6 py-3 bg-green-500 text-white rounded-lg disabled:opacity-50"
    >
      {isCompiling ? 'Compiling...' : 'Compile Website'}
    </button>
  )
}'''
    write_file(file_path, content)
    log_fn(f"Created {file_path}")


def _create_preview_panel(file_path: str, log_fn) -> None:
    """Create preview panel component"""
    content = ''''use client'

export function PreviewPanel() {
  return (
    <div className="border rounded p-4">
      <h2 className="text-xl font-bold mb-4">Website Preview</h2>
      <div className="border rounded p-4 bg-gray-50">
        <p>Preview will appear here after compilation</p>
      </div>
    </div>
  )
}'''
    write_file(file_path, content)
    log_fn(f"Created {file_path}")


def _create_deploy_button(file_path: str, log_fn) -> None:
    """Create deploy button component"""
    content = ''''use client'

import { useState } from 'react'

export function DeployButton() {
  const [isDeploying, setIsDeploying] = useState(false)

  const handleDeploy = async () => {
    setIsDeploying(true)
    try {
      // Call deploy API
      const response = await fetch('/api/cobuilder/deploy', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ target: 'vercel' })
      })
      const result = await response.json()
      console.log('Deploy result:', result)
    } catch (error) {
      console.error('Deploy error:', error)
    } finally {
      setIsDeploying(false)
    }
  }

  return (
    <button
      onClick={handleDeploy}
      disabled={isDeploying}
      className="px-6 py-3 bg-purple-500 text-white rounded-lg disabled:opacity-50"
    >
      {isDeploying ? 'Deploying...' : 'Deploy to Vercel'}
    </button>
  )
}'''


def _create_studio_utils(studio_path: str, log_fn) -> None:
    """Create Studio utility functions"""
    
    # Create utils
    utils = '''import { type ClassValue, clsx } from "clsx"
import { twMerge } from "tailwind-merge"

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}'''
    
    write_file(
        os.path.join(studio_path, "lib", "utils.ts"),
        utils,
        log_fn
    )
    
    # Create types
    types = '''export interface CoreSpec {
  brand: {
    name: string
    tagline: string
    description: string
    logo?: string
  }
  goals: string[]
  sections: Section[]
  payments?: {
    stripe?: boolean
    pricing?: PricingTier[]
  }
  hosting?: {
    provider: 'vercel' | 'netlify' | 'custom'
    domain?: string
  }
  i18n?: {
    defaultLanguage: string
    supportedLanguages: string[]
  }
}

export interface Section {
  id: string
  type: 'hero' | 'feature-grid' | 'logo-cloud' | 'showreel' | 'pricing' | 'cta'
  title?: string
  subtitle?: string
  content: any
}

export interface PricingTier {
  name: string
  price: number
  currency: string
  features: string[]
  popular?: boolean
}

export interface CompileResult {
  writes: Array<{
    path: string
    sha256: string
  }>
  diffs: Array<{
    path: string
    type: 'added' | 'modified' | 'deleted'
    content?: string
  }>
}'''
    
    write_file(
        os.path.join(studio_path, "types", "index.ts"),
        types,
        log_fn
    )
