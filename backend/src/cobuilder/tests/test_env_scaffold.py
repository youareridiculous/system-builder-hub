"""
Tests for .env file creation in repo scaffold generator.
"""

import os
import tempfile
import shutil
from pathlib import Path
import sys

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from cobuilder.generators.repo_scaffold import _create_env_files


def test_env_files_created_on_fresh_scaffold():
    """Test that .env files are created with correct content on fresh scaffold."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Run the env creation function
        result = _create_env_files(temp_dir)
        
        # Check that both files were created
        assert result["root_env"]["status"] == "created"
        assert result["prisma_env"]["status"] == "created"
        
        # Check that files exist
        root_env_path = os.path.join(temp_dir, ".env")
        prisma_env_path = os.path.join(temp_dir, "prisma", ".env")
        
        assert os.path.exists(root_env_path), "Root .env file should exist"
        assert os.path.exists(prisma_env_path), "Prisma .env file should exist"
        
        # Check content
        with open(root_env_path, 'r') as f:
            root_content = f.read()
        assert 'DATABASE_URL="file:./apps/site/dev.db"' in root_content, "Root .env should contain correct DATABASE_URL"
        
        with open(prisma_env_path, 'r') as f:
            prisma_content = f.read()
        assert 'DATABASE_URL="file:../apps/site/dev.db"' in prisma_content, "Prisma .env should contain correct DATABASE_URL"


def test_env_files_not_overwritten():
    """Test that existing .env files are not overwritten."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Pre-create files with sentinel content
        root_env_path = os.path.join(temp_dir, ".env")
        prisma_env_path = os.path.join(temp_dir, "prisma", ".env")
        
        # Ensure prisma directory exists
        os.makedirs(os.path.dirname(prisma_env_path), exist_ok=True)
        
        sentinel_content = "SENTINEL_CONTENT=test\n"
        with open(root_env_path, 'w') as f:
            f.write(sentinel_content)
        with open(prisma_env_path, 'w') as f:
            f.write(sentinel_content)
        
        # Run the env creation function
        result = _create_env_files(temp_dir)
        
        # Check that both files were marked as existing
        assert result["root_env"]["status"] == "exists"
        assert result["prisma_env"]["status"] == "exists"
        
        # Check that content was not changed
        with open(root_env_path, 'r') as f:
            root_content = f.read()
        assert root_content == sentinel_content, "Root .env content should not be changed"
        
        with open(prisma_env_path, 'r') as f:
            prisma_content = f.read()
        assert prisma_content == sentinel_content, "Prisma .env content should not be changed"


def test_verifier_warns_when_env_missing():
    """Test that verifier warns when .env files are missing but still passes."""
    # This test would require setting up a minimal workspace and running the verifier
    # For now, we'll just verify the function exists and can be imported
    from cobuilder.verifiers.pass1_verifier import verify_pass1_bootable
    
    # Create a minimal workspace structure
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create basic structure
        os.makedirs(os.path.join(temp_dir, "apps", "site", "app"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "prisma"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "packages", "core", "src"), exist_ok=True)
        os.makedirs(os.path.join(temp_dir, "packages", "codegen-next"), exist_ok=True)
        
        # Create minimal package.json files
        import json
        
        # Root package.json
        root_package = {
            "name": "@sbh/monorepo",
            "private": True,
            "workspaces": ["apps/*", "packages/*"],
            "trustedDependencies": ["@prisma/client", "@prisma/engines", "prisma"],
            "devDependencies": {
                "prisma": "5.22.0"
            },
            "scripts": {
                "db:generate": "prisma generate --schema=prisma/schema.prisma",
                "db:migrate": "prisma migrate dev --name init --schema=prisma/schema.prisma --skip-generate"
            }
        }
        with open(os.path.join(temp_dir, "package.json"), 'w') as f:
            json.dump(root_package, f)
        
        # Site package.json
        site_package = {
            "name": "@app/site",
            "private": True,
            "scripts": {
                "db:generate": "pnpm -w run db:generate",
                "db:migrate": "pnpm -w run db:migrate"
            },
            "prisma": {
                "schema": "../../prisma/schema.prisma"
            }
        }
        with open(os.path.join(temp_dir, "apps", "site", "package.json"), 'w') as f:
            json.dump(site_package, f)
        
        # Prisma schema
        prisma_schema = """generator client {
  provider = "prisma-client-js"
  output   = "../apps/site/node_modules/@prisma/client"
}

datasource db {
  provider = "sqlite"
  url      = env("DATABASE_URL")
}

model Lead {
  id        String   @id @default(cuid())
  email     String   @unique
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt
}"""
        with open(os.path.join(temp_dir, "prisma", "schema.prisma"), 'w') as f:
            f.write(prisma_schema)
        
        # Next.js config
        with open(os.path.join(temp_dir, "apps", "site", "next.config.mjs"), 'w') as f:
            f.write("export default {}")
        
        # App files
        with open(os.path.join(temp_dir, "apps", "site", "app", "page.tsx"), 'w') as f:
            f.write("export default function Page() { return <main>Test</main> }")
        
        with open(os.path.join(temp_dir, "apps", "site", "app", "layout.tsx"), 'w') as f:
            f.write("export default function Layout({ children }) { return <html>{children}</html> }")
        
        # API route
        os.makedirs(os.path.join(temp_dir, "apps", "site", "app", "api", "lead"), exist_ok=True)
        with open(os.path.join(temp_dir, "apps", "site", "app", "api", "lead", "route.ts"), 'w') as f:
            f.write("export async function POST() { return Response.json({ ok: true }) }")
        
        # Core tokens
        with open(os.path.join(temp_dir, "packages", "core", "src", "tokens.ts"), 'w') as f:
            f.write("export const tokens = {}")
        
        # Codegen package
        codegen_package = {"name": "@sbh/codegen-next"}
        with open(os.path.join(temp_dir, "packages", "codegen-next", "package.json"), 'w') as f:
            json.dump(codegen_package, f)
        
        # Add missing required files
        with open(os.path.join(temp_dir, "pnpm-workspace.yaml"), 'w') as f:
            f.write("packages:\n  - 'apps/*'\n  - 'packages/*'")
        
        with open(os.path.join(temp_dir, "README.md"), 'w') as f:
            f.write("# Test Project")
        
        with open(os.path.join(temp_dir, "apps", "site", "tailwind.config.ts"), 'w') as f:
            f.write("export default {}")
        
        with open(os.path.join(temp_dir, "apps", "site", "postcss.config.js"), 'w') as f:
            f.write("module.exports = {}")
        
        with open(os.path.join(temp_dir, "apps", "site", "tsconfig.json"), 'w') as f:
            f.write("{}")
        
        with open(os.path.join(temp_dir, "apps", "site", "app", "globals.css"), 'w') as f:
            f.write("/* global styles */")
        
        # API checkout route
        os.makedirs(os.path.join(temp_dir, "apps", "site", "app", "api", "checkout"), exist_ok=True)
        with open(os.path.join(temp_dir, "apps", "site", "app", "api", "checkout", "route.ts"), 'w') as f:
            f.write("import Stripe from 'stripe';\nexport async function POST() { return Response.json({ ok: true }) }")
        
        # SEO files
        with open(os.path.join(temp_dir, "apps", "site", "app", "robots.ts"), 'w') as f:
            f.write("export default function robots() { return {} }")
        
        with open(os.path.join(temp_dir, "apps", "site", "app", "sitemap.ts"), 'w') as f:
            f.write("export default function sitemap() { return [] }")
        
        # Core package
        core_package = {"name": "@sbh/core"}
        with open(os.path.join(temp_dir, "packages", "core", "package.json"), 'w') as f:
            json.dump(core_package, f)
        
        # Section components
        os.makedirs(os.path.join(temp_dir, "apps", "site", "components", "sections"), exist_ok=True)
        for component in ["Hero.tsx", "FeatureGrid.tsx", "LogoCloud.tsx", "Showreel.tsx", "Pricing.tsx", "CtaBanner.tsx"]:
            with open(os.path.join(temp_dir, "apps", "site", "components", "sections", component), 'w') as f:
                f.write(f"export default function {component[:-4]}() {{ return <div>{component[:-4]}</div> }}")
        
        # Lib directory
        os.makedirs(os.path.join(temp_dir, "apps", "site", "lib"), exist_ok=True)
        
        # Codegen src
        os.makedirs(os.path.join(temp_dir, "packages", "codegen-next", "src"), exist_ok=True)
        
        # Run verifier (should pass with warnings about missing .env)
        warnings = []
        def log_fn(msg):
            warnings.append(msg)
        
        ok, missing = verify_pass1_bootable(temp_dir, log_fn)
        
        # Should pass (bootable=True) even with missing .env files
        assert ok, f"Verifier should pass but failed with missing: {missing}"
        
        # Should have warnings about missing .env files
        env_warnings = [w for w in warnings if ".env" in w and "warn" in w]
        assert len(env_warnings) >= 2, f"Should have .env warnings, got: {env_warnings}"


if __name__ == "__main__":
    test_env_files_created_on_fresh_scaffold()
    test_env_files_not_overwritten()
    test_verifier_warns_when_env_missing()
    print("✅ All .env scaffold tests passed!")
