"""
Simple test to verify the testing framework setup
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

def test_sample_spec():
    """Test that we can create a sample specification."""
    spec_data = {
        "name": "Test CRM",
        "domain": "crm",
        "entities": [
            {
                "name": "Contact",
                "fields": [
                    {"name": "email", "type": "email", "unique": True},
                    {"name": "name", "type": "string", "required": True}
                ]
            }
        ]
    }
    
    assert spec_data["name"] == "Test CRM"
    assert spec_data["domain"] == "crm"
    assert len(spec_data["entities"]) == 1
    assert len(spec_data["entities"][0]["fields"]) == 2
    
    print("✅ Sample spec test passed")

def test_agent_roles():
    """Test agent role definitions."""
    agent_roles = [
        "product_architect",
        "system_designer", 
        "security_compliance",
        "codegen_engineer",
        "qa_evaluator",
        "auto_fixer",
        "devops",
        "reviewer"
    ]
    
    assert len(agent_roles) == 8
    assert "product_architect" in agent_roles
    assert "codegen_engineer" in agent_roles
    
    print("✅ Agent roles test passed")

def test_evaluation_criteria():
    """Test evaluation criteria structure."""
    criteria = [
        {"id": "A1", "text": "Create contact", "category": "functional"},
        {"id": "A2", "text": "User auth", "category": "security"},
        {"id": "A3", "text": "Payment processing", "category": "integration"}
    ]
    
    assert len(criteria) == 3
    assert criteria[0]["category"] == "functional"
    assert criteria[1]["category"] == "security"
    assert criteria[2]["category"] == "integration"
    
    print("✅ Evaluation criteria test passed")

if __name__ == "__main__":
    print("🧪 Running simple tests...")
    test_sample_spec()
    test_agent_roles()
    test_evaluation_criteria()
    print("🎉 All simple tests passed!")
