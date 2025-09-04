#!/usr/bin/env python3
"""
Test Core Build Loop functionality
"""
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_imports():
    """Test that core modules can be imported"""
    print("Testing core module imports...")
    
    try:
        from ui_build import ui_build_bp
        print("✅ ui_build imported")
    except Exception as e:
        print(f"❌ ui_build failed: {e}")
    
    try:
        from ui_project_loader import ui_project_loader_bp
        print("✅ ui_project_loader imported")
    except Exception as e:
        print(f"❌ ui_project_loader failed: {e}")
    
    try:
        from ui_visual_builder import ui_visual_builder_bp
        print("✅ ui_visual_builder imported")
    except Exception as e:
        print(f"❌ ui_visual_builder failed: {e}")
    
    try:
        from ui_guided import ui_guided_bp
        print("✅ ui_guided imported")
    except Exception as e:
        print(f"❌ ui_guided failed: {e}")
    
    try:
        from templates_catalog import TEMPLATES
        print(f"✅ templates_catalog imported ({len(TEMPLATES)} templates)")
    except Exception as e:
        print(f"❌ templates_catalog failed: {e}")
    
    try:
        from features_catalog import FEATURES
        print(f"✅ features_catalog imported ({len(FEATURES)} features)")
    except Exception as e:
        print(f"❌ features_catalog failed: {e}")

def test_endpoints():
    """Test that endpoints would work"""
    print("\nTesting endpoint definitions...")
    
    try:
        from ui_build import ui_build_bp
        routes = [rule.rule for rule in ui_build_bp.url_map.iter_rules()]
        print(f"✅ ui_build routes: {routes}")
    except Exception as e:
        print(f"❌ ui_build routes failed: {e}")
    
    try:
        from ui_project_loader import ui_project_loader_bp
        routes = [rule.rule for rule in ui_project_loader_bp.url_map.iter_rules()]
        print(f"✅ ui_project_loader routes: {routes}")
    except Exception as e:
        print(f"❌ ui_project_loader routes failed: {e}")

def main():
    """Main test function"""
    print("🧪 Testing Core Build Loop Implementation")
    print("=" * 50)
    
    test_imports()
    test_endpoints()
    
    print("\n" + "=" * 50)
    print("✅ Core Build Loop test completed!")

if __name__ == '__main__':
    main()
