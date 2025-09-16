#!/usr/bin/env python3
"""
Direct build script to bypass API issues and demonstrate the working generators.
"""

import sys
import os
import argparse
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.cobuilder.plan_parser import PlanParser
from src.cobuilder.orchestrator import FullBuildOrchestrator


def main():
    parser = argparse.ArgumentParser(description="Run Co-Builder directly")
    parser.add_argument("document", help="Path to the specification document")
    parser.add_argument("--tenant", default="demo", help="Tenant ID")
    args = parser.parse_args()
    
    # Read document content
    if args.document.endswith('.docx'):
        import subprocess
        result = subprocess.run(['textutil', '-convert', 'txt', '-stdout', '--', args.document], 
                              capture_output=True, text=True)
        if result.returncode != 0:
            print(f"Error converting docx: {result.stderr}")
            sys.exit(1)
        content = result.stdout
    else:
        with open(args.document, 'r') as f:
            content = f.read()
    
    print(f"📄 Processing document: {args.document}")
    print(f"👤 Tenant: {args.tenant}")
    print(f"📏 Content length: {len(content)} characters")
    print()
    
    # Parse the plan
    plan_parser = PlanParser()
    task_graph = plan_parser.parse_plan(content)
    
    print(f"🏗️  Plan parser generated {len(task_graph.nodes)} build steps:")
    for i, node in enumerate(task_graph.nodes, 1):
        print(f"  {i}. {node.task_id}")
    print()
    
    # Execute the build
    orchestrator = FullBuildOrchestrator()
    result = orchestrator.execute_task_graph(task_graph, args.tenant, f"direct-{int(time.time())}", "2025-09-08T04:30:00Z")
    
    print(f"✅ Build completed!")
    print(f"🆔 Build ID: {result.build_id}")
    print(f"📊 Status: {result.status}")
    print(f"📈 Completed steps: {result.completed_steps}/{len(result.steps)}")
    print(f"⏱️  Total time: {result.total_elapsed_ms}ms")
    
    if result.status.name == "COMPLETED":
        workspace_path = Path("workspace") / result.build_id
        print(f"📁 Workspace: {workspace_path.absolute()}")
        print()
        print("🚀 Next steps:")
        print(f"  cd {workspace_path}")
        print("  pnpm install")
        print("  pnpm --filter @app/site dev")
        print()
        print("🎯 Test the API:")
        print("  curl -X POST localhost:3000/api/lead -H 'Content-Type: application/json' \\")
        print("    -d '{\"email\":\"test@example.com\",\"source\":\"cli\"}'")
    else:
        print(f"❌ Build failed: {result.status}")
        for step in result.steps:
            if step.error:
                print(f"  - {step.step_id}: {step.error}")


if __name__ == "__main__":
    import time
    main()
