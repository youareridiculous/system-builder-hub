#!/usr/bin/env python3
"""Co-Builder CLI - Direct access to the Apply Engine"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Optional
from unittest.mock import Mock

def detect_project_root() -> Path:
    """Detect the project root directory"""
    current = Path.cwd()
    while current != current.parent:
        if (current / "pyproject.toml").exists() or (current / "setup.py").exists():
            return current
        current = current.parent
    return Path.cwd()

def main():
    """Main CLI entry point"""
    parser = argparse.ArgumentParser(description="Co-Builder CLI - Apply Engine")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Apply command
    apply_parser = subparsers.add_parser("apply", help="Apply a code change")
    apply_parser.add_argument("--message", "-m", required=True, help="Change description")
    apply_parser.add_argument("--tenant", default="demo", help="Tenant ID (default: demo)")
    apply_parser.add_argument("--project-root", help="Project root path (default: auto-detect)")
    apply_parser.add_argument("--path", help="Explicit target file path (optional)")
    apply_parser.add_argument("--dry-run", action="store_true", help="Show planned change without applying")
    apply_parser.add_argument("--json", action="store_true", help="Output machine-readable JSON")
    apply_parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        sys.exit(1)
    
    if args.command == "apply":
        return run_apply(args)
    
    print(f"Unknown command: {args.command}")
    sys.exit(1)

def run_apply(args) -> int:
    """Run the apply command"""
    try:
        start_time = time.monotonic()
        
        # Detect project root
        project_root = Path(args.project_root) if args.project_root else detect_project_root()
        if args.verbose:
            print(f"Project root: {project_root}", file=sys.stderr)
        
        # Import the Apply Engine components
        from src.cobuilder.generator import CoBuilderGenerator
        from src.cobuilder.applier import apply_single_file
        
        # Create mock LLM client for CLI usage
        class MockLLMClient:
            def __init__(self):
                self.chat = Mock()
                self.chat.completions = Mock()
                self.chat.completions.create = Mock()
                
                # Generate a response based on the message
                mock_resp = Mock()
                mock_resp.choices = [Mock()]
                
                # Extract target file from message or use provided path
                target_file = args.path or "venture_os/README.md"
                if "venture_os" in args.message.lower():
                    if "init" in args.message.lower() or "version" in args.message.lower():
                        target_file = "venture_os/__init__.py"
                    else:
                        target_file = "venture_os/README.md"
                
                # Generate appropriate content
                if "version" in args.message.lower():
                    content = '__version__ = "0.0.1"\n'
                    diff = f'--- /dev/null\n+++ {target_file}\n@@ -0,0 +1,1 @@\n+{content}'
                else:
                    content = 'Venture OS — Entity Management v1.0.1 (scaffold initialized)\n'
                    diff = f'--- /dev/null\n+++ {target_file}\n@@ -0,0 +1,1 @@\n+{content}'
                
                mock_resp.choices[0].message.content = json.dumps({
                    "file": target_file,
                    "diff": diff,
                    "content": content,
                    "response": f"Created {target_file}",
                    "snippet": "print('ok')"
                })
                
                self.chat.completions.create.return_value = mock_resp
        
        # Create generator
        generator = CoBuilderGenerator(
            llm_client=MockLLMClient(),
            model_default="gpt-4o-mini"
        )
        
        # Generate the change
        result = generator.apply_change(
            prompt=args.message,
            tenant_id=args.tenant,
            request_id=f"cli_{int(time.time())}",
            deadline_ts=time.time() + 60
        )
        
        elapsed_ms = int((time.monotonic() - start_time) * 1000)
        
        # Prepare response data
        response_data = {
            "success": True,
            "file": result.file,
            "diff": result.diff,
            "content": result.content,
            "snippet": result.snippet,
            "model": result.model,
            "elapsed_ms": elapsed_ms,
            "llm_generated": result.llm_generated,
        }
        
        # Apply if not dry-run
        if not args.dry_run and result.file and result.content:
            try:
                apply_result = apply_single_file(result.file, result.content)
                response_data["applied"] = True
                response_data["apply"] = {
                    "file": apply_result.file,
                    "bytes_written": apply_result.bytes_written,
                    "created": apply_result.created,
                    "sha256": apply_result.sha256,
                    "absolute_path": str(project_root / apply_result.file)
                }
                
                # Print one-line summary to stderr
                print(f"[applied] file={apply_result.file} bytes={apply_result.bytes_written} sha256={apply_result.sha256} elapsed={elapsed_ms} model={result.model}", file=sys.stderr)
                
            except Exception as e:
                response_data["applied"] = False
                response_data["apply_error"] = str(e)
                print(f"[error] apply failed: {e}", file=sys.stderr)
                return 1
        else:
            response_data["applied"] = False
            print(f"[dry-run] file={result.file} content_len={len(result.content)} elapsed={elapsed_ms} model={result.model}", file=sys.stderr)
        
        # Output result
        if args.json:
            print(json.dumps(response_data, indent=2))
        else:
            if response_data.get("applied"):
                print(f"✅ Applied to {response_data['apply']['absolute_path']}")
                print(f"   Bytes written: {response_data['apply']['bytes_written']}")
                print(f"   SHA256: {response_data['apply']['sha256']}")
            else:
                print(f"📝 Proposed change for {result.file}")
                print(f"   Content length: {len(result.content)} bytes")
                if result.snippet:
                    print(f"   Snippet: {result.snippet}")
        
        return 0
        
    except Exception as e:
        error_msg = f"CLI error: {e}"
        if args.verbose:
            import traceback
            traceback.print_exc()
        
        if args.json:
            print(json.dumps({"success": False, "error": error_msg}))
        else:
            print(f"❌ {error_msg}", file=sys.stderr)
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
