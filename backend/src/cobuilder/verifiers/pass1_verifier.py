"""
Pass-1 Bootable Verifier

Verifies that the generated Next.js 14 monorepo is bootable by checking for required files
and performing lightweight content validation.
"""

import os
import json
from typing import List, Tuple, Callable, Optional


def verify_pass1_bootable(workspace_dir: str, log_fn: Optional[Callable[[str], None]] = None) -> Tuple[bool, List[str]]:
    """
    Verify that the Pass-1 generated workspace is bootable.
    
    Args:
        workspace_dir: Path to the workspace root directory
        log_fn: Optional logging function (e.g., registry.append_log)
        
    Returns:
        Tuple of (is_bootable: bool, missing_files: List[str])
    """
    missing = []
    debug_mode = os.environ.get('COB_DEBUG_VERIFY', '0') == '1'
    
    def log(msg: str):
        if log_fn:
            log_fn(msg)
    
    # Required files for a bootable Next.js 14 monorepo
    required_files = [
        # Root configuration
        "package.json",
        "pnpm-workspace.yaml", 
        "README.md",
        
        # Site app configuration
        "apps/site/package.json",
        "apps/site/tailwind.config.ts",
        "apps/site/postcss.config.js",
        "apps/site/tsconfig.json",
        "apps/site/next.config.mjs",
        
        # Site app structure
        "apps/site/app/layout.tsx",
        "apps/site/app/page.tsx",
        "apps/site/app/globals.css",
        
        # API routes
        "apps/site/app/api/lead/route.ts",
        "apps/site/app/api/checkout/route.ts",
        
        # SEO files
        "apps/site/app/robots.ts",
        "apps/site/app/sitemap.ts",
        
        # Database
        "prisma/schema.prisma",
        
        # Packages
        "packages/core/package.json",
        "packages/core/src/tokens.ts",
        "packages/codegen-next/package.json",
        
        # Studio app
        "apps/studio/package.json",
        "apps/studio/next.config.mjs",
        "apps/studio/app/page.tsx",
        "apps/studio/app/layout.tsx",
        
        # Compiler packages
        "packages/compiler/package.json",
        "packages/validators/package.json",
        "packages/integrations/package.json",
        "packages/infra/package.json",
        "packages/runtime/package.json",
    ]
    
    # Check required files
    for file_path in required_files:
        full_path = os.path.join(workspace_dir, file_path)
        if not os.path.exists(full_path):
            missing.append(file_path)
            log(f"[VERIFY] missing: {file_path}")
        elif debug_mode:
            log(f"[VERIFY] ok: {file_path}")
    
    # Check that next.config.ts does NOT exist (should be next.config.mjs)
    next_config_ts_path = os.path.join(workspace_dir, "apps/site/next.config.ts")
    if os.path.exists(next_config_ts_path):
        missing.append("apps/site/next.config.ts (should not exist, use next.config.mjs)")
        log(f"[VERIFY] missing: apps/site/next.config.ts (should not exist, use next.config.mjs)")
    
    # Check required directories
    required_dirs = [
        "apps/site",
        "apps/site/app",
        "apps/site/app/api",
        "apps/site/app/api/lead",
        "apps/site/app/api/checkout",
        "apps/site/components",
        "apps/site/components/sections",
        "apps/site/lib",
        "packages/core",
        "packages/core/src",
        "packages/codegen-next",
        "packages/codegen-next/src",
        "packages/compiler",
        "packages/compiler/src",
        "packages/validators",
        "packages/validators/src",
        "packages/integrations",
        "packages/integrations/src",
        "packages/infra",
        "packages/infra/src",
        "packages/runtime",
        "packages/runtime/src",
        "apps/studio",
        "apps/studio/app",
        "apps/studio/components",
        "apps/studio/lib",
        "apps/studio/types",
        "apps/studio/storage",
        "prisma",
    ]
    
    for dir_path in required_dirs:
        full_path = os.path.join(workspace_dir, dir_path)
        if not os.path.isdir(full_path):
            missing.append(f"{dir_path}/")
            log(f"[VERIFY] missing: {dir_path}/")
        elif debug_mode:
            log(f"[VERIFY] ok: {dir_path}/")
    
    # Check section components (at least 6)
    required_sections = [
        "apps/site/components/sections/Hero.tsx",
        "apps/site/components/sections/FeatureGrid.tsx", 
        "apps/site/components/sections/LogoCloud.tsx",
        "apps/site/components/sections/Showreel.tsx",
        "apps/site/components/sections/Pricing.tsx",
        "apps/site/components/sections/CtaBanner.tsx",
    ]
    
    for section_path in required_sections:
        full_path = os.path.join(workspace_dir, section_path)
        if not os.path.exists(full_path):
            missing.append(section_path)
            log(f"[VERIFY] missing: {section_path}")
        elif debug_mode:
            log(f"[VERIFY] ok: {section_path}")
    
    # Lightweight content checks
    content_checks_passed = True
    
    # Check root package.json has trustedDependencies and Prisma CLI
    root_package_json = os.path.join(workspace_dir, "package.json")
    if os.path.exists(root_package_json):
        try:
            with open(root_package_json, 'r') as f:
                root_package = json.load(f)
            
            # Check trustedDependencies
            trusted_deps = root_package.get("trustedDependencies", [])
            required_trusted = ["@prisma/client", "@prisma/engines", "prisma"]
            if not all(dep in trusted_deps for dep in required_trusted):
                missing.append("package.json (missing trustedDependencies for Prisma)")
                content_checks_passed = False
                log(f"[VERIFY] missing: package.json (missing trustedDependencies for Prisma)")
            
            # Check Prisma CLI in devDependencies
            dev_deps = root_package.get("devDependencies", {})
            if dev_deps.get("prisma") != "5.22.0":
                missing.append("package.json (missing prisma@5.22.0 in devDependencies)")
                content_checks_passed = False
                log(f"[VERIFY] missing: package.json (missing prisma@5.22.0 in devDependencies)")
            
            # Check root scripts
            scripts = root_package.get("scripts", {})
            if scripts.get("db:generate") != "prisma generate --schema=prisma/schema.prisma":
                missing.append("package.json (missing correct db:generate script)")
                content_checks_passed = False
                log(f"[VERIFY] missing: package.json (missing correct db:generate script)")
            
            if scripts.get("db:migrate") != "prisma migrate dev --name init --schema=prisma/schema.prisma --skip-generate":
                missing.append("package.json (missing correct db:migrate script)")
                content_checks_passed = False
                log(f"[VERIFY] missing: package.json (missing correct db:migrate script)")
                
        except Exception as e:
            missing.append("package.json (invalid JSON)")
            content_checks_passed = False
            log(f"[VERIFY] missing: package.json (invalid JSON: {e})")
    
    # Check apps/site/package.json has correct name and Prisma schema pointer
    site_package_path = os.path.join(workspace_dir, "apps/site/package.json")
    if os.path.exists(site_package_path):
        try:
            with open(site_package_path, 'r') as f:
                site_package = json.load(f)
            if site_package.get("name") != "@app/site":
                missing.append("apps/site/package.json (incorrect name)")
                content_checks_passed = False
                log(f"[VERIFY] missing: apps/site/package.json (incorrect name: {site_package.get('name')})")
            
            # Check Prisma schema pointer
            prisma_config = site_package.get("prisma", {})
            if prisma_config.get("schema") != "../../prisma/schema.prisma":
                missing.append("apps/site/package.json (missing Prisma schema pointer)")
                content_checks_passed = False
                log(f"[VERIFY] missing: apps/site/package.json (missing Prisma schema pointer)")
            
            # Check scripts delegate to root
            scripts = site_package.get("scripts", {})
            if scripts.get("db:generate") != "pnpm -w run db:generate":
                missing.append("apps/site/package.json (db:generate should delegate to root)")
                content_checks_passed = False
                log(f"[VERIFY] missing: apps/site/package.json (db:generate should delegate to root)")
            
            if scripts.get("db:migrate") != "pnpm -w run db:migrate":
                missing.append("apps/site/package.json (db:migrate should delegate to root)")
                content_checks_passed = False
                log(f"[VERIFY] missing: apps/site/package.json (db:migrate should delegate to root)")
            
            # Check that prisma is NOT in devDependencies (root owns it)
            dev_deps = site_package.get("devDependencies", {})
            if "prisma" in dev_deps:
                missing.append("apps/site/package.json (prisma should not be in devDependencies)")
                content_checks_passed = False
                log(f"[VERIFY] missing: apps/site/package.json (prisma should not be in devDependencies)")
            
            # Check for TypeScript types (warning, not failure)
            if "@types/node" not in dev_deps:
                log(f"[VERIFY] warn: apps/site/package.json (missing @types/node - Next.js may auto-install via npm)")
            if "@types/react" not in dev_deps:
                log(f"[VERIFY] warn: apps/site/package.json (missing @types/react - Next.js may auto-install via npm)")
                
        except Exception as e:
            missing.append("apps/site/package.json (invalid JSON)")
            content_checks_passed = False
            log(f"[VERIFY] missing: apps/site/package.json (invalid JSON: {e})")
    
    # Check prisma/schema.prisma contains model Lead and correct generator output
    prisma_schema_path = os.path.join(workspace_dir, "prisma/schema.prisma")
    if os.path.exists(prisma_schema_path):
        try:
            with open(prisma_schema_path, 'r') as f:
                schema_content = f.read()
            if "model Lead" not in schema_content:
                missing.append("prisma/schema.prisma (missing model Lead)")
                content_checks_passed = False
                log(f"[VERIFY] missing: prisma/schema.prisma (missing model Lead)")
            
            # Check generator output path
            if 'output   = "../apps/site/node_modules/@prisma/client"' not in schema_content:
                missing.append("prisma/schema.prisma (missing correct generator output path)")
                content_checks_passed = False
                log(f"[VERIFY] missing: prisma/schema.prisma (missing correct generator output path)")
        except Exception as e:
            missing.append("prisma/schema.prisma (read error)")
            content_checks_passed = False
            log(f"[VERIFY] missing: prisma/schema.prisma (read error: {e})")
    
    # Check apps/site/app/page.tsx contains expected content
    page_path = os.path.join(workspace_dir, "apps/site/app/page.tsx")
    if os.path.exists(page_path):
        try:
            with open(page_path, 'r') as f:
                page_content = f.read()
            # Check for basic React component structure
            if not ("export default function" in page_content and 
                   ("<main>" in page_content or "return (" in page_content)):
                missing.append("apps/site/app/page.tsx (missing expected content)")
                content_checks_passed = False
                log(f"[VERIFY] missing: apps/site/app/page.tsx (missing expected content)")
        except Exception as e:
            missing.append("apps/site/app/page.tsx (read error)")
            content_checks_passed = False
            log(f"[VERIFY] missing: apps/site/app/page.tsx (read error: {e})")
    
    # Check .env files (warning, not failure)
    root_env_path = os.path.join(workspace_dir, ".env")
    if not os.path.exists(root_env_path):
        log(f"[VERIFY] warn: .env missing at workspace root; Prisma migrations may fail until it exists")
    else:
        log(f"[VERIFY] env ok: {root_env_path}")
    
    prisma_env_path = os.path.join(workspace_dir, "prisma", ".env")
    if not os.path.exists(prisma_env_path):
        log(f"[VERIFY] warn: prisma/.env missing; some tooling may not find DATABASE_URL")
    else:
        log(f"[VERIFY] env ok: {prisma_env_path}")
    
    # Check API routes have expected content
    lead_api_path = os.path.join(workspace_dir, "apps/site/app/api/lead/route.ts")
    if os.path.exists(lead_api_path):
        try:
            with open(lead_api_path, 'r') as f:
                lead_content = f.read()
            if "POST" not in lead_content or "ok: true" not in lead_content:
                missing.append("apps/site/app/api/lead/route.ts (missing expected content)")
                content_checks_passed = False
                log(f"[VERIFY] missing: apps/site/app/api/lead/route.ts (missing expected content)")
        except Exception as e:
            missing.append("apps/site/app/api/lead/route.ts (read error)")
            content_checks_passed = False
            log(f"[VERIFY] missing: apps/site/app/api/lead/route.ts (read error: {e})")
    
    checkout_api_path = os.path.join(workspace_dir, "apps/site/app/api/checkout/route.ts")
    if os.path.exists(checkout_api_path):
        try:
            with open(checkout_api_path, 'r') as f:
                checkout_content = f.read()
            if "Stripe" not in checkout_content:
                missing.append("apps/site/app/api/checkout/route.ts (missing Stripe content)")
                content_checks_passed = False
                log(f"[VERIFY] missing: apps/site/app/api/checkout/route.ts (missing Stripe content)")
        except Exception as e:
            missing.append("apps/site/app/api/checkout/route.ts (read error)")
            content_checks_passed = False
            log(f"[VERIFY] missing: apps/site/app/api/checkout/route.ts (read error: {e})")
    
    # Determine if bootable
    is_bootable = len(missing) == 0 and content_checks_passed
    
    if is_bootable:
        log(f"[VERIFY] Pass-1 bootable: ok")
    else:
        log(f"[VERIFY] Pass-1 bootable: failed")
        if missing:
            log(f"[VERIFY] missing ({len(missing)}):")
            for item in missing:
                log(f" - {item}")
    
    return is_bootable, missing
