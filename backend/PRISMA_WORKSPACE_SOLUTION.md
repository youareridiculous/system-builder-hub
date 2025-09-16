# Prisma Workspace Solution

## Problem

Prisma CLI's auto-installation behavior causes `ERR_PNPM_RECURSIVE_RUN_FIRST_FAIL` errors when running in pnpm workspaces. This happens because Prisma tries to install dependencies during recursive pnpm operations, which is forbidden.

## Solution: Root-Pinned Prisma Pattern

We implement a "Root-Pinned Prisma Pattern" that:

1. **Pins Prisma CLI at the repo root** as a `devDependency`
2. **Always runs `prisma` from root** (workspace context)
3. **Generates the Prisma client into the site package's `node_modules`** by setting `generator client.output` relative to `prisma/schema.prisma`
4. **Makes site scripts delegate to root scripts** so the site never invokes Prisma in a way that triggers auto-install

## Implementation

### Root Package.json

```json
{
  "name": "@sbh/monorepo",
  "private": true,
  "workspaces": ["apps/*", "packages/*"],
  "devDependencies": {
    "prisma": "5.22.0",
    "turbo": "2.5.6"
  },
  "trustedDependencies": ["@prisma/client", "@prisma/engines", "prisma"],
  "scripts": {
    "prisma": "prisma",
    "db:generate": "prisma generate --schema=prisma/schema.prisma",
    "db:migrate": "prisma migrate dev --name init --schema=prisma/schema.prisma --skip-generate"
  }
}
```

### Site Package.json

```json
{
  "name": "@app/site",
  "private": true,
  "scripts": {
    "dev": "next dev -p 3000",
    "build": "next build",
    "start": "next start -p 3000",
    "db:generate": "pnpm -w run db:generate",
    "db:migrate": "pnpm -w run db:migrate"
  },
  "dependencies": {
    "@prisma/client": "5.22.0"
  },
  "devDependencies": {
    // Note: NO "prisma" here - root owns the CLI
  },
  "prisma": {
    "schema": "../../prisma/schema.prisma"
  }
}
```

### Prisma Schema

```prisma
generator client {
  provider = "prisma-client-js"
  // Output client into the site package:
  output   = "./apps/site/node_modules/@prisma/client"
}

datasource db {
  provider = "sqlite"
  url      = env("DATABASE_URL")
}

model Lead {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  company   String?
  phone     String?
  message   String?
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  @@map("leads")
}
```

## Usage

### From Root (Recommended)

```bash
# Generate Prisma client
pnpm run db:generate

# Run migrations
pnpm run db:migrate

# Direct Prisma commands
pnpm run prisma -- --help
```

### From Site Package

```bash
# These delegate to root automatically
pnpm --filter @app/site run db:generate
pnpm --filter @app/site run db:migrate
```

### Environment Variables

Create `.env` files:

**Root `.env`:**
```
DATABASE_URL="file:./apps/site/dev.db"
```

**`prisma/.env`:**
```
DATABASE_URL="file:../apps/site/dev.db"
```

## Benefits

1. **No Auto-Install Issues**: Prisma CLI is pinned at root, preventing auto-installation
2. **Workspace Compatibility**: All commands work within pnpm workspace constraints
3. **Clear Ownership**: Root owns Prisma CLI, site owns Prisma client
4. **Consistent Paths**: All Prisma operations use consistent schema paths
5. **No Interactive Prompts**: `trustedDependencies` prevents pnpm approval prompts

## Troubleshooting

### Common Issues

1. **"Could not load schema"**: Ensure `prisma/schema.prisma` exists at workspace root
2. **"Command failed with exit code 1"**: Check that Prisma CLI is installed at root
3. **"pnpm add @prisma/client" errors**: This is Prisma trying to auto-install - our pattern prevents this

### Verification

Check that the setup is correct:

```bash
# Verify Prisma CLI is at root
pnpm list prisma

# Verify @prisma/client is in site
pnpm --filter @app/site list @prisma/client

# Verify schema path
ls -la prisma/schema.prisma

# Test generation
pnpm run db:generate
```

## Migration from Legacy Setup

If you have an existing setup with Prisma in the site package:

1. **Remove Prisma from site**:
   ```bash
   pnpm --filter @app/site remove prisma
   ```

2. **Add Prisma to root**:
   ```bash
   pnpm add -D prisma@5.22.0
   ```

3. **Update site scripts** to delegate to root:
   ```json
   {
     "scripts": {
       "db:generate": "pnpm -w run db:generate",
       "db:migrate": "pnpm -w run db:migrate"
     }
   }
   ```

4. **Update Prisma schema** with correct output path:
   ```prisma
   generator client {
     provider = "prisma-client-js"
     output   = "./apps/site/node_modules/@prisma/client"
   }
   ```

5. **Add trustedDependencies** to root package.json:
   ```json
   {
     "trustedDependencies": ["@prisma/client", "@prisma/engines", "prisma"]
   }
   ```

This pattern ensures stable, predictable Prisma operations in pnpm workspaces without auto-installation issues.