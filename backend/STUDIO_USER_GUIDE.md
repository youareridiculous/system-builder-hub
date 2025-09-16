# AI Website Builder Studio - User Guide

## Overview

The AI Website Builder Studio is the control plane for building and managing AI-generated websites. It provides a comprehensive interface for uploading specifications, editing configurations, compiling websites, and deploying to production.

## Architecture

The system follows a two-plane architecture:

- **Control Plane (Studio)**: `apps/studio` - Next.js 14 app for managing specifications and compilation
- **Data Plane (Site)**: `apps/site` - Generated Next.js 14 website from specifications

## Getting Started

### 1. Build the System

```bash
# From the backend directory
PLAN=~/Downloads/"AI Website Builder System.docx"
TENANT=demo
backend/scripts/kickoff_full_build.sh "$PLAN" "$TENANT"
backend/scripts/watch_build.sh <BUILD_ID> "$TENANT"
```

### 2. Navigate to Workspace

```bash
cd backend/workspace/<BUILD_ID>
```

### 3. Install Dependencies

```bash
corepack enable && corepack prepare pnpm@latest --activate
pnpm install
```

### 4. Setup Database

```bash
pnpm run db:migrate
```

### 5. Start Both Applications

```bash
# Terminal 1: Start Studio (Control Plane)
pnpm --filter @app/studio dev

# Terminal 2: Start Site (Data Plane)  
pnpm --filter @app/site dev
```

## Studio Interface

### Home Dashboard (`/`)

The main dashboard provides access to all Studio features:

- **Spec Editor**: Upload and edit website specifications
- **Compile**: Generate websites from specifications
- **Preview**: Preview generated websites
- **Diff**: View changes from last compilation
- **Pricing**: Generate pricing from specifications
- **Deploy**: Deploy websites to production

### Spec Editor (`/spec`)

Upload and edit your website specification:

1. **Upload DOCX**: Drag and drop a DOCX file containing your specification
2. **Edit JSON**: Use the Monaco editor to edit the extracted JSON specification
3. **Validate**: Real-time validation using Zod schemas
4. **Save**: Save your specification for compilation

### Compile (`/compile`)

Generate your website from the specification:

1. **Select Spec**: Choose the specification to compile
2. **Compile**: Click "Compile Website" to generate the site
3. **Monitor**: Watch the compilation progress and logs
4. **Review**: Check the compilation results and file changes

### Preview (`/preview`)

Preview your generated website:

1. **Iframe Preview**: Embedded preview of the generated site
2. **Live Updates**: Real-time updates as you make changes
3. **Responsive**: Test different screen sizes

### Diff (`/diff`)

View changes from the last compilation:

1. **File Tree**: See which files were added, modified, or deleted
2. **Unified Diff**: View detailed changes in each file
3. **Rollback**: Option to revert changes if needed

### Pricing (`/pricing`)

Generate pricing information from your specification:

1. **Auto-Calculate**: Pricing based on sections, goals, and complexity
2. **Tier Options**: Multiple pricing tiers (Basic, Pro, Enterprise)
3. **Export**: Download pricing information

### Deploy (`/deploy`)

Deploy your website to production:

1. **Provider Selection**: Choose hosting provider (Vercel, Netlify, Custom)
2. **Domain Setup**: Configure custom domains
3. **SSL**: Automatic SSL certificate setup
4. **Deploy**: One-click deployment

## API Endpoints

### Compile API

```bash
POST /api/cobuilder/compile
{
  "spec": { /* specification object */ },
  "build_id": "build_demo_123"
}
```

### Spec Management

```bash
# Get spec
GET /api/cobuilder/spec?build_id=build_demo_123

# Save spec
POST /api/cobuilder/spec
{
  "spec": { /* specification object */ },
  "build_id": "build_demo_123"
}
```

### Diff API

```bash
GET /api/cobuilder/diff?build_id=build_demo_123
```

### Pricing API

```bash
POST /api/cobuilder/pricing
{
  "spec": { /* specification object */ }
}
```

## CLI Compilation

You can also compile specifications from the command line:

```bash
# Compile from default spec location
pnpm run compile:from-spec

# Compile from specific spec file
node scripts/compile-from-spec.js path/to/spec.json
```

## Specification Format

The specification follows this structure:

```json
{
  "brand": {
    "name": "Your Company",
    "tagline": "Your tagline",
    "description": "Your description",
    "logo": "path/to/logo.png"
  },
  "goals": [
    "Goal 1",
    "Goal 2"
  ],
  "sections": [
    {
      "id": "hero",
      "type": "hero",
      "title": "Welcome",
      "subtitle": "Subtitle",
      "content": {}
    }
  ],
  "payments": {
    "stripe": true,
    "pricing": [
      {
        "name": "Basic",
        "price": 99,
        "currency": "USD",
        "features": ["Feature 1", "Feature 2"]
      }
    ]
  },
  "hosting": {
    "provider": "vercel",
    "domain": "example.com"
  }
}
```

## Troubleshooting

### Common Issues

1. **Memory Issues**: If you encounter "JavaScript heap out of memory" errors, increase Node.js memory:
   ```bash
   NODE_OPTIONS="--max-old-space-size=8192" pnpm --filter @app/site dev
   ```

2. **Prisma Issues**: Ensure the database is properly set up:
   ```bash
   pnpm run db:generate
   pnpm run db:migrate
   ```

3. **Port Conflicts**: If ports 3000 or 3001 are in use, modify the package.json scripts to use different ports.

### Logs

Check the build logs for detailed information:

```bash
# View build logs
backend/scripts/watch_build.sh <BUILD_ID> <TENANT>

# View specific build logs
curl -H "X-Tenant-ID: demo" "http://127.0.0.1:5001/api/cobuilder/builds/<BUILD_ID>/logs"
```

## Development

### Adding New Features

1. **Studio Routes**: Add new routes in `apps/studio/app/`
2. **API Endpoints**: Add endpoints in `src/cobuilder/api/`
3. **Generators**: Add generators in `src/cobuilder/generators/`
4. **Packages**: Add packages in `packages/`

### Testing

```bash
# Run tests
PYTHONPATH=src pytest -q

# Run specific tests
PYTHONPATH=src pytest src/cobuilder/tests/test_*.py -v
```

## Support

For issues and questions:

1. Check the build logs for error details
2. Verify all dependencies are installed correctly
3. Ensure the database is properly configured
4. Check that all required files are present

The system is designed to be robust and provide clear error messages to help with troubleshooting.
