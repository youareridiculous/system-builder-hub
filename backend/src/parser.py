import json
import csv
import re
from pathlib import Path
from typing import Dict, Optional
from datetime import datetime
import hashlib

try:
    from PyPDF2 import PdfReader
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

try:
    import docx
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

def parse_txt(path: Path) -> str:
    """Parse plain text files"""
    return path.read_text(encoding='utf-8')

def parse_md(path: Path) -> str:
    """Parse markdown files"""
    return path.read_text(encoding='utf-8')

def parse_mdx(path: Path) -> str:
    """Parse MDX files (markdown with JSX)"""
    content = path.read_text(encoding='utf-8')
    # Remove JSX components but keep markdown
    content = re.sub(r'<[^>]+>', '', content)
    return content

def parse_json(path: Path) -> str:
    """Parse JSON files with pretty formatting"""
    data = json.loads(path.read_text(encoding='utf-8'))
    return json.dumps(data, indent=2)

def parse_csv(path: Path) -> str:
    """Parse CSV files to markdown table format"""
    content = path.read_text(encoding='utf-8')
    reader = csv.reader(content.splitlines())
    rows = list(reader)
    
    if not rows:
        return "Empty CSV file"
    
    # Convert to markdown table
    markdown = []
    for i, row in enumerate(rows):
        if i == 0:  # Header
            markdown.append("| " + " | ".join(row) + " |")
            markdown.append("| " + " | ".join(["---"] * len(row)) + " |")
        else:
            markdown.append("| " + " | ".join(row) + " |")
    
    return "\n".join(markdown)

def parse_rtf(path: Path) -> str:
    """Parse RTF files (basic text extraction)"""
    content = path.read_text(encoding='utf-8')
    # Remove RTF formatting codes
    content = re.sub(r'\\[a-z0-9-]+\d?', '', content)
    content = re.sub(r'\{[^}]*\}', '', content)
    content = re.sub(r'\s+', ' ', content)
    return content.strip()

def parse_docx(path: Path) -> str:
    """Parse DOCX files"""
    if not DOCX_AVAILABLE:
        raise ImportError("python-docx not installed. Run: pip install python-docx")
    
    doc = docx.Document(str(path))
    paragraphs = []
    for paragraph in doc.paragraphs:
        if paragraph.text.strip():
            paragraphs.append(paragraph.text)
    return "\n\n".join(paragraphs)

def parse_pdf(path: Path) -> str:
    """Parse PDF files"""
    if not PDF_AVAILABLE:
        raise ImportError("PyPDF2 not installed. Run: pip install PyPDF2")
    
    reader = PdfReader(str(path))
    text = "\n".join([page.extract_text() or "" for page in reader.pages])
    return text.strip()

def parse_code_file(path: Path) -> str:
    """Parse code files (Python, JavaScript, TypeScript, etc.)"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add file type comment for context
        file_type = path.suffix[1:].upper()
        return f"# {file_type} File: {path.name}\n\n{content}"
    except UnicodeDecodeError:
        # Try with different encoding
        with open(path, 'r', encoding='latin-1') as f:
            content = f.read()
        return f"# {path.suffix[1:].upper()} File: {path.name}\n\n{content}"

def parse_yaml(path: Path) -> str:
    """Parse YAML files"""
    try:
        import yaml
        with open(path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return f"# YAML File: {path.name}\n\n{json.dumps(data, indent=2)}"
    except ImportError:
        # Fallback to text parsing if PyYAML not available
        return parse_txt(path)

def parse_xml(path: Path) -> str:
    """Parse XML files"""
    try:
        import xml.etree.ElementTree as ET
        tree = ET.parse(path)
        root = tree.getroot()
        
        # Convert to readable format
        def element_to_text(element, indent=0):
            text = "  " * indent + f"<{element.tag}"
            if element.attrib:
                text += " " + " ".join([f'{k}="{v}"' for k, v in element.attrib.items()])
            text += ">"
            
            if element.text and element.text.strip():
                text += f" {element.text.strip()}"
            
            for child in element:
                text += "\n" + element_to_text(child, indent + 1)
            
            if element.tail and element.tail.strip():
                text += f" {element.tail.strip()}"
            
            text += f"</{element.tag}>"
            return text
        
        return f"# XML File: {path.name}\n\n{element_to_text(root)}"
    except Exception:
        # Fallback to text parsing
        return parse_txt(path)

def parse_shell_script(path: Path) -> str:
    """Parse shell scripts and configuration files"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add shebang and comments for context
        lines = content.split('\n')
        if lines and lines[0].startswith('#!'):
            shebang = lines[0]
            script_content = '\n'.join(lines[1:])
            return f"# Shell Script: {path.name}\n# {shebang}\n\n{script_content}"
        else:
            return f"# Configuration File: {path.name}\n\n{content}"
    except UnicodeDecodeError:
        with open(path, 'r', encoding='latin-1') as f:
            content = f.read()
        return f"# Configuration File: {path.name}\n\n{content}"

def generate_content_preview(content: str, max_length: int = 200) -> str:
    """Generate a preview/summary of content"""
    # Remove extra whitespace and get first few sentences
    cleaned = re.sub(r'\s+', ' ', content.strip())
    if len(cleaned) <= max_length:
        return cleaned
    
    # Try to break at sentence boundaries
    sentences = re.split(r'[.!?]+', cleaned)
    preview = ""
    for sentence in sentences:
        if len(preview + sentence) > max_length:
            break
        preview += sentence + ". "
    
    return preview.strip() or cleaned[:max_length] + "..."

def calculate_content_hash(content: str) -> str:
    """Calculate SHA-256 hash of content for change detection"""
    return hashlib.sha256(content.encode('utf-8')).hexdigest()[:16]

def parse_file(path: Path) -> Dict:
    """
    Enhanced file parser with metadata and content preview.
    Returns a dict with comprehensive file information.
    """
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
    
    ext = path.suffix.lower()
    timestamp = datetime.fromtimestamp(path.stat().st_mtime)
    
    # Parse content based on file type
    if ext == '.txt':
        content = parse_txt(path)
    elif ext == '.md':
        content = parse_md(path)
    elif ext == '.mdx':
        content = parse_mdx(path)
    elif ext == '.json':
        content = parse_json(path)
    elif ext == '.csv':
        content = parse_csv(path)
    elif ext == '.rtf':
        content = parse_rtf(path)
    elif ext == '.docx':
        content = parse_docx(path)
    elif ext == '.pdf':
        content = parse_pdf(path)
    elif ext in ['.yaml', '.yml']:
        content = parse_yaml(path)
    elif ext == '.xml':
        content = parse_xml(path)
    elif ext in ['.sh', '.bash', '.ps1', '.bat', '.ini', '.cfg', '.conf', '.env', '.properties']:
        content = parse_shell_script(path)
    elif ext in ['.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss', '.sass',
                 '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php', '.rb', '.go', '.rs',
                 '.swift', '.kt', '.scala', '.r', '.m', '.mm', '.pl', '.sql', '.graphql', '.gql']:
        content = parse_code_file(path)
    else:
        # Fallback to text parsing for unknown types
        content = parse_txt(path)

    # Generate metadata
    content_hash = calculate_content_hash(content)
    preview = generate_content_preview(content)
    
    return {
        'filename': path.name,
        'content': content,
        'metadata': {
            'file_path': str(path),
            'file_size': path.stat().st_size,
            'content_length': len(content),
            'content_hash': content_hash,
            'timestamp': timestamp.isoformat(),
            'file_type': ext[1:],  # Remove the dot
            'preview': preview
        }
    }

def get_supported_extensions() -> list[str]:
    """Get list of supported file extensions"""
    extensions = [
        # Text and Documentation
        '.txt', '.md', '.mdx', '.rst', '.adoc',
        
        # Data Formats
        '.json', '.yaml', '.yml', '.xml', '.csv', '.tsv',
        
        # Documents
        '.rtf', '.odt',
        
        # Code Files
        '.py', '.js', '.jsx', '.ts', '.tsx', '.html', '.css', '.scss', '.sass',
        '.java', '.cpp', '.c', '.h', '.hpp', '.cs', '.php', '.rb', '.go', '.rs',
        '.swift', '.kt', '.scala', '.r', '.m', '.mm', '.pl', '.sh', '.bash',
        '.ps1', '.bat', '.sql', '.graphql', '.gql',
        
        # Configuration
        '.ini', '.cfg', '.conf', '.toml', '.env', '.properties',
        
        # Markup
        '.htm', '.svg', '.tex', '.latex'
    ]
    
    # Add conditional extensions
    if PDF_AVAILABLE:
        extensions.append('.pdf')
    if DOCX_AVAILABLE:
        extensions.extend(['.docx', '.doc'])
    
    return extensions