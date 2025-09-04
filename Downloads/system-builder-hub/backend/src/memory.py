from pathlib import Path
from typing import Dict, List, Optional
import re
import json
from datetime import datetime

# Enhanced patterns for better extraction
EXTRACTION_PATTERNS = {
    "reusable_logic": [
        r"reusable logic:?\s*(.*?)(?:\n\n|$)",
        r"code snippet:?\s*(.*?)(?:\n\n|$)",
        r"function:?\s*(.*?)(?:\n\n|$)",
        r"pattern:?\s*(.*?)(?:\n\n|$)",
        r"template:?\s*(.*?)(?:\n\n|$)",
        r"utility:?\s*(.*?)(?:\n\n|$)",
        r"helper:?\s*(.*?)(?:\n\n|$)"
    ],
    "wins": [
        r"breakthrough:?\s*(.*?)(?:\n\n|$)",
        r"win:?\s*(.*?)(?:\n\n|$)",
        r"success:?\s*(.*?)(?:\n\n|$)",
        r"achievement:?\s*(.*?)(?:\n\n|$)",
        r"solved:?\s*(.*?)(?:\n\n|$)",
        r"figured out:?\s*(.*?)(?:\n\n|$)"
    ],
    "bugs": [
        r"bug:?\s*(.*?)(?:\n\n|$)",
        r"pitfall:?\s*(.*?)(?:\n\n|$)",
        r"error:?\s*(.*?)(?:\n\n|$)",
        r"issue:?\s*(.*?)(?:\n\n|$)",
        r"problem:?\s*(.*?)(?:\n\n|$)",
        r"failed:?\s*(.*?)(?:\n\n|$)"
    ],
    "prompts": [
        r"prompt:?\s*(.*?)(?:\n\n|$)",
        r"idea:?\s*(.*?)(?:\n\n|$)",
        r"concept:?\s*(.*?)(?:\n\n|$)",
        r"thought:?\s*(.*?)(?:\n\n|$)",
        r"question:?\s*(.*?)(?:\n\n|$)",
        r"hypothesis:?\s*(.*?)(?:\n\n|$)"
    ],
    "guidelines": [
        r"lesson:?\s*(.*?)(?:\n\n|$)",
        r"guideline:?\s*(.*?)(?:\n\n|$)",
        r"rule:?\s*(.*?)(?:\n\n|$)",
        r"principle:?\s*(.*?)(?:\n\n|$)",
        r"best practice:?\s*(.*?)(?:\n\n|$)",
        r"tip:?\s*(.*?)(?:\n\n|$)"
    ]
}

# Subcategories for better organization
SUBCATEGORIES = {
    "prompts": {
        "brainstorm": ["brainstorm", "ideation", "creative", "exploration"],
        "clarification": ["clarify", "understand", "explain", "define"],
        "problem_solving": ["solve", "fix", "resolve", "debug"],
        "planning": ["plan", "strategy", "roadmap", "timeline"]
    },
    "reusable_logic": {
        "functions": ["function", "method", "def ", "func "],
        "patterns": ["pattern", "design", "architecture"],
        "utilities": ["utility", "helper", "tool", "helper"],
        "configurations": ["config", "setup", "configuration"]
    }
}

def categorize_item(item: str, category: str) -> Optional[str]:
    """Categorize an item into subcategories based on content"""
    if category not in SUBCATEGORIES:
        return None
    
    item_lower = item.lower()
    for subcat, keywords in SUBCATEGORIES[category].items():
        if any(keyword in item_lower for keyword in keywords):
            return subcat
    
    return None

def extract_section(content: str, category: str, patterns: List[str]) -> Dict[str, List[str]]:
    """Extract items from content and organize into subcategories"""
    matches = []
    for pattern in patterns:
        regex = re.compile(pattern, re.IGNORECASE | re.DOTALL)
        matches += regex.findall(content)
    
    # Clean and filter matches
    items = [match.strip() for match in matches if match.strip()]
    
    # Organize into subcategories
    categorized = {"general": []}
    
    for item in items:
        subcategory = categorize_item(item, category)
        if subcategory:
            if subcategory not in categorized:
                categorized[subcategory] = []
            categorized[subcategory].append(item)
        else:
            categorized["general"].append(item)
    
    return categorized

def format_section_with_subcategories(categorized_items: Dict[str, List[str]], section_title: str) -> str:
    """Format a section with subcategories"""
    if not any(categorized_items.values()):
        return f"## {section_title}\n- No items found\n\n"
    
    result = f"## {section_title}\n"
    
    # Add general items first
    if categorized_items.get("general"):
        result += "\n### General\n"
        for item in categorized_items["general"]:
            result += f"- {item}\n"
    
    # Add subcategories
    for subcat, items in categorized_items.items():
        if subcat != "general" and items:
            subcat_title = subcat.replace("_", " ").title()
            result += f"\n### {subcat_title}\n"
            for item in items:
                result += f"- {item}\n"
    
    return result + "\n"

def build_memory(parsed: Dict, output_path: Path, reprocess: bool = False) -> Dict:
    """
    Enhanced memory builder with subcategories and metadata.
    Returns processing metadata for tracking.
    """
    content = parsed['content']
    filename = parsed['filename']
    metadata = parsed.get('metadata', {})
    
    # Build memory content
    memory_md = f"# 🧠 Memory Summary for `{filename}`\n\n"
    
    # Add metadata section
    if metadata:
        memory_md += "## 📊 Metadata\n"
        memory_md += f"- **File Type**: {metadata.get('file_type', 'unknown')}\n"
        memory_md += f"- **File Size**: {metadata.get('file_size', 0)} bytes\n"
        memory_md += f"- **Content Length**: {metadata.get('content_length', 0)} characters\n"
        memory_md += f"- **Processed**: {datetime.now().isoformat()}\n"
        memory_md += f"- **Content Hash**: {metadata.get('content_hash', 'unknown')}\n"
        if metadata.get('preview'):
            memory_md += f"- **Preview**: {metadata['preview']}\n"
        memory_md += "\n"
    
    # Extract and format sections
    sections = {
        "🔁 Reusable Logic": extract_section(content, "reusable_logic", EXTRACTION_PATTERNS["reusable_logic"]),
        "🔥 Wins & Breakthroughs": extract_section(content, "wins", EXTRACTION_PATTERNS["wins"]),
        "🐛 Bugs & Pitfalls": extract_section(content, "bugs", EXTRACTION_PATTERNS["bugs"]),
        "💡 Prompts & Ideas": extract_section(content, "prompts", EXTRACTION_PATTERNS["prompts"]),
        "📚 Guidelines & Lessons": extract_section(content, "guidelines", EXTRACTION_PATTERNS["guidelines"])
    }
    
    # Format each section
    for section_title, categorized_items in sections.items():
        memory_md += format_section_with_subcategories(categorized_items, section_title)
    
    # Write to file
    output_path.write_text(memory_md.strip(), encoding='utf-8')
    
    # Return processing metadata
    processing_stats = {
        'filename': filename,
        'output_path': str(output_path),
        'processed_at': datetime.now().isoformat(),
        'reprocessed': reprocess,
        'sections': {
            title: sum(len(items) for items in categorized.values())
            for title, categorized in sections.items()
        },
        'total_items': sum(
            sum(len(items) for items in categorized.values())
            for categorized in sections.values()
        )
    }
    
    return processing_stats

def reprocess_memory_session(session_dir: Path) -> Dict:
    """Reprocess an existing memory session"""
    memory_file = session_dir / "memory.md"
    raw_file = session_dir / "raw_content.txt"
    
    if not memory_file.exists():
        raise FileNotFoundError(f"Memory file not found: {memory_file}")
    
    if not raw_file.exists():
        raise FileNotFoundError(f"Raw content file not found: {raw_file}")
    
    # Read the original raw content
    content = raw_file.read_text(encoding='utf-8')
    
    # Create parsed dict structure
    parsed = {
        'filename': session_dir.name,
        'content': content,
        'metadata': {
            'file_path': str(raw_file),
            'file_size': raw_file.stat().st_size,
            'content_length': len(content),
            'content_hash': calculate_content_hash(content),
            'timestamp': datetime.fromtimestamp(raw_file.stat().st_mtime).isoformat(),
            'file_type': 'txt',
            'preview': generate_content_preview(content)
        }
    }
    
    # Rebuild memory
    return build_memory(parsed, memory_file, reprocess=True)

def calculate_content_hash(content: str) -> str:
    """Calculate content hash for change detection"""
    import hashlib
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

def generate_content_preview(content: str, max_length: int = 200) -> str:
    """Generate content preview"""
    cleaned = re.sub(r'\s+', ' ', content.strip())
    if len(cleaned) <= max_length:
        return cleaned
    
    sentences = re.split(r'[.!?]+', cleaned)
    preview = ""
    for sentence in sentences:
        if len(preview + sentence) > max_length:
            break
        preview += sentence + ". "
    
    return preview.strip() or cleaned[:max_length] + "..."