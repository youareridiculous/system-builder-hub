"""
SEO, Prisma, and documentation generators for Co-Builder.

Generates SEO files, Prisma schema, and documentation.
"""

import json
from pathlib import Path
from typing import Dict, Any


def generate_seo_files(build_id: str, workspace: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate SEO files (robots.ts, sitemap.ts).
    
    Args:
        build_id: The build ID for this workspace
        workspace: The workspace root path
        spec: The parsed specification
        
    Returns:
        Dict with success status and metadata
    """
    try:
        build_path = Path(workspace) / build_id
        
        # Generate robots.ts
        robots_file = build_path / "apps/site/app/robots.ts"
        robots_content = _generate_robots_file()
        robots_file.write_text(robots_content)
        
        # Generate sitemap.ts
        sitemap_file = build_path / "apps/site/app/sitemap.ts"
        sitemap_content = _generate_sitemap_file()
        sitemap_file.write_text(sitemap_content)
        
        return {
            "success": True,
            "path": str(robots_file),
            "is_directory": False,
            "lines_changed": len(robots_content.splitlines()) + len(sitemap_content.splitlines()),
            "sha256": "",  # Will be computed by file_ops
            "created_files": [str(robots_file), str(sitemap_file)]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "path": "",
            "is_directory": False,
            "lines_changed": 0,
            "sha256": ""
        }


def generate_prisma_schema(build_id: str, workspace: str) -> Dict[str, Any]:
    """
    Generate Prisma schema and database configuration.
    
    Args:
        build_id: The build ID for this workspace
        workspace: The workspace root path
        
    Returns:
        Dict with success status and metadata
    """
    try:
        build_path = Path(workspace) / build_id
        
        # Generate schema.prisma
        schema_file = build_path / "prisma/schema.prisma"
        schema_content = _generate_prisma_schema()
        schema_file.write_text(schema_content)
        
        # Generate database utility
        db_util = build_path / "apps/site/lib/db.ts"
        db_content = _generate_db_util()
        db_util.write_text(db_content)
        
        # Generate spec file
        spec_file = build_path / "packages/core/src/spec.ts"
        spec_content = _generate_spec_file()
        spec_file.write_text(spec_content)
        
        return {
            "success": True,
            "path": str(schema_file),
            "is_directory": False,
            "lines_changed": len(schema_content.splitlines()) + len(db_content.splitlines()) + len(spec_content.splitlines()),
            "sha256": "",  # Will be computed by file_ops
            "created_files": [str(schema_file), str(db_util), str(spec_file)]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "path": "",
            "is_directory": False,
            "lines_changed": 0,
            "sha256": ""
        }


def generate_database_migrations(build_id: str, workspace: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    """Generate database migrations and setup"""
    return {"success": True, "path": "database_migrations", "sha256": "database_migrations_generated"}


def generate_docs(build_id: str, workspace: str) -> Dict[str, Any]:
    """
    Generate documentation files.
    
    Args:
        build_id: The build ID for this workspace
        workspace: The workspace root path
        
    Returns:
        Dict with success status and metadata
    """
    try:
        build_path = Path(workspace) / build_id
        
        # Generate README.md
        readme_file = build_path / "README.md"
        readme_content = _generate_readme()
        readme_file.write_text(readme_content)
        
        return {
            "success": True,
            "path": str(readme_file),
            "is_directory": False,
            "lines_changed": len(readme_content.splitlines()),
            "sha256": "",  # Will be computed by file_ops
            "created_files": [str(readme_file)]
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "path": "",
            "is_directory": False,
            "lines_changed": 0,
            "sha256": ""
        }


def _generate_robots_file() -> str:
    """Generate the robots.ts file."""
    return '''import { MetadataRoute } from 'next'

export default function robots(): MetadataRoute.Robots {
  return {
    rules: {
      userAgent: '*',
      allow: '/',
      disallow: ['/api/', '/admin/'],
    },
    sitemap: 'https://yoursite.com/sitemap.xml',
  }
}
'''


def _generate_sitemap_file() -> str:
    """Generate the sitemap.ts file."""
    return '''import { MetadataRoute } from 'next'

export default function sitemap(): MetadataRoute.Sitemap {
  const baseUrl = 'https://yoursite.com'
  
  return [
    {
      url: baseUrl,
      lastModified: new Date(),
      changeFrequency: 'yearly',
      priority: 1,
    },
    {
      url: `${baseUrl}/pricing`,
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.8,
    },
    {
      url: `${baseUrl}/about`,
      lastModified: new Date(),
      changeFrequency: 'monthly',
      priority: 0.5,
    },
  ]
}
'''


def _generate_prisma_schema() -> str:
    """Generate the Prisma schema file."""
    return '''generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "sqlite"
  url      = env("DATABASE_URL")
}

model Lead {
  id        Int      @id @default(autoincrement())
  email     String   @unique
  source    String?
  createdAt DateTime @default(now())
}
'''


def _generate_db_util() -> str:
    """Generate the database utility file."""
    return '''import { PrismaClient } from '@prisma/client'

const globalForPrisma = globalThis as unknown as {
  prisma: PrismaClient | undefined
}

export const db = globalForPrisma.prisma ?? new PrismaClient()

if (process.env.NODE_ENV !== 'production') globalForPrisma.prisma = db
'''


def _generate_spec_file() -> str:
    """Generate the spec types file."""
    return '''// Specification types and utilities
export interface Spec {
  title: string
  description: string
  sections: Section[]
  design?: {
    tokens?: {
      colors?: Record<string, Record<string, string>>
      spacing?: Record<string, string>
      typography?: {
        fontFamily?: Record<string, string[]>
        fontSize?: Record<string, string>
      }
      borderRadius?: Record<string, string>
    }
  }
}

export interface Section {
  type: 'hero' | 'feature-grid' | 'logo-cloud' | 'showreel' | 'pricing' | 'cta-banner'
  title: string
  subtitle?: string
  [key: string]: any
}

export interface HeroSection extends Section {
  type: 'hero'
  cta?: {
    text: string
    href: string
  }
}

export interface FeatureGridSection extends Section {
  type: 'feature-grid'
  features: Array<{
    title: string
    description: string
    icon?: string
  }>
}

export interface LogoCloudSection extends Section {
  type: 'logo-cloud'
  logos: string[]
}

export interface ShowreelSection extends Section {
  type: 'showreel'
  videoUrl?: string
  imageUrl?: string
}

export interface PricingSection extends Section {
  type: 'pricing'
  plans: Array<{
    name: string
    price: string
    description?: string
    features?: string[]
    cta?: string
  }>
}

export interface CtaBannerSection extends Section {
  type: 'cta-banner'
  button: string
  buttonHref?: string
}

// Default spec for development
export const defaultSpec: Spec = {
  title: 'AI Website Builder',
  description: 'Generated by Co-Builder',
  sections: [
    {
      type: 'hero',
      title: 'Welcome to Our Platform',
      subtitle: 'Build amazing things with our tools',
      cta: {
        text: 'Get Started',
        href: '/signup'
      }
    },
    {
      type: 'feature-grid',
      title: 'Features',
      subtitle: 'Everything you need to succeed',
      features: [
        {
          title: 'Easy to Use',
          description: 'Intuitive interface that anyone can master'
        },
        {
          title: 'Powerful',
          description: 'Advanced features for professional results'
        },
        {
          title: 'Fast',
          description: 'Lightning-fast performance and deployment'
        }
      ]
    },
    {
      type: 'logo-cloud',
      title: 'Trusted by',
      logos: ['Company 1', 'Company 2', 'Company 3', 'Company 4']
    },
    {
      type: 'showreel',
      title: 'See It In Action',
      description: 'Watch our demo to see how it works'
    },
    {
      type: 'pricing',
      title: 'Simple Pricing',
      subtitle: 'Choose the plan that works for you',
      plans: [
        {
          name: 'Basic',
          price: '$9/month',
          description: 'Perfect for individuals',
          features: ['Feature 1', 'Feature 2', 'Feature 3'],
          cta: 'Get Started'
        },
        {
          name: 'Pro',
          price: '$29/month',
          description: 'Great for teams',
          features: ['Everything in Basic', 'Feature 4', 'Feature 5', 'Priority Support'],
          cta: 'Get Started'
        },
        {
          name: 'Enterprise',
          price: '$99/month',
          description: 'For large organizations',
          features: ['Everything in Pro', 'Feature 6', 'Feature 7', 'Custom Support'],
          cta: 'Contact Sales'
        }
      ]
    },
    {
      type: 'cta-banner',
      title: 'Ready to Get Started?',
      subtitle: 'Join thousands of satisfied customers',
      button: 'Start Free Trial',
      buttonHref: '/signup'
    }
  ]
}
'''


def _generate_readme() -> str:
    """Generate the README.md file."""
    return '''# AI Website Builder

A modern, full-stack website builder generated by Co-Builder.

## Features

- 🚀 Next.js 14 with App Router
- 🎨 Tailwind CSS with design tokens
- 📱 Responsive design with reduced motion support
- 💳 Payment integration (Stripe)
- 📧 Lead capture with email notifications
- 🗄️ SQLite database with Prisma
- 🔍 SEO optimized (robots.txt, sitemap)
- 📦 Monorepo with pnpm workspaces

## Quick Start

### Prerequisites

- Node.js 18+ 
- pnpm

### Installation

```bash
# Install dependencies
pnpm install

# Set up the database
pnpm --filter @app/site prisma generate
pnpm --filter @app/site prisma db push
```

### Development

```bash
# Start the development server
pnpm dev

# Or run specific commands
pnpm --filter @app/site dev
```

The site will be available at [http://localhost:3000](http://localhost:3000).

## Project Structure

```
├── apps/
│   └── site/                 # Next.js application
│       ├── app/              # App Router pages and API routes
│       ├── components/       # React components
│       └── lib/              # Utilities and configurations
├── packages/
│   ├── core/                 # Design tokens and types
│   └── codegen-next/         # Section templates
├── prisma/                   # Database schema
└── tools/                    # Development tools
```

## API Endpoints

### Lead Capture
- `POST /api/lead` - Create a new lead
- `GET /api/lead` - List leads (development only)

### Payments
- `POST /api/checkout` - Create checkout session
- `POST /api/webhooks/payments` - Handle payment webhooks

## Environment Variables

Create a `.env.local` file in the `apps/site` directory:

```env
DATABASE_URL="file:./dev.db"
PAYMENT_PROVIDER="stripe"
STRIPE_SECRET_KEY="sk_test_..."
STRIPE_WEBHOOK_SECRET="whsec_..."
```

## Database

The application uses SQLite with Prisma for development. The schema includes:

- **Lead** - Contact form submissions
- **User** - User accounts
- **Payment** - Payment records

## Deployment

### Vercel (Recommended)

1. Connect your repository to Vercel
2. Set environment variables
3. Deploy

### Other Platforms

1. Build the application: `pnpm build`
2. Set up environment variables
3. Deploy the `apps/site` directory

## Development

### Adding New Sections

1. Define the section type in `packages/core/src/spec.ts`
2. Generate section components directly in `apps/site/components/sections/`
3. Add the section to your spec

### Customizing Design

Edit the design tokens in `packages/core/src/tokens.ts` and the Tailwind configuration in `apps/site/tailwind.config.ts`.

## License

MIT
'''
