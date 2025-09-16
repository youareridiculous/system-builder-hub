#!/usr/bin/env python3
"""
Test runner for SBH Meta-Builder v2
Runs comprehensive test suite with coverage and reporting.
"""

import sys
import os
import subprocess
import argparse
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print('='*60)
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running {description}:")
        print(f"Exit code: {e.returncode}")
        print(f"STDOUT: {e.stdout}")
        print(f"STDERR: {e.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description='Run SBH Meta-Builder v2 tests')
    parser.add_argument('--unit', action='store_true', help='Run unit tests only')
    parser.add_argument('--integration', action='store_true', help='Run integration tests only')
    parser.add_argument('--coverage', action='store_true', help='Run with coverage')
    parser.add_argument('--verbose', '-v', action='store_true', help='Verbose output')
    parser.add_argument('--parallel', '-n', type=int, default=1, help='Number of parallel processes')
    parser.add_argument('--pattern', '-k', help='Test pattern to match')
    parser.add_argument('--html-report', action='store_true', help='Generate HTML coverage report')
    
    args = parser.parse_args()
    
    # Ensure we're in the right directory
    project_root = Path(__file__).parent.parent
    os.chdir(project_root)
    
    # Add src to Python path
    sys.path.insert(0, str(project_root / 'src'))
    
    # Build pytest command
    cmd = ['python', '-m', 'pytest']
    
    if args.verbose:
        cmd.append('-v')
    
    if args.parallel > 1:
        cmd.extend(['-n', str(args.parallel)])
    
    if args.pattern:
        cmd.extend(['-k', args.pattern])
    
    if args.coverage:
        cmd.extend([
            '--cov=src',
            '--cov-report=term-missing',
            '--cov-report=html:htmlcov' if args.html_report else '--cov-report=term'
        ])
    
    # Add test files
    if args.unit:
        cmd.append('tests/test_meta_builder_v2.py::TestMetaBuilderV2Models')
        cmd.append('tests/test_meta_builder_v2.py::TestMetaBuilderV2Agents')
        cmd.append('tests/test_meta_builder_v2.py::TestMetaBuilderV2Orchestrator')
        cmd.append('tests/test_meta_builder_v2.py::TestMetaBuilderV2Evaluator')
    elif args.integration:
        cmd.append('tests/test_meta_builder_v2.py::TestMetaBuilderV2API')
        cmd.append('tests/test_meta_builder_v2.py::TestMetaBuilderV2Integration')
    else:
        cmd.append('tests/')
    
    # Run tests
    success = run_command(cmd, 'Test Suite')
    
    if success:
        print("\n✅ All tests passed!")
        
        if args.coverage:
            print("\n📊 Coverage Summary:")
            if args.html_report:
                print("📁 HTML report generated in htmlcov/")
                print("🌐 Open htmlcov/index.html in your browser to view detailed coverage")
    else:
        print("\n❌ Some tests failed!")
        sys.exit(1)

if __name__ == '__main__':
    main()
