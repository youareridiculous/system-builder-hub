"""
Pass-1 Orchestrator for generating a complete bootable Next.js monorepo
"""

import os
import logging
from typing import Dict, List, Any, Optional

from .repo_scaffold import generate_repo_scaffold
from .tokens_tailwind import generate_tokens_tailwind
from .sections_codegen import generate_sections_codegen
from .api_generators import generate_lead_api, generate_payments_router
from .seo_prisma_docs import generate_seo_files, generate_prisma_schema, generate_docs
from ..workspace_utils import get_workspace_path, verify_bootable_repo


def _verify_bootable_repo_at_path(workspace_path: str) -> Dict[str, Any]:
    """
    Verify that the generated repo is bootable by checking for required files at a specific path.
    This is a helper function that doesn't rely on environment variables.
    """
    # Required files for a bootable Next.js monorepo
    required_files = [
        "package.json",  # Root package.json
        "pnpm-workspace.yaml",  # pnpm workspace config
        "apps/site/package.json",  # Site package.json
        "prisma/schema.prisma",  # Prisma schema
    ]
    
    # Required directories
    required_dirs = [
        "apps/site",
        "packages/core",
        "packages/codegen-next",
        "prisma",
    ]
    
    # Required section components (at least 6)
    required_sections = [
        "apps/site/components/sections/Hero.tsx",
        "apps/site/components/sections/FeatureGrid.tsx",
        "apps/site/components/sections/LogoCloud.tsx",
        "apps/site/components/sections/Showreel.tsx",
        "apps/site/components/sections/Pricing.tsx",
        "apps/site/components/sections/CtaBanner.tsx",
    ]
    
    missing_files = []
    missing_dirs = []
    missing_sections = []
    
    # Check required files
    for file_path in required_files:
        full_path = os.path.join(workspace_path, file_path)
        if not os.path.exists(full_path):
            missing_files.append(file_path)
    
    # Check required directories
    for dir_path in required_dirs:
        full_path = os.path.join(workspace_path, dir_path)
        if not os.path.isdir(full_path):
            missing_dirs.append(dir_path)
    
    # Check required section components
    for section_path in required_sections:
        full_path = os.path.join(workspace_path, section_path)
        if not os.path.exists(full_path):
            missing_sections.append(section_path)
    
    # Check if main page exists
    main_page_path = os.path.join(workspace_path, "apps/site/app/page.tsx")
    has_main_page = os.path.exists(main_page_path)
    
    # Check if API routes exist
    lead_api_path = os.path.join(workspace_path, "apps/site/app/api/lead/route.ts")
    checkout_api_path = os.path.join(workspace_path, "apps/site/app/api/checkout/route.ts")
    has_lead_api = os.path.exists(lead_api_path)
    has_checkout_api = os.path.exists(checkout_api_path)
    
    # Determine if bootable
    is_bootable = (
        len(missing_files) == 0 and
        len(missing_dirs) == 0 and
        len(missing_sections) == 0 and
        has_main_page and
        has_lead_api and
        has_checkout_api
    )
    
    return {
        "is_bootable": is_bootable,
        "workspace_path": workspace_path,
        "missing_files": missing_files,
        "missing_dirs": missing_dirs,
        "missing_sections": missing_sections,
        "has_main_page": has_main_page,
        "has_lead_api": has_lead_api,
        "has_checkout_api": has_checkout_api,
        "total_files_checked": len(required_files) + len(required_sections) + 3,  # +3 for main page and APIs
        "files_present": len(required_files) + len(required_sections) + 3 - len(missing_files) - len(missing_sections) - (0 if has_main_page else 1) - (0 if has_lead_api else 1) - (0 if has_checkout_api else 1)
    }

logger = logging.getLogger(__name__)


def generate_pass1_demo(build_id: str, workspace: str, spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a complete Pass-1 demo with all 8 generators in the correct order.
    This is the main entry point for the API orchestration.
    """
    try:
        logger.info(f"Starting Pass-1 demo generation for build {build_id}")
        
        # Step 1: Repository Scaffold
        logger.info("Step 1/8: Generating repository scaffold")
        scaffold_result = generate_repo_scaffold(build_id, workspace)
        if not scaffold_result["success"]:
            return {
                "success": False,
                "error": f"Repository scaffold failed: {scaffold_result.get('error', 'Unknown error')}",
                "step": "repo_scaffold"
            }
        
        # Step 2: Design Tokens & Tailwind
        logger.info("Step 2/8: Generating design tokens and Tailwind config")
        tokens_result = generate_tokens_tailwind(build_id, workspace, spec)
        if not tokens_result["success"]:
            return {
                "success": False,
                "error": f"Tokens generation failed: {tokens_result.get('error', 'Unknown error')}",
                "step": "tokens_tailwind"
            }
        
        # Step 3: Section Components
        logger.info("Step 3/8: Generating section components")
        sections_result = generate_sections_codegen(build_id, workspace, spec)
        if not sections_result["success"]:
            return {
                "success": False,
                "error": f"Sections generation failed: {sections_result.get('error', 'Unknown error')}",
                "step": "sections_codegen"
            }
        
        # Step 4: Lead API
        logger.info("Step 4/8: Generating lead API")
        lead_api_result = generate_lead_api(build_id, workspace)
        if not lead_api_result["success"]:
            return {
                "success": False,
                "error": f"Lead API generation failed: {lead_api_result.get('error', 'Unknown error')}",
                "step": "lead_api"
            }
        
        # Step 5: Payments Router
        logger.info("Step 5/8: Generating payments router")
        payments_result = generate_payments_router(build_id, workspace)
        if not payments_result["success"]:
            return {
                "success": False,
                "error": f"Payments router generation failed: {payments_result.get('error', 'Unknown error')}",
                "step": "payments_router"
            }
        
        # Step 6: SEO Files
        logger.info("Step 6/8: Generating SEO files")
        seo_result = generate_seo_files(build_id, workspace, spec)
        if not seo_result["success"]:
            return {
                "success": False,
                "error": f"SEO generation failed: {seo_result.get('error', 'Unknown error')}",
                "step": "seo_files"
            }
        
        # Step 7: Prisma Schema
        logger.info("Step 7/8: Generating Prisma schema")
        prisma_result = generate_prisma_schema(build_id, workspace)
        if not prisma_result["success"]:
            return {
                "success": False,
                "error": f"Prisma generation failed: {prisma_result.get('error', 'Unknown error')}",
                "step": "prisma_schema"
            }
        
        # Step 8: Documentation
        logger.info("Step 8/8: Generating documentation")
        docs_result = generate_docs(build_id, workspace)
        if not docs_result["success"]:
            return {
                "success": False,
                "error": f"Documentation generation failed: {docs_result.get('error', 'Unknown error')}",
                "step": "docs"
            }
        
        # Post-build verification
        logger.info("Running post-build verification")
        # Use the actual workspace path where files were created
        actual_workspace_path = os.path.join(workspace, build_id)
        verification = _verify_bootable_repo_at_path(actual_workspace_path)
        
        if not verification["is_bootable"]:
            missing_items = []
            missing_items.extend(verification["missing_files"])
            missing_items.extend(verification["missing_dirs"])
            missing_items.extend(verification["missing_sections"])
            if not verification["has_main_page"]:
                missing_items.append("apps/site/app/page.tsx")
            if not verification["has_lead_api"]:
                missing_items.append("apps/site/app/api/lead/route.ts")
            if not verification["has_checkout_api"]:
                missing_items.append("apps/site/app/api/checkout/route.ts")
            
            return {
                "success": False,
                "error": f"Build verification failed. Missing: {', '.join(missing_items)}",
                "step": "verification",
                "verification": verification
            }
        
        # Success summary
        workspace_path = get_workspace_path(build_id)
        summary = {
            "success": True,
            "build_id": build_id,
            "workspace_path": workspace_path,
            "bootable": True,
            "verification": verification,
            "steps_completed": 8,
            "generated_files": {
                "repo_scaffold": scaffold_result.get("path", ""),
                "tokens_tailwind": tokens_result.get("path", ""),
                "sections_codegen": sections_result.get("path", ""),
                "lead_api": lead_api_result.get("path", ""),
                "payments_router": payments_result.get("path", ""),
                "seo_files": seo_result.get("path", ""),
                "prisma_schema": prisma_result.get("path", ""),
                "docs": docs_result.get("path", "")
            },
            "key_paths": {
                "root_package_json": os.path.join(workspace_path, "package.json"),
                "site_package_json": os.path.join(workspace_path, "apps/site/package.json"),
                "prisma_schema": os.path.join(workspace_path, "prisma/schema.prisma"),
                "main_page": os.path.join(workspace_path, "apps/site/app/page.tsx"),
                "lead_api": os.path.join(workspace_path, "apps/site/app/api/lead/route.ts"),
                "checkout_api": os.path.join(workspace_path, "apps/site/app/api/checkout/route.ts")
            }
        }
        
        logger.info(f"Pass-1 demo generation completed successfully for build {build_id}")
        return summary
        
    except Exception as e:
        logger.error(f"Pass-1 demo generation failed: {e}")
        return {
            "success": False,
            "error": f"Pass-1 generation failed: {str(e)}",
            "step": "orchestration"
        }
