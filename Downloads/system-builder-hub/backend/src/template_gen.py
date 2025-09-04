import os
import re
import json
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

TEMPLATE_DIR = Path(__file__).resolve().parent.parent.parent / "templates"
MEMORY_SESSIONS_DIR = Path(__file__).resolve().parent.parent.parent / "memory/SESSIONS"

# Ensure output dir exists
TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

# Enhanced signal patterns for better template detection
TEMPLATE_SIGNALS = {
    "code_patterns": [
        r"def\s+\w+\s*\([^)]*\):",
        r"class\s+\w+",
        r"function\s+\w+\s*\([^)]*\)",
        r"const\s+\w+\s*=",
        r"let\s+\w+\s*=",
        r"var\s+\w+\s*=",
        r"export\s+(default\s+)?(function|class|const)",
        r"import\s+.*\s+from",
        r"@\w+",  # Decorators
        r"async\s+function",
        r"async\s+def",
    ],
    "utility_patterns": [
        r"utility|helper|tool|util",
        r"helper\s+function",
        r"utility\s+function",
        r"common\s+pattern",
        r"reusable\s+code",
        r"template\s+for",
        r"boilerplate",
        r"setup\s+script",
        r"configuration",
        r"config\s+file",
    ],
    "problem_solving": [
        r"solve\s+.*\s+problem",
        r"fix\s+.*\s+issue",
        r"handle\s+.*\s+case",
        r"workaround\s+for",
        r"solution\s+to",
        r"pattern\s+for\s+.*",
        r"approach\s+to\s+.*",
    ]
}

def calculate_template_confidence(logic_text: str) -> float:
    """
    Calculate confidence score for template generation based on signal strength.
    Returns a score between 0 and 1.
    """
    score = 0.0
    logic_lower = logic_text.lower()
    
    # Check for code patterns
    code_matches = 0
    for pattern in TEMPLATE_SIGNALS["code_patterns"]:
        if re.search(pattern, logic_text, re.IGNORECASE):
            code_matches += 1
    score += min(code_matches * 0.2, 0.4)  # Max 0.4 for code patterns
    
    # Check for utility indicators
    utility_matches = 0
    for pattern in TEMPLATE_SIGNALS["utility_patterns"]:
        if re.search(pattern, logic_lower):
            utility_matches += 1
    score += min(utility_matches * 0.15, 0.3)  # Max 0.3 for utility patterns
    
    # Check for problem-solving context
    problem_matches = 0
    for pattern in TEMPLATE_SIGNALS["problem_solving"]:
        if re.search(pattern, logic_lower):
            problem_matches += 1
    score += min(problem_matches * 0.1, 0.2)  # Max 0.2 for problem context
    
    # Length bonus (longer, more detailed logic gets higher score)
    length_bonus = min(len(logic_text) / 1000, 0.1)  # Max 0.1 for length
    score += length_bonus
    
    return min(score, 1.0)

def generate_template_filename(logic_text: str, session_name: str) -> str:
    """Generate a descriptive filename for the template"""
    # Extract key words from logic text
    words = re.findall(r'\b\w+\b', logic_text.lower())
    # Filter out common words
    common_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be', 'been', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'can', 'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them'}
    key_words = [word for word in words if word not in common_words and len(word) > 2][:5]
    
    # Create filename
    if key_words:
        filename = '_'.join(key_words)
    else:
        filename = 'template'
    
    # Add session prefix for organization
    session_prefix = session_name.replace('-', '_')[:20]
    return f"{session_prefix}_{filename}.py"

def extract_templates_from_memory(memory_path: Path, session_name: str) -> List[Dict]:
    """Enhanced template extraction with confidence scoring and metadata"""
    if not memory_path.exists():
        return []

    content = memory_path.read_text(encoding='utf-8')
    logic_section = re.search(r"## 🔁 Reusable Logic\n(.+?)(?:\n##|$)", content, re.DOTALL)
    if not logic_section:
        return []

    lines = logic_section.group(1).strip().split("\n")
    templates = []
    
    # Group consecutive logic items
    current_logic = []
    
    for line in lines:
        if line.strip().startswith("- "):
            if current_logic:
                # Process the previous logic group
                logic_text = " ".join(current_logic)
                confidence = calculate_template_confidence(logic_text)
                
                if confidence > 0.3:  # Only generate templates with sufficient confidence
                    template_info = create_template_info(logic_text, session_name, confidence, memory_path)
                    templates.append(template_info)
            
            # Start new logic group
            current_logic = [line.strip("- ").strip()]
        elif line.strip() and current_logic:
            # Continue current logic group
            current_logic.append(line.strip())
    
    # Process the last logic group
    if current_logic:
        logic_text = " ".join(current_logic)
        confidence = calculate_template_confidence(logic_text)
        
        if confidence > 0.3:
            template_info = create_template_info(logic_text, session_name, confidence, memory_path)
            templates.append(template_info)
    
    return templates

def create_template_info(logic_text: str, session_name: str, confidence: float, memory_path: Path) -> Dict:
    """Create comprehensive template information"""
    filename = generate_template_filename(logic_text, session_name)
    
    # Extract key concepts for template content
    key_concepts = extract_key_concepts(logic_text)
    
    template_content = f'''"""
# Auto-generated template from memory
# Source Session: {session_name}
# Source File: {memory_path.name}
# Confidence Score: {confidence:.2f}
# Generated: {datetime.now().isoformat()}

# Key Concepts: {', '.join(key_concepts)}

# Original Logic: {logic_text[:200]}{'...' if len(logic_text) > 200 else ''}
"""

# TODO: Implement this logic based on the extracted patterns
# Consider the following approach:
{generate_implementation_guidance(logic_text)}

def main():
    """
    Main implementation of the extracted logic pattern.
    """
    pass

if __name__ == "__main__":
    main()
'''
    
    return {
        "name": filename,
        "content": template_content,
        "metadata": {
            "source_session": session_name,
            "source_file": str(memory_path),
            "confidence_score": confidence,
            "key_concepts": key_concepts,
            "original_logic": logic_text,
            "generated_at": datetime.now().isoformat(),
            "template_type": determine_template_type(logic_text)
        }
    }

def extract_key_concepts(logic_text: str) -> List[str]:
    """Extract key concepts from logic text"""
    # Simple keyword extraction
    words = re.findall(r'\b\w+\b', logic_text.lower())
    word_freq = {}
    
    for word in words:
        if len(word) > 3 and word not in ['this', 'that', 'with', 'from', 'they', 'have', 'will', 'been', 'were', 'said', 'each', 'which', 'their', 'time', 'would', 'there', 'could', 'other', 'about', 'many', 'then', 'them', 'these', 'some', 'what', 'just', 'know', 'take', 'into', 'year', 'your', 'good', 'some', 'could', 'them', 'see', 'other', 'than', 'then', 'now', 'look', 'only', 'come', 'over', 'think', 'also', 'back', 'after', 'work', 'first', 'well', 'way', 'even', 'new', 'want', 'because', 'any', 'these', 'give', 'day', 'most', 'us']:
            word_freq[word] = word_freq.get(word, 0) + 1
    
    # Return top 5 most frequent words
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    return [word for word, freq in sorted_words[:5]]

def generate_implementation_guidance(logic_text: str) -> str:
    """Generate implementation guidance based on logic content"""
    guidance = []
    logic_lower = logic_text.lower()
    
    if any(pattern in logic_lower for pattern in ['function', 'def ', 'func ']):
        guidance.append("# - Define a function with appropriate parameters")
        guidance.append("# - Consider error handling and edge cases")
    
    if any(pattern in logic_lower for pattern in ['class', 'object']):
        guidance.append("# - Create a class with relevant methods")
        guidance.append("# - Define proper initialization and attributes")
    
    if any(pattern in logic_lower for pattern in ['api', 'request', 'http']):
        guidance.append("# - Implement API calls with proper error handling")
        guidance.append("# - Consider rate limiting and authentication")
    
    if any(pattern in logic_lower for pattern in ['database', 'db', 'sql']):
        guidance.append("# - Set up database connection and queries")
        guidance.append("# - Implement proper data validation")
    
    if any(pattern in logic_lower for pattern in ['file', 'read', 'write']):
        guidance.append("# - Handle file operations with proper error handling")
        guidance.append("# - Consider file permissions and paths")
    
    if not guidance:
        guidance.append("# - Analyze the original logic and implement accordingly")
        guidance.append("# - Add proper documentation and error handling")
    
    return "\n".join(guidance)

def determine_template_type(logic_text: str) -> str:
    """Determine the type of template based on content"""
    logic_lower = logic_text.lower()
    
    if any(pattern in logic_lower for pattern in ['api', 'request', 'http', 'endpoint']):
        return 'api_endpoint'
    elif any(pattern in logic_lower for pattern in ['database', 'db', 'sql', 'query']):
        return 'database'
    elif any(pattern in logic_lower for pattern in ['file', 'read', 'write', 'io']):
        return 'file_operation'
    elif any(pattern in logic_lower for pattern in ['class', 'object', 'model']):
        return 'class_template'
    elif any(pattern in logic_lower for pattern in ['function', 'utility', 'helper']):
        return 'utility_function'
    elif any(pattern in logic_lower for pattern in ['config', 'setup', 'init']):
        return 'configuration'
    else:
        return 'general'

def generate_templates_from_all_sessions() -> Dict:
    """Generate templates from all memory sessions with comprehensive reporting"""
    session_dirs = [p for p in MEMORY_SESSIONS_DIR.glob("*") if p.is_dir()]
    created = []
    skipped = []
    errors = []
    
    total_confidence = 0
    total_templates = 0
    
    for session in session_dirs:
        memory_file = session / "memory.md"
        
        if not memory_file.exists():
            continue
            
        try:
            templates = extract_templates_from_memory(memory_file, session.name)
            
            for tpl in templates:
                tpl_path = TEMPLATE_DIR / tpl['name']
                
                if tpl_path.exists():
                    skipped.append({
                        'name': tpl['name'],
                        'reason': 'Template already exists',
                        'session': session.name
                    })
                    continue
                
                # Write template file
                tpl_path.write_text(tpl['content'], encoding='utf-8')
                
                # Save metadata
                metadata_path = TEMPLATE_DIR / f"{tpl['name']}.meta.json"
                with open(metadata_path, 'w', encoding='utf-8') as f:
                    json.dump(tpl['metadata'], f, indent=2, ensure_ascii=False)
                
                created.append({
                    'name': tpl['name'],
                    'session': session.name,
                    'confidence': tpl['metadata']['confidence_score'],
                    'type': tpl['metadata']['template_type']
                })
                
                total_confidence += tpl['metadata']['confidence_score']
                total_templates += 1
                
        except Exception as e:
            errors.append({
                'session': session.name,
                'error': str(e)
            })
    
    avg_confidence = total_confidence / total_templates if total_templates > 0 else 0
    
    return {
        'created': created,
        'skipped': skipped,
        'errors': errors,
        'stats': {
            'total_created': len(created),
            'total_skipped': len(skipped),
            'total_errors': len(errors),
            'average_confidence': avg_confidence,
            'sessions_processed': len(session_dirs)
        }
    }

def get_template_metadata(template_name: str) -> Optional[Dict]:
    """Get metadata for a specific template"""
    metadata_path = TEMPLATE_DIR / f"{template_name}.meta.json"
    if metadata_path.exists():
        with open(metadata_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

if __name__ == "__main__":
    results = generate_templates_from_all_sessions()
    
    print(f"✅ Generated {results['stats']['total_created']} new templates.")
    print(f"⏭️  Skipped {results['stats']['total_skipped']} existing templates.")
    print(f"❌ {results['stats']['total_errors']} errors encountered.")
    print(f"📊 Average confidence: {results['stats']['average_confidence']:.2f}")
    
    if results['created']:
        print("\n📝 Created templates:")
        for tpl in results['created']:
            print(f" - {tpl['name']} (confidence: {tpl['confidence']:.2f}, type: {tpl['type']})")
    
    if results['errors']:
        print("\n❌ Errors:")
        for error in results['errors']:
            print(f" - {error['session']}: {error['error']}")