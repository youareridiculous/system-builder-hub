"""
Workspace utilities for Co-Builder builds
"""

import os
from typing import Dict, List, Any, Optional


def get_workspace_path(build_id: str) -> str:
    """Get the workspace path for a build"""
    workspace_root = os.environ.get('COB_WORKSPACE', 'workspace')
    return os.path.join(workspace_root, build_id)


def ensure_workspace_exists(build_id: str) -> str:
    """Ensure workspace directory exists and return the path"""
    workspace_path = get_workspace_path(build_id)
    os.makedirs(workspace_path, exist_ok=True)
    return workspace_path


def verify_bootable_repo(build_id: str) -> Dict[str, Any]:
    """
    Verify that the generated repo is bootable by checking for required files.
    Returns verification result with missing files if any.
    """
    workspace_path = get_workspace_path(build_id)
    
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
        "apps/site/components/sections/Feature_Grid.tsx",
        "apps/site/components/sections/Logo_Cloud.tsx",
        "apps/site/components/sections/Showreel.tsx",
        "apps/site/components/sections/Pricing.tsx",
        "apps/site/components/sections/Cta_Banner.tsx",
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


def get_build_summary(build_id: str) -> Dict[str, Any]:
    """Get a summary of the generated build"""
    workspace_path = get_workspace_path(build_id)
    verification = verify_bootable_repo(build_id)
    
    # Count files in key directories
    file_counts = {}
    key_dirs = ["apps/site", "packages/core", "packages/codegen-next", "prisma"]
    
    for dir_name in key_dirs:
        dir_path = os.path.join(workspace_path, dir_name)
        if os.path.exists(dir_path):
            count = sum(1 for _ in os.walk(dir_path) for _ in _[2])
            file_counts[dir_name] = count
        else:
            file_counts[dir_name] = 0
    
    return {
        "build_id": build_id,
        "workspace_path": workspace_path,
        "verification": verification,
        "file_counts": file_counts,
        "total_files": sum(file_counts.values())
    }
